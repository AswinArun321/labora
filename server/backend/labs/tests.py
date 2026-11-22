import base64
import os
import time
from datetime import timedelta
from unittest.mock import MagicMock, patch

import requests
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import CollegeSettings, User
from labs.models import ActivityEvent, Execution, Practical, Submission
from labs.secure_browser import compute_signature
from labs.tasks import dispatch_execution_task, poll_execution_task, reconcile_stale_executions



KEY = "test-key"



PY_PRIME = (

    "n = int(input('Enter a number: '))\n"

    "print('Prime' if n > 1 and all(n % i for i in range(2, int(n**0.5) + 1)) else 'Not prime')\n"

)

C_SUM = (

    "#include <stdio.h>\nint main(){int n,x,s=0;scanf(\"%d\",&n);"

    "for(int i=0;i<n;i++){scanf(\"%d\",&x);s+=x;}printf(\"Sum = %d\\\n\",s);return 0;}\n"

)

JAVA_FACT = (

    "import java.util.Scanner;\npublic class Main{static long f(int n){return n<=1?1:n*f(n-1);}"

    "public static void main(String[] a){int n=new Scanner(System.in).nextInt();System.out.println(f(n));}}\n"

)





@override_settings(CODE_EXECUTOR="local", SECURE_BROWSER_KEY=KEY, CELERY_TASK_ALWAYS_EAGER=True)

