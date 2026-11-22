import React, { useState, useEffect } from 'react';
import { User, Department } from '../../types';
import { api } from '../../services/api';
import { Layout } from '../../components/Layout';
import { PageHeader } from '../../components/PageHeader';
import { ErrorAlert } from '../../components/ErrorAlert';
import { LoadingSpinner } from '../../components/LoadingSpinner';

const INITIAL_USER_STATE = {
  username: '',
  first_name: '',
  last_name: '',
  role: 'student' as 'student' | 'teacher' | 'admin',
  roll_no: '',
  batch: '',
  semester: '',
  department: '',
  password: '',
};

export function AdminUsers() {
  const [users, setUsers] = useState<User[] | null>(null);
  const [departments, setDepartments] = useState<Department[]>([]);
  const [roleFilter, setRoleFilter] = useState('');
  const [newUser, setNewUser] = useState(INITIAL_USER_STATE);
  const [error, setError] = useState<any>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  const fetchUsers = () =>
    api<User[]>(`/users/${roleFilter ? `?role=${roleFilter}` : ''}`)
      .then(setUsers)
      .catch(setError);

  useEffect(() => {
    fetchUsers();
  }, [roleFilter]);

  useEffect(() => {
    api<Department[]>('/departments/').then(setDepartments).catch(() => {});
  }, []);

  const handleCreateUser = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMsg(null);
    try {
      await api('/users/', {
        method: 'POST',
        body: {
          ...newUser,
          department: newUser.department ? Number(newUser.department) : null,
          semester: newUser.semester ? Number(newUser.semester) : null,
        },
      });
      setNewUser(INITIAL_USER_STATE);
      setSuccessMsg('User created.');
      fetchUsers();
    } catch (err: any) {
      setError(
        err.data && !err.data.detail ? JSON.stringify(err.data) : err
      );
    }
  };

  const handleCsvImport = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setError(null);
    setSuccessMsg(null);
    const form = new FormData();
    form.append('file', file);
    try {
      const res = await api<{ created: number; errors: string[] }>(
        '/users/import/',
        {
          method: 'POST',
          form,
        }
      );
      setSuccessMsg(
        `Imported ${res.created} users.${
          res.errors.length ? ` Issues: ${res.errors.join('; ')}` : ''
        }`
      );
      fetchUsers();
    } catch (err) {
      setError(err);
    }
    e.target.value = '';
  };

  const handleToggleActive = async (u: User) => {
    await api(`/users/${u.id}/`, {
      method: 'PATCH',
      body: { is_active: !u.is_active },
    });
    fetchUsers();
  };

  const handleResetPassword = async (u: User) => {
    const newPass = prompt(`New password for ${u.username}:`);
    if (newPass) {
      await api(`/users/${u.id}/set-password/`, {
        method: 'POST',
        body: { password: newPass },
      });
      setSuccessMsg(`Password updated for ${u.username}.`);
    }
  };

  return (
    <Layout>
      <PageHeader
        title="Users"
        subtitle="Manage student, teacher and administrator accounts."
      >
        <label className="btn-secondary cursor-pointer">
          <span>Import CSV</span>
          <input
            type="file"
            accept=".csv"
            className="hidden"
            onChange={handleCsvImport}
          />
        </label>
      </PageHeader>

      <ErrorAlert error={error} />
      {successMsg && (
        <div className="mb-4 rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-800 ring-1 ring-emerald-200">
          {successMsg}
        </div>
      )}

      {/* Add User Form */}
      <form
        onSubmit={handleCreateUser}
        className="card mb-6 grid gap-3 p-4 sm:grid-cols-2 lg:grid-cols-4"
      >
        <div className="lg:col-span-4 font-semibold text-sm text-slate-800">
          + Add single user
        </div>
        <input
          className="input"
          placeholder="Username / Roll No"
          value={newUser.username}
          onChange={(e) =>
            setNewUser({ ...newUser, username: e.target.value })
          }
          required
        />
        <input
          className="input"
          placeholder="First name"
          value={newUser.first_name}
          onChange={(e) =>
            setNewUser({ ...newUser, first_name: e.target.value })
          }
          required
        />
        <input
          className="input"
          placeholder="Last name"
          value={newUser.last_name}
          onChange={(e) =>
            setNewUser({ ...newUser, last_name: e.target.value })
          }
        />
        <input
          type="password"
          className="input"
          placeholder="Password"
          value={newUser.password}
          onChange={(e) =>
            setNewUser({ ...newUser, password: e.target.value })
          }
          required
        />
        <select
          className="input"
          value={newUser.role}
          onChange={(e) =>
            setNewUser({
              ...newUser,
              role: e.target.value as 'student' | 'teacher' | 'admin',
            })
          }
        >
          <option value="student">Student</option>
          <option value="teacher">Teacher</option>
          <option value="admin">Admin</option>
        </select>
        <select
          className="input"
          value={newUser.department}
          onChange={(e) =>
            setNewUser({ ...newUser, department: e.target.value })
          }
        >
          <option value="">Department (optional)</option>
          {departments.map((d) => (
            <option key={d.id} value={d.id}>
              {d.code} - {d.name}
            </option>
          ))}
        </select>
        <input
          className="input"
          placeholder="Roll No (student)"
          value={newUser.roll_no}
          onChange={(e) =>
            setNewUser({ ...newUser, roll_no: e.target.value })
          }
        />
        <div className="flex gap-2">
          <input
            className="input !w-24"
            placeholder="Batch"
            value={newUser.batch}
            onChange={(e) =>
              setNewUser({ ...newUser, batch: e.target.value })
            }
          />
          <button type="submit" className="btn-primary flex-1">
            Create
          </button>
        </div>
      </form>

      {/* Role Tabs */}
      <div className="mb-4 flex gap-2">
        {[
          ['', 'All roles'],
          ['student', 'Students'],
          ['teacher', 'Teachers'],
          ['admin', 'Admins'],
        ].map(([val, label]) => (
          <button
            key={val}
            onClick={() => setRoleFilter(val)}
            className={`rounded-full px-3 py-1 text-sm transition ${
              roleFilter === val
                ? 'bg-brand-600 font-medium text-white shadow-sm'
                : 'bg-white text-slate-700 ring-1 ring-slate-200 hover:bg-slate-50'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {/* Users Table */}
      {users ? (
        <div className="card overflow-hidden p-0">
          <table className="w-full">
            <thead>
              <tr>
                <th className="th">Username</th>
                <th className="th">Name</th>
                <th className="th">Role</th>
                <th className="th">Roll No</th>
                <th className="th">Batch</th>
                <th className="th">Dept</th>
                <th className="th">Active</th>
                <th className="th"></th>
              </tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <tr key={u.id}>
                  <td className="td font-mono text-xs">{u.username}</td>
                  <td className="td font-medium">{u.full_name}</td>
                  <td className="td">
                    <span className="badge bg-slate-100 text-slate-700">
                      {u.role}
                    </span>
                  </td>
                  <td className="td font-mono text-xs">{u.roll_no || '—'}</td>
                  <td className="td">{u.batch || '—'}</td>
                  <td className="td">{u.department_name || '—'}</td>
                  <td className="td">
                    <button
                      onClick={() => handleToggleActive(u)}
                      className={`badge cursor-pointer ${
                        u.is_active
                          ? 'bg-emerald-100 text-emerald-800'
                          : 'bg-rose-100 text-rose-800'
                      }`}
                    >
                      {u.is_active ? 'Active' : 'Disabled'}
                    </button>
                  </td>
                  <td className="td text-right">
                    <button
                      className="btn-secondary !py-1 text-xs"
                      onClick={() => handleResetPassword(u)}
                    >
                      Reset pass
                    </button>
                  </td>
                </tr>
              ))}
              {users.length === 0 && (
                <tr>
                  <td className="td text-slate-400" colSpan={8}>
                    No users found.
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
