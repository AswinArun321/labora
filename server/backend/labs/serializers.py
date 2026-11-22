from rest_framework import serializers

from .models import ActivityEvent, CodeVersion, Execution, Practical, Submission


class PracticalSerializer(serializers.ModelSerializer):
    subject_name = serializers.CharField(source="subject.name", read_only=True)
    subject_code = serializers.CharField(source="subject.code", read_only=True)

    class Meta:
        model = Practical
        fields = ["id", "subject", "subject_name", "subject_code", "experiment_no", "title", "aim", "question",
                  "language", "starter_code", "sample_input", "restricted", "require_secure_browser",
                  "is_published", "due_date", "created_at"]
        read_only_fields = ["created_at"]


class StudentPracticalSerializer(PracticalSerializer):
    my_status = serializers.SerializerMethodField()

    class Meta(PracticalSerializer.Meta):
        fields = PracticalSerializer.Meta.fields + ["my_status"]

    def get_my_status(self, obj):
        subs = self.context.get("my_subs", {})
        return subs.get(obj.id, "not_started")


class ExecutionSerializer(serializers.ModelSerializer):
    is_complete = serializers.BooleanField(read_only=True)

    class Meta:
        model = Execution
        fields = [
            "id", "stdin", "stdout", "stderr", "compile_output", "status", "state",
            "is_complete", "time", "memory", "judge0_token", "last_error",
            "started_at", "completed_at", "created_at"
        ]


class VersionSerializer(serializers.ModelSerializer):
    class Meta:
        model = CodeVersion
        fields = ["id", "number", "code", "reason", "created_at"]


class EventSerializer(serializers.ModelSerializer):
    kind_label = serializers.CharField(source="get_kind_display", read_only=True)

    class Meta:
        model = ActivityEvent
        fields = ["id", "kind", "kind_label", "chars", "detail", "client_time", "created_at", "secure_browser"]


class SubmissionSerializer(serializers.ModelSerializer):
    student_name = serializers.SerializerMethodField()
    roll_no = serializers.CharField(source="student.roll_no", read_only=True)
    locked = serializers.BooleanField(source="is_locked", read_only=True)

    class Meta:
        model = Submission
        fields = ["id", "practical", "student", "student_name", "roll_no", "code", "status", "locked", "result",
                  "teacher_note", "started_at", "updated_at", "submitted_at", "approved_at", "record_execution"]

    def get_student_name(self, obj):
        return obj.student.get_full_name() or obj.student.username
