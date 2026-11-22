# LABORA — Comprehensive API Documentation & Contract Specification

**Base URL:** `/api/`  
**Authentication Standard:** HTTP Authorization Header: `Bearer <jwt_access_token>`  
**Secure Browser Attestation:** Headers: `X-Labora-Ts`, `X-Labora-Signature`, `X-Labora-Client`  
**Throttling:** Default User: `600/min`; Execution (`RunThrottle`): `20/min`; Login: `20/min`  

---

## 1. Authentication & Session Endpoints

### 1.1 User Login
- **URL:** `POST /api/auth/login/`
- **Permissions:** `AllowAny`
- **Rate Limit:** `20/min` (Anonymous IP throttle)
- **Optional Headers:** `X-Labora-Ts`, `X-Labora-Signature`
- **Request Body (JSON):**
  ```json
  {
    "username": "student1",
    "password": "student123"
  }
  ```
- **Responses:**
  - `200 OK`:
    ```json
    {
      "access": "eyJhbGciOi...",
      "refresh": "eyJhbGciOi...",
      "user": {
        "id": 3,
        "username": "student1",
        "full_name": "Student A",
        "role": "student",
        "roll_no": "MCA001",
        "batch": "2025-27",
        "semester": 1,
        "department_name": "Computer Applications"
      }
    }
    ```
  - `401 Unauthorized`: `{"detail": "Invalid username or password."}`
  - `403 Forbidden`: `{"detail": "Students must sign in from the LABORA Secure Browser.", "code": "secure_browser_required"}` (when `students_secure_browser_only=True` and signature missing).

### 1.2 Token Refresh
- **URL:** `POST /api/auth/refresh/`
- **Permissions:** `AllowAny`
- **Request Body:** `{"refresh": "eyJhbGciOi..."}`
- **Responses:**
  - `200 OK`: `{"access": "eyJhbGciOi..."}`
  - `401 Unauthorized`: Token invalid or expired.

### 1.3 Active User Profile (`Me`)
- **URL:** `GET /api/auth/me/`
- **Permissions:** `IsAuthenticated`
- **Responses:**
  - `200 OK`: Returns authenticated user JSON (same schema as `user` in login response).

### 1.4 Secure Browser Client Status
- **URL:** `GET /api/client-status/`
- **Permissions:** `AllowAny`
- **Headers Checked:** `X-Labora-Ts`, `X-Labora-Signature`
- **Response:**
  - `200 OK`: `{"secure_browser": true, "college_name": "Demo College of Engineering"}`

---

## 2. Institutional Administration Endpoints

### 2.1 College Settings
- **URL:** `GET /api/college-settings/`
  - **Permissions:** `IsAuthenticated`
  - **Response `200 OK`:**
    ```json
    {
      "college_name": "Demo College of Engineering",
      "college_address": "Kerala, India",
      "logo": "/media/logo/college.png",
      "record_title": "LABORATORY RECORD",
      "record_footer": "Certified bonafide record of work done by the student.",
      "students_secure_browser_only": false
    }
    ```
- **URL:** `PUT/PATCH /api/college-settings/`
  - **Permissions:** `IsAdminRole`
  - **Request Body:** Partial or full settings fields.

### 2.2 Department Management (`/api/departments/`)
- `GET`: Lists all departments (`ReadOnlyOrAdmin`).
- `POST`: Creates a department (`IsAdminRole`). Payload: `{"name": "Mechanical", "code": "ME"}`.

### 2.3 User Management (`/api/users/`)
- `GET`: Lists users (`IsAdminRole`). Query params: `?role=student`.
- `POST`: Creates user (`IsAdminRole`).
- `POST /api/users/import/`: Bulk CSV user onboarding (`IsAdminRole`).
  - **Input:** Multipart form upload (`file`).
  - **Expected CSV Format:**
    `username,password,first_name,last_name,role,roll_no,batch,semester,department_code`
  - **Response `200 OK`:** `{"created": 45, "errors": []}`

