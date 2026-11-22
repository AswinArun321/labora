export interface LaboraSecureAPI {
  isSecureBrowser: boolean;
  quit: () => void;
  onAlert?: (callback: (message: string) => void) => () => void;
}

declare global {
  interface Window {
    laboraSecure?: LaboraSecureAPI;
  }
}

export const laboraSecure: LaboraSecureAPI | undefined =
  typeof window !== 'undefined' ? window.laboraSecure : undefined;

export const isSecureBrowser: boolean = !!laboraSecure?.isSecureBrowser;

export function onSecureAlert(callback: (message: string) => void): () => void {
  if (laboraSecure?.onAlert) {
    return laboraSecure.onAlert(callback);
  }
  return () => {};
}
