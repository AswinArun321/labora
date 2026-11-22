"""
LABORA Model Extension Blueprint & Migration Reference

Shows how the Execution model is safely enhanced for production asynchronous operation
without breaking backward compatibility with existing lab records or submission models.
"""
from django.db import models


class ExecutionExtensionMixin(models.Model):
    """
    Mixin representing the production fields added to labs.models.Execution.
    Existing fields (submission, code, stdin, stdout, stderr, compile_output,
    status, time, memory, created_at) are fully retained.
    """
    STATUS_CHOICES = [
        ("QUEUED", "Queued"),
        ("DISPATCHING", "Dispatching to sandbox"),
        ("PROCESSING", "Running in sandbox"),
        ("Accepted", "Accepted"),
        ("Compilation Error", "Compilation Error"),
        ("Time Limit Exceeded", "Time Limit Exceeded"),
        ("Memory Limit Exceeded", "Memory Limit Exceeded"),
        ("Runtime Error (NZEC)", "Runtime Error (NZEC)"),
        ("Runtime Error (Other)", "Runtime Error (Other)"),
        ("FAILED", "System failure"),
    ]

    # New production attributes
    judge0_token = models.CharField(max_length=64, blank=True, null=True, db_index=True)
    runner_instance = models.CharField(max_length=80, blank=True, default="judge0-primary")
    attempt_count = models.PositiveSmallIntegerField(default=1)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
