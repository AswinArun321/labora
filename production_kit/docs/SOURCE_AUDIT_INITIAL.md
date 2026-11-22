# LABORA Source Audit — Initial Inspection

Source: `LABORA-Test-Windows(1).zip` supplied in this conversation.
Inspection copy: `/mnt/data/labora_working/LABORA-Test-Windows`.
Original uploaded ZIP has not been modified.

## Verified archive facts
- ZIP integrity check passed.
- 146 archive entries; 127 regular files after extraction.
- Includes Windows batch launchers and README.
- Includes Electron Secure Browser packaged application.
- Includes Django backend and React `dist` assets.
- Does not include `production_kit/` or `delivery_evidence/`.

## Verified implementation facts
- Django app includes `accounts` and `labs`.
- Existing `Execution` model has code/stdin/stdout/stderr/compile_output/status/time/memory/created_at.
- It does not currently include Judge0 token, runner identity, queue error or completion timestamp fields.
- `workspace_run` is a synchronous DRF endpoint. It calls `run_code`, then creates the Execution row after the call returns.
- `run_judge0` posts to `/submissions?...&wait=true`.
- `run_local` invokes Python/GCC/Javac/Java subprocesses on the Django host. Its module docstring explicitly says this is development-only and not a sandbox.
- Settings default `DEBUG=True`, use a development secret fallback and default to SQLite unless `POSTGRES_DB` is configured.
- `CODE_EXECUTOR` defaults to `judge0`; local mode can be selected through environment.
- Existing API paths include login, workspace, save, run, events, submit, submissions, records and reports.

## Critical implications
1. Do not expose the current default settings to the internet.
2. Do not run student code through `CODE_EXECUTOR=local` in production.
3. Async execution needs persistent state fields and an integrated API/worker path.
4. Async submission workflow must be reconciled with the existing submit flow, which currently expects an already-completed Accepted execution.
5. The existing Secure Browser shared HMAC key is configured in the client package; this requires threat-model review and should not be treated as strong client attestation.

## Not yet verified
- Full Django test suite result.
- Frontend source availability/build reproducibility.
- Electron source build reproducibility and code-signing.
- Production Docker build.
- Judge0 sandbox deployment.
- PostgreSQL migration and restore.
- Actual security test results.
- Any 1,000-user load-test result.
