"""
Asynchronous execution tasks for LABORA.
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
    default_retry_delay=3,
    name="labs.tasks.dispatch_execution_task"
)
def dispatch_execution_task(self, execution_id: int):
    """
    Asynchronously executes untrusted student code using Judge0 or the local runner.
    Updates the execution record's state, status, timing, and outputs.
    """
    from labs.models import Execution, ActivityEvent

    try:
        ex = Execution.objects.select_related("submission__practical", "submission__student").get(pk=execution_id)
    except Execution.DoesNotExist:
        logger.error(f"[Execution {execution_id}] Record not found.")
        return False

    practical = ex.submission.practical
    language = practical.language
    code = ex.code
    stdin = ex.stdin

    ex.state = Execution.State.DISPATCHING
    ex.started_at = timezone.now()
    ex.save(update_fields=["state", "started_at"])

    # ---------------------------------------------------------------------------
    # Local Development Runner (when CODE_EXECUTOR == "local")
    # ---------------------------------------------------------------------------
    if getattr(settings, "CODE_EXECUTOR", "judge0") == "local":
        from labs.executor import run_local
        try:
            res = run_local(language, code, stdin)
            ex.stdout = res.stdout[:50_000]
            ex.stderr = res.stderr[:20_000]
            ex.compile_output = res.compile_output[:20_000]
            ex.status = res.status
            ex.state = Execution.State.COMPLETED
            ex.time = str(res.time)
            ex.memory = res.memory
            ex.completed_at = timezone.now()
            ex.save()

            ActivityEvent.objects.create(
                submission=ex.submission,
                kind=ActivityEvent.Kind.RUN,
                detail={"status": res.status, "async": True}
            )
            return True
        except Exception as err:
            logger.exception(f"[Execution {execution_id}] Local execution error: {err}")
            ex.state = Execution.State.FAILED
            ex.status = "System Error"
            ex.last_error = str(err)
            ex.completed_at = timezone.now()
            ex.save()
            return False

    # ---------------------------------------------------------------------------
    # Production Judge0 Asynchronous Execution (wait=false)
    # ---------------------------------------------------------------------------
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

        ex.judge0_token = token
        ex.runner_url = judge0_url
        ex.state = Execution.State.PROCESSING
        ex.status = "In Queue"
        ex.save(update_fields=["judge0_token", "runner_url", "state", "status"])

    except requests.RequestException as exc:
        logger.warning(f"[Execution {execution_id}] Failed to dispatch to Judge0: {exc}")
        ex.retry_count += 1
        ex.last_error = f"Runner dispatch error: {exc}"
        if ex.retry_count >= 3:
            ex.state = Execution.State.FAILED
            ex.status = "System Error"
            ex.completed_at = timezone.now()
        ex.save()
        raise self.retry(exc=exc)

    # Poll Judge0 for result
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
                    desc = (result.get("status") or {}).get("description", "Unknown")
                    ex.status = desc
                    ex.state = Execution.State.COMPLETED
                    ex.stdout = _unb64(result.get("stdout"))[:50_000]
                    ex.stderr = _unb64(result.get("stderr"))[:20_000]
                    ex.compile_output = _unb64(result.get("compile_output"))[:20_000]
                    ex.time = str(result.get("time") or "")
                    ex.memory = result.get("memory")
                    ex.completed_at = timezone.now()
                    ex.save()

                    ActivityEvent.objects.create(
                        submission=ex.submission,
                        kind=ActivityEvent.Kind.RUN,
                        detail={"status": desc, "time": ex.time, "async": True}
                    )
                    return True

            time.sleep(poll_interval)
            poll_interval = min(poll_interval * 1.25, 2.0)
        except requests.RequestException as poll_err:
            logger.warning(f"[Execution {execution_id}] Poll error: {poll_err}")
            time.sleep(1.0)

    # Exceeded polling timeout
    ex.state = Execution.State.TIMED_OUT
    ex.status = "Time Limit Exceeded"
    ex.stderr = "Execution timed out waiting for sandbox worker."
    ex.completed_at = timezone.now()
    ex.save()

    ActivityEvent.objects.create(
        submission=ex.submission,
        kind=ActivityEvent.Kind.RUN,
        detail={"status": "Time Limit Exceeded", "timeout": True}
    )
    return False
