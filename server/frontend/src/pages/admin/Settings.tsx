import React, { useState, useEffect } from 'react';
import { CollegeSettings } from '../../types';
import { api } from '../../services/api';
import { Layout } from '../../components/Layout';
import { PageHeader } from '../../components/PageHeader';
import { ErrorAlert } from '../../components/ErrorAlert';
import { LoadingSpinner } from '../../components/LoadingSpinner';

export function AdminSettings() {
  const [settings, setSettings] = useState<CollegeSettings | null>(null);
  const [logoFile, setLogoFile] = useState<File | null>(null);
  const [error, setError] = useState<any>(null);
  const [savedMsg, setSavedMsg] = useState<string | null>(null);

  useEffect(() => {
    api<CollegeSettings>('/college-settings/')
      .then(setSettings)
      .catch(setError);
  }, []);

  if (!settings) {
    return (
      <Layout>
        <ErrorAlert error={error} />
        <LoadingSpinner />
      </Layout>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSavedMsg(null);

    const form = new FormData();
    for (const key of [
      'college_name',
      'college_address',
      'record_title',
      'record_footer',
    ] as (keyof CollegeSettings)[]) {
      form.append(key, (settings[key] as string) || '');
    }
    form.append(
      'students_secure_browser_only',
      settings.students_secure_browser_only ? 'true' : 'false'
    );
    if (logoFile) {
      form.append('logo', logoFile);
    }

    try {
      const updated = await api<CollegeSettings>('/college-settings/', {
        method: 'PATCH',
        form,
      });
      setSettings(updated);
      setSavedMsg('Saved.');
    } catch (err) {
      setError(err);
    }
  };

  const updateField =
    (field: keyof CollegeSettings) =>
    (
      e: React.ChangeEvent<
        HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement
      >
    ) => {
      const target = e.target as HTMLInputElement;
      setSettings({
        ...settings,
        [field]: target.type === 'checkbox' ? target.checked : target.value,
      });
    };

  return (
    <Layout>
      <PageHeader
        title="Lab record template & security"
        subtitle="Used on every generated lab record."
      />

      <form onSubmit={handleSubmit} className="card grid max-w-2xl gap-4 p-5">
        <div>
          <label className="label">College Name</label>
          <input
            className="input"
            value={settings.college_name}
            onChange={updateField('college_name')}
            required
          />
        </div>

        <div>
          <label className="label">College Address / Subtitle</label>
          <textarea
            className="input h-16"
            value={settings.college_address}
            onChange={updateField('college_address')}
          />
        </div>

        <div>
          <label className="label">Record Document Title</label>
          <input
            className="input"
            value={settings.record_title}
            onChange={updateField('record_title')}
            required
          />
        </div>

        <div>
          <label className="label">Record Footer / Certificate Note</label>
          <textarea
            className="input h-16"
            value={settings.record_footer}
            onChange={updateField('record_footer')}
          />
        </div>

        <div>
          <label className="label">Logo</label>
          {settings.logo && (
            <img src={settings.logo} alt="College Logo" className="mb-2 h-16 object-contain" />
          )}
          <input
            type="file"
            accept="image/*"
            onChange={(e) => setLogoFile(e.target.files?.[0] || null)}
          />
        </div>

        <label className="flex items-start gap-2 rounded-lg bg-slate-50 p-3 text-sm">
          <input
            type="checkbox"
            className="mt-1"
            checked={settings.students_secure_browser_only}
            onChange={updateField('students_secure_browser_only')}
          />
          <span>
            <b>Students can sign in only from the LABORA Secure Browser.</b>
            <br />
            <span className="text-slate-500">
              Teachers and admins can still use a normal browser.
            </span>
          </span>
        </label>

        <ErrorAlert error={error} />
        {savedMsg && (
          <div className="text-sm font-medium text-emerald-700">{savedMsg}</div>
        )}

        <button type="submit" className="btn-primary w-fit">
          Save
        </button>
      </form>
    </Layout>
  );
}
