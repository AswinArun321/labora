"""
Asynchronous execution tasks for LABORA.
"""
import base64
import logging
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


def _get_judge0_headers():
    headers = {"Content-Type": "application/json"}
    if getattr(settings, "JUDGE0_RAPIDAPI_HOST", ""):
        headers["X-RapidAPI-Key"] = settings.JUDGE0_API_KEY
        headers["X-RapidAPI-Host"] = settings.JUDGE0_RAPIDAPI_HOST
    elif getattr(settings, "JUDGE0_API_KEY", ""):
        headers["X-Auth-Token"] = settings.JUDGE0_API_KEY
    return headers


def _finalize_completed_execution(ex, result):
    from labs.models import ActivityEvent

    status_dict = result.get("status") or {}
    desc = status_dict.get("description", "Unknown")

    ex.status = desc
    ex.state = ex.State.COMPLETED
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


def _mark_timed_out(ex, error_msg="Execution timed out waiting for sandbox worker."):
    from labs.models import ActivityEvent

    ex.state = ex.State.TIMED_OUT
    ex.status = "Time Limit Exceeded"
    ex.stderr = error_msg
    ex.completed_at = timezone.now()
    ex.save(update_fields=["state", "status", "stderr", "completed_at"])

    ActivityEvent.objects.create(
        submission=ex.submission,
        kind=ActivityEvent.Kind.RUN,
        detail={"status": "Time Limit Exceeded", "timeout": True}
    )


def _schedule_poll_retry(execution_id, interval, eager_max_polls):
    if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
        if eager_max_polls > 1:
            poll_execution_task.apply_async(
                args=[execution_id, interval, eager_max_polls - 1],
                countdown=interval
            )
    else:
        poll_execution_task.apply_async(
            args=[execution_id, interval],
            countdown=interval
        )


@shared_task(
    bind=True,
    max_retries=3,
    default_retry_delay=3,
    name="labs.tasks.dispatch_execution_task"
)
def dispatch_execution_task(self, execution_id: int):
    """
    Asynchronously executes untrusted student code using Judge0 or the local runner.
    For Judge0:
      1. Dispatches code to Judge0 with wait=false.
      2. Records the submission token and sets state to PROCESSING.
      3. Schedules a non-blocking poll task and exits immediately (freeing worker threads).
    """
    from labs.models import Execution, ActivityEvent

    try:
        ex = Execution.objects.select_related("submission__practical", "submission__student").get(pk=execution_id)
    except Execution.DoesNotExist:
        logger.error(f"[Execution {execution_id}] Record not found.")
        return False

    # Guard against duplicate delivery
    if ex.is_complete:
        logger.info(f"[Execution {execution_id}] Already complete ({ex.state}). Skipping dispatch.")
        return True

    # If already processing with token, avoid re-dispatching; resume polling
    if ex.state == Execution.State.PROCESSING and ex.judge0_token:
        logger.info(f"[Execution {execution_id}] Already dispatched with token {ex.judge0_token}. Resuming poll.")
        poll_execution_task.apply_async(args=[ex.id], countdown=0.5)
        return True

    # Ambiguous dispatch outcome guard
    if ex.state == Execution.State.SUBMITTED_TO_RUNNER:
        if ex.judge0_token:
            ex.state = Execution.State.PROCESSING
            ex.save(update_fields=["state"])
            poll_execution_task.apply_async(args=[ex.id], countdown=0.5)
            return True
        logger.warning(f"[Execution {execution_id}] Ambiguous dispatch in progress without token. Awaiting reconciliation.")
        return False

    practical = ex.submission.practical
    language = practical.language
    code = ex.code
    stdin = ex.stdin

    ex.state = Execution.State.DISPATCHING
    if not ex.started_at:
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
    headers = _get_judge0_headers()
    cpu_limit = getattr(settings, "EXECUTION_TIMEOUT_SECONDS", 5)
    dispatch_timeout = getattr(settings, "JUDGE0_DISPATCH_TIMEOUT_SECONDS", 10.0)

    payload = {
        "language_id": lang_id,
        "source_code": _b64(code),
        "stdin": _b64(stdin),
        "cpu_time_limit": cpu_limit,
    }

    judge0_url = settings.JUDGE0_URL.rstrip("/")
    submit_url = f"{judge0_url}/submissions?base64_encoded=true&wait=false"

    try:
        resp = requests.post(submit_url, json=payload, headers=headers, timeout=dispatch_timeout)
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

        initial_interval = getattr(settings, "EXECUTION_POLL_INITIAL_INTERVAL_SECONDS", 0.5)
        poll_execution_task.apply_async(args=[ex.id, initial_interval], countdown=initial_interval)
        return True

    except requests.exceptions.Timeout as exc:
        logger.warning(f"[Execution {execution_id}] Ambiguous dispatch timeout to Judge0: {exc}")
        ex.state = Execution.State.SUBMITTED_TO_RUNNER
        ex.retry_count += 1
        ex.last_error = f"Ambiguous dispatch timeout: {exc}"
        ex.save(update_fields=["state", "retry_count", "last_error"])
        # Do not blindly retry POST or fail; let reconciliation handle or student re-check
        return False

    except requests.exceptions.RequestException as exc:
        logger.warning(f"[Execution {execution_id}] Failed to dispatch to Judge0: {exc}")
        ex.retry_count += 1
        ex.last_error = f"Runner dispatch error: {exc}"
        if ex.retry_count >= 3:
            ex.state = Execution.State.FAILED
            ex.status = "System Error"
            ex.completed_at = timezone.now()
            ex.save(update_fields=["state", "status", "retry_count", "last_error", "completed_at"])
            return False
        ex.save(update_fields=["retry_count", "last_error"])
        raise self.retry(exc=exc)

    except Exception as exc:
        logger.exception(f"[Execution {execution_id}] Unexpected error during dispatch: {exc}")
        ex.state = Execution.State.FAILED
        ex.status = "System Error"
        ex.last_error = f"Internal dispatch error: {exc}"
        ex.completed_at = timezone.now()
        ex.save(update_fields=["state", "status", "last_error", "completed_at"])
        return False


