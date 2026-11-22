import { useState, useEffect, useRef, useCallback } from 'react';
import { useParams, Link } from 'react-router-dom';
import { WorkspaceData, Execution } from '../../types';
import { api } from '../../services/api';
import { isSecureBrowser, onSecureAlert } from '../../services/secureBrowser';
import { Logo } from '../../components/Logo';
import { StatusBadge } from '../../components/StatusBadge';
import { LanguageBadge } from '../../components/LanguageBadge';
import { ErrorAlert } from '../../components/ErrorAlert';
import { LoadingSpinner } from '../../components/LoadingSpinner';
import { Editor, monaco } from '../../components/MonacoEditorWrapper';
import { attachAntiCheatProtection } from '../../components/ClipboardTracker';

const MONACO_LANGUAGES: Record<string, string> = {
  c: 'c',
  java: 'java',
  python: 'python',
};

const BATCH_INSERT_THRESHOLD = 20;

export function StudentWorkspace() {
  const { id } = useParams<{ id: string }>();
  const workspaceUrl = `/workspace/${id}/`;

  const [data, setData] = useState<WorkspaceData | null>(null);
  const [error, setError] = useState<any>(null);
  const [stdin, setStdin] = useState('');
  const [lastExecution, setLastExecution] = useState<Execution | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [lastSaved, setLastSaved] = useState<Date | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [isFullscreenSession, setIsFullscreenSession] = useState<boolean>(isSecureBrowser);
  const [isSubmitModalOpen, setIsSubmitModalOpen] = useState(false);

  const currentCode = useRef('');
  const savedCode = useRef('');
  const eventQueue = useRef<any[]>([]);
  const pendingTyping = useRef({ ins: 0, del: 0 });
  const isInternalPaste = useRef(false);
  const stdinRef = useRef<HTMLTextAreaElement | null>(null);
  const cleanupFns = useRef<(() => void)[]>([]);

  const isRestricted = !!data?.practical.restricted;
  const isLocked = !!data?.submission.locked;

  const logEvent = useCallback((kind: string, chars = 0, detail = {}) => {
    eventQueue.current.push({
      kind,
      chars,
      detail,
      t: Date.now(),
    });
  }, []);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Load initial workspace data
  useEffect(() => {
    api<WorkspaceData>(workspaceUrl)
      .then((res) => {
        setData(res);
        currentCode.current = res.submission.code;
        savedCode.current = res.submission.code;
        setStdin(res.practical.sample_input || '');
        setLastExecution(res.last_execution);
      })
      .catch(setError);
  }, [workspaceUrl]);

  // Flush activity events periodically
  const flushEvents = useCallback(async () => {
    const { ins, del } = pendingTyping.current;
    if (ins) {
      eventQueue.current.push({
        kind: 'insert',
        chars: ins,
        detail: { batch: '1' },
        t: Date.now(),
      });
    }
    if (del) {
      eventQueue.current.push({
        kind: 'delete',
        chars: del,
        detail: { batch: '1' },
        t: Date.now(),
      });
    }
    pendingTyping.current = { ins: 0, del: 0 };

    if (!eventQueue.current.length) return;
    const batch = eventQueue.current.splice(0, 500);
    try {
      await api(workspaceUrl + 'events/', {
        method: 'POST',
        body: { events: batch },
      });
    } catch {
      eventQueue.current.unshift(...batch);
    }
  }, [workspaceUrl]);

  // Autosave code periodically
  const autosaveCode = useCallback(async () => {
    if (!data || isLocked || currentCode.current === savedCode.current) return;
    const codeToSave = currentCode.current;
    try {
      await api(workspaceUrl + 'save/', {
        method: 'POST',
        body: { code: codeToSave },
      });
      savedCode.current = codeToSave;
      setLastSaved(new Date());
    } catch (err: any) {
      if (err.code === 'locked') {
        setData((prev) =>
          prev
            ? { ...prev, submission: { ...prev.submission, locked: true } }
            : prev
        );
      }
    }
  }, [workspaceUrl, data, isLocked]);

  // Periodic intervals
  useEffect(() => {
    if (!data || !isRestricted) return;
    const timer = setInterval(flushEvents, 5000);
    return () => {
      clearInterval(timer);
      flushEvents();
    };
  }, [data, isRestricted, flushEvents]);

  useEffect(() => {
    if (!data || isLocked) return;
    const timer = setInterval(autosaveCode, 10000);
    return () => clearInterval(timer);
  }, [data, isLocked, autosaveCode]);

  // Restricted event listeners & hotkey suppression
  useEffect(() => {
    if (!data || !isRestricted || isLocked) return;

    const onBlur = () => logEvent('focus_lost');
    const onFocus = () => logEvent('focus_back');
    const onContextMenu = (e: MouseEvent) => e.preventDefault();
    const onKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && ['p', 's', 'u'].includes(e.key.toLowerCase())) {
        e.preventDefault();
      }
    };
    const onFullscreenChange = () => {
      if (!isSecureBrowser && !document.fullscreenElement) {
        logEvent('fullscreen_exit');
        setIsFullscreenSession(false);
      }
    };
    const onDragOver = (e: DragEvent) => e.preventDefault();
    const onDrop = (e: DragEvent) => e.preventDefault();

    window.addEventListener('blur', onBlur);
    window.addEventListener('focus', onFocus);
    document.addEventListener('contextmenu', onContextMenu);
    document.addEventListener('keydown', onKeyDown, true);
    document.addEventListener('fullscreenchange', onFullscreenChange);
    window.addEventListener('dragover', onDragOver);
    window.addEventListener('drop', onDrop);

    const detachAlert = onSecureAlert((msg) => {
      logEvent('secure_alert', 0, { message: msg });
      showToast(msg);
    });

    return () => {
      window.removeEventListener('blur', onBlur);
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('contextmenu', onContextMenu);
      document.removeEventListener('keydown', onKeyDown, true);
      document.removeEventListener('fullscreenchange', onFullscreenChange);
      window.removeEventListener('dragover', onDragOver);
      window.removeEventListener('drop', onDrop);
      detachAlert();
    };
  }, [data, isRestricted, isLocked, logEvent]);

  // Anti-cheat clipboard handler for Stdin
  useEffect(() => {
    if (data && isRestricted && stdinRef.current) {
      return attachAntiCheatProtection(stdinRef.current, {
        onBlocked: (kind, len) => {
          logEvent(kind, len, { target: 'stdin' });
          showToast('Pasting from outside LABORA is blocked.');
        },
      });
    }
  }, [data, isRestricted, logEvent]);

  // Cleanup on unmount
  useEffect(() => {
    return () => cleanupFns.current.forEach((fn) => fn());
  }, []);

  // Monaco Editor mount handler
  const handleEditorMount = (
    editor: monaco.editor.IStandaloneCodeEditor,
    monacoInstance: typeof monaco
  ) => {
    if (isRestricted) {
      cleanupFns.current.push(
        attachAntiCheatProtection(editor.getContainerDomNode(), {
          onBlocked: (kind, len) => {
            logEvent(kind, len);
            showToast(
              kind === 'drop_blocked'
                ? 'Drag-and-drop is blocked.'
                : 'Pasting from outside LABORA is blocked. Type your program yourself.'
            );
          },
          onBeforeInternalPaste: () => {
            isInternalPaste.current = true;
            setTimeout(() => {
              isInternalPaste.current = false;
            }, 50);
          },
          onInternal: (len) => logEvent('internal_paste', len),
        })
      );
    }

    editor.addCommand(monacoInstance.KeyCode.F1, () => {});

    const disposable = editor.onDidChangeModelContent((e) => {
      currentCode.current = editor.getValue();
      if (isRestricted) {
        for (const change of e.changes) {
          if (change.rangeLength) {
            pendingTyping.current.del += change.rangeLength;
          }
          const textLen = change.text.length;
          if (textLen && !isInternalPaste.current) {
            if (
              textLen >= BATCH_INSERT_THRESHOLD &&
              !e.isUndoing &&
              !e.isRedoing &&
              change.text.trim().length >= BATCH_INSERT_THRESHOLD
            ) {
              logEvent('insert', textLen, {
                lines: String(change.text.split('\n').length),
              });
            } else {
              pendingTyping.current.ins += textLen;
            }
          }
        }
      }
    });

    cleanupFns.current.push(() => disposable.dispose());
    editor.focus();
  };

  // Run program (Async dispatch with polling & fallback)
  const handleRun = async () => {
    setIsRunning(true);
    setError(null);
    try {
      await flushEvents();
      let resultExecution: Execution | null = null;
      try {
        const asyncRes = await api<{ execution_id?: number; state?: string }>(
          workspaceUrl + 'run-async/',
          {
            method: 'POST',
            body: { code: currentCode.current, stdin },
          }
        );

        if (asyncRes && asyncRes.execution_id) {
          setLastExecution({
            id: asyncRes.execution_id,
            status: 'Queued',
            state: (asyncRes.state as any) || 'QUEUED',
            stdin,
            stdout: `[LABORA] Code queued in Celery worker (ID: ${asyncRes.execution_id}). Waiting for sandbox runner...\n`,
            stderr: '',
            compile_output: '',
            time: null,
            memory: null,
            created_at: new Date().toISOString(),
          });

          let tries = 0;
          while (tries < 60) {
            await new Promise((res) => setTimeout(res, 1000));
            tries++;
            try {
              const pollRes = await api<Execution>(
                `/executions/${asyncRes.execution_id}/`
              );
              if (pollRes) {
                if (
                  pollRes.is_complete ||
                  ['COMPLETED', 'FAILED', 'TIMED_OUT', 'TIMEOUT', 'CANCELLED'].includes(
                    pollRes.state || ''
                  )
                ) {
                  resultExecution = pollRes;
                  break;
                } else {
                  setLastExecution(pollRes);
                }
              }
            } catch (pollErr) {
              console.warn('Polling error:', pollErr);
            }
          }

          if (!resultExecution) {
            throw new Error('Execution timed out waiting for runner.');
          }
        } else {
          resultExecution = asyncRes as unknown as Execution;
        }
      } catch (asyncErr) {
        console.warn('Async execution fallback:', asyncErr);
        resultExecution = await api<Execution>(workspaceUrl + 'run/', {
          method: 'POST',
          body: { code: currentCode.current, stdin },
        });
      }

      savedCode.current = currentCode.current;
      setLastSaved(new Date());
      setLastExecution(resultExecution);
    } catch (err) {
      setError(err);
    } finally {
      setIsRunning(false);
    }
  };

  // Submit program
  const handleSubmit = async () => {
    setIsSubmitModalOpen(false);
    setError(null);
    try {
      await flushEvents();
      const updated = await api<WorkspaceData>(workspaceUrl + 'submit/', {
        method: 'POST',
        body: { code: currentCode.current },
      });
      setData(updated);
      showToast('Submitted. Your teacher will review it.');
    } catch (err) {
      setError(err);
    }
  };

  const handleStartFullscreen = async () => {
    try {
      await document.documentElement.requestFullscreen();
    } catch {
      // ignore
    }
    setIsFullscreenSession(true);
    logEvent('session_start', 0, { fullscreen: true });
  };

  // Check if Secure Browser is required
  if (error?.code === 'secure_browser_required') {
    return (
      <div className="grid h-full place-items-center p-6">
        <div className="card max-w-md p-6 text-center">
          <div className="mb-2 text-4xl">🔒</div>
          <h1 className="text-lg font-semibold">
            Open this practical in the LABORA Secure Browser
          </h1>
          <p className="mt-2 text-sm text-slate-500">
            Your teacher has set this practical to run only inside the college's
            secure exam browser.
          </p>
          <Link to="/" className="btn-secondary mt-4">
            Back
          </Link>
        </div>
      </div>
    );
  }

  if (!data) {
    return error ? (
      <div className="p-6">
        <ErrorAlert error={error} />
      </div>
    ) : (
      <LoadingSpinner />
    );
  }

  const practical = data.practical;
  const submission = data.submission;
  const canSubmit = lastExecution?.status === 'Accepted' && !isLocked;

  return (
    <div className="flex h-full flex-col bg-slate-100">
      <header className="flex items-center gap-4 border-b border-slate-200 bg-white px-4 py-2">
        <Link to="/" title="Back to practicals">
          <Logo small />
        </Link>
        <div className="h-6 w-px bg-slate-200" />
        <div className="font-semibold">
          Experiment {practical.experiment_no}
        </div>
        <div className="text-sm text-slate-500">{practical.subject_code}</div>
        <LanguageBadge lang={practical.language} />
        {isRestricted && (
          <span className="badge bg-rose-100 text-rose-800">
            Restricted Assessment
          </span>
        )}
        {isSecureBrowser && (
          <span className="badge bg-emerald-100 text-emerald-800">
            🔒 Secure Browser
          </span>
        )}
        <StatusBadge status={submission.status} />

        <div className="ml-auto flex items-center gap-3">
          <span className="text-xs text-slate-500">
            {lastSaved ? `Saved ${lastSaved.toLocaleTimeString()}` : ''}
          </span>
          <button
            className="btn-primary"
            onClick={handleRun}
            disabled={isRunning || isLocked}
          >
            {isRunning ? 'Running…' : '▶ Run'}
          </button>
          <button
            className="btn-success"
            onClick={() => setIsSubmitModalOpen(true)}
            disabled={!canSubmit}
            title={canSubmit ? '' : 'Run your program successfully first'}
          >
            Submit
          </button>
        </div>
      </header>

      <div className="flex min-h-0 flex-1 gap-3 p-3">
        <aside className="card flex w-80 shrink-0 flex-col overflow-auto p-4">
          <h2 className="font-semibold text-slate-900">{practical.title}</h2>
          <div className="label mt-4">Question</div>
          <p className="whitespace-pre-wrap text-sm">{practical.question}</p>
          <div className="label mt-4">Aim</div>
          <p className="whitespace-pre-wrap text-sm text-slate-600">
            {practical.aim}
          </p>

          {practical.language === 'java' && (
            <p className="mt-3 rounded bg-orange-50 p-2 text-xs text-orange-800">
              Java: the public class must be named <b>Main</b>.
            </p>
          )}

          {submission.status === 'correction' && submission.teacher_note && (
            <div className="mt-4 rounded-lg bg-rose-50 p-3 text-sm text-rose-800">
              <b>Teacher:</b> {submission.teacher_note}
            </div>
          )}

          {isRestricted && (
            <div className="mt-auto pt-4">
              <div className="rounded-lg bg-slate-50 p-3 text-xs text-slate-600 ring-1 ring-slate-200">
                <div className="mb-1 font-semibold text-slate-800">
                  Restrictions On
                </div>
                <ul className="space-y-0.5">
                  <li>✕ Paste from outside blocked</li>
                  <li>✕ Drag-and-drop blocked</li>
                  <li>✓ Copy / paste inside LABORA allowed</li>
                  <li>● Activity is recorded</li>
                  <li>● No AI or hints</li>
                </ul>
              </div>
            </div>
          )}
        </aside>

        <section className="flex min-w-0 flex-1 flex-col gap-3">
          <div className="card min-h-0 flex-1 overflow-hidden p-0">
            <Editor
              height="100%"
              language={MONACO_LANGUAGES[practical.language]}
              defaultValue={submission.code}
              onMount={handleEditorMount}
              theme="vs-dark"
              options={{
                readOnly: isLocked,
                fontSize: 14,
                minimap: { enabled: false },
                automaticLayout: true,
                contextmenu: !isRestricted,
                dragAndDrop: false,
                dropIntoEditor: { enabled: false },
                quickSuggestions: false,
                suggestOnTriggerCharacters: false,
                wordBasedSuggestions: 'off',
                parameterHints: { enabled: false },
                scrollBeyondLastLine: false,
                tabSize: 4,
              }}
            />
          </div>

          <div className="grid h-56 shrink-0 grid-cols-3 gap-3">
            <div className="card flex flex-col p-3">
              <div className="label">Input (stdin)</div>
              <textarea
                ref={stdinRef}
                className="input flex-1 resize-none font-mono text-xs"
                value={stdin}
                onChange={(e) => setStdin(e.target.value)}
                disabled={isLocked}
                spellCheck={false}
              />
            </div>

            <div className="card col-span-2 flex min-h-0 flex-col p-3">
              <div className="mb-1 flex items-center gap-2">
                <div className="label !mb-0">Output</div>
                {lastExecution && (
                  <span
                    className={`badge ${
                      lastExecution.status === 'Accepted'
                        ? 'bg-emerald-100 text-emerald-800'
                        : lastExecution.status === 'Queued' ||
                          ['QUEUED', 'DISPATCHING', 'SUBMITTED_TO_RUNNER', 'PROCESSING'].includes(
                            lastExecution.state || lastExecution.status
                          )
                        ? 'bg-amber-100 text-amber-800'
                        : 'bg-rose-100 text-rose-800'
                    }`}
                  >
                    {lastExecution.status || lastExecution.state}
                  </span>
                )}
                {lastExecution?.time && (
                  <span className="text-xs text-slate-400">
                    {lastExecution.time}s
                    {lastExecution.memory ? ` · ${lastExecution.memory} KB` : ''}
                  </span>
                )}
              </div>
              <pre className="flex-1 overflow-auto rounded-lg bg-slate-900 p-3 font-mono text-xs text-slate-100">
                {lastExecution
                  ? (lastExecution.compile_output || '') +
                    (lastExecution.stdout || '') +
                    (lastExecution.stderr ? `\n${lastExecution.stderr}` : '') ||
                    '(no output)'
                  : 'Run your program to see its real output here.'}
              </pre>
            </div>
          </div>

          <ErrorAlert error={error} />
        </section>
      </div>

      {isRestricted && !isFullscreenSession && !isLocked && (
        <div className="fixed inset-0 z-40 grid place-items-center bg-slate-900/70 p-4">
          <div className="card max-w-md p-6 text-center">
            <h2 className="text-lg font-semibold">Start restricted session</h2>
            <p className="mt-2 text-sm text-slate-600">
              The workspace opens in fullscreen. Pasting from outside, drag-and-drop
              and leaving the window are recorded for your teacher.
            </p>
            <button className="btn-primary mt-4" onClick={handleStartFullscreen}>
              Start
            </button>
          </div>
        </div>
      )}

      {isSubmitModalOpen && (
        <div className="fixed inset-0 z-40 grid place-items-center bg-slate-900/50 p-4">
          <div className="card max-w-sm p-6">
            <h2 className="font-semibold">
              Submit Experiment {practical.experiment_no}?
            </h2>
            <p className="mt-2 text-sm text-slate-600">
              Your program and its last output will be locked and sent to your
              teacher for approval.
            </p>
            <div className="mt-4 flex justify-end gap-2">
              <button
                className="btn-secondary"
                onClick={() => setIsSubmitModalOpen(false)}
              >
                Cancel
              </button>
              <button className="btn-success" onClick={handleSubmit}>
                Submit
              </button>
            </div>
          </div>
        </div>
      )}

      {toastMessage && (
        <div className="fixed bottom-5 left-1/2 z-50 -translate-x-1/2 rounded-lg bg-slate-900 px-4 py-2 text-sm text-white shadow-lg">
          {toastMessage}
        </div>
      )}
    </div>
  );
}
