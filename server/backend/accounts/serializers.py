from rest_framework import serializers

from .models import CollegeSettings, Department, Subject, User


class DepartmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Department
        fields = ["id", "name", "code"]


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=6)
    department_name = serializers.CharField(source="department.name", read_only=True, default="")
    full_name = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "full_name", "email", "role", "department",
                  "department_name", "roll_no", "semester", "batch", "is_active", "password"]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username

    def create(self, validated):
        pw = validated.pop("password", None)
        user = User(**validated)
        if pw:
            user.set_password(pw)
        else:
            user.set_unusable_password()
        user.save()
        return user

    def update(self, instance, validated):
        pw = validated.pop("password", None)
        for k, v in validated.items():
            setattr(instance, k, v)
        if pw:
            instance.set_password(pw)
        instance.save()
        return instance


class MeSerializer(serializers.ModelSerializer):
    full_name = serializers.SerializerMethodField()
    department_name = serializers.CharField(source="department.name", read_only=True, default="")

    class Meta:
        model = User
        fields = ["id", "username", "full_name", "role", "roll_no", "batch", "semester", "department_name"]

    def get_full_name(self, obj):
        return obj.get_full_name() or obj.username


class SubjectSerializer(serializers.ModelSerializer):
    department_name = serializers.CharField(source="department.name", read_only=True)
    teacher_names = serializers.SerializerMethodField()
    student_count = serializers.SerializerMethodField()

    class Meta:
        model = Subject
        fields = ["id", "name", "code", "semester", "academic_year", "department", "department_name",
                  "teachers", "teacher_names", "students", "student_count"]
        extra_kwargs = {"students": {"required": False}, "teachers": {"required": False}}

    def get_teacher_names(self, obj):
        return [t.get_full_name() or t.username for t in obj.teachers.all()]

    def get_student_count(self, obj):
        return obj.students.count()

    def to_representation(self, instance):
        data = super().to_representation(instance)
        req = self.context.get("request")
        if req and req.user.is_student:
            data.pop("students", None)
        return data


class CollegeSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CollegeSettings
        fields = ["college_name", "college_address", "logo", "record_title", "record_footer",
                  "students_secure_browser_only"]
