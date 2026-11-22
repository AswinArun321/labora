import React, { useState, useEffect } from 'react';
import { Subject, Department, User } from '../../types';
import { api } from '../../services/api';
import { Layout } from '../../components/Layout';
import { PageHeader } from '../../components/PageHeader';
import { ErrorAlert } from '../../components/ErrorAlert';
import { LoadingSpinner } from '../../components/LoadingSpinner';

export function AdminSubjects() {
  const [subjects, setSubjects] = useState<Subject[] | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [teachers, setTeachers] = useState<User[]>([]);
  const [newSubject, setNewSubject] = useState({
    name: '',
    code: '',
    semester: 1,
    academic_year: '2026-27',
    department: '',
  });
  const [enrollTextMap, setEnrollTextMap] = useState<Record<number, string>>({});
  const [error, setError] = useState<any>(null);
  const [feedbackMsg, setFeedbackMsg] = useState<string | null>(null);

  const fetchSubjects = () =>
    api<Subject[]>('/subjects/').then(setSubjects).catch(setError);

  useEffect(() => {
    fetchSubjects();
    api<Department[]>('/departments/').then(setDepartments);
    api<User[]>('/users/?role=teacher').then(setTeachers);
  }, []);

  const handleCreateSubject = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api('/subjects/', {
        method: 'POST',
        body: {
          ...newSubject,
          department: Number(newSubject.department),
          semester: Number(newSubject.semester),
        },
      });
      setNewSubject({ ...newSubject, name: '', code: '' });
      fetchSubjects();
    } catch (err: any) {
      setError(
        err.data && !err.data.detail ? JSON.stringify(err.data) : err
      );
    }
  };

  const handleToggleTeacher = async (subject: Subject, teacherId: number) => {
    const updatedTeachers = subject.teachers.includes(teacherId)
      ? subject.teachers.filter((id) => id !== teacherId)
      : [...subject.teachers, teacherId];

    try {
      await api(`/subjects/${subject.id}/`, {
        method: 'PATCH',
        body: { teachers: updatedTeachers },
      });
      fetchSubjects();
    } catch (err) {
      setError(err);
    }
  };

  const handleEnrollStudents = async (subject: Subject) => {
    const raw = enrollTextMap[subject.id] || '';
    const students = raw.split(/[\s,]+/).filter(Boolean);
    if (!students.length) return;

    try {
      const res = await api<{ enrolled: number; not_found: string[] }>(
        `/subjects/${subject.id}/enroll/`,
        {
          method: 'POST',
          body: { students },
        }
      );
      setFeedbackMsg(
        `${subject.code}: enrolled ${res.enrolled}.${
          res.not_found.length
            ? ` Not found: ${res.not_found.join(', ')}`
            : ''
        }`
      );
      setEnrollTextMap((prev) => ({ ...prev, [subject.id]: '' }));
      fetchSubjects();
    } catch (err) {
      setError(err);
    }
  };

  return (
    <Layout>
      <PageHeader
        title="Subjects"
        subtitle="Create academic courses, assign instructors and enroll student cohorts."
      />
      <ErrorAlert error={error} />
      {feedbackMsg && (
        <div className="mb-4 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800 ring-1 ring-emerald-200">
          {feedbackMsg}
        </div>
      )}

      {/* Create Subject Form */}
      <form
        onSubmit={handleCreateSubject}
        className="card mb-6 grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-5"
      >
        <div className="lg:col-span-5 font-semibold text-sm text-slate-800">
          + Add subject
        </div>
        <input
          className="input"
          placeholder="Code (e.g. CS201)"
          value={newSubject.code}
          onChange={(e) =>
            setNewSubject({ ...newSubject, code: e.target.value })
          }
          required
        />
        <input
          className="input"
          placeholder="Subject Name"
          value={newSubject.name}
          onChange={(e) =>
            setNewSubject({ ...newSubject, name: e.target.value })
          }
          required
        />
        <select
          className="input"
          value={newSubject.department}
          onChange={(e) =>
            setNewSubject({ ...newSubject, department: e.target.value })
          }
          required
        >
          <option value="">Select department</option>
          {departments.map((d) => (
            <option key={d.id} value={d.id}>
              {d.code} - {d.name}
            </option>
          ))}
        </select>
        <input
          type="number"
          min="1"
          max="8"
          className="input"
          placeholder="Semester"
          value={newSubject.semester}
          onChange={(e) =>
            setNewSubject({ ...newSubject, semester: Number(e.target.value) })
          }
          required
        />
        <button type="submit" className="btn-primary">
          Create subject
        </button>
      </form>

      {/* Subjects Catalog */}
      {subjects ? (
        <div className="space-y-4">
          {subjects.map((sub) => (
            <div key={sub.id} className="card p-5">
              <div className="flex flex-wrap items-start justify-between gap-2 border-b border-slate-100 pb-3">
                <div>
                  <span className="text-lg font-bold text-slate-900">
                    {sub.code}
                  </span>{' '}
                  · <span className="font-semibold text-slate-800">{sub.name}</span>
                  <div className="text-xs text-slate-500">
                    Semester {sub.semester} · {sub.academic_year} ·{' '}
                    {sub.student_count || 0} students enrolled
                  </div>
                </div>
              </div>

              <div className="mt-4 grid gap-4 lg:grid-cols-2">
                {/* Teachers Assignment */}
                <div>
                  <div className="label">Assigned Teachers</div>
                  <div className="flex flex-wrap gap-1.5">
                    {teachers.map((t) => {
                      const isAssigned = sub.teachers.includes(t.id);
                      return (
                        <button
                          key={t.id}
                          type="button"
                          onClick={() => handleToggleTeacher(sub, t.id)}
                          className={`rounded-full px-2.5 py-0.5 text-xs font-medium transition ${
                            isAssigned
                              ? 'bg-brand-600 text-white'
                              : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                          }`}
                        >
                          {isAssigned ? '✓ ' : '+ '}
                          {t.full_name}
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Bulk Student Enrollment */}
                <div>
                  <div className="label">Enroll Students (by Roll No)</div>
                  <div className="flex gap-2">
                    <input
                      className="input !text-xs font-mono"
                      placeholder="e.g. 23MCA001, 23MCA002, 23MCA003"
                      value={enrollTextMap[sub.id] || ''}
                      onChange={(e) =>
                        setEnrollTextMap({
                          ...enrollTextMap,
                          [sub.id]: e.target.value,
                        })
                      }
                    />
                    <button
                      type="button"
                      className="btn-secondary !py-1 text-xs shrink-0"
                      onClick={() => handleEnrollStudents(sub)}
                    >
                      Enroll
                    </button>
                  </div>
                </div>
              </div>
            </div>
          ))}
          {subjects.length === 0 && (
            <div className="card p-8 text-center text-slate-500">
              No subjects registered yet.
            </div>
          )}
        </div>
      ) : (
        <LoadingSpinner />
      )}
    </Layout>
  );
}
