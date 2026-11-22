import * as monaco from 'monaco-editor';
import { loader, Editor, DiffEditor } from '@monaco-editor/react';
import editorWorker from 'monaco-editor/esm/vs/editor/editor.worker?worker';

if (typeof window !== 'undefined') {
  (window as any).MonacoEnvironment = {
    getWorker() {
      return new editorWorker();
    },
  };
  loader.config({ monaco });
}

export { Editor, DiffEditor, monaco };
