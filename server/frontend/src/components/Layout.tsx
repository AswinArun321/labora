import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Logo } from './Logo';
import { isSecureBrowser, laboraSecure } from '../services/secureBrowser';

const NAV_LINKS_BY_ROLE: Record<string, [string, string][]> = {
  student: [
    ['/', 'My Practicals'],
    ['/records', 'Lab Records'],
  ],
  teacher: [
    ['/', 'Subjects'],
    ['/reports', 'Reports'],
  ],
  admin: [
    ['/', 'Overview'],
    ['/admin/users', 'Users'],
    ['/admin/subjects', 'Subjects'],
    ['/admin/departments', 'Departments'],
    ['/admin/settings', 'Record Template'],
    ['/reports', 'Reports'],
  ],
};

export function Layout({
  children,
  wide = false,
}: {
  children: React.ReactNode;
  wide?: boolean;
}) {
  const { user, logout } = useAuth();
  const navLinks = (user?.role && NAV_LINKS_BY_ROLE[user.role]) || [];

  return (
    <div className="min-h-full">
      <header className="sticky top-0 z-20 border-b border-slate-200 bg-white/90 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-7xl items-center gap-6 px-4">
          <Link to="/">
            <Logo small />
          </Link>
          <nav className="flex gap-1">
            {navLinks.map(([path, label]) => (
              <NavLink
                key={path}
                to={path}
                end={path === '/'}
                className={({ isActive }) =>
                  `rounded-md px-3 py-1.5 text-sm transition ${
                    isActive
                      ? 'bg-brand-50 font-semibold text-brand-700'
                      : 'text-slate-600 hover:bg-slate-100'
                  }`
                }
              >
                {label}
              </NavLink>
            ))}
          </nav>
          <div className="ml-auto flex items-center gap-3 text-sm">
            {isSecureBrowser && (
              <span className="badge bg-emerald-100 text-emerald-800">
                🔒 Secure Browser
              </span>
            )}
            <span className="text-slate-600">
              {user?.full_name}{' '}
              <span className="text-slate-400">· {user?.role}</span>
            </span>
            <button className="btn-secondary !py-1" onClick={logout}>
              Sign out
            </button>
            {isSecureBrowser && (
              <button
                className="btn-danger !py-1"
                onClick={() => laboraSecure?.quit()}
              >
                Exit
              </button>
            )}
          </div>
        </div>
      </header>
      <main className={`mx-auto px-4 py-6 ${wide ? 'max-w-[1600px]' : 'max-w-7xl'}`}>
        {children}
      </main>
    </div>
  );
}