class LaboraFlowTests(TestCase):

    def setUp(self):

        call_command("seed_demo", stdout=open(os.devnull, "w"))

        self.c = APIClient()

        self.py = Practical.objects.get(language="python")

        self.cprog = Practical.objects.get(language="c")

        self.java = Practical.objects.get(language="java")



    def login(self, username, pw):

        r = self.c.post("/api/auth/login/", {"username": username, "password": pw}, format="json")

        self.assertEqual(r.status_code, 200, r.content)

        self.c.credentials(HTTP_AUTHORIZATION="Bearer " + r.json()["access"])



    def signed(self, method, path):

        ts = str(int(time.time()))

        return {"HTTP_X_LABORA_TS": ts, "HTTP_X_LABORA_SIGNATURE": compute_signature(KEY, ts, method, path)}



    def test_secure_browser_required(self):

        self.py.require_secure_browser = True

        self.py.save()

        self.login("student1", "student123")

        path = f"/api/workspace/{self.py.id}/"

        r = self.c.get(path)

        self.assertEqual(r.status_code, 403)

        self.assertIn("Secure Browser", str(r.content))

        r = self.c.get(path, **self.signed("GET", path))

        self.assertEqual(r.status_code, 200)

        self.assertTrue(r.json()["secure_browser"])

        # wrong signature / stale timestamp rejected

        bad = self.signed("GET", path)

        bad["HTTP_X_LABORA_SIGNATURE"] = "0" * 64

        self.assertEqual(self.c.get(path, **bad).status_code, 403)



    def test_student_login_gate(self):

        cs = CollegeSettings.load()

        cs.students_secure_browser_only = True

        cs.save()

        r = self.c.post("/api/auth/login/", {"username": "student1", "password": "student123"}, format="json")

        self.assertEqual(r.status_code, 403)

        r = self.c.post("/api/auth/login/", {"username": "student1", "password": "student123"}, format="json",

                        **self.signed("POST", "/api/auth/login/"))

        self.assertEqual(r.status_code, 200)

        # teachers are not gated

        r = self.c.post("/api/auth/login/", {"username": "teacher", "password": "teacher123"}, format="json")

        self.assertEqual(r.status_code, 200)



    def test_run_all_languages(self):

        self.login("student1", "student123")

        for p, code, stdin, expect in [(self.py, PY_PRIME, "7\n", "Prime"),

                                       (self.cprog, C_SUM, "3\n1 2 3\n", "Sum = 6"),

                                       (self.java, JAVA_FACT, "5\n", "120")]:

            r = self.c.post(f"/api/workspace/{p.id}/run/", {"code": code, "stdin": stdin}, format="json")

            self.assertEqual(r.status_code, 200, r.content)

            self.assertEqual(r.json()["status"], "Accepted", r.json())

            self.assertIn(expect, r.json()["stdout"])



    def test_compile_error_reported(self):

        self.login("student1", "student123")

        r = self.c.post(f"/api/workspace/{self.cprog.id}/run/", {"code": "int main( {", "stdin": ""}, format="json")

        self.assertEqual(r.json()["status"], "Compilation Error")



    def test_full_flow_submit_approve_record(self):

        self.login("student1", "student123")

        base = f"/api/workspace/{self.py.id}/"

        self.c.get(base)

        # must run before submit

        r = self.c.post(base + "submit/", {"code": PY_PRIME, "stdin": "7\n"}, format="json")

        self.assertEqual(r.status_code, 400)

        self.c.post(base + "run/", {"code": PY_PRIME, "stdin": "7\n"}, format="json")

        self.c.post(base + "events/", {"events": [

            {"kind": "insert", "chars": 300, "t": int(time.time() * 1000)},

            {"kind": "paste_blocked", "chars": 50},

            {"kind": "run"},  # not allowed from the client - ignored

        ]}, format="json")

        r = self.c.post(base + "submit/", {"code": PY_PRIME, "stdin": "7\n"}, format="json")

        self.assertEqual(r.status_code, 200, r.content)

        # locked after submit

        self.assertEqual(self.c.post(base + "save/", {"code": "x"}, format="json").status_code, 403)



        sub = Submission.objects.get(practical=self.py, student__username="student1")

        # another student cannot see it

        self.login("student2", "student123")

        self.assertEqual(self.c.get(f"/api/submissions/{sub.id}/").status_code, 403)

        self.assertEqual(self.c.get(f"/api/records/submission/{sub.id}/").status_code, 404)



        self.login("teacher", "teacher123")

        rows = self.c.get(f"/api/practicals/{self.py.id}/submissions/").json()["rows"]

        row = [x for x in rows if x["submission_id"] == sub.id][0]

        codes = {i["code"] for i in row["indicators"]}

        self.assertTrue({"large_insertion", "blocked_paste"} <= codes, codes)

        self.assertEqual(len(rows), 4)

        detail = self.c.get(f"/api/submissions/{sub.id}/").json()

        self.assertGreaterEqual(len(detail["versions"]), 1)

        self.assertNotIn("run", [e["kind"] for e in detail["events"] if e["chars"] == 0 and e["detail"] == {}])

        r = self.c.post(f"/api/submissions/{sub.id}/approve/", {"result": "Verified."}, format="json")

        self.assertEqual(r.json()["status"], "approved")



        self.login("student1", "student123")

        r = self.c.get(f"/api/records/subject/{self.py.subject_id}/?type=docx")

        self.assertEqual(r.status_code, 200)

        self.assertTrue(r.content.startswith(b"PK"))

        r = self.c.get(f"/api/records/submission/{sub.id}/?type=pdf")

        self.assertIn(r.status_code, (200, 501))

        if r.status_code == 200:

            self.assertTrue(r.content.startswith(b"%PDF"))



    def test_correction_unlocks(self):

        self.login("student1", "student123")

        base = f"/api/workspace/{self.py.id}/"

        self.c.post(base + "run/", {"code": PY_PRIME, "stdin": "7\n"}, format="json")

        self.c.post(base + "submit/", {"code": PY_PRIME, "stdin": "7\n"}, format="json")

        sub = Submission.objects.get(practical=self.py, student__username="student1")

        self.login("teacher", "teacher123")

        self.c.post(f"/api/submissions/{sub.id}/request-correction/", {"note": "Add comments"}, format="json")

        self.login("student1", "student123")

        self.assertEqual(self.c.post(base + "save/", {"code": PY_PRIME + "# fixed\n"}, format="json").status_code, 200)



    def test_student_cannot_create_practical_or_see_question_directly(self):

        self.login("student1", "student123")

        r = self.c.post("/api/practicals/", {"subject": self.py.subject_id, "experiment_no": 9, "title": "x",

                                             "aim": "x", "question": "x", "language": "c"}, format="json")

        self.assertEqual(r.status_code, 403)

        r = self.c.get(f"/api/practicals/{self.py.id}/")

        self.assertNotIn("question", r.json())



    def test_unenrolled_student_blocked(self):

        User.objects.create_user("outsider", password="pw12345", role="student")

        self.login("outsider", "pw12345")

        self.assertEqual(self.c.get(f"/api/workspace/{self.py.id}/").status_code, 403)



    def test_async_execution_flow(self):

        self.login("student1", "student123")

        base = f"/api/workspace/{self.py.id}/"

        # 1. Trigger async execution

        r = self.c.post(base + "run-async/", {"code": PY_PRIME, "stdin": "7\n"}, format="json")

        self.assertEqual(r.status_code, 202, r.content)

        exec_id = r.json()["execution_id"]

        self.assertIn("poll_url", r.json())



        # 2. Check execution detail endpoint

        r_poll = self.c.get(f"/api/executions/{exec_id}/")

        self.assertEqual(r_poll.status_code, 200)

        data = r_poll.json()

        self.assertEqual(data["status"], "Accepted")

        self.assertEqual(data["state"], "COMPLETED")

        self.assertTrue(data["is_complete"])

        self.assertIn("Prime", data["stdout"])



        # 3. Isolation: student2 cannot access student1's execution

        self.login("student2", "student123")

        r_forbidden = self.c.get(f"/api/executions/{exec_id}/")

        self.assertEqual(r_forbidden.status_code, 403)



        # 4. Teacher CAN access student1's execution

        self.login("teacher", "teacher123")

        r_teacher = self.c.get(f"/api/executions/{exec_id}/")

        self.assertEqual(r_teacher.status_code, 200)



    def test_submit_rejects_older_success_when_newer_execution_is_pending(self):
        self.login("student1", "student123")
        base = f"/api/workspace/{self.py.id}/"
        run = self.c.post(base + "run/", {"code": PY_PRIME, "stdin": "7\n"}, format="json")
        self.assertEqual(run.status_code, 200, run.content)
        sub = Submission.objects.get(practical=self.py, student__username="student1")
        Execution.objects.create(
            submission=sub, code=PY_PRIME, stdin="7\n",
            state=Execution.State.PROCESSING, status="In Queue",
        )
        response = self.c.post(base + "submit/", {"code": PY_PRIME, "stdin": "7\n"}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["code"], "run_required")

    def test_submit_rejects_code_or_stdin_different_from_latest_success(self):
        self.login("student1", "student123")
        base = f"/api/workspace/{self.py.id}/"
        self.c.post(base + "run/", {"code": PY_PRIME, "stdin": "7\n"}, format="json")

        wrong_code = self.c.post(
            base + "submit/", {"code": PY_PRIME + "# changed\n", "stdin": "7\n"}, format="json"
        )
        self.assertEqual(wrong_code.status_code, 400)
        self.assertEqual(wrong_code.json()["code"], "run_required")

        wrong_stdin = self.c.post(
            base + "submit/", {"code": PY_PRIME, "stdin": "11\n"}, format="json"
        )
        self.assertEqual(wrong_stdin.status_code, 400)
        self.assertEqual(wrong_stdin.json()["code"], "run_required")

    def test_execution_api_does_not_expose_internal_judge0_fields(self):
        self.login("student1", "student123")
        base = f"/api/workspace/{self.py.id}/"
        response = self.c.post(
            base + "run-async/", {"code": PY_PRIME, "stdin": "7\n"}, format="json"
        )
        self.assertEqual(response.status_code, 202, response.content)
        execution = self.c.get(f"/api/executions/{response.json()['execution_id']}/")
        self.assertEqual(execution.status_code, 200)
        self.assertNotIn("judge0_token", execution.json())
        self.assertNotIn("last_error", execution.json())

    def test_cannot_submit_while_execution_pending(self):

        self.login("student1", "student123")

        base = f"/api/workspace/{self.py.id}/"

        st = User.objects.get(username="student1")

        sub, _ = Submission.objects.get_or_create(practical=self.py, student=st, defaults={"code": self.py.starter_code})

        # Create a pending execution manually

        Execution.objects.create(

            submission=sub, code=PY_PRIME, stdin="7\n",

            state=Execution.State.PROCESSING, status="In Queue"

        )

        r = self.c.post(base + "submit/", {"code": PY_PRIME, "stdin": "7\n"}, format="json")

        self.assertEqual(r.status_code, 400)

        self.assertEqual(r.json()["code"], "run_required")


