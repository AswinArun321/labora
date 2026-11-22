import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import { User, AuthTokens } from '../types';
import { api, getTokens, setTokens } from '../services/api';

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (username: string, password: string) => Promise<User>;
  logout: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState<boolean>(true);

  const logout = useCallback(() => {
    const tokens = getTokens();
    if (tokens?.refresh) {
      fetch('/api/auth/logout/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(tokens.access ? { Authorization: `Bearer ${tokens.access}` } : {}),
        },
        body: JSON.stringify({ refresh: tokens.refresh }),
      }).catch(() => {});
    }
    setTokens(null);
    setUser(null);
  }, []);

  useEffect(() => {
    if (getTokens()) {
      api<User>('/auth/me/')
        .then(setUser)
        .catch(() => {
          setTokens(null);
          setUser(null);
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    const handleLogout = () => logout();
    window.addEventListener('labora:logout', handleLogout);
    return () => window.removeEventListener('labora:logout', handleLogout);
  }, [logout]);

  const login = async (username: string, password: string): Promise<User> => {
    const res = await api<{ access: string; refresh: string; user: User }>('/auth/login/', {
      method: 'POST',
      body: { username, password },
    });
    setTokens({ access: res.access, refresh: res.refresh } as AuthTokens);
    setUser(res.user);
    return res.user;
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextType {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}