@shared_task(
    bind=True,
    max_retries=10,
    default_retry_delay=1,
    name="labs.tasks.poll_execution_task"
)
def poll_execution_task(self, execution_id: int, current_interval: float = None, eager_max_polls: int = 10):
    """
    Non-blocking polling task for an individual execution.
    Fetches status from Judge0 without holding worker slots across poll waits.
    Reschedules itself with exponential backoff until terminal status or deadline is reached.
    """
    from labs.models import Execution

    try:
        ex = Execution.objects.select_related("submission__practical", "submission__student").get(pk=execution_id)
    except Execution.DoesNotExist:
        logger.error(f"[Poll {execution_id}] Execution record not found.")
        return False

    if ex.is_complete:
        logger.info(f"[Poll {execution_id}] Already terminal ({ex.state}). Skipping poll.")
        return True

    if not ex.judge0_token:
        logger.error(f"[Poll {execution_id}] No runner token present for polling.")
        ex.state = Execution.State.FAILED
        ex.status = "System Error"
        ex.last_error = "No runner token for polling"
        ex.completed_at = timezone.now()
        ex.save(update_fields=["state", "status", "last_error", "completed_at"])
        return False

    poll_timeout_seconds = getattr(settings, "EXECUTION_POLL_TIMEOUT_SECONDS", 30)
    start_time = ex.started_at or ex.created_at or timezone.now()
    elapsed = (timezone.now() - start_time).total_seconds()

    judge0_url = (ex.runner_url or getattr(settings, "JUDGE0_URL", "http://localhost:2358")).rstrip("/")
    poll_url = f"{judge0_url}/submissions/{ex.judge0_token}?base64_encoded=true"
    headers = _get_judge0_headers()

    initial_interval = getattr(settings, "EXECUTION_POLL_INITIAL_INTERVAL_SECONDS", 0.5)
    max_interval = getattr(settings, "EXECUTION_POLL_MAX_INTERVAL_SECONDS", 2.0)
    if current_interval is None:
        current_interval = initial_interval
    next_interval = min(current_interval * 1.25, max_interval)

    is_deadline_passed = elapsed >= poll_timeout_seconds

    try:
        status_resp = requests.get(poll_url, headers=headers, timeout=5)
        if status_resp.status_code == 200:
            result = status_resp.json()
            status_id = (result.get("status") or {}).get("id", 1)

            # Status 1 = In Queue, 2 = Processing
            if status_id not in (1, 2):
                _finalize_completed_execution(ex, result)
                return True

            desc = (result.get("status") or {}).get("description", "In Queue")
            if ex.status != desc:
                ex.status = desc
                ex.save(update_fields=["status"])

            if is_deadline_passed:
                _mark_timed_out(ex)
                return False

            _schedule_poll_retry(ex.id, next_interval, eager_max_polls)
            return None

        elif status_resp.status_code == 404:
            logger.error(f"[Poll {execution_id}] Judge0 returned 404 for token {ex.judge0_token}")
            ex.state = Execution.State.FAILED
            ex.status = "System Error"
            ex.last_error = f"Submission token {ex.judge0_token} not found on runner."
            ex.completed_at = timezone.now()
            ex.save(update_fields=["state", "status", "last_error", "completed_at"])
            return False

        else:
            logger.warning(f"[Poll {execution_id}] Unexpected HTTP {status_resp.status_code} from runner.")
            if is_deadline_passed:
                _mark_timed_out(ex)
                return False
            _schedule_poll_retry(ex.id, next_interval, eager_max_polls)
            return None

    except requests.RequestException as poll_err:
        logger.warning(f"[Poll {execution_id}] Poll network error: {poll_err}")
        if is_deadline_passed:
            _mark_timed_out(ex, error_msg=str(poll_err))
            return False
        _schedule_poll_retry(ex.id, next_interval, eager_max_polls)
        return None