### 2.4 Subject Management (`/api/subjects/`)
- `GET`: Lists subjects (`ReadOnlyOrAdmin`). Filtered automatically by caller's role.
- `POST`: Creates subject (`IsAdminRole`).
- `POST /api/subjects/<id>/enroll/`: Bulk enrolls students (`IsAdminRole`).
  - **Payload:** `{"students": ["MCA001", "student2"]}`
  - **Response `200 OK`:** `{"enrolled": 2, "not_found": []}`

---

## 3. Practical Examination Endpoints

### 3.1 Practicals List & Detail (`/api/practicals/`)
- `GET /api/practicals/`: Lists practicals for user's courses.
- `GET /api/practicals/<id>/`: Detail view.
  - **Note for Students:** The serializer automatically strips `question`, `starter_code`, `sample_input`, and `aim`. Students can only receive problem details through `/api/workspace/<id>/`.
- `POST /api/practicals/`: Teacher creates assignment (`IsTeacherOrAdmin`).
  - **Payload:**
    ```json
    {
      "subject": 1,
      "experiment_no": 4,
      "title": "Binary Search Tree",
      "aim": "To implement BST insertion and traversal in C.",
      "question": "Write a C program to implement BST...",
      "language": "c",
      "starter_code": "#include <stdio.h>\n...",
      "sample_input": "5\n10 20 5 15 30\n",
      "restricted": true,
      "require_secure_browser": true,
      "is_published": true,
      "due_date": "2026-11-30T17:00:00Z"
    }
    ```

### 3.2 Teacher Practical Submissions Dashboard
- **URL:** `GET /api/practicals/<id>/submissions/`
- **Permissions:** `IsTeacherOrAdmin`
- **Response `200 OK`:**
  ```json
  {
    "practical": { "id": 1, "title": "Sum of N Numbers", "language": "c" },
    "rows": [
      {
        "student_id": 3,
        "student_name": "Student A",
        "roll_no": "MCA001",
        "submission_id": 12,
        "status": "submitted",
        "runs": 4,
        "submitted_at": "2026-11-22T08:15:00Z",
        "indicators": [
          { "code": "large_insertion", "label": "Large insertion", "detail": "1 single insertion(s) of 120+ characters." }
        ]
      }
    ]
  }
  ```

---

## 4. Student Workspace Endpoints

### 4.1 Initialize Workspace
- **URL:** `GET /api/workspace/<id>/`
- **Permissions:** `IsStudent`
- **Security Check:** If `require_secure_browser=True`, request MUST carry valid HMAC headers (`X-Labora-Signature`).
- **Response `200 OK`:**
  ```json
  {
    "practical": {
      "id": 1,
      "experiment_no": 1,
      "title": "Sum of N Numbers",
      "question": "Write a C program...",
      "language": "c",
      "starter_code": "#include <stdio.h>\n...",
      "sample_input": "5\n1 2 3 4 5\n",
      "restricted": true,
      "require_secure_browser": true
    },
    "submission": {
      "id": 12,
      "code": "#include <stdio.h>\nint main() { ... }",
      "status": "in_progress",
      "locked": false
    },
    "last_execution": null,
    "secure_browser": true
  }
  ```

### 4.2 Workspace Autosave
- **URL:** `POST /api/workspace/<id>/save/`
- **Permissions:** `IsStudent`
- **Payload:** `{"code": "#include <stdio.h>\n..."}`
- **Response `200 OK`:** `{"saved_at": "2026-11-22T08:10:00Z", "version": 3}`

### 4.3 Workspace Asynchronous Code Execution (Recommended)
- **URL:** `POST /api/workspace/<id>/run-async/`
- **Permissions:** `IsStudent`
- **Rate Limit:** `20/min`
- **Payload:** `{"code": "...", "stdin": "5\n"}`
- **Response `202 Accepted`:**
  ```json
  {
    "execution_id": 48,
    "state": "QUEUED",
    "status": "In Queue",
    "created_at": "2026-11-22T08:12:00Z",
    "poll_url": "/api/executions/48/"
  }
  ```

