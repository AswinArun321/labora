"""
LABORA Management Command: Seed Isolated Load Test Data
Creates or removes synthetic students, subject, and practicals for high-concurrency load testing.

Usage:
  python manage.py seed_load_test_data --count 1000
  python manage.py seed_load_test_data --cleanup
"""
from django.core.management.base import BaseCommand
from django.contrib.auth.hashers import make_password
from django.db import transaction

from accounts.models import Department, Subject, User
from labs.models import Practical, Submission, Execution, ActivityEvent, CodeVersion


LOAD_TEST_PRACTICALS = [
    {
        "experiment_no": 1,
        "language": "python",
        "title": "Prime Sieve Benchmark",
        "aim": "Compute primes up to N using sieve algorithm under load.",
        "question": "Read N and output whether N is prime.",
        "starter_code": "n = int(input())\nis_p = n > 1 and all(n % i != 0 for i in range(2, int(n**0.5) + 1))\nprint('Prime' if is_p else 'Not prime')\n",
        "sample_input": "17\n",
    },
    {
        "experiment_no": 2,
        "language": "c",
        "title": "Array Sum Concurrency Test",
        "aim": "Calculate sum of N elements in C under concurrent dispatch.",
        "question": "Read N and N integers, print their sum.",
        "starter_code": "#include <stdio.h>\nint main() {\n    int n, x, s = 0;\n    if (scanf(\"%d\", &n) != 1) return 0;\n    for (int i = 0; i < n; i++) {\n        if (scanf(\"%d\", &x) == 1) s += x;\n    }\n    printf(\"%d\\n\", s);\n    return 0;\n}\n",
        "sample_input": "5\n10 20 30 40 50\n",
    },
    {
        "experiment_no": 3,
        "language": "java",
        "title": "Recursive Fibonacci",
        "aim": "Calculate Fibonacci sequence in Java.",
        "question": "Read N and print the Nth Fibonacci number.",
        "starter_code": "import java.util.Scanner;\npublic class Main {\n    public static void main(String[] args) {\n        Scanner sc = new Scanner(System.in);\n        int n = sc.nextInt();\n        System.out.println(n);\n    }\n}\n",
        "sample_input": "7\n",
    },
]


class Command(BaseCommand):
    help = "Seed or cleanup isolated synthetic data for high-concurrency Locust load testing."

    def add_arguments(self, parser):
        parser.add_argument("--count", type=int, default=1000, help="Number of synthetic student accounts to create.")
        parser.add_argument("--cleanup", action="store_true", help="Remove all synthetic load test data.")
        parser.add_argument("--password", type=str, default="LoadTest123!", help="Password for synthetic test accounts.")

    def handle(self, *args, count=1000, cleanup=False, password="LoadTest123!", **opts):
        if cleanup:
            self.stdout.write("Cleaning up synthetic load test data...")
            with transaction.atomic():
                test_users = User.objects.filter(username__startswith="load_student_")
                test_subjs = Subject.objects.filter(code="LOAD101")
                test_pracs = Practical.objects.filter(subject__in=test_subjs)
                test_subs = Submission.objects.filter(practical__in=test_pracs)

                ActivityEvent.objects.filter(submission__in=test_subs).delete()
                CodeVersion.objects.filter(submission__in=test_subs).delete()
                Execution.objects.filter(submission__in=test_subs).delete()
                test_subs.delete()
                test_pracs.delete()
                test_subjs.delete()
                deleted_users_count = test_users.count()
                test_users.delete()
                User.objects.filter(username="load_teacher").delete()
                Department.objects.filter(code="LTDEPT").delete()

            self.stdout.write(self.style.SUCCESS(f"Cleaned up {deleted_users_count} synthetic users and associated data."))
            return

        self.stdout.write(f"Seeding {count} isolated load test student accounts...")

        with transaction.atomic():
            dept, _ = Department.objects.get_or_create(
                code="LTDEPT",
                defaults={"name": "Load Testing Department"}
            )

            # Isolated load test teacher
            teacher, t_created = User.objects.get_or_create(
                username="load_teacher",
                defaults={
                    "role": User.Role.TEACHER,
                    "first_name": "Benchmark",
                    "last_name": "Teacher",
                    "department": dept,
                    "is_staff": False,
                }
            )
            if t_created:
                teacher.set_password(password)
                teacher.save()

            # Isolated load test subject
            subject, _ = Subject.objects.get_or_create(
                code="LOAD101",
                academic_year="2026-27",
                defaults={
                    "name": "High-Concurrency Benchmark Lab",
                    "semester": 1,
                    "department": dept,
                }
            )
            subject.teachers.add(teacher)

            # Practicals
            practicals = []
            for item in LOAD_TEST_PRACTICALS:
                prac, _ = Practical.objects.update_or_create(
                    subject=subject,
                    experiment_no=item["experiment_no"],
                    defaults={
                        "title": item["title"],
                        "language": item["language"],
                        "aim": item["aim"],
                        "question": item["question"],
                        "starter_code": item["starter_code"],
                        "is_published": True,
                        "restricted": False,
                        "require_secure_browser": False,
                        "created_by": teacher,
                    }
                )
                practicals.append(prac)

            # Check existing test users
            existing_usernames = set(
                User.objects.filter(username__startswith="load_student_")
                .values_list("username", flat=True)
            )

            hashed_password = make_password(password)
            users_to_create = []

            for i in range(1, count + 1):
                uname = f"load_student_{i:04d}"
                if uname not in existing_usernames:
                    users_to_create.append(
                        User(
                            username=uname,
                            password=hashed_password,
                            role=User.Role.STUDENT,
                            first_name="Load",
                            last_name=f"Student{i:04d}",
                            roll_no=f"LT-2026-{i:04d}",
                            batch="2026-2028",
                            semester=1,
                            department=dept,
                            is_active=True,
                        )
                    )

            if users_to_create:
                User.objects.bulk_create(users_to_create, batch_size=500)
                self.stdout.write(f"Created {len(users_to_create)} new synthetic student accounts.")

            # Enroll all synthetic students into the benchmark subject
            all_load_students = User.objects.filter(username__startswith="load_student_")
            subject.students.add(*all_load_students)

        self.stdout.write(self.style.SUCCESS(
            f"Successfully prepared load test data:\n"
            f" - Department: {dept.name} ({dept.code})\n"
            f" - Subject: {subject.name} ({subject.code}) with {len(practicals)} practicals\n"
            f" - Teacher: {teacher.username} / {password}\n"
            f" - Students: load_student_0001 .. load_student_{count:04d} / {password}\n"
            f" - Practical IDs: {[p.id for p in practicals]}"
        ))
