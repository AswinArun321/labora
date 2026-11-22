"""
LABORA Production Asynchronous Code Execution Engine (Celery Tasks)

Solves the 1,000 concurrent user scaling bottleneck identified in plann.md:
- Replaces synchronous request-blocking execution with non-blocking Celery dispatch.
- Uses Judge0 asynchronous API (wait=false) with token tracking.
- Implements resilient result reconciliation, timeouts, and state persistence.
"""
import base64
import logging
import time
import requests
from celery import shared_task
from django.conf import settings
from django.utils import timezone

logger = logging.getLogger("labora.execution")


def _b64(s: str) -> str:
    return base64.b64encode((s or "").encode()).decode()


def _unb64(s):
    if not s:
        return ""
    return base64.b64decode(s).decode(errors="replace")


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=5,
    rate_limit="120/m",
    name="labora.tasks.dispatch_execution_task"
)
def dispatch_execution_task(self, execution_id: int):
    """
    Asynchronously dispatches an execution job to Judge0 or local runner,
    polls for status asynchronously, and updates the database record.
    """
    from labs.models import Execution, ActivityEvent

    try:
        ex = Execution.objects.select_related("submission__practical").get(pk=execution_id)
    except Execution.DoesNotExist:
        logger.error(f"[Execution {execution_id}] Execution record not found.")
        return False

    practical = ex.submission.practical
    language = practical.language
    code = ex.code
    stdin = ex.stdin

    # Mark as dispatching
    ex.status = "DISPATCHING"
    ex.save(update_fields=["status"])

    # Development fallback if local mode is explicitly configured
    if getattr(settings, "CODE_EXECUTOR", "judge0") == "local":
        from labs.executor import run_local
        try:
            res = run_local(language, code, stdin)
            ex.stdout = res.stdout[:50_000]
            ex.stderr = res.stderr[:20_000]
            ex.compile_output = res.compile_output[:20_000]
            ex.status = res.status
            ex.time = str(res.time)
            ex.memory = res.memory
            ex.save()
            ActivityEvent.objects.create(
                submission=ex.submission,
                kind=ActivityEvent.Kind.RUN,
                detail={"status": res.status, "async": True}
            )
            return True
        except Exception as err:
            ex.status = "FAILED"
            ex.stderr = f"Local executor error: {err}"
            ex.save()
            return False

    # Production Judge0 Asynchronous Workflow (wait=false)
    lang_id = settings.JUDGE0_LANGUAGE_IDS.get(language, 71)
    headers = {"Content-Type": "application/json"}
    if getattr(settings, "JUDGE0_RAPIDAPI_HOST", ""):
        headers["X-RapidAPI-Key"] = settings.JUDGE0_API_KEY
        headers["X-RapidAPI-Host"] = settings.JUDGE0_RAPIDAPI_HOST
    elif getattr(settings, "JUDGE0_API_KEY", ""):
        headers["X-Auth-Token"] = settings.JUDGE0_API_KEY

    payload = {
        "language_id": lang_id,
        "source_code": _b64(code),
        "stdin": _b64(stdin),
        "cpu_time_limit": getattr(settings, "EXECUTION_TIMEOUT_SECONDS", 5),
    }

    judge0_url = settings.JUDGE0_URL.rstrip("/")
    submit_url = f"{judge0_url}/submissions?base64_encoded=true&wait=false"

    try:
        resp = requests.post(submit_url, json=payload, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()
        token = data.get("token")
        if not token:
            raise ValueError(f"Judge0 did not return a submission token: {resp.text}")

        ex.status = "PROCESSING"
        if hasattr(ex, "judge0_token"):
            ex.judge0_token = token
        ex.save()

    except requests.RequestException as exc:
        logger.warning(f"[Execution {execution_id}] Failed to dispatch to Judge0: {exc}")
        ex.status = "FAILED"
        ex.stderr = f"Could not reach code execution runner: {exc}"
        ex.save()
        raise self.retry(exc=exc)

    # Poll Judge0 with exponential backoff up to timeout
    poll_url = f"{judge0_url}/submissions/{token}?base64_encoded=true"
    max_wait_seconds = int(getattr(settings, "EXECUTION_TIMEOUT_SECONDS", 5)) + 15
    start_time = time.time()
    poll_interval = 0.5

    while time.time() - start_time < max_wait_seconds:
        try:
            status_resp = requests.get(poll_url, headers=headers, timeout=5)
            if status_resp.status_code == 200:
                result = status_resp.json()
                status_id = (result.get("status") or {}).get("id", 1)

                # Status 1 = In Queue, 2 = Processing
                if status_id not in (1, 2):
                    # Completed execution
                    desc = (result.get("status") or {}).get("description", "Unknown")
                    ex.status = desc
                    ex.stdout = _unb64(result.get("stdout"))[:50_000]
                    ex.stderr = _unb64(result.get("stderr"))[:20_000]
                    ex.compile_output = _unb64(result.get("compile_output"))[:20_000]
                    ex.time = str(result.get("time") or "")
                    ex.memory = result.get("memory")
                    ex.save()

                    # Record run event
                    ActivityEvent.objects.create(
                        submission=ex.submission,
                        kind=ActivityEvent.Kind.RUN,
                        detail={"status": desc, "time": ex.time, "async": True}
                    )
                    logger.info(f"[Execution {execution_id}] Completed with status '{desc}'.")
                    return True

            time.sleep(poll_interval)
            poll_interval = min(poll_interval * 1.25, 2.0)
        except requests.RequestException as poll_err:
            logger.warning(f"[Execution {execution_id}] Poll error: {poll_err}")
            time.sleep(1.0)

    # Exceeded polling timeout
    ex.status = "Time Limit Exceeded"
    ex.stderr = "Execution timed out waiting for sandbox worker."
    ex.save()
    ActivityEvent.objects.create(
        submission=ex.submission,
        kind=ActivityEvent.Kind.RUN,
        detail={"status": "Time Limit Exceeded", "timeout": True}
    )
    return False
