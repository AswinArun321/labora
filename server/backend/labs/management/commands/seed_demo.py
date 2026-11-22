from django.core.management.base import BaseCommand

from accounts.models import CollegeSettings, Department, Subject, User
from labs.models import Practical

PRACTICALS = [
    {
        "experiment_no": 1, "language": "c", "title": "Sum of N Numbers",
        "aim": "To write a C program to find the sum of N numbers entered by the user.",
        "question": "Write a C program that reads N and then N integers, and prints their sum.",
        "starter_code": "#include <stdio.h>\n\nint main() {\n    // write your program here\n    return 0;\n}\n",
        "sample_input": "5\n1 2 3 4 5\n",
    },
    {
        "experiment_no": 2, "language": "java", "title": "Factorial using Recursion",
        "aim": "To write a Java program to find the factorial of a number using recursion.",
        "question": "Write a Java program that reads a number and prints its factorial using a recursive method. "
                    "The class must be named Main.",
        "starter_code": "import java.util.Scanner;\n\npublic class Main {\n    public static void main(String[] args) {\n"
                        "        // write your program here\n    }\n}\n",
        "sample_input": "5\n",
    },
    {
        "experiment_no": 3, "language": "python", "title": "Prime Number Check",
        "aim": "To write a Python program to check whether a number is prime.",
        "question": "Write a program to check whether a number is prime.",
        "starter_code": 'n = int(input("Enter a number: "))\n# write your program here\n',
        "sample_input": "7\n",
    },
]


class Command(BaseCommand):
    help = "Create demo admin / teacher / students, a subject and C, Java, Python practicals."

    def add_arguments(self, parser):
        parser.add_argument("--secure", action="store_true",
                            help="Require the LABORA Secure Browser for all demo practicals.")
        parser.add_argument("--secure-langs", default="",
                            help="Comma-separated languages whose practicals require the Secure Browser, e.g. c,java")

    def handle(self, *args, secure=False, secure_langs="", **opts):
        secure_set = {x.strip() for x in secure_langs.split(",") if x.strip()}
        cs = CollegeSettings.load()
        if cs.college_name == "Your College Name":
            cs.college_name = "Demo College of Engineering"
            cs.college_address = "Kerala, India"
            cs.save()
        dept, _ = Department.objects.get_or_create(code="MCA", defaults={"name": "Computer Applications"})

        def mk(username, role, pw, **extra):
            u, created = User.objects.get_or_create(username=username, defaults={"role": role, "department": dept, **extra})
            if created:
                u.set_password(pw)
                if role == User.Role.ADMIN:
                    u.is_staff = u.is_superuser = True
                u.save()
            return u

        mk("admin", User.Role.ADMIN, "admin123", first_name="Lab", last_name="Admin")
        teacher = mk("teacher", User.Role.TEACHER, "teacher123", first_name="Anitha", last_name="R")
        students = [mk(f"student{i}", User.Role.STUDENT, "student123", first_name="Student", last_name=chr(64 + i),
                       roll_no=f"MCA{i:03d}", batch="2025-27", semester=1) for i in range(1, 5)]

        subj, _ = Subject.objects.get_or_create(code="MCA101", academic_year="2026-27",
                                                defaults={"name": "Programming Lab", "semester": 1, "department": dept})
        subj.teachers.add(teacher)
        subj.students.add(*students)
        for data in PRACTICALS:
            Practical.objects.update_or_create(
                subject=subj, experiment_no=data["experiment_no"],
                defaults={**data, "restricted": True, "require_secure_browser": secure or data["language"] in secure_set, "created_by": teacher},
            )
        self.stdout.write(self.style.SUCCESS(
            "Demo data ready. Logins: admin/admin123, teacher/teacher123, student1..student4/student123"
            + (" (practicals require the Secure Browser)" if secure else "")))
