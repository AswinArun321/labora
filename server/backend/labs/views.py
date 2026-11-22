import logging
import os
import re
import shutil
import tempfile
import time
from contextlib import contextmanager
from datetime import datetime, timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Count
from django.http import FileResponse, HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view, permission_classes, throttle_classes
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import UserRateThrottle

logger = logging.getLogger("labora.labs")



from accounts.models import Subject, User

from accounts.permissions import IsStudent, IsTeacherOrAdmin



from . import records

from .ai_review import AIUnavailable, ai_enabled, summarize_submission

from .executor import ExecutorError, run_code

from .indicators import compute_indicators

from .models import ActivityEvent, CodeVersion, Execution, Practical, Submission

from .secure_browser import is_secure_browser_request

from .serializers import (EventSerializer, ExecutionSerializer, PracticalSerializer, StudentPracticalSerializer,

                          SubmissionSerializer, VersionSerializer)



MAX_CODE_CHARS = 100_000

MAX_STDIN_CHARS = 20_000





class RunThrottle(UserRateThrottle):

    scope = "run"





# ---------------------------------------------------------------------------

# helpers

# ---------------------------------------------------------------------------

def teacher_can_access_subject(user, subject: Subject) -> bool:

    return user.is_admin_role or subject.teachers.filter(pk=user.pk).exists()





def get_student_practical(request, practical_id) -> Practical:

    p = get_object_or_404(Practical.objects.select_related("subject"), pk=practical_id, is_published=True)

    if not p.subject.students.filter(pk=request.user.pk).exists():

        raise PermissionDenied("You are not enrolled in this subject.")

    if p.require_secure_browser and not is_secure_browser_request(request):

        raise PermissionDenied({"detail": "This practical can only be opened in the LABORA Secure Browser.",

                                "code": "secure_browser_required"})

    return p





def get_submission(request, practical) -> Submission:

    sub, created = Submission.objects.get_or_create(

        practical=practical, student=request.user, defaults={"code": practical.starter_code}

    )

    return sub





def add_version(sub: Submission, code: str, reason: str):

    last = sub.versions.order_by("-number").first()

    if last and last.code == code:

        return last

    return CodeVersion.objects.create(submission=sub, number=(last.number + 1 if last else 1), code=code,

                                      reason=reason)





def clean_code(data, key="code", limit=MAX_CODE_CHARS):

    val = data.get(key, "")

    if not isinstance(val, str):

        raise ValidationError({key: "Must be text."})

    if len(val) > limit:

        raise ValidationError({key: f"Too long (max {limit} characters)."})

    return val





def ensure_editable(sub: Submission):

    if sub.is_locked:

        raise PermissionDenied({"detail": "This practical has been submitted and is locked.", "code": "locked"})





# ---------------------------------------------------------------------------

# Practicals (teacher CRUD, student list)

# ---------------------------------------------------------------------------

