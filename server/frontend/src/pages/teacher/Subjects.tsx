import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Subject, Practical } from '../../types';
import { api } from '../../services/api';
import { Layout } from '../../components/Layout';
import { PageHeader } from '../../components/PageHeader';
import { ErrorAlert } from '../../components/ErrorAlert';
import { LoadingSpinner } from '../../components/LoadingSpinner';
import { LanguageBadge } from '../../components/LanguageBadge';

export function TeacherSubjects() {
  const [data, setData] = useState<{
    subjects: Subject[];
    practicals: Practical[];
  } | null>(null);
  const [error, setError] = useState<any>(null);

  useEffect(() => {
    Promise.all([
      api<Subject[]>('/subjects/'),
      api<Practical[]>('/practicals/'),
    ])
      .then(([subjects, practicals]) => setData({ subjects, practicals }))
      .catch(setError);
  }, []);

  return (
    <Layout>
      <PageHeader
        title="Subjects & Practicals"
        subtitle="Create practicals, then review submissions and approve them for the lab record."
      />
      <ErrorAlert error={error} />

      {data ? (
        data.subjects.length === 0 ? (
          <div className="card p-8 text-center text-slate-500">
            No subjects assigned to you yet. Ask the admin to assign you.
          </div>
        ) : (
          data.subjects.map((subject) => {
            const subjectPracticals = data.practicals.filter(
              (p) => p.subject === subject.id
            );

            return (
              <section key={subject.id} className="card mb-5 overflow-hidden">
                <div className="flex items-center justify-between border-b border-slate-100 bg-slate-50 px-4 py-3">
                  <div>
                    <span className="font-semibold">{subject.code}</span> · {subject.name}{' '}
                    <span className="text-sm text-slate-500">
                      · Sem {subject.semester} · {subject.student_count || 0} students
                    </span>
                  </div>
                  <Link
                    to={`/subject/${subject.id}/practical/new`}
                    className="btn-primary !py-1"
                  >
                    + New practical
                  </Link>
                </div>

                <table className="w-full">
                  <thead>
                    <tr>
                      <th className="th w-16">Exp</th>
                      <th className="th">Title</th>
                      <th className="th">Language</th>
                      <th className="th">Mode</th>
                      <th className="th"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {subjectPracticals.map((practical) => (
                      <tr key={practical.id}>
                        <td className="td font-semibold">
                          {practical.experiment_no}
                        </td>
                        <td className="td">
                          {practical.title}
                          {!practical.is_published && (
                            <span className="badge ml-2 bg-slate-100 text-slate-500">
                              draft
                            </span>
                          )}
                        </td>
                        <td className="td">
                          <LanguageBadge lang={practical.language} />
                        </td>
                        <td className="td text-xs text-slate-500">
                          {practical.restricted ? 'Restricted' : 'Open'}
                          {practical.require_secure_browser ? ' · Secure Browser only' : ''}
                        </td>
                        <td className="td text-right">
                          <Link
                            to={`/practical/${practical.id}/edit`}
                            className="btn-secondary mr-2 !py-1"
                          >
                            Edit
                          </Link>
                          <Link
                            to={`/practical/${practical.id}/submissions`}
                            className="btn-primary !py-1"
                          >
                            Submissions
                          </Link>
                        </td>
                      </tr>
                    ))}
                    {subjectPracticals.length === 0 && (
                      <tr>
                        <td className="td text-slate-400" colSpan={5}>
                          No practicals created yet.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </section>
            );
          })
        )
      ) : (
        <LoadingSpinner />
      )}
    </Layout>
  );
}
