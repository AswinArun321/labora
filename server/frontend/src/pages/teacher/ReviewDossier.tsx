import { useState, useEffect, useMemo } from 'react';
import { useParams, Link } from 'react-router-dom';
import { SubmissionDetailResponse } from '../../types';
import { api, downloadFile } from '../../services/api';
import { Layout } from '../../components/Layout';
import { PageHeader } from '../../components/PageHeader';
import { ErrorAlert } from '../../components/ErrorAlert';
import { LoadingSpinner } from '../../components/LoadingSpinner';
import { StatusBadge } from '../../components/StatusBadge';
import { LanguageBadge } from '../../components/LanguageBadge';
import { IndicatorsList } from '../../components/IndicatorsList';
import { DiffEditor } from '../../components/MonacoEditorWrapper';

const EVENT_KIND_STYLES: Record<string, string> = {
  insert: 'bg-slate-100 text-slate-700',
  delete: 'bg-slate-100 text-slate-500',
  internal_paste: 'bg-sky-100 text-sky-800',
  paste_blocked: 'bg-rose-100 text-rose-800',
  drop_blocked: 'bg-rose-100 text-rose-800',
  focus_lost: 'bg-amber-100 text-amber-800',
  focus_back: 'bg-slate-100 text-slate-500',
  fullscreen_exit: 'bg-amber-100 text-amber-800',
  secure_alert: 'bg-rose-100 text-rose-800',
  run: 'bg-indigo-100 text-indigo-800',
  submit: 'bg-emerald-100 text-emerald-800',
  session_start: 'bg-slate-200 text-slate-700',
};

const MONACO_LANGUAGES: Record<string, string> = {
  c: 'c',
  java: 'java',
  python: 'python',
};

