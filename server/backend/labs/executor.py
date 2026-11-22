"""
Program execution.

Production: Judge0 (self-hosted or RapidAPI). Untrusted student code never runs
on the LABORA server.

Development: CODE_EXECUTOR=local runs code with a timeout in a temp directory on
this machine. It is NOT a sandbox - use it only on a developer laptop.
"""
import base64
import os
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass

import requests
from django.conf import settings


@dataclass
class RunResult:
    status: str
    stdout: str = ""
    stderr: str = ""
    compile_output: str = ""
    time: str = ""
    memory: int | None = None


class ExecutorError(Exception):
    pass


def _b64(s: str) -> str:
    return base64.b64encode((s or "").encode()).decode()


def _unb64(s):
    if not s:
        return ""
    return base64.b64decode(s).decode(errors="replace")


def run_judge0(language: str, code: str, stdin: str) -> RunResult:
    lang_id = settings.JUDGE0_LANGUAGE_IDS[language]
    headers = {"Content-Type": "application/json"}
    if settings.JUDGE0_RAPIDAPI_HOST:
        headers["X-RapidAPI-Key"] = settings.JUDGE0_API_KEY
        headers["X-RapidAPI-Host"] = settings.JUDGE0_RAPIDAPI_HOST
    elif settings.JUDGE0_API_KEY:
        headers["X-Auth-Token"] = settings.JUDGE0_API_KEY
    payload = {
        "language_id": lang_id,
        "source_code": _b64(code),
        "stdin": _b64(stdin),
        "cpu_time_limit": settings.EXECUTION_TIMEOUT_SECONDS,
    }
    url = settings.JUDGE0_URL.rstrip("/") + "/submissions?base64_encoded=true&wait=true"
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=60)
    except requests.RequestException as exc:
        raise ExecutorError(f"Could not reach Judge0 at {settings.JUDGE0_URL}: {exc}") from exc
    if resp.status_code >= 400:
        raise ExecutorError(f"Judge0 returned HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json()
    return RunResult(
        status=(data.get("status") or {}).get("description", "Unknown"),
        stdout=_unb64(data.get("stdout")),
        stderr=_unb64(data.get("stderr")),
        compile_output=_unb64(data.get("compile_output")),
        time=str(data.get("time") or ""),
        memory=data.get("memory"),
    )


def _proc(cmd, cwd, stdin, timeout):
    return subprocess.run(cmd, cwd=cwd, input=stdin, capture_output=True, text=True, timeout=timeout)


def run_local(language: str, code: str, stdin: str) -> RunResult:
    """DEVELOPMENT ONLY. Mirrors Judge0 status names."""
    timeout = settings.EXECUTION_TIMEOUT_SECONDS
    work = tempfile.mkdtemp(prefix="labora-run-")
    try:
        if language == "python":
            path = os.path.join(work, "main.py")
            open(path, "w").write(code)
            run_cmd = [sys.executable, "-I", path]
        elif language == "c":
            src = os.path.join(work, "main.c")
            open(src, "w").write(code)
            exe = os.path.join(work, "main.exe" if os.name == "nt" else "main")
            try:
                comp = _proc(["gcc", src, "-o", exe, "-lm"], work, "", 30)
            except FileNotFoundError:
                raise ExecutorError("gcc is not installed on this server (needed for C in local mode).")
            if comp.returncode != 0:
                return RunResult(status="Compilation Error", compile_output=comp.stderr)
            run_cmd = [exe]
        elif language == "java":
            src = os.path.join(work, "Main.java")
            open(src, "w").write(code)
            try:
                comp = _proc(["javac", src], work, "", 60)
            except FileNotFoundError:
                raise ExecutorError("javac (JDK) is not installed on this server (needed for Java in local mode).")
            if comp.returncode != 0:
                return RunResult(status="Compilation Error", compile_output=comp.stderr)
            run_cmd = ["java", "-cp", work, "Main"]
        else:
            raise ExecutorError(f"Unsupported language {language}")
        try:
            p = _proc(run_cmd, work, stdin, timeout)
        except subprocess.TimeoutExpired as exc:
            out = exc.stdout.decode(errors="replace") if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            return RunResult(status="Time Limit Exceeded", stdout=out)
        status = "Accepted" if p.returncode == 0 else "Runtime Error (NZEC)"
        return RunResult(status=status, stdout=p.stdout, stderr=p.stderr)
    finally:
        shutil.rmtree(work, ignore_errors=True)


def run_code(language: str, code: str, stdin: str = "") -> RunResult:
    if settings.CODE_EXECUTOR == "local":
        return run_local(language, code, stdin)
    return run_judge0(language, code, stdin)
