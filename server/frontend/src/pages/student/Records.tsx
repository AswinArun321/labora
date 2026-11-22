import { useState, useEffect } from 'react';
import { StudentSubjectRecord } from '../../types';
import { api, downloadFile } from '../../services/api';
import { Layout } from '../../components/Layout';
import { PageHeader } from '../../components/PageHeader';
import { ErrorAlert } from '../../components/ErrorAlert';
import { LoadingSpinner } from '../../components/LoadingSpinner';

export function StudentRecords() {
  const [records, setRecords] = useState<StudentSubjectRecord[] | null>(null);
  const [error, setError] = useState<any>(null);

  useEffect(() => {
    api<StudentSubjectRecord[]>('/records/')
      .then(setRecords)
      .catch(setError);
  }, []);

  const handleDownload = (endpoint: string, filename: string) => {
    downloadFile(endpoint, filename).catch(setError);
  };

  const formatDate = (dateStr: string) =>
    new Date(dateStr).toLocaleString(undefined, {
      dateStyle: 'medium',
      timeStyle: 'short',
    });

  return (
    <Layout>
      <PageHeader
        title="Lab Records"
        subtitle="Generated automatically from your approved practicals, with the real program output."
      />
      <ErrorAlert error={error} />

      {records ? (
        records.map((item) => (
          <section key={item.subject.id} className="card mb-5 p-4">
            <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
              <div>
                <div className="font-semibold">
                  {item.subject.code} · {item.subject.name}
                </div>
                <div className="text-sm text-slate-500">
                  {item.approved.length} of {item.total} practicals approved
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  className="btn-primary"
                  disabled={!item.approved.length}
                  onClick={() =>
                    handleDownload(
                      `/records/subject/${item.subject.id}/?type=pdf`,
                      'record.pdf'
                    )
                  }
                >
                  Download full record (PDF)
                </button>
                <button
                  className="btn-secondary"
                  disabled={!item.approved.length}
                  onClick={() =>
                    handleDownload(
                      `/records/subject/${item.subject.id}/?type=docx`,
                      'record.docx'
                    )
                  }
                >
                  DOCX
                </button>
              </div>
            </div>

            <div className="h-2 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full bg-emerald-500"
                style={{
                  width: `${item.total ? (100 * item.approved.length) / item.total : 0}%`,
                }}
              />
            </div>

            <ul className="mt-3 divide-y divide-slate-100">
              {item.approved.map((exp) => (
                <li
                  key={exp.submission_id}
                  className="flex items-center justify-between py-2 text-sm"
                >
                  <span>
                    Exp {exp.experiment_no}: {exp.title}{' '}
                    <span className="text-slate-400">
                      · approved {formatDate(exp.approved_at)}
                    </span>
                  </span>
                  <span className="flex gap-2">
                    <button
                      className="btn-secondary !py-1"
                      onClick={() =>
                        handleDownload(
                          `/records/submission/${exp.submission_id}/?type=pdf`,
                          'exp.pdf'
                        )
                      }
                    >
                      PDF
                    </button>
                    <button
                      className="btn-secondary !py-1"
                      onClick={() =>
                        handleDownload(
                          `/records/submission/${exp.submission_id}/?type=docx`,
                          'exp.docx'
                        )
                      }
                    >
                      DOCX
                    </button>
                  </span>
                </li>
              ))}
            </ul>
          </section>
        ))
      ) : (
        <LoadingSpinner />
      )}
    </Layout>
  );
}
