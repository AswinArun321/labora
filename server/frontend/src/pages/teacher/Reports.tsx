import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Subject, SubjectReportResponse } from '../../types';
import { api } from '../../services/api';
import { Layout } from '../../components/Layout';
import { PageHeader } from '../../components/PageHeader';
import { ErrorAlert } from '../../components/ErrorAlert';
import { LoadingSpinner } from '../../components/LoadingSpinner';
import { LanguageBadge } from '../../components/LanguageBadge';

export function TeacherReports() {
  const [subjects, setSubjects] = useState<Subject[] | null>(null);
  const [selectedSubjectId, setSelectedSubjectId] = useState<string>('');
  const [report, setReport] = useState<SubjectReportResponse | null>(null);
  const [error, setError] = useState<any>(null);

  useEffect(() => {
    api<Subject[]>('/subjects/')
      .then((res) => {
        setSubjects(res);
        if (res.length > 0) {
          setSelectedSubjectId(String(res[0].id));
        }
      })
      .catch(setError);
  }, []);

  useEffect(() => {
    if (selectedSubjectId) {
      setReport(null);
      api<SubjectReportResponse>(`/reports/subject/${selectedSubjectId}/`)
        .then(setReport)
        .catch(setError);
    }
  }, [selectedSubjectId]);

  if (!subjects) {
    return (
      <Layout>
        <ErrorAlert error={error} />
        <LoadingSpinner />
      </Layout>
    );
  }

  return (
    <Layout>
      <PageHeader
        title="Reports"
        subtitle="Progress of each practical across the class."
      >
        <select
          className="input !w-auto"
          value={selectedSubjectId}
          onChange={(e) => setSelectedSubjectId(e.target.value)}
        >
          {subjects.map((sub) => (
            <option key={sub.id} value={sub.id}>
              {sub.code} · {sub.name}
            </option>
          ))}
        </select>
      </PageHeader>

      <ErrorAlert error={error} />

      {report ? (
        <div className="card overflow-hidden p-0">
          <table className="w-full">
            <thead>
              <tr>
                {[
                  'Exp',
                  'Title',
                  'Lang',
                  'Not started',
                  'In progress',
                  'Submitted',
                  'Correction',
                  'Approved',
                  'Indicators',
                  'Completion',
                ].map((col) => (
                  <th key={col} className="th">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {report.rows.map((row) => (
                <tr key={row.practical_id}>
                  <td className="td font-semibold">{row.experiment_no}</td>
                  <td className="td">
                    <Link
                      to={`/practical/${row.practical_id}/submissions`}
                      className="text-brand-700 hover:underline"
                    >
                      {row.title}
                    </Link>
                  </td>
                  <td className="td">
                    <LanguageBadge lang={row.language} />
                  </td>
                  <td className="td">{row.not_started}</td>
                  <td className="td">{row.in_progress}</td>
                  <td className="td">{row.submitted}</td>
                  <td className="td">{row.correction}</td>
                  <td className="td font-semibold text-emerald-700">
                    {row.approved}
                  </td>
                  <td className="td">
                    {row.with_indicators ? (
                      <span className="badge bg-amber-100 text-amber-900">
                        {row.with_indicators}
                      </span>
                    ) : (
                      0
                    )}
                  </td>
                  <td className="td w-40">
                    <div className="h-2 overflow-hidden rounded-full bg-slate-100">
                      <div
                        className="h-full bg-emerald-500"
                        style={{
                          width: `${row.students ? (100 * row.approved) / row.students : 0}%`,
                        }}
                      />
                    </div>
                    <div className="mt-1 text-xs text-slate-400">
                      {row.approved}/{row.students}
                    </div>
                  </td>
                </tr>
              ))}
              {report.rows.length === 0 && (
                <tr>
                  <td className="td text-slate-400" colSpan={10}>
                    No practicals found for this subject.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      ) : (
        <LoadingSpinner />
      )}
    </Layout>
  );
}
