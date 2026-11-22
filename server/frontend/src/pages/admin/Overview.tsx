import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { User, Subject, Department, Practical } from '../../types';
import { api } from '../../services/api';
import { Layout } from '../../components/Layout';
import { PageHeader } from '../../components/PageHeader';
import { ErrorAlert } from '../../components/ErrorAlert';
import { LoadingSpinner } from '../../components/LoadingSpinner';

export function AdminOverview() {
  const [data, setData] = useState<{
    users: User[];
    subjects: Subject[];
    depts: Department[];
    practicals: Practical[];
  } | null>(null);
  const [error, setError] = useState<any>(null);

  useEffect(() => {
    Promise.all([
      api<User[]>('/users/'),
      api<Subject[]>('/subjects/'),
      api<Department[]>('/departments/'),
      api<Practical[]>('/practicals/'),
    ])
      .then(([users, subjects, depts, practicals]) =>
        setData({ users, subjects, depts, practicals })
      )
      .catch(setError);
  }, []);

  const stats = data
    ? [
        [
          'Students',
          data.users.filter((u) => u.role === 'student').length,
          '/admin/users',
        ],
        [
          'Teachers',
          data.users.filter((u) => u.role === 'teacher').length,
          '/admin/users',
        ],
        ['Departments', data.depts.length, '/admin/departments'],
        ['Subjects', data.subjects.length, '/admin/subjects'],
        ['Practicals', data.practicals.length, '/subjects'],
      ]
    : [];

  return (
    <Layout>
      <PageHeader
        title="Administration"
        subtitle="Set up departments, subjects, users and the lab record template."
      />
      <ErrorAlert error={error} />

      {data ? (
        <div className="space-y-6">
          <div className="grid gap-4 sm:grid-cols-3 lg:grid-cols-5">
            {stats.map(([label, count, path]) => (
              <Link
                key={label}
                to={path as string}
                className="card p-5 transition hover:ring-2 hover:ring-brand-500"
              >
                <div className="text-3xl font-bold text-slate-900">{count}</div>
                <div className="mt-1 text-sm font-medium text-slate-500">
                  {label}
                </div>
              </Link>
            ))}
          </div>

          <div className="card p-6">
            <h2 className="text-base font-semibold text-slate-900">
              Setup checklist
            </h2>
            <ol className="mt-3 list-decimal space-y-2 pl-5 text-sm text-slate-600">
              <li>
                Create departments, then teacher and student accounts (or import
                a CSV).
              </li>
              <li>
                Create subjects, assign teachers and enroll students by roll
                number.
              </li>
              <li>Fill in the record template with the college name and logo.</li>
              <li>
                Teachers create practicals; students do them in the LABORA Secure
                Browser.
              </li>
            </ol>
          </div>
        </div>
      ) : (
        <LoadingSpinner />
      )}
    </Layout>
  );
}
