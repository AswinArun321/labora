import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { Practical } from '../../types';
import { api } from '../../services/api';
import { Layout } from '../../components/Layout';
import { PageHeader } from '../../components/PageHeader';
import { ErrorAlert } from '../../components/ErrorAlert';
import { LoadingSpinner } from '../../components/LoadingSpinner';

const STARTER_CODES = {
  c: `#include <stdio.h>

int main() {
    
    return 0;
}
`,
  java: `import java.util.Scanner;

public class Main {
    public static void main(String[] args) {
        
    }
}
`,
  python: `def main():
    pass

if __name__ == "__main__":
    main()
`,
};

export function PracticalForm() {
  const { id, subjectId } = useParams<{ id?: string; subjectId?: string }>();
  const navigate = useNavigate();

  const [form, setForm] = useState<Partial<Practical> | null>(null);
  const [error, setError] = useState<any>(null);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    if (id) {
      api<Practical>(`/practicals/${id}/`)
        .then((p) => {
          setForm({
            ...p,
            due_date: p.due_date ? p.due_date.slice(0, 16) : null,
          });
        })
        .catch(setError);
    } else if (subjectId) {
      api<Practical[]>(`/practicals/?subject=${subjectId}`)
        .then((existing) => {
          const nextExpNo =
            existing.length > 0
              ? Math.max(...existing.map((e) => e.experiment_no)) + 1
              : 1;

          setForm({
            subject: Number(subjectId),
            experiment_no: nextExpNo,
            title: '',
            aim: '',
            question: '',
            language: 'c',
            starter_code: STARTER_CODES.c,
            sample_input: '',
            restricted: true,
            require_secure_browser: true,
            is_published: true,
            due_date: null,
          });
        })
        .catch(setError);
    }
  }, [id, subjectId]);

  if (!form) {
    return (
      <Layout>
        <ErrorAlert error={error} />
        <LoadingSpinner />
      </Layout>
    );
  }

  const handleLanguageChange = (lang: 'c' | 'java' | 'python') => {
    const isDefaultCode = Object.values(STARTER_CODES).includes(
      form.starter_code || ''
    );
    setForm({
      ...form,
      language: lang,
      starter_code:
        isDefaultCode || !form.starter_code
          ? STARTER_CODES[lang]
          : form.starter_code,
    });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const payload = {
        ...form,
        due_date: form.due_date ? new Date(form.due_date).toISOString() : null,
      };

      if (id) {
        await api(`/practicals/${id}/`, { method: 'PUT', body: payload });
      } else {
        await api('/practicals/', { method: 'POST', body: payload });
      }
      navigate('/');
    } catch (err) {
      setError(err);
    } finally {
      setSaving(false);
    }
  };

  return (
    <Layout>
      <PageHeader
        title={id ? `Edit Experiment ${form.experiment_no}` : 'New practical'}
      />
      <ErrorAlert error={error} />

      <form onSubmit={handleSubmit} className="card max-w-3xl space-y-4 p-6">
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Experiment No</label>
            <input
              type="number"
              className="input"
              value={form.experiment_no ?? ''}
              onChange={(e) =>
                setForm({ ...form, experiment_no: Number(e.target.value) })
              }
              required
            />
          </div>
          <div>
            <label className="label">Programming Language</label>
            <select
              className="input"
              value={form.language || 'c'}
              onChange={(e) =>
                handleLanguageChange(e.target.value as 'c' | 'java' | 'python')
              }
            >
              <option value="c">C</option>
              <option value="java">Java</option>
              <option value="python">Python</option>
            </select>
          </div>
        </div>

        <div>
          <label className="label">Title</label>
          <input
            type="text"
            className="input"
            value={form.title || ''}
            onChange={(e) => setForm({ ...form, title: e.target.value })}
            placeholder="e.g. Binary Search Tree Implementation"
            required
          />
        </div>

        <div>
          <label className="label">Aim</label>
          <textarea
            className="input h-20"
            value={form.aim || ''}
            onChange={(e) => setForm({ ...form, aim: e.target.value })}
            placeholder="Objective of the experiment (printed in the lab record)"
            required
          />
        </div>

        <div>
          <label className="label">Question & Requirements</label>
          <textarea
            className="input h-24"
            value={form.question || ''}
            onChange={(e) => setForm({ ...form, question: e.target.value })}
            placeholder="Detailed problem statement shown to students"
            required
          />
        </div>

        <div>
          <label className="label">Sample Input (stdin)</label>
          <textarea
            className="input h-16 font-mono text-xs"
            value={form.sample_input || ''}
            onChange={(e) => setForm({ ...form, sample_input: e.target.value })}
            placeholder="Default input pre-populated in student workspace"
          />
        </div>

        <div>
          <label className="label">Starter Code</label>
          <textarea
            className="input h-36 font-mono text-xs"
            value={form.starter_code || ''}
            onChange={(e) => setForm({ ...form, starter_code: e.target.value })}
            required
          />
        </div>

        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="label">Due Date & Time (Optional)</label>
            <input
              type="datetime-local"
              className="input"
              value={form.due_date || ''}
              onChange={(e) => setForm({ ...form, due_date: e.target.value || null })}
            />
          </div>
        </div>

        <div className="space-y-2 rounded-lg bg-slate-50 p-4">
          <label className="flex items-center gap-2 text-sm font-medium text-slate-800">
            <input
              type="checkbox"
              checked={form.restricted ?? true}
              onChange={(e) =>
                setForm({ ...form, restricted: e.target.checked })
              }
            />
            Restricted assessment (Block external pasting, suppress devtools, record telemetry)
          </label>

          <label className="flex items-center gap-2 text-sm font-medium text-slate-800">
            <input
              type="checkbox"
              checked={form.require_secure_browser ?? true}
              onChange={(e) =>
                setForm({ ...form, require_secure_browser: e.target.checked })
              }
            />
            Require LABORA Secure Browser (Enforce Electron client application)
          </label>

          <label className="flex items-center gap-2 text-sm font-medium text-slate-800">
            <input
              type="checkbox"
              checked={form.is_published ?? true}
              onChange={(e) =>
                setForm({ ...form, is_published: e.target.checked })
              }
            />
            Publish immediately (Visible on student dashboard)
          </label>
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            className="btn-secondary"
            onClick={() => navigate('/')}
          >
            Cancel
          </button>
          <button type="submit" className="btn-primary" disabled={saving}>
            {saving ? 'Saving…' : 'Save practical'}
          </button>
        </div>
      </form>
    </Layout>
  );
}
