import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Subject, Practical } from '../../types';
import { api } from '../../services/api';
import { Layout } from '../../components/Layout';
import { PageHeader } from '../../components/PageHeader';
import { ErrorAlert } from '../../components/ErrorAlert';
import { LoadingSpinner } from '../../components/LoadingSpinner';
import { StatusBadge } from '../../components/StatusBadge';
import { LanguageBadge } from '../../components/LanguageBadge';
import { isSecureBrowser } from '../../services/secureBrowser';

interface StudentPractical extends Practical {
  my_status: string;
}

export function StudentDashboard() {
  const [data, setData] = useState<{
    subjects: Subject[];
    practicals: StudentPractical[];
  } | null>(null);
  const [error, setError] = useState<any>(null);

  useEffect(() => {
    Promise.all([
      api<Subject[]>('/subjects/'),
      api<StudentPractical[]>('/practicals/'),
    ])
      .then(([subjects, practicals]) => setData({ subjects, practicals }))
      .catch(setError);
  }, []);

  const formatDate = (dateStr: string | null) =>
    dateStr
      ? new Date(dateStr).toLocaleString(undefined, {
          dateStyle: 'medium',
          timeStyle: 'short',
        })
      : '—';

  return (
    <Layout>
      <PageHeader
        title="My Practicals"
        subtitle="Open a practical to write, run and submit your program."
      />
      <ErrorAlert error={error} />

      {data ? (
        data.subjects.length === 0 ? (
          <div className="card p-8 text-center text-slate-500">
            You are not enrolled in any subject yet.
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
                    <span className="font-semibold">{subject.code}</span> · {subject.name}
                  </div>
                  <div className="text-xs text-slate-500">
                    Semester {subject.semester} · {subject.teacher_names.join(', ')}
                  </div>
                </div>

                <table className="w-full">
                  <thead>
                    <tr>
                      <th className="th w-16">Exp</th>
                      <th className="th">Title</th>
                      <th className="th">Language</th>
                      <th className="th">Due</th>
                      <th className="th">Status</th>
                      <th className="th"></th>
                    </tr>
                  </thead>
                  <tbody>
                    {subjectPracticals.map((practical) => {
                      const blockedWithoutSecureBrowser =
                        practical.require_secure_browser && !isSecureBrowser;
                      const isCompleted = ['submitted', 'approved'].includes(
                        practical.my_status
                      );

                      return (
                        <tr key={practical.id}>
                          <td className="td font-semibold">
                            {practical.experiment_no}
                          </td>
                          <td className="td">
                            {practical.title}
                            {practical.require_secure_browser && (
                              <span className="ml-2 text-xs text-slate-400">
                                🔒 secure browser
                              </span>
                            )}
                          </td>
                          <td className="td">
                            <LanguageBadge lang={practical.language} />
                          </td>
                          <td className="td text-slate-500">
                            {formatDate(practical.due_date)}
                          </td>
                          <td className="td">
                            <StatusBadge status={practical.my_status} />
                          </td>
                          <td className="td text-right">
                            {blockedWithoutSecureBrowser ? (
                              <span className="text-xs text-amber-700">
                                Open in LABORA Secure Browser
                              </span>
                            ) : (
                              <Link
                                to={`/practical/${practical.id}`}
                                className="btn-primary !py-1"
                              >
                                {isCompleted ? 'View' : 'Open'}
                              </Link>
                            )}
                          </td>
                        </tr>
                      );
                    })}
                    {subjectPracticals.length === 0 && (
                      <tr>
                        <td className="td text-slate-400" colSpan={6}>
                          No practicals published yet.
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
