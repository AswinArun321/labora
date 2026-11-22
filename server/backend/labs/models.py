from django.conf import settings
from django.db import models

from accounts.models import Subject

LANGUAGE_CHOICES = [("c", "C"), ("java", "Java"), ("python", "Python")]


class Practical(models.Model):
    subject = models.ForeignKey(Subject, on_delete=models.CASCADE, related_name="practicals")
    experiment_no = models.PositiveIntegerField()
    title = models.CharField(max_length=200)
    aim = models.TextField(help_text="Printed in the lab record.")
    question = models.TextField(help_text="Shown to the student in the workspace.")
    language = models.CharField(max_length=10, choices=LANGUAGE_CHOICES)
    starter_code = models.TextField(blank=True)
    sample_input = models.TextField(blank=True)
    restricted = models.BooleanField(default=True, help_text="Block external paste / drag-drop and log activity.")
    require_secure_browser = models.BooleanField(
        default=True, help_text="Workspace only opens inside the LABORA Secure Browser."
    )
    is_published = models.BooleanField(default=True)
    due_date = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL,
                                   related_name="created_practicals")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["subject", "experiment_no"]
        unique_together = [("subject", "experiment_no")]

    def __str__(self):
        return f"{self.subject.code} Exp {self.experiment_no}: {self.title}"


class Submission(models.Model):
    class Status(models.TextChoices):
        IN_PROGRESS = "in_progress", "In progress"
        SUBMITTED = "submitted", "Submitted"
        CORRECTION = "correction", "Correction requested"
        APPROVED = "approved", "Approved"

    practical = models.ForeignKey(Practical, on_delete=models.CASCADE, related_name="submissions")
    student = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="submissions")
    code = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.IN_PROGRESS)
    result = models.TextField(blank=True, help_text="Result line printed in the record.")
    teacher_note = models.TextField(blank=True)
    started_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
                                    related_name="approved_submissions")
    # The execution whose real output goes into the lab record.
    record_execution = models.ForeignKey("Execution", null=True, blank=True, on_delete=models.SET_NULL,
                                         related_name="+")

    class Meta:
        unique_together = [("practical", "student")]
        ordering = ["practical", "student__roll_no", "student__username"]

    @property
    def is_locked(self):
        return self.status in (self.Status.SUBMITTED, self.Status.APPROVED)

    def __str__(self):
        return f"{self.student} - {self.practical}"


class CodeVersion(models.Model):
    class Reason(models.TextChoices):
        AUTOSAVE = "autosave", "Autosave"
        RUN = "run", "Run"
        SUBMIT = "submit", "Submit"

    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="versions")
    number = models.PositiveIntegerField()
    code = models.TextField()
    reason = models.CharField(max_length=10, choices=Reason.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["submission", "number"]
        unique_together = [("submission", "number")]


class ActivityEvent(models.Model):
    class Kind(models.TextChoices):
        SESSION_START = "session_start", "Workspace opened"
        INSERT = "insert", "Typed / inserted"
        DELETE = "delete", "Deleted"
        INTERNAL_PASTE = "internal_paste", "Internal paste (allowed)"
        PASTE_BLOCKED = "paste_blocked", "External paste blocked"
        DROP_BLOCKED = "drop_blocked", "Drag-and-drop blocked"
        FOCUS_LOST = "focus_lost", "Left the window"
        FOCUS_BACK = "focus_back", "Returned to the window"
        FULLSCREEN_EXIT = "fullscreen_exit", "Exited fullscreen"
        SECURE_ALERT = "secure_alert", "Secure browser alert"
        RUN = "run", "Program executed"
        SUBMIT = "submit", "Submitted"

    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="events")
    kind = models.CharField(max_length=20, choices=Kind.choices)
    chars = models.IntegerField(default=0, help_text="Characters inserted/deleted, where relevant.")
    detail = models.JSONField(default=dict, blank=True)
    client_time = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    secure_browser = models.BooleanField(default=False)

    class Meta:
        ordering = ["created_at", "id"]


class Execution(models.Model):
    class State(models.TextChoices):
        QUEUED = "QUEUED", "Queued"
        DISPATCHING = "DISPATCHING", "Dispatching"
        SUBMITTED_TO_RUNNER = "SUBMITTED_TO_RUNNER", "Submitted to runner"
        PROCESSING = "PROCESSING", "Processing"
        COMPLETED = "COMPLETED", "Completed"
        FAILED = "FAILED", "Failed"
        TIMED_OUT = "TIMED_OUT", "Timed out"
        CANCELLED = "CANCELLED", "Cancelled"

    submission = models.ForeignKey(Submission, on_delete=models.CASCADE, related_name="executions")
    code = models.TextField()
    stdin = models.TextField(blank=True)
    stdout = models.TextField(blank=True)
    stderr = models.TextField(blank=True)
    compile_output = models.TextField(blank=True)
    state = models.CharField(max_length=30, choices=State.choices, default=State.QUEUED, db_index=True)
    status = models.CharField(max_length=60, default="In Queue")
    time = models.CharField(max_length=20, blank=True)
    memory = models.IntegerField(null=True, blank=True)
    judge0_token = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    runner_url = models.CharField(max_length=200, blank=True)
    last_error = models.TextField(blank=True)
    retry_count = models.PositiveSmallIntegerField(default=0)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["created_at"]

    @property
    def succeeded(self):
        return self.status == "Accepted"

    @property
    def is_complete(self):
        return self.state in (self.State.COMPLETED, self.State.FAILED, self.State.TIMED_OUT, self.State.CANCELLED)
