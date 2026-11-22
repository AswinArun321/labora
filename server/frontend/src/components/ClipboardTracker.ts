let lastInternalCopiedText: string | null = null;

const normalizeNewlines = (str: string) => (str || '').replace(/\r\n/g, '\n');

function handleCopyOrCut(e: ClipboardEvent) {
  let text = '';
  try {
    text = e.clipboardData?.getData('text/plain') || '';
  } catch {
    // fallback
  }
  text ||= window.getSelection()?.toString() || '';
  lastInternalCopiedText = text ? normalizeNewlines(text) : lastInternalCopiedText;
}

let isClipboardTrackerInitialized = false;

export function initClipboardTracker() {
  if (isClipboardTrackerInitialized || typeof window === 'undefined') return;
  isClipboardTrackerInitialized = true;
  document.addEventListener('copy', handleCopyOrCut);
  document.addEventListener('cut', handleCopyOrCut);
}

export function isInternalText(text: string): boolean {
  return lastInternalCopiedText !== null && normalizeNewlines(text) === lastInternalCopiedText;
}

export interface AntiCheatOptions {
  onBlocked?: (kind: 'paste_blocked' | 'drop_blocked', length: number) => void;
  onInternal?: (length: number) => void;
  onBeforeInternalPaste?: (length: number) => void;
}

export function attachAntiCheatProtection(
  domNode: HTMLElement,
  { onBlocked, onInternal, onBeforeInternalPaste }: AntiCheatOptions = {}
): () => void {
  const handlePaste = (e: ClipboardEvent) => {
    const text = e.clipboardData?.getData('text/plain') ?? '';
    if (isInternalText(text)) {
      onBeforeInternalPaste?.(text.length);
      onInternal?.(text.length);
    } else {
      e.preventDefault();
      e.stopPropagation();
      e.stopImmediatePropagation?.();
      onBlocked?.('paste_blocked', text.length);
    }
  };

  const handleDrop = (e: DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    const text = e.dataTransfer?.getData('text/plain') ?? '';
    onBlocked?.('drop_blocked', text.length);
  };

  const handleDragOver = (e: DragEvent) => {
    e.preventDefault();
    if (e.dataTransfer) {
      e.dataTransfer.dropEffect = 'none';
    }
  };

  domNode.addEventListener('paste', handlePaste, true);
  domNode.addEventListener('drop', handleDrop, true);
  domNode.addEventListener('dragover', handleDragOver, true);

  return () => {
    domNode.removeEventListener('paste', handlePaste, true);
    domNode.removeEventListener('drop', handleDrop, true);
    domNode.removeEventListener('dragover', handleDragOver, true);
  };
}
