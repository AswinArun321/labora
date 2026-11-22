"""
LABORA High-Concurrency Institutional Load Testing Suite (Locust)
Simulates realistic collegiate practical examination workflows:
1. Authentication & Session Hydration (POST /api/auth/login/, GET /api/auth/me/)
2. Curriculum Navigation (GET /api/subjects/, GET /api/practicals/?subject=<id>)
3. Workspace Loading (GET /api/workspace/<id>/)
4. Monaco Typing & Autosave Cadence (POST /api/workspace/<id>/save/)
5. Telemetry Ingestion (POST /api/workspace/<id>/events/)
6. Non-blocking Code Execution & Status Polling (POST /api/workspace/<id>/run-async/, GET /api/executions/<id>/)
7. Final Practical Submission (POST /api/workspace/<id>/submit/)
8. Teacher In-Flight Supervision (GET /api/practicals/<id>/submissions/)

Supports targeted sub-scenarios via Locust tags:
  --tags browsing
  --tags autosave
  --tags execution
  --tags submission
  --tags teacher
"""
import os
import random
import time
import gevent
from locust import HttpUser, task, tag, between, events


SAMPLE_PYTHON_CODE = [
    'n = int(input())\nprint("Prime" if n > 1 and all(n % i for i in range(2, int(n**0.5)+1)) else "Not prime")\n',
    'def factorial(n):\n    return 1 if n <= 1 else n * factorial(n - 1)\nprint(factorial(int(input())))\n',
    'arr = list(map(int, input().split()))\nprint(sum(arr))\n',
    'def fib(n):\n    a, b = 0, 1\n    for _ in range(n): a, b = b, a + b\n    return a\nprint(fib(int(input())))\n',
]

SAMPLE_C_CODE = [
    '#include <stdio.h>\nint main() {\n    int n, s=0, x;\n    if (scanf("%d", &n) != 1) return 0;\n    for(int i=0; i<n; i++){ if(scanf("%d", &x)==1) s+=x; }\n    printf("Sum = %d\\n", s);\n    return 0;\n}\n',
]


