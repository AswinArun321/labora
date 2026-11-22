import React, { useState, useEffect } from 'react';
import { Department } from '../../types';
import { api } from '../../services/api';
import { Layout } from '../../components/Layout';
import { PageHeader } from '../../components/PageHeader';
import { ErrorAlert } from '../../components/ErrorAlert';
import { LoadingSpinner } from '../../components/LoadingSpinner';

export function AdminDepartments() {
  const [departments, setDepartments] = useState<Department[] | null>(null);
  const [form, setForm] = useState({ code: '', name: '' });
  const [error, setError] = useState<any>(null);

  const fetchDepts = () =>
    api<Department[]>('/departments/').then(setDepartments).catch(setError);

  useEffect(() => {
    fetchDepts();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await api('/departments/', { method: 'POST', body: form });
      setForm({ code: '', name: '' });
      fetchDepts();
    } catch (err: any) {
      setError(
        err.data && !err.data.detail ? JSON.stringify(err.data) : err
      );
    }
  };

  const handleDelete = async (dept: Department) => {
    if (confirm(`Delete ${dept.name}? Its subjects will be deleted too.`)) {
      try {
        await api(`/departments/${dept.id}/`, { method: 'DELETE' });
        fetchDepts();
      } catch (err) {
        setError(err);
      }
    }
  };

  return (
    <Layout>
      <PageHeader
        title="Departments"
        subtitle="Manage academic faculties and branches."
      />
      <ErrorAlert error={error} />

      <form onSubmit={handleCreate} className="card mb-4 flex gap-3 p-4">
        <input
          className="input !w-40 font-mono"
          placeholder="Code (e.g. MCA)"
          value={form.code}
          onChange={(e) => setForm({ ...form, code: e.target.value })}
          required
        />
        <input
          className="input"
          placeholder="Department Name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          required
        />
        <button type="submit" className="btn-primary">
          Add department
        </button>
      </form>

      {departments ? (
        <div className="card overflow-hidden p-0">
          <table className="w-full">
            <thead>
              <tr>
                <th className="th w-28">Code</th>
                <th className="th">Name</th>
                <th className="th w-24"></th>
              </tr>
            </thead>
            <tbody>
              {departments.map((d) => (
                <tr key={d.id}>
                  <td className="td font-mono font-semibold">{d.code}</td>
                  <td className="td font-medium">{d.name}</td>
                  <td className="td text-right">
                    <button
                      className="btn-danger !py-1 text-xs"
                      onClick={() => handleDelete(d)}
                    >
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
              {departments.length === 0 && (
                <tr>
                  <td className="td text-slate-400" colSpan={3}>
                    No departments added yet.
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
