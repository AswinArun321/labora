export interface User {
  id: number;
  username: string;
  first_name: string;
  last_name: string;
  full_name: string;
  role: 'student' | 'teacher' | 'admin';
  roll_no?: string;
  batch?: string;
  semester?: number;
  department?: number | null;
  department_name?: string;
  is_active: boolean;
}

export interface Department {
  id: number;
  code: string;
  name: string;
}

export interface Subject {
  id: number;
  code: string;
  name: string;
  semester: number;
  academic_year: string;
  department: number;
  teachers: number[];
  teacher_names: string[];
  student_count?: number;
}

export interface Practical {
  id: number;
  subject: number;
  subject_code: string;
  subject_name?: string;
  experiment_no: number;
  title: string;
  aim: string;
  question: string;
  language: 'c' | 'java' | 'python';
  starter_code: string;
  sample_input: string;
  restricted: boolean;
  require_secure_browser: boolean;
  is_published: boolean;
  due_date: string | null;
  created_at?: string;
  updated_at?: string;
}

export interface Submission {
  id: number;
  student: number;
  student_name: string;
  roll_no: string;
  practical: number;
  code: string;
  status: 'not_started' | 'in_progress' | 'submitted' | 'correction' | 'approved';
  teacher_note?: string;
  result?: string;
  submitted_at?: string | null;
  approved_at?: string | null;
  record_execution?: number | null;
  locked?: boolean;
}

export interface Execution {
  id: number;
  submission?: number;
  status: string;
  state?: 'QUEUED' | 'DISPATCHING' | 'RUNNING' | 'COMPLETED' | 'FAILED' | 'TIMEOUT';
  stdin: string;
  stdout: string;
  stderr: string;
  compile_output: string;
  time: string | null;
  memory: number | null;
  created_at: string;
  is_complete?: boolean;
  execution_id?: number;
}

export interface CodeVersion {
  id: number;
  number: number;
  reason: string;
  code: string;
  created_at: string;
}

export interface ActivityEvent {
  id: number;
  kind: string;
  kind_label: string;
  chars: number;
  detail?: Record<string, any>;
  client_time?: number;
  created_at: string;
  secure_browser?: boolean;
}

export interface Indicator {
  code: string;
  label: string;
  detail: string;
}

export interface CollegeSettings {
  college_name: string;
  college_address: string;
  record_title: string;
  record_footer: string;
  students_secure_browser_only: boolean;
  logo?: string | null;
}

export interface ClientStatus {
  college_name: string;
  logo?: string | null;
  students_secure_browser_only: boolean;
  is_secure_browser: boolean;
}

export interface WorkspaceData {
  practical: Practical;
  submission: Submission;
  last_execution: Execution | null;
}

export interface PracticalSubmissionRow {
  student_id: number;
  student_name: string;
  roll_no: string;
  submission_id: number | null;
  status: 'not_started' | 'in_progress' | 'submitted' | 'correction' | 'approved';
  runs: number;
  submitted_at: string | null;
  indicators: Indicator[];
}

export interface PracticalSubmissionsResponse {
  practical: Practical;
  rows: PracticalSubmissionRow[];
}

export interface SubmissionDetailResponse {
  submission: Submission;
  practical: Practical;
  versions: CodeVersion[];
  executions: Execution[];
  events: ActivityEvent[];
  indicators: Indicator[];
  ai_enabled?: boolean;
}

export interface SubjectReportRow {
  practical_id: number;
  experiment_no: number;
  title: string;
  language: 'c' | 'java' | 'python';
  students: number;
  not_started: number;
  in_progress: number;
  submitted: number;
  correction: number;
  approved: number;
  with_indicators: number;
}

export interface SubjectReportResponse {
  subject: Subject;
  rows: SubjectReportRow[];
}

export interface StudentSubjectRecord {
  subject: {
    id: number;
    code: string;
    name: string;
  };
  total: number;
  approved: {
    submission_id: number;
    experiment_no: number;
    title: string;
    language: string;
    approved_at: string;
  }[];
}

export interface AuthTokens {
  access: string;
  refresh: string;
}
