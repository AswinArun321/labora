import time

from django.core.management import call_command
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from accounts.models import CollegeSettings, User
from labs.models import Practical, Submission
from labs.secure_browser import compute_signature

KEY = "test-key"

PY_PRIME = (
    "n = int(input('Enter a number: '))\n"
    "print('Prime' if n > 1 and all(n % i for i in range(2, int(n**0.5) + 1)) else 'Not prime')\n"
)
C_SUM = (
    "#include <stdio.h>\nint main(){int n,x,s=0;scanf(\"%d\",&n);"
    "for(int i=0;i<n;i++){scanf(\"%d\",&x);s+=x;}printf(\"Sum = %d\\n\",s);return 0;}\n"
)
JAVA_FACT = (
    "import java.util.Scanner;\npublic class Main{static long f(int n){return n<=1?1:n*f(n-1);}"
    "public static void main(String[] a){int n=new Scanner(System.in).nextInt();System.out.println(f(n));}}\n"
)


@override_settings(CODE_EXECUTOR="local", SECURE_BROWSER_KEY=KEY)
class LaboraFlowTests(TestCase):
    def setUp(self):
        call_command("seed_demo", stdout=open("/dev/null", "w"))
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
        r = self.c.post(base + "submit/", {"code": PY_PRIME}, format="json")
        self.assertEqual(r.status_code, 400)
        self.c.post(base + "run/", {"code": PY_PRIME, "stdin": "7\n"}, format="json")
        self.c.post(base + "events/", {"events": [
            {"kind": "insert", "chars": 300, "t": int(time.time() * 1000)},
            {"kind": "paste_blocked", "chars": 50},
            {"kind": "run"},  # not allowed from the client - ignored
        ]}, format="json")
        r = self.c.post(base + "submit/", {"code": PY_PRIME}, format="json")
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
        self.c.post(base + "submit/", {"code": PY_PRIME}, format="json")
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
