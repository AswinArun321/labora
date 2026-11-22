import '@testing-library/jest-dom';
import React from 'react';
import { vi } from 'vitest';

// Mock Monaco Editor in JSDOM environment
vi.mock('../components/MonacoEditorWrapper', () => ({
  Editor: (props: any) =>
    React.createElement('textarea', {
      'data-testid': 'mock-monaco-editor',
      defaultValue: props.defaultValue,
      readOnly: props.options?.readOnly,
    }),
  DiffEditor: () =>
    React.createElement('div', {
      'data-testid': 'mock-monaco-diff-editor',
    }),
  monaco: {
    KeyCode: { F1: 112 },
  },
}));
