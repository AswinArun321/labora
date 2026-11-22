// Exposes a tiny, read-only bridge to the LABORA web app. No Node APIs are exposed.
const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('laboraSecure', {
  isSecureBrowser: true,
  onAlert(cb) {
    const handler = (_e, msg) => cb(String(msg))
    ipcRenderer.on('labora:alert', handler)
    return () => ipcRenderer.removeListener('labora:alert', handler)
  },
  quit: () => ipcRenderer.invoke('labora:quit'),
  retry: () => ipcRenderer.invoke('labora:retry'),
})
