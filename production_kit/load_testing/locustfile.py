"""
LABORA 1,000 Concurrent User Realistic Load Testing Suite (Locust)

Implements realistic collegiate lab testing required by plann.md Section 7 & 19:
- 1,000 concurrent student sessions with realistic user think-times
- Monaco editor typing cadence & autosave writes
- Asynchronous code execution dispatching and status polling
- Submission workflow
- Teacher monitoring and review dashboard activity
"""
import random
import time
from locust import HttpUser, task, between, events


SAMPLE_PYTHON_CODE = [
    'n = int(input())\nprint("Prime" if n > 1 and all(n % i for i in range(2, int(n**0.5)+1)) else "Not prime")\n',
    'def factorial(n):\n    return 1 if n <= 1 else n * factorial(n - 1)\nprint(factorial(int(input())))\n',
    'arr = list(map(int, input().split()))\nprint(sum(arr))\n',
]

SAMPLE_C_CODE = [
    '#include <stdio.h>\nint main() {\n    int n, s=0, x;\n    scanf("%d", &n);\n    for(int i=0; i<n; i++){ scanf("%d", &x); s+=x; }\n    printf("Sum = %d\\n", s);\n    return 0;\n}\n',
]


class StudentUser(HttpUser):
    wait_time = between(2, 6) # Realistic thinking time between student actions

    def on_start(self):
        """Simulate student login via JWT"""
        self.student_id = random.randint(1, 1000)
        self.username = f"student{self.student_id}"
        self.password = "student123"
        self.token = None
        self.practical_id = random.choice([1, 2, 3])

        resp = self.client.post("/api/auth/login/", json={
            "username": self.username,
            "password": self.password
        })
        if resp.status_code == 200:
            self.token = resp.json().get("access")
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})

    @task(5)
    def open_workspace(self):
        """Load assignment instructions and starter code"""
        if not self.token:
            return
        self.client.get(f"/api/workspace/{self.practical_id}/", name="/api/workspace/[id]/")

    @task(10)
    def autosave_code(self):
        """Simulate periodic Monaco editor autosaving (every ~10-15s)"""
        if not self.token:
            return
        code = random.choice(SAMPLE_PYTHON_CODE)
        self.client.post(f"/api/workspace/{self.practical_id}/save/", json={
            "code": code
        }, name="/api/workspace/[id]/save/")

    @task(8)
    def report_activity_events(self):
        """Simulate typing events and focus telemetry batching"""
        if not self.token:
            return
        self.client.post(f"/api/workspace/{self.practical_id}/events/", json={
            "events": [
                {"kind": "insert", "chars": random.randint(1, 15), "t": int(time.time() * 1000)},
                {"kind": "delete", "chars": random.randint(0, 3), "t": int(time.time() * 1000)}
            ]
        }, name="/api/workspace/[id]/events/")

    @task(3)
    def execute_and_poll_code(self):
        """Simulate code execution and non-blocking polling"""
        if not self.token:
            return
        code = random.choice(SAMPLE_PYTHON_CODE)
        run_resp = self.client.post(f"/api/workspace/{self.practical_id}/run-async/", json={
            "code": code,
            "stdin": "5\n"
        }, name="/api/workspace/[id]/run-async/")

        if run_resp.status_code == 202:
            exec_id = run_resp.json().get("execution_id")
            # Poll status until terminal state (max 10 attempts)
            for _ in range(10):
                time.sleep(1.5)
                poll = self.client.get(
                    f"/api/workspace/{self.practical_id}/executions/{exec_id}/",
                    name="/api/workspace/[id]/executions/[id]/"
                )
                if poll.status_code == 200 and poll.json().get("is_complete"):
                    break

    @task(1)
    def submit_practical(self):
        """Simulate final student submission"""
        if not self.token:
            return
        self.client.post(f"/api/workspace/{self.practical_id}/submit/", json={
            "code": SAMPLE_PYTHON_CODE[0]
        }, name="/api/workspace/[id]/submit/")


class TeacherUser(HttpUser):
    wait_time = between(5, 10)

    def on_start(self):
        """Simulate teacher login"""
        resp = self.client.post("/api/auth/login/", json={
            "username": "teacher",
            "password": "teacher123"
        })
        if resp.status_code == 200:
            token = resp.json().get("access")
            self.client.headers.update({"Authorization": f"Bearer {token}"})

    @task(5)
    def view_dashboard(self):
        """Monitor student progress dashboard and review indicators"""
        self.client.get("/api/practicals/1/submissions/", name="/api/practicals/[id]/submissions/")

    @task(2)
    def view_student_detail(self):
        """Inspect student code versions and telemetry events"""
        sub_id = random.randint(1, 100)
        self.client.get(f"/api/submissions/{sub_id}/", name="/api/submissions/[id]/")