class StudentUser(HttpUser):
    """
    Simulates a student taking a practical examination.
    Wait time: 2 to 6 seconds between actions (realistic typing and thinking interval).
    Weight: 95% of active users.
    """
    weight = 95
    wait_time = between(2, 6)

    def on_start(self):
        """Simulate realistic student login and session bootstrap"""
        self.max_students = int(os.environ.get("LOAD_TEST_STUDENT_COUNT", "1000"))
        self.student_num = random.randint(1, self.max_students)
        self.username = f"load_student_{self.student_num:04d}"
        self.password = os.environ.get("LOAD_TEST_PASSWORD", "LoadTest123!")
        self.token = None
        self.practical_id = None
        self.subject_id = None
        self.latest_accepted_code = None
        self.latest_accepted_stdin = ""

        login_res = self.client.post("/api/auth/login/", json={
            "username": self.username,
            "password": self.password,
        }, name="/api/auth/login/")

        if login_res.status_code == 200:
            data = login_res.json()
            self.token = data.get("access")
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})

            # Hydrate user session
            self.client.get("/api/auth/me/", name="/api/auth/me/")

            # Load student subjects
            subj_res = self.client.get("/api/subjects/", name="/api/subjects/")
            if subj_res.status_code == 200 and len(subj_res.json()) > 0:
                self.subject_id = subj_res.json()[0]["id"]
                # Load practicals for this subject
                prac_res = self.client.get(f"/api/practicals/?subject={self.subject_id}", name="/api/practicals/?subject=[id]")
                if prac_res.status_code == 200 and len(prac_res.json()) > 0:
                    self.practical_id = random.choice(prac_res.json())["id"]

        if not self.practical_id:
            self.practical_id = int(os.environ.get("DEFAULT_PRACTICAL_ID", "1"))

    @task(4)
    @tag('browsing')
    def open_workspace(self):
        """Load assignment instructions, starter code, and latest code version"""
        if not self.token:
            return
        self.client.get(f"/api/workspace/{self.practical_id}/", name="/api/workspace/[id]/")

    @task(8)
    @tag('autosave')
    def autosave_code(self):
        """Simulate periodic Monaco editor autosaving (every ~10-15s)"""
        if not self.token:
            return
        code = random.choice(SAMPLE_PYTHON_CODE)
        self.client.post(f"/api/workspace/{self.practical_id}/save/", json={
            "code": code
        }, name="/api/workspace/[id]/save/")

    @task(6)
    @tag('autosave')
    def report_activity_events(self):
        """Simulate keystroke batches and focus telemetry reporting"""
        if not self.token:
            return
        now_ms = int(time.time() * 1000)
        self.client.post(f"/api/workspace/{self.practical_id}/events/", json={
            "events": [
                {"kind": "insert", "chars": random.randint(1, 20), "t": now_ms},
                {"kind": "delete", "chars": random.randint(0, 4), "t": now_ms + 100}
            ]
        }, name="/api/workspace/[id]/events/")

    @task(3)
    @tag('execution')
    def execute_and_poll_code(self):
        """Simulate code execution dispatch to Celery and asynchronous polling"""
        if not self.token:
            return
        code = random.choice(SAMPLE_PYTHON_CODE)
        stdin = "17\n"
        run_resp = self.client.post(f"/api/workspace/{self.practical_id}/run-async/", json={
            "code": code,
            "stdin": stdin
        }, name="/api/workspace/[id]/run-async/")

        if run_resp.status_code == 202:
            exec_id = run_resp.json().get("execution_id")
            # Poll status until terminal state (max 10 polling attempts with non-blocking sleep)
            for _ in range(10):
                gevent.sleep(1.0)
                poll = self.client.get(
                    f"/api/executions/{exec_id}/",
                    name="/api/executions/[id]/"
                )
                if poll.status_code == 200:
                    data = poll.json()
                    if data.get("is_complete") or data.get("status") in ["Accepted", "Wrong Answer", "Runtime Error", "Time Limit Exceeded", "FAILED"]:
                        if data.get("status") == "Accepted":
                            self.latest_accepted_code = code
                            self.latest_accepted_stdin = stdin
                        break

    @task(1)
    @tag('submission')
    def submit_practical(self):
        """Simulate final student practical submission"""
        if not self.token or not self.latest_accepted_code:
            return
        self.client.post(f"/api/workspace/{self.practical_id}/submit/", json={
            "code": self.latest_accepted_code,
            "stdin": self.latest_accepted_stdin,
        }, name="/api/workspace/[id]/submit/")


class TeacherUser(HttpUser):
    """
    Simulates a teacher / invigilator supervising active practicals.
    Wait time: 5 to 10 seconds.
    Weight: 5% of active users.
    """
    weight = 5
    wait_time = between(5, 10)

    def on_start(self):
        """Simulate teacher login"""
        self.username = os.environ.get("LOAD_TEST_TEACHER", "load_teacher")
        self.password = os.environ.get("LOAD_TEST_PASSWORD", "LoadTest123!")
        self.token = None

        resp = self.client.post("/api/auth/login/", json={
            "username": self.username,
            "password": self.password
        }, name="/api/auth/login/")

        if resp.status_code == 200:
            self.token = resp.json().get("access")
            self.client.headers.update({"Authorization": f"Bearer {self.token}"})

    @task(4)
    @tag('teacher', 'browsing')
    def view_dashboard(self):
        """Monitor student progress dashboard and review indicators"""
        if not self.token:
            return
        practical_id = int(os.environ.get("DEFAULT_PRACTICAL_ID", "1"))
        self.client.get(f"/api/practicals/{practical_id}/submissions/", name="/api/practicals/[id]/submissions/")

    @task(2)
    @tag('teacher', 'browsing')
    def view_student_detail(self):
        """Inspect student submission detail"""
        if not self.token:
            return
        sub_id = random.randint(1, 10)
        self.client.get(f"/api/submissions/{sub_id}/", name="/api/submissions/[id]/")
