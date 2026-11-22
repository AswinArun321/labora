from django.contrib import admin

from .models import ActivityEvent, CodeVersion, Execution, Practical, Submission


@admin.register(Practical)
class PracticalAdmin(admin.ModelAdmin):
    list_display = ("subject", "experiment_no", "title", "language", "restricted", "require_secure_browser", "is_published")
    list_filter = ("subject", "language")


@admin.register(Submission)
class SubmissionAdmin(admin.ModelAdmin):
    list_display = ("practical", "student", "status", "submitted_at", "approved_at")
    list_filter = ("status", "practical__subject")


admin.site.register(CodeVersion)
admin.site.register(ActivityEvent)
admin.site.register(Execution)
