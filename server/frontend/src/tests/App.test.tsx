import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../App';
import * as authContext from '../context/AuthContext';

describe('App Routing and Role Guards', () => {
  it('renders LoginPage when user is not authenticated', () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: null,
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument();
  });

  it('renders student dashboard when authenticated as student', () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: {
        id: 1,
        username: 'student1',
        first_name: 'John',
        last_name: 'Doe',
        full_name: 'John Doe',
        role: 'student',
        is_active: true,
      },
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    expect(
      screen.getByRole('heading', { name: 'My Practicals' })
    ).toBeInTheDocument();
  });

  it('renders teacher subjects when authenticated as teacher', () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: {
        id: 2,
        username: 'teacher1',
        first_name: 'Jane',
        last_name: 'Smith',
        full_name: 'Jane Smith',
        role: 'teacher',
        is_active: true,
      },
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    expect(
      screen.getByRole('heading', { name: 'Subjects & Practicals' })
    ).toBeInTheDocument();
  });

  it('renders admin overview when authenticated as admin', () => {
    vi.spyOn(authContext, 'useAuth').mockReturnValue({
      user: {
        id: 3,
        username: 'admin',
        first_name: 'Admin',
        last_name: 'User',
        full_name: 'Admin User',
        role: 'admin',
        is_active: true,
      },
      loading: false,
      login: vi.fn(),
      logout: vi.fn(),
    });

    render(
      <MemoryRouter initialEntries={['/']}>
        <App />
      </MemoryRouter>
    );

    expect(
      screen.getByRole('heading', { name: 'Administration' })
    ).toBeInTheDocument();
  });
});
