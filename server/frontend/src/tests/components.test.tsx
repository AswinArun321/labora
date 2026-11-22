import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { StatusBadge } from '../components/StatusBadge';
import { LanguageBadge } from '../components/LanguageBadge';
import { Logo } from '../components/Logo';
import { IndicatorsList } from '../components/IndicatorsList';
import { ErrorAlert } from '../components/ErrorAlert';

describe('Shared UI Components', () => {
  it('renders StatusBadge with correct label and color', () => {
    const { rerender } = render(<StatusBadge status="approved" />);
    expect(screen.getByText('Approved')).toBeInTheDocument();
    expect(screen.getByText('Approved')).toHaveClass('bg-emerald-100');

    rerender(<StatusBadge status="submitted" />);
    expect(screen.getByText('Submitted')).toBeInTheDocument();
    expect(screen.getByText('Submitted')).toHaveClass('bg-blue-100');

    rerender(<StatusBadge status="correction" />);
    expect(screen.getByText('Correction requested')).toBeInTheDocument();

    rerender(<StatusBadge status="in_progress" />);
    expect(screen.getByText('In progress')).toBeInTheDocument();
  });

  it('renders LanguageBadge for supported languages', () => {
    const { rerender } = render(<LanguageBadge lang="c" />);
    expect(screen.getByText('C')).toBeInTheDocument();

    rerender(<LanguageBadge lang="java" />);
    expect(screen.getByText('Java')).toBeInTheDocument();

    rerender(<LanguageBadge lang="python" />);
    expect(screen.getByText('Python')).toBeInTheDocument();
  });

  it('renders Logo correctly', () => {
    render(<Logo />);
    expect(screen.getByText('LABORA')).toBeInTheDocument();
    expect(screen.getByText('Write. Execute. Verify. Record.')).toBeInTheDocument();
  });

  it('renders IndicatorsList when indicators exist', () => {
    const indicators = [
      { code: 'burst_paste', label: 'Large paste', detail: 'Pastes > 50 chars' },
      { code: 'rapid_runs', label: 'Rapid runs', detail: 'Too many runs quickly' },
    ];
    render(<IndicatorsList items={indicators} />);
    expect(screen.getByText('Large paste')).toBeInTheDocument();
    expect(screen.getByText('Rapid runs')).toBeInTheDocument();
  });

  it('renders None when indicators list is empty', () => {
    render(<IndicatorsList items={[]} />);
    expect(screen.getByText('None')).toBeInTheDocument();
  });

  it('renders ErrorAlert with error string or object', () => {
    const { rerender } = render(<ErrorAlert error={new Error('Network error')} />);
    expect(screen.getByText('Network error')).toBeInTheDocument();

    rerender(<ErrorAlert error={{ message: 'Custom failure' }} />);
    expect(screen.getByText('Custom failure')).toBeInTheDocument();
  });
});