export function SubmissionReview() {
  const { id } = useParams<{ id: string }>();
  const [data, setData] = useState<SubmissionDetailResponse | null>(null);
  const [error, setError] = useState<any>(null);
  const [vIndexA, setVIndexA] = useState<number | null>(null);
  const [vIndexB, setVIndexB] = useState<number | null>(null);
  const [resultText, setResultText] = useState('');
  const [noteText, setNoteText] = useState('');
  const [aiState, setAiState] = useState<{
    loading?: boolean;
    summary?: string;
    note?: string;
    error?: string;
  } | null>(null);
  const [showTypingEvents, setShowTypingEvents] = useState(false);

  const fetchDossier = () =>
    api<SubmissionDetailResponse>(`/submissions/${id}/`)
      .then((res) => {
        setData(res);
        const count = res.versions.length;
        setVIndexA(count > 1 ? count - 2 : 0);
        setVIndexB(Math.max(0, count - 1));
        setResultText(
          res.submission.result ||
            'The program was executed successfully and the output was verified.'
        );
        setNoteText(res.submission.teacher_note || '');
      })
      .catch(setError);

  useEffect(() => {
    fetchDossier();
  }, [id]);

  const filteredEvents = useMemo(
    () =>
      (data?.events || []).filter(
        (ev) => showTypingEvents || !ev.detail?.batch
      ),
    [data, showTypingEvents]
  );

  if (!data) {
    return (
      <Layout wide>
        <ErrorAlert error={error} />
        <LoadingSpinner />
      </Layout>
    );
  }

  const { submission, practical, versions, executions, indicators } = data;
  const versionA = vIndexA !== null ? versions[vIndexA] : null;
  const versionB = vIndexB !== null ? versions[vIndexB] : null;
  const recordExecution = executions.find(
    (e) => e.id === submission.record_execution
  );

  const handleAction = async (action: 'approve' | 'request-correction', body: any) => {
    setError(null);
    try {
      await api(`/submissions/${id}/${action}/`, {
        method: 'POST',
        body,
      });
      await fetchDossier();
    } catch (err) {
      setError(err);
    }
  };

  const handleAiSummary = async () => {
    setAiState({ loading: true });
    try {
      const res = await api<{ summary: string; note: string }>(
        `/submissions/${id}/ai-summary/`,
        { method: 'POST' }
      );
      setAiState(res);
    } catch (err: any) {
      setAiState({ error: err.message });
    }
  };

  const formatDate = (dateStr?: string | null) =>
    dateStr
      ? new Date(dateStr).toLocaleString(undefined, {
          dateStyle: 'medium',
          timeStyle: 'short',
        })
      : '—';

  return (
    <Layout wide>
      <PageHeader
        title={`${submission.student_name} · ${submission.roll_no}`}
        subtitle={`Experiment ${practical.experiment_no}: ${practical.title} (${practical.subject_code})`}
      >
        <LanguageBadge lang={practical.language} />
        <StatusBadge status={submission.status} />
        <Link
          to={`/practical/${practical.id}/submissions`}
          className="btn-secondary !py-1"
        >
          ← All submissions
        </Link>
      </PageHeader>

      <ErrorAlert error={error} />

      <div className="grid gap-4 lg:grid-cols-[320px_1fr_340px]">
        {/* Left Column: Indicators & Activity Timeline */}
        <section className="card flex max-h-[78vh] flex-col p-4">
          <div className="label">Review indicators</div>
          <IndicatorsList items={indicators} />
          <ul className="mt-2 space-y-1 text-xs text-slate-600">
            {indicators.map((ind) => (
              <li key={ind.code}>• {ind.detail}</li>
            ))}
          </ul>

          <div className="mt-4 flex items-center justify-between">
            <div className="label !mb-0">Code activity timeline</div>
            <label className="flex items-center gap-1 text-xs text-slate-500">
              <input
                type="checkbox"
                checked={showTypingEvents}
                onChange={(e) => setShowTypingEvents(e.target.checked)}
              />
              typing
            </label>
          </div>

          <ol className="mt-2 flex-1 space-y-1 overflow-auto pr-1">
            {filteredEvents.map((ev) => (
              <li key={ev.id} className="flex items-center gap-2 text-xs">
                <span className="w-16 shrink-0 font-mono text-slate-400">
                  {new Date(ev.client_time || ev.created_at).toLocaleTimeString()}
                </span>
                <span
                  className={`badge ${EVENT_KIND_STYLES[ev.kind] || 'bg-slate-100 text-slate-700'}`}
                >
                  {ev.kind_label}
                </span>
                {ev.chars > 0 && (
                  <span className="text-slate-500">{ev.chars} ch</span>
                )}
                {ev.detail?.message && (
                  <span
                    className="truncate text-slate-500"
                    title={ev.detail.message}
                  >
                    {ev.detail.message}
                  </span>
                )}
                {!ev.secure_browser && ev.kind === 'session_start' && (
                  <span className="text-amber-700 font-medium">normal browser</span>
                )}
              </li>
            ))}
          </ol>
        </section>

        {/* Center Column: Version Diff Viewer */}
        <section className="card flex flex-col p-4">
          <div className="mb-2 flex flex-wrap items-center gap-2 text-sm">
            <span className="label !mb-0">Version comparison</span>
            <select
              className="input !w-auto !py-1"
              value={vIndexA ?? ''}
              onChange={(e) => setVIndexA(Number(e.target.value))}
            >
              {versions.map((ver, idx) => (
                <option key={ver.id} value={idx}>
                  v{ver.number} · {ver.reason} ·{' '}
                  {new Date(ver.created_at).toLocaleTimeString()}
                </option>
              ))}
            </select>
            <span>→</span>
            <select
              className="input !w-auto !py-1"
              value={vIndexB ?? ''}
              onChange={(e) => setVIndexB(Number(e.target.value))}
            >
              {versions.map((ver, idx) => (
                <option key={ver.id} value={idx}>
                  v{ver.number} · {ver.reason} ·{' '}
                  {new Date(ver.created_at).toLocaleTimeString()}
                </option>
              ))}
            </select>
            {versionA && versionB && (
              <span className="text-xs text-slate-500">
                {versionA.code.split('\n').length} →{' '}
                {versionB.code.split('\n').length} lines
              </span>
            )}
            <span className="ml-auto text-xs text-slate-400">
              {versions.length} versions
            </span>
          </div>

          <div className="h-[62vh] overflow-hidden rounded-lg ring-1 ring-slate-200">
            {versions.length ? (
              <DiffEditor
                height="100%"
                language={MONACO_LANGUAGES[practical.language]}
                original={versionA?.code || ''}
                modified={versionB?.code || submission.code}
                theme="vs-dark"
                options={{
                  readOnly: true,
                  renderSideBySide: true,
                  minimap: { enabled: false },
                  automaticLayout: true,
                  fontSize: 13,
                }}
              />
            ) : (
              <div className="p-6 text-sm text-slate-400">
                No saved versions yet.
              </div>
            )}
          </div>
        </section>

        {/* Right Column: Executions & Actions */}
        <section className="flex max-h-[78vh] flex-col gap-4">
          <div className="card flex min-h-0 flex-1 flex-col p-4">
            <div className="label">
              Program executions ({executions.length})
            </div>
            <div className="flex-1 space-y-2 overflow-auto">
              {[...executions].reverse().map((exec) => (
                <details
                  key={exec.id}
                  className="rounded-lg ring-1 ring-slate-200 p-1"
                  open={exec.id === submission.record_execution}
                >
                  <summary className="cursor-pointer px-2 py-1 text-xs font-medium">
                    <span
                      className={
                        exec.status === 'Accepted'
                          ? 'text-emerald-700'
                          : 'text-rose-700'
                      }
                    >
                      {exec.status}
                    </span>
                    <span className="text-slate-400">
                      {' '}
                      · {new Date(exec.created_at).toLocaleTimeString()}
                    </span>
                    {exec.id === submission.record_execution && (
                      <span className="badge ml-1 bg-emerald-100 text-emerald-800">
                        in record
                      </span>
                    )}
                  </summary>
                  {exec.stdin && (
                    <pre className="mx-2 mb-1 whitespace-pre-wrap rounded bg-slate-100 p-1 text-[11px]">
                      in: {exec.stdin}
                    </pre>
                  )}
                  <pre className="mx-2 mb-2 max-h-40 overflow-auto whitespace-pre-wrap rounded bg-slate-900 p-2 text-[11px] text-slate-100">
                    {exec.compile_output}
                    {exec.stdout}
                    {exec.stderr}
                  </pre>
                </details>
              ))}
            </div>
          </div>

          <div className="card space-y-2 p-4">
            {submission.status === 'submitted' && (
              <>
                <label className="label">Result (printed in the record)</label>
                <textarea
                  className="input h-16"
                  value={resultText}
                  onChange={(e) => setResultText(e.target.value)}
                />
                <label className="label">Note to student</label>
                <textarea
                  className="input h-14"
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                  placeholder="Required when requesting a correction"
                />
                <div className="flex gap-2">
                  <button
                    className="btn-success flex-1"
                    onClick={() =>
                      handleAction('approve', {
                        result: resultText,
                        note: noteText,
                      })
                    }
                    disabled={!recordExecution}
                    title={
                      recordExecution
                        ? ''
                        : 'Cannot approve without a successful Accepted execution'
                    }
                  >
                    Approve
                  </button>
                  <button
                    className="btn-danger flex-1"
                    onClick={() =>
                      handleAction('request-correction', { note: noteText })
                    }
                    disabled={!noteText.trim()}
                  >
                    Request correction
                  </button>
                </div>
              </>
            )}

            {submission.status === 'approved' && (
              <>
                <div className="text-sm font-medium text-emerald-700">
                  Approved {formatDate(submission.approved_at)}
                </div>
                <div className="flex gap-2">
                  <button
                    className="btn-secondary flex-1"
                    onClick={() =>
                      downloadFile(
                        `/records/submission/${submission.id}/?type=pdf`,
                        'exp.pdf'
                      ).catch(setError)
                    }
                  >
                    Record PDF
                  </button>
                  <button
                    className="btn-secondary flex-1"
                    onClick={() =>
                      downloadFile(
                        `/records/submission/${submission.id}/?type=docx`,
                        'exp.docx'
                      ).catch(setError)
                    }
                  >
                    DOCX
                  </button>
                </div>
                <button
                  className="btn-secondary w-full"
                  onClick={() => {
                    const note = prompt('Note to student:');
                    if (note) {
                      handleAction('request-correction', { note });
                    }
                  }}
                >
                  Reopen for correction
                </button>
              </>
            )}

            {['in_progress', 'correction'].includes(submission.status) && (
              <div className="text-sm text-slate-500">
                Student is still working on this practical.
              </div>
            )}

            {data.ai_enabled && (
              <div className="border-t border-slate-100 pt-2">
                <button
                  className="btn-secondary w-full"
                  onClick={handleAiSummary}
                  disabled={aiState?.loading}
                >
                  {aiState?.loading
                    ? 'Analysing…'
                    : 'AI-assisted code summary (teacher only)'}
                </button>
                {aiState?.summary && (
                  <div className="mt-2 whitespace-pre-wrap rounded bg-slate-50 p-2 text-xs">
                    {aiState.summary}
                    <div className="mt-1 text-slate-400">{aiState.note}</div>
                  </div>
                )}
                {aiState?.error && (
                  <div className="mt-2 text-xs text-rose-700">
                    {aiState.error}
                  </div>
                )}
              </div>
            )}
          </div>
        </section>
      </div>
    </Layout>
  );
}