class AsyncExecutionTaskTests(TestCase):
    def setUp(self):
        call_command("seed_demo", stdout=open(os.devnull, "w"))
        self.c = APIClient()
        self.py = Practical.objects.get(language="python")
        self.student = User.objects.get(username="student1")
        self.sub, _ = Submission.objects.get_or_create(
            practical=self.py,
            student=self.student,
            defaults={"code": self.py.starter_code}
        )

    def login(self, username, pw):
        r = self.c.post("/api/auth/login/", {"username": username, "password": pw}, format="json")
        self.assertEqual(r.status_code, 200)
        self.c.credentials(HTTP_AUTHORIZATION="Bearer " + r.json()["access"])

    @override_settings(CODE_EXECUTOR="judge0", EXECUTION_POLL_INITIAL_INTERVAL_SECONDS=0.5)
    @patch("labs.tasks.poll_execution_task.apply_async")
    @patch("requests.post")
    def test_judge0_dispatch_success_schedules_poll(self, mock_post, mock_apply_async):
        mock_resp = MagicMock()
        mock_resp.status_code = 201
        mock_resp.json.return_value = {"token": "token-test-123"}
        mock_post.return_value = mock_resp

        ex = Execution.objects.create(
            submission=self.sub,
            code="print('Hello Async')",
            stdin="",
            state=Execution.State.QUEUED,
            status="In Queue"
        )

        res = dispatch_execution_task(ex.id)
        self.assertTrue(res)

        ex.refresh_from_db()
        self.assertEqual(ex.state, Execution.State.PROCESSING)
        self.assertEqual(ex.judge0_token, "token-test-123")
        self.assertEqual(ex.status, "In Queue")

        # Verify requests.post was called with wait=false
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertIn("wait=false", args[0])

        # Verify poll task was scheduled with countdown
        mock_apply_async.assert_called_once_with(args=[ex.id, 0.5], countdown=0.5)

    @override_settings(CODE_EXECUTOR="judge0")
    @patch("requests.post")
    def test_judge0_dispatch_ambiguous_timeout(self, mock_post):
        mock_post.side_effect = requests.exceptions.Timeout("Read timeout on POST")

        ex = Execution.objects.create(
            submission=self.sub,
            code="print('Ambiguous')",
            stdin="",
            state=Execution.State.QUEUED,
            status="In Queue"
        )

        res = dispatch_execution_task(ex.id)
        self.assertFalse(res)

        ex.refresh_from_db()
        self.assertEqual(ex.state, Execution.State.SUBMITTED_TO_RUNNER)
        self.assertEqual(ex.retry_count, 1)
        self.assertIn("Ambiguous dispatch timeout", ex.last_error)

        # Subsequent call does NOT re-dispatch (avoids duplicate execution)
        mock_post.reset_mock()
        res2 = dispatch_execution_task(ex.id)
        self.assertFalse(res2)
        mock_post.assert_not_called()

    def test_duplicate_task_delivery_guard(self):
        ex = Execution.objects.create(
            submission=self.sub,
            code="print('Done')",
            stdin="",
            state=Execution.State.COMPLETED,
            status="Accepted"
        )
        with patch("requests.post") as mock_post:
            res = dispatch_execution_task(ex.id)
            self.assertTrue(res)
            mock_post.assert_not_called()

        with patch("requests.get") as mock_get:
            res_poll = poll_execution_task(ex.id)
            self.assertTrue(res_poll)
            mock_get.assert_not_called()

    @override_settings(CELERY_TASK_ALWAYS_EAGER=False)
    @patch("labs.tasks.poll_execution_task.apply_async")
    @patch("requests.get")
    def test_poll_task_pending_status_reschedules(self, mock_get, mock_apply_async):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": {"id": 2, "description": "Processing"}
        }
        mock_get.return_value = mock_resp

        ex = Execution.objects.create(
            submission=self.sub,
            code="print('Waiting')",
            stdin="",
            state=Execution.State.PROCESSING,
            status="In Queue",
            judge0_token="token-abc"
        )

        res = poll_execution_task(ex.id, current_interval=0.5)
        self.assertIsNone(res)

        ex.refresh_from_db()
        self.assertEqual(ex.status, "Processing")
        self.assertEqual(ex.state, Execution.State.PROCESSING)

        # Backoff: 0.5 * 1.25 = 0.625
        mock_apply_async.assert_called_once_with(args=[ex.id, 0.625], countdown=0.625)

    @patch("requests.get")
    def test_poll_task_terminal_accepted_finalizes_execution(self, mock_get):
        stdout_b64 = base64.b64encode(b"Output Hello\n").decode()
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": {"id": 3, "description": "Accepted"},
            "stdout": stdout_b64,
            "stderr": None,
            "compile_output": None,
            "time": "0.045",
            "memory": 2048
        }
        mock_get.return_value = mock_resp

        ex = Execution.objects.create(
            submission=self.sub,
            code="print('Output Hello')",
            stdin="",
            state=Execution.State.PROCESSING,
            status="Processing",
            judge0_token="token-abc"
        )

        res = poll_execution_task(ex.id)
        self.assertTrue(res)

        ex.refresh_from_db()
        self.assertEqual(ex.state, Execution.State.COMPLETED)
        self.assertEqual(ex.status, "Accepted")
        self.assertEqual(ex.stdout, "Output Hello\n")
        self.assertEqual(ex.time, "0.045")
        self.assertEqual(ex.memory, 2048)
        self.assertIsNotNone(ex.completed_at)

        # Activity event created
        event = ActivityEvent.objects.filter(submission=self.sub, kind=ActivityEvent.Kind.RUN).latest("created_at")
        self.assertEqual(event.detail.get("status"), "Accepted")
        self.assertEqual(event.detail.get("time"), "0.045")

    @override_settings(EXECUTION_POLL_TIMEOUT_SECONDS=30)
    @patch("requests.get")
    def test_poll_task_deadline_timeout(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {
            "status": {"id": 1, "description": "In Queue"}
        }
        mock_get.return_value = mock_resp

        ex = Execution.objects.create(
            submission=self.sub,
            code="while True: pass",
            stdin="",
            state=Execution.State.PROCESSING,
            status="In Queue",
            judge0_token="token-abc",
            started_at=timezone.now() - timedelta(seconds=35)
        )

        res = poll_execution_task(ex.id)
        self.assertFalse(res)

        ex.refresh_from_db()
        self.assertEqual(ex.state, Execution.State.TIMED_OUT)
        self.assertEqual(ex.status, "Time Limit Exceeded")
        self.assertIn("timed out waiting for sandbox worker", ex.stderr)
        self.assertIsNotNone(ex.completed_at)

    @patch("requests.get")
    def test_poll_task_runner_404_fails_cleanly(self, mock_get):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_get.return_value = mock_resp

        ex = Execution.objects.create(
            submission=self.sub,
            code="print('Lost')",
            stdin="",
            state=Execution.State.PROCESSING,
            status="In Queue",
            judge0_token="missing-token"
        )

        res = poll_execution_task(ex.id)
        self.assertFalse(res)

        ex.refresh_from_db()
        self.assertEqual(ex.state, Execution.State.FAILED)
        self.assertEqual(ex.status, "System Error")
        self.assertIn("not found on runner", ex.last_error)

    def test_workspace_run_async_broker_enqueue_failure(self):
        self.login("student1", "student123")
        base = f"/api/workspace/{self.py.id}/"

        with patch("labs.tasks.dispatch_execution_task.delay", side_effect=Exception("Redis connection refused")):
            r = self.c.post(base + "run-async/", {"code": "print('Test')", "stdin": ""}, format="json")

        self.assertEqual(r.status_code, 503)
        self.assertEqual(r.json()["code"], "queue_unavailable")
        self.assertNotIn("Redis connection refused", r.json()["detail"])

        # Confirm no orphaned QUEUED execution exists
        failed_ex = Execution.objects.filter(submission=self.sub, state=Execution.State.FAILED).latest("created_at")
        self.assertEqual(failed_ex.status, "System Error")
        self.assertIn("broker unavailable", failed_ex.last_error)

    @patch("labs.tasks.poll_execution_task.delay")
    def test_reconcile_stale_executions_task(self, mock_poll_delay):
        old_time = timezone.now() - timedelta(seconds=250)

        # 1. PROCESSING with token -> should resume poll
        ex_proc = Execution.objects.create(
            submission=self.sub, code="c1", state=Execution.State.PROCESSING,
            judge0_token="tok1", status="Processing"
        )
        Execution.objects.filter(id=ex_proc.id).update(created_at=old_time)

        # 2. SUBMITTED_TO_RUNNER with token -> should move to PROCESSING & resume poll
        ex_sub = Execution.objects.create(
            submission=self.sub, code="c2", state=Execution.State.SUBMITTED_TO_RUNNER,
            judge0_token="tok2", status="In Queue"
        )
        Execution.objects.filter(id=ex_sub.id).update(created_at=old_time)

        # 3. SUBMITTED_TO_RUNNER without token -> should fail
        ex_ambig = Execution.objects.create(
            submission=self.sub, code="c3", state=Execution.State.SUBMITTED_TO_RUNNER,
            judge0_token="", status="In Queue"
        )
        Execution.objects.filter(id=ex_ambig.id).update(created_at=old_time)

        # 4. QUEUED without token -> should fail
        ex_queued = Execution.objects.create(
            submission=self.sub, code="c4", state=Execution.State.QUEUED,
            judge0_token="", status="In Queue"
        )
        Execution.objects.filter(id=ex_queued.id).update(created_at=old_time)

        report = reconcile_stale_executions(stale_threshold_seconds=180)
        self.assertEqual(report["reconciled"], 4)
        self.assertEqual(report["resumed"], 2)
        self.assertEqual(report["failed"], 2)

        ex_proc.refresh_from_db()
        ex_sub.refresh_from_db()
        ex_ambig.refresh_from_db()
        ex_queued.refresh_from_db()

        self.assertEqual(ex_proc.state, Execution.State.PROCESSING)
        self.assertEqual(ex_sub.state, Execution.State.PROCESSING)
        self.assertEqual(ex_ambig.state, Execution.State.FAILED)
        self.assertEqual(ex_ambig.status, "System Error")
        self.assertEqual(ex_queued.state, Execution.State.FAILED)
        self.assertEqual(ex_queued.status, "System Error")
