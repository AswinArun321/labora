import { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { PracticalSubmissionsResponse } from '../../types';
import { api } from '../../services/api';
import { Layout } from '../../components/Layout';
import { PageHeader } from '../../components/PageHeader';
import { ErrorAlert } from '../../components/ErrorAlert';
import { LoadingSpinner } from '../../components/LoadingSpinner';
import { StatusBadge } from '../../components/StatusBadge';
import { LanguageBadge } from '../../components/LanguageBadge';
import { IndicatorsList } from '../../components/IndicatorsList';

export function PracticalSubmissions() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<PracticalSubmissionsResponse | null>(null);
  const [error, setError] = useState<any>(null);
  const [tab, setTab] = useState<string>('all');

  useEffect(() => {
    const fetchData = () =>
      api<PracticalSubmissionsResponse>(`/practicals/${id}/submissions/`)
        .then(setData)
        .catch(setError);

    fetchData();
    const interval = setInterval(fetchData, 15000);
    return () => clearInterval(interval);
  }, [id]);

  if (!data) {
    return (
      <Layout>
        <ErrorAlert error={error} />
        <LoadingSpinner />
      </Layout>
    );
  }

  const practical = data.practical;
  const filteredRows = data.rows.filter(
    (row) =>
      tab === 'all' ||
      row.status === tab ||
      (tab === 'flagged' && row.indicators.length > 0)
  );

  const countByStatus = (status: string) =>
    data.rows.filter((r) => r.status === status).length;

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
        title={`Submissions: Experiment ${practical.experiment_no}`}
        subtitle={`${practical.subject_code} · ${practical.title}`}
      >
        <LanguageBadge lang={practical.language} />
      </PageHeader>

      <ErrorAlert error={error} />

      <div className="mb-4 flex flex-wrap gap-2">
        {[
          ['all', `All (${data.rows.length})`],
          ['submitted', `To review (${countByStatus('submitted')})`],
          ['in_progress', `In progress (${countByStatus('in_progress')})`],
          ['not_started', `Not started (${countByStatus('not_started')})`],
          ['approved', `Approved (${countByStatus('approved')})`],
          ['flagged', 'With indicators'],
        ].map(([key, label]) => (
          <button
            key={key}
            onClick={() => setTab(key)}
            className={`rounded-full px-3 py-1 text-sm transition ${
              tab === key
                ? 'bg-brand-600 font-medium text-white shadow-sm'
                : 'bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      <div className="card overflow-hidden p-0">
        <table className="w-full">
          <thead>
            <tr>
              <th className="th">Roll No</th>
              <th className="th">Student</th>
              <th className="th">Status</th>
              <th className="th">Runs</th>
              <th className="th">Submitted</th>
              <th className="th">Indicators</th>
              <th className="th"></th>
            </tr>
          </thead>
          <tbody>
            {filteredRows.map((row) => (
              <tr key={row.student_id}>
                <td className="td font-mono text-xs">{row.roll_no}</td>
                <td className="td font-medium">{row.student_name}</td>
                <td className="td">
                  <StatusBadge status={row.status} />
                </td>
                <td className="td">{row.runs}</td>
                <td className="td text-slate-500">
                  {formatDate(row.submitted_at)}
                </td>
                <td className="td">
                  <IndicatorsList items={row.indicators} />
                </td>
                <td className="td text-right">
                  {row.submission_id && (
                    <Link
                      to={`/submission/${row.submission_id}`}
                      className="btn-secondary !py-1"
                    >
                      {row.status === 'submitted' ? 'Review' : 'View history'}
                    </Link>
                  )}
                </td>
              </tr>
            ))}
            {filteredRows.length === 0 && (
              <tr>
                <td className="td text-slate-400" colSpan={7}>
                  No submissions in this filter.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      <p className="mt-3 text-xs text-slate-500">
        Indicators are review hints only, not proof. Open the history dossier to
        see code activity, typing patterns and version diffs.
      </p>
    </Layout>
  );
}
