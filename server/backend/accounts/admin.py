from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import CollegeSettings, Department, Subject, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("username", "first_name", "last_name", "role", "roll_no", "department", "is_active")
    list_filter = ("role", "department", "is_active")
    search_fields = ("username", "first_name", "last_name", "roll_no")
    fieldsets = BaseUserAdmin.fieldsets + (("LABORA", {"fields": ("role", "department", "roll_no", "semester", "batch")}),)
    add_fieldsets = BaseUserAdmin.add_fieldsets + (("LABORA", {"fields": ("role", "department", "roll_no")}),)


@admin.register(Subject)
class SubjectAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "semester", "academic_year", "department")
    filter_horizontal = ("teachers", "students")


admin.site.register(Department)
admin.site.register(CollegeSettings)
