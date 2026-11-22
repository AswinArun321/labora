"""
LABORA Asynchronous Workspace Execution API Views

Provides non-blocking endpoints for student code execution:
1. POST /api/workspace/<id>/run-async/  -> Enqueues job and returns HTTP 202
2. GET  /api/workspace/<id>/executions/<execution_id>/ -> Returns current job status
"""
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle
from rest_framework.exceptions import PermissionDenied, ValidationError

from accounts.permissions import IsStudent
from labs.models import CodeVersion, Execution, Practical, Submission
from labs.serializers import ExecutionSerializer
from labs.views import clean_code, ensure_editable, get_student_practical, get_submission, MAX_STDIN_CHARS

try:
    from .tasks import dispatch_execution_task
except ImportError:
    from production_kit.backend_async.tasks import dispatch_execution_task


class AsyncRunThrottle(UserRateThrottle):
    scope = "run"
    rate = "30/min"


@api_view(["POST"])
@permission_classes([IsStudent])
@throttle_classes([AsyncRunThrottle])
def workspace_run_async(request, practical_id: int):
    """
    Non-blocking code execution. Immediately creates a persistent Execution record
    with status 'QUEUED' and dispatches a background task to Celery.
    """
    practical = get_student_practical(request, practical_id)
    submission = get_submission(request, practical)
    ensure_editable(submission)

    code = clean_code(request.data, "code")
    stdin = clean_code(request.data, "stdin", MAX_STDIN_CHARS)

    # Save code to submission and version history
    submission.code = code
    submission.save(update_fields=["code", "updated_at"])

    last_ver = submission.versions.order_by("-number").first()
    ver_num = (last_ver.number + 1) if last_ver else 1
    CodeVersion.objects.create(
        submission=submission,
        number=ver_num,
        code=code,
        reason=CodeVersion.Reason.RUN
    )

    # Create persistent execution record prior to background dispatch
    execution = Execution.objects.create(
        submission=submission,
        code=code,
        stdin=stdin,
        status="QUEUED"
    )

    # Dispatch Celery background task
    dispatch_execution_task.delay(execution.id)

    return Response({
        "execution_id": execution.id,
        "status": "QUEUED",
        "created_at": execution.created_at,
        "poll_url": f"/api/workspace/{practical_id}/executions/{execution.id}/"
    }, status=status.HTTP_202_ACCEPTED)


@api_view(["GET"])
@permission_classes([IsStudent])
def workspace_execution_status(request, practical_id: int, execution_id: int):
    """
    Polls the current status of an asynchronous execution request.
    Returns full stdout, stderr, and status once finished.
    """
    practical = get_student_practical(request, practical_id)
    submission = get_submission(request, practical)

    try:
        ex = Execution.objects.get(pk=execution_id, submission=submission)
    except Execution.DoesNotExist:
        return Response({"detail": "Execution not found."}, status=status.HTTP_404_NOT_FOUND)

    is_complete = ex.status not in ("QUEUED", "DISPATCHING", "PROCESSING")

    return Response({
        "id": ex.id,
        "status": ex.status,
        "is_complete": is_complete,
        "stdout": ex.stdout if is_complete else "",
        "stderr": ex.stderr if is_complete else "",
        "compile_output": ex.compile_output if is_complete else "",
        "time": ex.time if is_complete else "",
        "memory": ex.memory if is_complete else None,
        "created_at": ex.created_at,
    })