class PracticalViewSet(viewsets.ModelViewSet):

    permission_classes = [IsAuthenticated]



    def get_queryset(self):

        u = self.request.user

        qs = Practical.objects.select_related("subject")

        subject = self.request.query_params.get("subject")

        if subject:

            qs = qs.filter(subject_id=subject)

        if u.is_admin_role:

            return qs

        if u.is_teacher:

            return qs.filter(subject__teachers=u)

        return qs.filter(subject__students=u, is_published=True)



    def get_serializer_class(self):

        return StudentPracticalSerializer if self.request.user.is_student else PracticalSerializer



    def get_serializer_context(self):

        ctx = super().get_serializer_context()

        if self.request.user.is_authenticated and self.request.user.is_student:

            ctx["my_subs"] = dict(Submission.objects.filter(student=self.request.user)

                                  .values_list("practical_id", "status"))

        return ctx



    def retrieve(self, request, *args, **kwargs):

        if request.user.is_student:

            # Students open practicals through /workspace/, which enforces secure-browser rules.

            p = self.get_object()

            data = {k: v for k, v in self.get_serializer(p).data.items()

                    if k not in ("question", "starter_code", "sample_input", "aim")}

            return Response(data)

        return super().retrieve(request, *args, **kwargs)



    def _check_write(self, subject):

        u = self.request.user

        if u.is_student or not teacher_can_access_subject(u, subject):

            raise PermissionDenied("You do not teach this subject.")



    def perform_create(self, serializer):

        self._check_write(serializer.validated_data["subject"])

        serializer.save(created_by=self.request.user)



    def perform_update(self, serializer):

        self._check_write(serializer.instance.subject)

        if "subject" in serializer.validated_data:

            self._check_write(serializer.validated_data["subject"])

        serializer.save()



    def perform_destroy(self, instance):

        self._check_write(instance.subject)

        instance.delete()



    @action(detail=True, methods=["get"], permission_classes=[IsTeacherOrAdmin])

    def submissions(self, request, pk=None):

        """Teacher dashboard table (slide 10): every enrolled student with status, runs and indicators."""

        p = self.get_object()

        subs = {s.student_id: s for s in p.submissions.select_related("student")

                .prefetch_related("events", "versions").annotate(runs=Count("executions", distinct=True))}

        rows = []

        for st in p.subject.students.order_by("roll_no", "username"):

            s = subs.get(st.id)

            rows.append({

                "student_id": st.id,

                "student_name": st.get_full_name() or st.username,

                "roll_no": st.roll_no,

                "submission_id": s.id if s else None,

                "status": s.status if s else "not_started",

                "runs": s.runs if s else 0,

                "submitted_at": s.submitted_at if s else None,

                "indicators": compute_indicators(s) if s else [],

            })

        return Response({"practical": PracticalSerializer(p).data, "rows": rows})





# ---------------------------------------------------------------------------

# Student workspace (restricted environment)

# ---------------------------------------------------------------------------

def workspace_payload(request, p, sub):

    return {

        "practical": PracticalSerializer(p).data,

        "submission": SubmissionSerializer(sub).data,

        "last_execution": ExecutionSerializer(sub.executions.last()).data if sub.executions.exists() else None,

        "secure_browser": is_secure_browser_request(request),

    }





@api_view(["GET"])

@permission_classes([IsStudent])

def workspace(request, practical_id):

    p = get_student_practical(request, practical_id)

    sub = get_submission(request, p)

    recent = sub.events.filter(kind=ActivityEvent.Kind.SESSION_START,

                               created_at__gte=timezone.now() - timedelta(seconds=10)).exists()

    if not recent:  # page reloads within a few seconds count as one session start

        ActivityEvent.objects.create(submission=sub, kind=ActivityEvent.Kind.SESSION_START,

                                     secure_browser=is_secure_browser_request(request),

                                     detail={"ua": request.headers.get("User-Agent", "")[:200]})

    return Response(workspace_payload(request, p, sub))





@api_view(["POST"])

@permission_classes([IsStudent])

def workspace_save(request, practical_id):

    p = get_student_practical(request, practical_id)

    sub = get_submission(request, p)

    ensure_editable(sub)

    sub.code = clean_code(request.data)

    sub.save(update_fields=["code", "updated_at"])

    v = add_version(sub, sub.code, CodeVersion.Reason.AUTOSAVE)

    return Response({"saved_at": timezone.now(), "version": v.number})





@api_view(["POST"])

@permission_classes([IsStudent])

@throttle_classes([RunThrottle])

