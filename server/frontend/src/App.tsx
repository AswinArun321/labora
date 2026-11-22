import { Routes, Route, Navigate } from 'react-router-dom';
import { useAuth } from './context/AuthContext';
import { LoadingSpinner } from './components/LoadingSpinner';
import { LoginPage } from './pages/auth/LoginPage';

// Student pages
import { StudentDashboard } from './pages/student/Dashboard';
import { StudentRecords } from './pages/student/Records';
import { StudentWorkspace } from './pages/student/Workspace';

// Teacher & Admin shared pages
import { TeacherSubjects } from './pages/teacher/Subjects';
import { PracticalForm } from './pages/teacher/PracticalForm';
import { PracticalSubmissions } from './pages/teacher/Submissions';
import { SubmissionReview } from './pages/teacher/ReviewDossier';
import { TeacherReports } from './pages/teacher/Reports';

// Admin pages
import { AdminOverview } from './pages/admin/Overview';
import { AdminUsers } from './pages/admin/Users';
import { AdminSubjects } from './pages/admin/Subjects';
import { AdminDepartments } from './pages/admin/Departments';
import { AdminSettings } from './pages/admin/Settings';

export function App() {
  const { user, loading } = useAuth();

  if (loading) {
    return (
      <div className="grid h-screen place-items-center">
        <LoadingSpinner />
      </div>
    );
  }

  if (!user) {
    return <LoginPage />;
  }

  if (user.role === 'student') {
    return (
      <Routes>
        <Route path="/" element={<StudentDashboard />} />
        <Route path="/records" element={<StudentRecords />} />
        <Route path="/practical/:id" element={<StudentWorkspace />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    );
  }

  const sharedRoutes = (
    <>
      <Route
        path="/subject/:subjectId/practical/new"
        element={<PracticalForm />}
      />
      <Route path="/practical/:id/edit" element={<PracticalForm />} />
      <Route
        path="/practical/:id/submissions"
        element={<PracticalSubmissions />}
      />
      <Route path="/submission/:id" element={<SubmissionReview />} />
      <Route path="/reports" element={<TeacherReports />} />
    </>
  );

  if (user.role === 'teacher') {
    return (
      <Routes>
        <Route path="/" element={<TeacherSubjects />} />
        {sharedRoutes}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    );
  }

  // Admin role
  return (
    <Routes>
      <Route path="/" element={<AdminOverview />} />
      <Route path="/admin/users" element={<AdminUsers />} />
      <Route path="/admin/subjects" element={<AdminSubjects />} />
      <Route path="/admin/departments" element={<AdminDepartments />} />
      <Route path="/admin/settings" element={<AdminSettings />} />
      <Route path="/subjects" element={<TeacherSubjects />} />
      {sharedRoutes}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default App;