### 4.4 Execution Status Polling
- **URL:** `GET /api/executions/<pk>/` (or `/api/workspace/<id>/executions/<pk>/`)
- **Permissions:** `IsAuthenticated` (Student must own execution; teacher must teach subject)
- **Response `200 OK`:**
  ```json
  {
    "id": 48,
    "stdin": "5\n",
    "stdout": "Sum = 15\n",
    "stderr": "",
    "compile_output": "",
    "status": "Accepted",
    "state": "COMPLETED",
    "is_complete": true,
    "time": "0.02",
    "memory": 2100,
    "judge0_token": "a1b2c3d4-...",
    "last_error": "",
    "started_at": "2026-11-22T08:12:01Z",
    "completed_at": "2026-11-22T08:12:03Z",
    "created_at": "2026-11-22T08:12:00Z"
  }
  ```

### 4.5 Batch Telemetry Ingestion
- **URL:** `POST /api/workspace/<id>/events/`
- **Permissions:** `IsStudent`
- **Payload:**
  ```json
  {
    "events": [
      { "kind": "insert", "chars": 12, "t": 1732263120000, "detail": {} },
      { "kind": "paste_blocked", "chars": 45, "t": 1732263125000 },
      { "kind": "focus_lost", "chars": 0, "t": 1732263130000 }
    ]
  }
  ```
- **Response `200 OK`:** `{"stored": 3}`

### 4.6 Final Practical Submission
- **URL:** `POST /api/workspace/<id>/submit/`
- **Permissions:** `IsStudent`
- **Payload:** `{"code": "..."}`
- **Validation:** Code must exactly match the code of the student's latest `status="Accepted"` and `state="COMPLETED"` execution.
- **Response `200 OK`:** Returns updated workspace payload with `submission.status="submitted"` and `locked=true`.
- **Response `400 Bad Request`:** `{"detail": "Run your final program successfully before submitting, so the record contains its real output.", "code": "run_required"}`

---

## 5. Teacher Review & Grading Endpoints

### 5.1 Review Dossier
- **URL:** `GET /api/submissions/<pk>/`
- **Permissions:** `IsTeacherOrAdmin`
- **Response `200 OK`:** Returns full dossier: `submission`, `practical`, `versions` array, `events` array, `executions` array, `indicators` list, `ai_enabled` flag.

### 5.2 Approve Submission
- **URL:** `POST /api/submissions/<pk>/approve/`
- **Permissions:** `IsTeacherOrAdmin`
- **Payload:**
  ```json
  {
    "execution_id": 48,
    "result": "Output verified. Program executes in O(N) time.",
    "note": "Good code style and comments."
  }
  ```
- **Response `200 OK`:** Updated submission object with `status="approved"`.

### 5.3 Request Correction
- **URL:** `POST /api/submissions/<pk>/request-correction/`
- **Permissions:** `IsTeacherOrAdmin`
- **Payload:** `{"note": "Handle negative input edge case."}`
- **Response `200 OK`:** Submission unlocks and status changes to `correction`.

### 5.4 AI Submission Summary (Optional)
- **URL:** `POST /api/submissions/<pk>/ai-summary/`
- **Permissions:** `IsTeacherOrAdmin`
- **Response `200 OK`:** `{"summary": "1. Program structure: ... 2. Concepts: ...", "note": "AI output is a review aid only, not proof."}`

---

## 6. Official Lab Records & Analytics Endpoints

### 6.1 Records Overview (Student)
- **URL:** `GET /api/records/`
- **Permissions:** `IsStudent`
- **Response `200 OK`:** Returns approved practicals per course ready for export.

### 6.2 Full Subject Lab Record Export
- **URL:** `GET /api/records/subject/<subject_id>/?type=docx` (or `?type=pdf`)
- **Permissions:** `IsAuthenticated` (Teacher must supply `?student=<id>`)
- **Response `200 OK`:** Binary file download with `Content-Disposition: attachment; filename="LabRecord_MCA101_MCA001.docx"`.

### 6.3 Single Practical Record Export
- **URL:** `GET /api/records/submission/<pk>/?type=docx` (or `?type=pdf`)
- **Response `200 OK`:** Binary download of single experiment record.

### 6.4 Subject Progress Analytics Report
- **URL:** `GET /api/reports/subject/<subject_id>/`
- **Permissions:** `IsTeacherOrAdmin`
- **Response `200 OK`:** Aggregated counts across practicals: `students`, `not_started`, `in_progress`, `submitted`, `correction`, `approved`, `with_indicators`.