@shared_task(name="labs.tasks.reconcile_stale_executions")
def reconcile_stale_executions(stale_threshold_seconds: int = 180):
    """
    Periodic reconciliation task to safely recover or terminate stalled executions.
    - PROCESSING with judge0_token: resumes polling.
    - SUBMITTED_TO_RUNNER with judge0_token: sets state to PROCESSING and resumes polling.
    - DISPATCHING or SUBMITTED_TO_RUNNER without token older than threshold: marks FAILED.
    - QUEUED older than threshold: marks FAILED.
    Avoids duplicate execution by never re-dispatching code to Judge0.
    """
    from labs.models import Execution
    now = timezone.now()
    threshold = now - timezone.timedelta(seconds=stale_threshold_seconds)

    stale_executions = Execution.objects.filter(
        state__in=[
            Execution.State.QUEUED,
            Execution.State.DISPATCHING,
            Execution.State.SUBMITTED_TO_RUNNER,
            Execution.State.PROCESSING,
        ],
        created_at__lt=threshold,
    )

    reconciled_count = 0
    resumed_count = 0
    failed_count = 0

    for ex in stale_executions:
        if ex.is_complete:
            continue

        if ex.state == Execution.State.PROCESSING and ex.judge0_token:
            logger.info(f"[Reconciliation] Resuming poll for execution {ex.id} with token {ex.judge0_token}")
            poll_execution_task.delay(ex.id)
            resumed_count += 1
            reconciled_count += 1

        elif ex.state == Execution.State.SUBMITTED_TO_RUNNER and ex.judge0_token:
            ex.state = Execution.State.PROCESSING
            ex.save(update_fields=["state"])
            poll_execution_task.delay(ex.id)
            resumed_count += 1
            reconciled_count += 1

        elif ex.state in (Execution.State.DISPATCHING, Execution.State.SUBMITTED_TO_RUNNER) and not ex.judge0_token:
            logger.warning(f"[Reconciliation] Failing ambiguous execution {ex.id} without token after threshold")
            ex.state = Execution.State.FAILED
            ex.status = "System Error"
            ex.last_error = "Execution dispatch interrupted before runner token confirmation."
            ex.completed_at = now
            ex.save(update_fields=["state", "status", "last_error", "completed_at"])
            failed_count += 1
            reconciled_count += 1

        elif ex.state == Execution.State.QUEUED:
            logger.warning(f"[Reconciliation] Stale queued execution {ex.id} failed after broker timeout")
            ex.state = Execution.State.FAILED
            ex.status = "System Error"
            ex.last_error = "Execution queued but never picked up by worker."
            ex.completed_at = now
            ex.save(update_fields=["state", "status", "last_error", "completed_at"])
            failed_count += 1
            reconciled_count += 1

    return {"reconciled": reconciled_count, "resumed": resumed_count, "failed": failed_count}