def workspace_run(request, practical_id):

    p = get_student_practical(request, practical_id)

    sub = get_submission(request, p)

    ensure_editable(sub)

    code = clean_code(request.data)

    stdin = clean_code(request.data, "stdin", MAX_STDIN_CHARS)

    sub.code = code

    sub.save(update_fields=["code", "updated_at"])

    add_version(sub, code, CodeVersion.Reason.RUN)

    try:

        res = run_code(p.language, code, stdin)

    except ExecutorError as exc:

        return Response({"detail": str(exc)}, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    ex = Execution.objects.create(submission=sub, code=code, stdin=stdin, stdout=res.stdout[:50_000],

                                  stderr=res.stderr[:20_000], compile_output=res.compile_output[:20_000],

                                  status=res.status, state=Execution.State.COMPLETED,

                                  completed_at=timezone.now(), time=res.time, memory=res.memory)

    ActivityEvent.objects.create(submission=sub, kind=ActivityEvent.Kind.RUN, detail={"status": res.status},

                                 secure_browser=is_secure_browser_request(request))

    return Response(ExecutionSerializer(ex).data)





@api_view(["POST"])

@permission_classes([IsStudent])

@throttle_classes([RunThrottle])

def workspace_run_async(request, practical_id):

    """Asynchronous code execution endpoint. Returns HTTP 202 with execution_id."""

    p = get_student_practical(request, practical_id)

    sub = get_submission(request, p)

    ensure_editable(sub)

    code = clean_code(request.data)

    stdin = clean_code(request.data, "stdin", MAX_STDIN_CHARS)

    sub.code = code

    sub.save(update_fields=["code", "updated_at"])

    add_version(sub, code, CodeVersion.Reason.RUN)



    ex = Execution.objects.create(
        submission=sub,
        code=code,
        stdin=stdin,
        state=Execution.State.QUEUED,
        status="In Queue"
    )
    from .tasks import dispatch_execution_task
    try:
        dispatch_execution_task.delay(ex.id)
    except Exception as exc:
        logger.exception(f"[Execution {ex.id}] Failed to enqueue execution task: {exc}")
        ex.state = Execution.State.FAILED
        ex.status = "System Error"
        ex.last_error = "Execution queue broker unavailable"
        ex.completed_at = timezone.now()
        ex.save(update_fields=["state", "status", "last_error", "completed_at"])
        return Response({
            "detail": "Execution queue is temporarily unavailable. Please try again shortly.",
            "code": "queue_unavailable"
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)

    return Response({
        "execution_id": ex.id,
        "state": ex.state,
        "status": ex.status,
        "created_at": ex.created_at,
        "poll_url": f"/api/executions/{ex.id}/"
    }, status=status.HTTP_202_ACCEPTED)





@api_view(["GET"])

@permission_classes([IsAuthenticated])

def execution_detail(request, pk):

    """Retrieve execution status and outputs. Enforces student and teacher isolation."""

    ex = get_object_or_404(Execution.objects.select_related("submission__practical__subject", "submission__student"), pk=pk)

    u = request.user

    if u.is_student:

        if ex.submission.student_id != u.id:

            raise PermissionDenied("You can only view your own executions.")

    else:

        if not teacher_can_access_subject(u, ex.submission.practical.subject):

            raise PermissionDenied("You do not teach this subject.")

    return Response(ExecutionSerializer(ex).data)





ALLOWED_CLIENT_EVENTS = {

    ActivityEvent.Kind.INSERT, ActivityEvent.Kind.DELETE, ActivityEvent.Kind.INTERNAL_PASTE,

    ActivityEvent.Kind.PASTE_BLOCKED, ActivityEvent.Kind.DROP_BLOCKED, ActivityEvent.Kind.FOCUS_LOST,

    ActivityEvent.Kind.FOCUS_BACK, ActivityEvent.Kind.FULLSCREEN_EXIT, ActivityEvent.Kind.SECURE_ALERT,

}





@api_view(["POST"])

@permission_classes([IsStudent])

def workspace_events(request, practical_id):

    p = get_student_practical(request, practical_id)

    sub = get_submission(request, p)

    events = request.data.get("events", [])

    if not isinstance(events, list) or len(events) > 500:

        raise ValidationError({"events": "Send a list of at most 500 events."})

    secure = is_secure_browser_request(request)

    objs = []

    for e in events:

        if not isinstance(e, dict) or e.get("kind") not in ALLOWED_CLIENT_EVENTS:

            continue

        ct = None

        try:

            if e.get("t"):

                ct = datetime.fromtimestamp(int(e["t"]) / 1000, tz=timezone.get_current_timezone())

        except (TypeError, ValueError, OverflowError, OSError):

            ct = None

        detail = e.get("detail") if isinstance(e.get("detail"), dict) else {}

        objs.append(ActivityEvent(submission=sub, kind=e["kind"], chars=int(e.get("chars") or 0),

                                  detail={k: str(v)[:300] for k, v in list(detail.items())[:10]},

                                  client_time=ct, secure_browser=secure))

    ActivityEvent.objects.bulk_create(objs)

    return Response({"stored": len(objs)})





@api_view(["POST"])

@permission_classes([IsStudent])

def workspace_submit(request, practical_id):
    p = get_student_practical(request, practical_id)
    sub = get_submission(request, p)
    ensure_editable(sub)
    code = clean_code(request.data)
    stdin = clean_code(request.data, "stdin", MAX_STDIN_CHARS)

    # Serialize concurrent submissions for this student/practical.
    with transaction.atomic():
        sub = Submission.objects.select_for_update().get(pk=sub.pk)
        ensure_editable(sub)
        latest_execution = sub.executions.order_by("-created_at", "-pk").first()
        if (
            latest_execution is None
            or latest_execution.state != Execution.State.COMPLETED
            or latest_execution.status != "Accepted"
            or latest_execution.code != code
            or latest_execution.stdin != stdin
        ):
            return Response(
                {
                    "detail": (
                        "Run your final program successfully with the same code and input "
                        "before submitting, so the record contains its real output."
                    ),
                    "code": "run_required",
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        sub.code = code
        sub.status = Submission.Status.SUBMITTED
        sub.submitted_at = timezone.now()
        sub.record_execution = latest_execution
        sub.save(update_fields=["code", "status", "submitted_at", "record_execution", "updated_at"])
        add_version(sub, code, CodeVersion.Reason.SUBMIT)
        ActivityEvent.objects.create(
            submission=sub,
            kind=ActivityEvent.Kind.SUBMIT,
            secure_browser=is_secure_browser_request(request),
        )

    return Response(workspace_payload(request, p, sub))



# ---------------------------------------------------------------------------

# Teacher review

# ---------------------------------------------------------------------------

def get_teacher_submission(request, pk) -> Submission:

    sub = get_object_or_404(Submission.objects.select_related("practical__subject", "student"), pk=pk)

    if not teacher_can_access_subject(request.user, sub.practical.subject):

        raise PermissionDenied("You do not teach this subject.")

    return sub





@api_view(["GET"])

@permission_classes([IsTeacherOrAdmin])

def submission_detail(request, pk):

    sub = get_teacher_submission(request, pk)

    return Response({

        "submission": SubmissionSerializer(sub).data,

        "practical": PracticalSerializer(sub.practical).data,

        "versions": VersionSerializer(sub.versions.all(), many=True).data,

        "events": EventSerializer(sub.events.all(), many=True).data,

        "executions": ExecutionSerializer(sub.executions.all(), many=True).data,

        "indicators": compute_indicators(sub),

        "ai_enabled": ai_enabled(),

    })





@api_view(["POST"])

@permission_classes([IsTeacherOrAdmin])

def submission_approve(request, pk):

    sub = get_teacher_submission(request, pk)

    if sub.status != Submission.Status.SUBMITTED:

        return Response({"detail": "Only submitted work can be approved."}, status=400)

    ex_id = request.data.get("execution_id")

    if ex_id:

        sub.record_execution = get_object_or_404(Execution, pk=ex_id, submission=sub, code=sub.code)

    sub.result = str(request.data.get("result", "") or sub.result)[:2000]

    sub.teacher_note = str(request.data.get("note", "") or "")[:2000]

    sub.status = Submission.Status.APPROVED

    sub.approved_at = timezone.now()

    sub.approved_by = request.user

    sub.save()

    return Response(SubmissionSerializer(sub).data)





@api_view(["POST"])

@permission_classes([IsTeacherOrAdmin])

def submission_request_correction(request, pk):

    sub = get_teacher_submission(request, pk)

    if sub.status not in (Submission.Status.SUBMITTED, Submission.Status.APPROVED):

        return Response({"detail": "Nothing to send back."}, status=400)

    sub.status = Submission.Status.CORRECTION

    sub.teacher_note = str(request.data.get("note", ""))[:2000]

    sub.approved_at = None

    sub.approved_by = None

    sub.save()

    return Response(SubmissionSerializer(sub).data)





@api_view(["POST"])

@permission_classes([IsTeacherOrAdmin])

def submission_ai_summary(request, pk):

    sub = get_teacher_submission(request, pk)

    try:

        text = summarize_submission(sub.practical.get_language_display(), sub.practical.question, sub.code,

                                    compute_indicators(sub), sub.versions.count())

    except AIUnavailable as exc:

        return Response({"detail": str(exc)}, status=503)

    return Response({"summary": text, "note": "AI output is a review aid only, not proof."})





# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------

class StreamingRecordResponse(FileResponse):
    """
    Streaming response for generated documents that safely retains
    the open file handle until streaming completes, and guarantees
    cleanup of the temporary directory and file upon close().
    """
    def __init__(self, file_path, cleanup_dir=None, *args, **kwargs):
        self._file_path = file_path
        self._cleanup_dir = cleanup_dir
        handle = open(file_path, "rb")
        super().__init__(handle, *args, **kwargs)

    @property
    def content(self):
        """Allow test clients and callers to inspect content as bytes without breaking streaming."""
        if not hasattr(self, "_cached_content"):
            self._cached_content = b"".join(self.streaming_content)
            self.streaming_content = iter([self._cached_content])
        return self._cached_content

    def close(self):
        super().close()
        if self._cleanup_dir and os.path.exists(self._cleanup_dir):
            try:
                shutil.rmtree(self._cleanup_dir, ignore_errors=True)
            except Exception as e:
                logger.warning(f"Error cleaning up temp directory {self._cleanup_dir}: {e}")
        elif os.path.exists(self._file_path):
            try:
                os.remove(self._file_path)
            except Exception as e:
                logger.warning(f"Error cleaning up temp file {self._file_path}: {e}")


LOCK_DIR = os.path.join(tempfile.gettempdir(), "labora_record_locks")
os.makedirs(LOCK_DIR, exist_ok=True)


@contextmanager
def record_generation_lock(lock_key: str, timeout: float = 30.0, poll_interval: float = 0.2):
    """
    Cross-process and cross-thread lock using kernel file locks.
    Compatible with Gunicorn multi-worker deployments on both Linux (fcntl.flock)
    and Windows (msvcrt.locking).
    """
    sanitized_key = re.sub(r"[^a-zA-Z0-9_\-\.]", "_", lock_key)
    lock_file_path = os.path.join(LOCK_DIR, f"{sanitized_key}.lock")
    start_time = time.time()
    file_fd = None
    acquired = False

    try:
        file_fd = os.open(lock_file_path, os.O_RDWR | os.O_CREAT, 0o666)
        while not acquired:
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(file_fd, msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(file_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except (OSError, IOError, BlockingIOError):
                if time.time() - start_time >= timeout:
                    logger.warning(f"Record generation lock timeout ({timeout}s) for {lock_key}")
                    raise TimeoutError(f"Could not acquire record generation lock within {timeout} seconds.")
                time.sleep(poll_interval)

        yield acquired

    finally:
        if acquired and file_fd is not None:
            try:
                if os.name == "nt":
                    import msvcrt
                    msvcrt.locking(file_fd, msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl
                    fcntl.flock(file_fd, fcntl.LOCK_UN)
            except Exception as e:
                logger.debug(f"Error unlocking {lock_file_path}: {e}")
        if file_fd is not None:
            try:
                os.close(file_fd)
            except Exception:
                pass


def _file_response(ctx, kind, filename, lock_key: str = None):
    lock_key = lock_key or filename
    tmp_dir = tempfile.mkdtemp(prefix="labora_doc_")

    try:
        lock_timeout = getattr(settings, "RECORD_GENERATION_TIMEOUT_SECONDS", 30)
        with record_generation_lock(lock_key, timeout=lock_timeout):
            if kind == "docx":
                file_path = os.path.join(tmp_dir, f"{filename}.docx")
                records.build_docx_file(ctx, file_path)
                ctype = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                resp = StreamingRecordResponse(file_path, cleanup_dir=tmp_dir, content_type=ctype)
                resp["Content-Disposition"] = f'attachment; filename="{filename}.docx"'
                return resp
            else:
                try:
                    file_path = records.build_pdf_file(ctx, tmp_dir, filename)
                except records.PDFConverterUnavailableError as exc:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                    return Response({"detail": str(exc)}, status=501)
                except (ImportError, OSError, RuntimeError, ValueError, TimeoutError) as exc:
                    shutil.rmtree(tmp_dir, ignore_errors=True)
                    logger.exception(f"PDF generation failed: {exc}")
                    return Response({"detail": f"PDF generation error: {exc}"}, status=500)

                ctype = "application/pdf"
                resp = StreamingRecordResponse(file_path, cleanup_dir=tmp_dir, content_type=ctype)
                resp["Content-Disposition"] = f'attachment; filename="{filename}.pdf"'
                return resp

    except TimeoutError as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        return Response({"detail": f"Server is busy processing records. Please try again shortly. ({exc})"}, status=503)
    except Exception as exc:
        shutil.rmtree(tmp_dir, ignore_errors=True)
        logger.exception(f"Document generation failed: {exc}")
        return Response({"detail": f"Document generation error: {exc}"}, status=500)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def record_overview(request):
    """Student: approved practicals per subject, ready for the record."""
    u = request.user
    if not u.is_student:
        return Response({"detail": "Students only."}, status=403)
    out = []
    for subj in u.enrolled_subjects.all():
        subs = Submission.objects.filter(student=u, practical__subject=subj).select_related("practical")
        out.append({
            "subject": {"id": subj.id, "name": subj.name, "code": subj.code},
            "total": subj.practicals.filter(is_published=True).count(),
            "approved": [{"submission_id": s.id, "experiment_no": s.practical.experiment_no,
                          "title": s.practical.title, "approved_at": s.approved_at}
                         for s in subs if s.status == Submission.Status.APPROVED],
        })
    return Response(out)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def record_subject(request, subject_id):
    subject = get_object_or_404(Subject, pk=subject_id)
    u = request.user
    if u.is_student:
        student = u
        if not subject.students.filter(pk=u.pk).exists():
            raise PermissionDenied()
    else:
        if not teacher_can_access_subject(u, subject):
            raise PermissionDenied()
        student = get_object_or_404(User, pk=request.query_params.get("student"), role=User.Role.STUDENT)

    subs = (Submission.objects.filter(student=student, practical__subject=subject, status=Submission.Status.APPROVED)
            .select_related("practical", "approved_by", "record_execution").order_by("practical__experiment_no"))
    if not subs:
        return Response({"detail": "No approved practicals yet."}, status=404)

    ctx = records.record_context(student, subject, subs)
    name = f"LabRecord_{subject.code}_{student.roll_no or student.username}"
    kind = request.query_params.get("type", "pdf")
    lock_key = f"record_subj_{subject.id}_{student.id}_{kind}"
    return _file_response(ctx, kind, name, lock_key=lock_key)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def record_single(request, pk):
    sub = get_object_or_404(Submission.objects.select_related("practical__subject", "student"), pk=pk,
                            status=Submission.Status.APPROVED)
    u = request.user
    if u.is_student and sub.student_id != u.id:
        raise PermissionDenied()
    if not u.is_student and not teacher_can_access_subject(u, sub.practical.subject):
        raise PermissionDenied()

    ctx = records.record_context(sub.student, sub.practical.subject, [sub])
    name = f"Exp{sub.practical.experiment_no}_{sub.student.roll_no or sub.student.username}"
    kind = request.query_params.get("type", "pdf")
    lock_key = f"record_sub_{sub.id}_{kind}"
    return _file_response(ctx, kind, name, lock_key=lock_key)





# ---------------------------------------------------------------------------

# Reports (module 10)

# ---------------------------------------------------------------------------

@api_view(["GET"])

@permission_classes([IsTeacherOrAdmin])

def subject_report(request, subject_id):

    subject = get_object_or_404(Subject, pk=subject_id)

    if not teacher_can_access_subject(request.user, subject):

        raise PermissionDenied()

    n_students = subject.students.count()

    rows = []

    for p in subject.practicals.all():

        counts = dict(p.submissions.values_list("status").annotate(c=Count("id")))

        flagged = sum(1 for s in p.submissions.prefetch_related("events", "versions") if compute_indicators(s))

        rows.append({"practical_id": p.id, "experiment_no": p.experiment_no, "title": p.title,

                     "language": p.language, "students": n_students,

                     "not_started": n_students - sum(counts.values()),

                     "in_progress": counts.get("in_progress", 0), "submitted": counts.get("submitted", 0),

                     "correction": counts.get("correction", 0), "approved": counts.get("approved", 0),

                     "with_indicators": flagged})

    return Response({"subject": {"id": subject.id, "name": subject.name, "code": subject.code}, "rows": rows})
