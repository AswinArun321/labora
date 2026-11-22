/**
 * LABORA Secure Browser
 *
 * A locked-down browser (similar in spirit to Safe Exam Browser) that can only
 * open the college's LABORA server. It:
 *   - runs fullscreen in kiosk mode, always on top, with no menus or dev tools
 *   - refuses to load or navigate to any other website (AI tools included)
 *   - has no browser extensions
 *   - clears the system clipboard on start, on focus changes and on exit, so code
 *     cannot be carried in from (or out to) other programs
 *   - denies clipboard-read and other permissions to the page
 *   - signs every LABORA API request with a shared key (HMAC), so the server can
 *     tell the request really came from this app
 *   - reports focus loss, extra displays and blocklisted programs to the workspace,
 *     where they are recorded for the teacher
 *
 * Run with --dev to disable kiosk mode and enable dev tools while developing.
 */
const { app, BrowserWindow, clipboard, dialog, globalShortcut, ipcMain, Menu, screen, session } = require('electron')
const crypto = require('crypto')
const fs = require('fs')
const path = require('path')
const { exec } = require('child_process')

const DEV = process.argv.includes('--dev') || process.env.LABORA_DEV === '1'
const VERSION = app.getVersion()

// ---------------------------------------------------------------------------
// configuration: env > labora.config.json next to the executable > bundled file
// ---------------------------------------------------------------------------
function loadConfig() {
  const candidates = [
    process.env.LABORA_CONFIG,
    path.join(path.dirname(process.execPath), 'labora.config.json'),
    path.join(process.resourcesPath || '', 'labora.config.json'),
    path.join(__dirname, 'labora.config.json'),
  ].filter(Boolean)
  let cfg = {}
  for (const file of candidates) {
    try { cfg = JSON.parse(fs.readFileSync(file, 'utf8')); cfg.__file = file; break } catch { /* try next */ }
  }
  if (process.env.LABORA_URL) cfg.serverUrl = process.env.LABORA_URL
  if (process.env.LABORA_SECURE_BROWSER_KEY) cfg.browserKey = process.env.LABORA_SECURE_BROWSER_KEY
  cfg.serverUrl = (cfg.serverUrl || 'http://127.0.0.1:5173').replace(/\/+$/, '')
  cfg.blockedProcesses = (cfg.blockedProcesses || []).map((s) => s.toLowerCase())
  return cfg
}
const config = loadConfig()
const SERVER_ORIGIN = new URL(config.serverUrl).origin
const ALLOWED_ORIGINS = new Set([SERVER_ORIGIN, ...(config.extraAllowedOrigins || [])])

function isAllowedUrl(raw) {
  try {
    const u = new URL(raw)
    if (['blob:', 'data:', 'devtools:'].includes(u.protocol)) return true
    if (u.protocol === 'file:') return u.pathname.endsWith('/offline.html') // our own error page only
    if (u.protocol === 'ws:' || u.protocol === 'wss:') {
      return ALLOWED_ORIGINS.has(`${u.protocol === 'wss:' ? 'https:' : 'http:'}//${u.host}`)
    }
    return ALLOWED_ORIGINS.has(u.origin)
  } catch {
    return false
  }
}

function sign(method, url) {
  const u = new URL(url)
  const ts = Math.floor(Date.now() / 1000).toString()
  const msg = `${ts}\n${method.toUpperCase()}\n${u.pathname}${u.search}`
  const sig = crypto.createHmac('sha256', config.browserKey || '').update(msg).digest('hex')
  return { ts, sig }
}

// ---------------------------------------------------------------------------
let win = null
let allowQuit = false

function sendAlert(message) {
  if (win && !win.isDestroyed()) win.webContents.send('labora:alert', message)
}

function clearClipboard() {
  try { clipboard.clear() } catch { /* ignore */ }
}

function hardenSession(ses) {
  // No network access except the LABORA server.
  ses.webRequest.onBeforeRequest((details, cb) => {
    if (isAllowedUrl(details.url)) return cb({})
    console.warn('[labora] blocked request', details.url)
    cb({ cancel: true })
  })
  // Sign API requests and identify the client.
  ses.webRequest.onBeforeSendHeaders((details, cb) => {
    const headers = details.requestHeaders
    headers['User-Agent'] = `${headers['User-Agent'] || ''} LaboraSecureBrowser/${VERSION}`.trim()
    try {
      const u = new URL(details.url)
      if (u.origin === SERVER_ORIGIN && u.pathname.startsWith('/api/')) {
        const { ts, sig } = sign(details.method, details.url)
        headers['X-Labora-Ts'] = ts
        headers['X-Labora-Signature'] = sig
        headers['X-Labora-Client'] = `secure-browser/${VERSION}`
      }
    } catch { /* ignore */ }
    cb({ requestHeaders: headers })
  })
  // Deny every permission (clipboard-read, camera, notifications...) except fullscreen.
  ses.setPermissionRequestHandler((_wc, permission, cb) => cb(permission === 'fullscreen'))
  ses.setPermissionCheckHandler((_wc, permission) => permission === 'fullscreen')
  // Downloads (lab records) are allowed; Electron asks where to save them.
  ses.on('will-download', (_e, item) => {
    item.setSaveDialogOptions({ defaultPath: path.join(app.getPath('downloads'), item.getFilename()) })
  })
}

function createWindow() {
  win = new BrowserWindow({
    width: 1366,
    height: 860,
    show: false,
    kiosk: !DEV,
    fullscreen: !DEV,
    alwaysOnTop: !DEV,
    autoHideMenuBar: true,
    closable: DEV,
    minimizable: DEV,
    backgroundColor: '#f8fafc',
    title: 'LABORA Secure Browser',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
      sandbox: true,
      devTools: DEV,
      spellcheck: false,
      webviewTag: false,
      navigateOnDragDrop: false,
    },
  })
  if (!DEV) win.setAlwaysOnTop(true, 'screen-saver')
  win.setContentProtection(true) // blocks screen capture / screen sharing of the window where the OS supports it

  const wc = win.webContents
  wc.setWindowOpenHandler(({ url }) => {
    // No pop-ups. Same-origin links open in the same window.
    if (isAllowedUrl(url)) wc.loadURL(url)
    return { action: 'deny' }
  })
  wc.on('will-navigate', (e, url) => { if (!isAllowedUrl(url)) e.preventDefault() })
  wc.on('will-redirect', (e, url) => { if (!isAllowedUrl(url)) e.preventDefault() })
  wc.on('will-attach-webview', (e) => e.preventDefault())
  wc.on('context-menu', (e) => e.preventDefault())
  wc.on('before-input-event', (e, input) => {
    if (DEV) return
    const k = (input.key || '').toLowerCase()
    const ctrl = input.control || input.meta
    const blocked =
      ['f5', 'f11', 'f12'].includes(k) ||
      (ctrl && ['r', 'w', 'q', 'n', 't', 'p', 's', 'o', 'u', 'l', 'j', 'h'].includes(k)) ||
      (ctrl && input.shift && ['i', 'j', 'c', 'r', 'delete'].includes(k)) ||
      (input.alt && ['f4', 'arrowleft', 'arrowright', 'home'].includes(k))
    if (blocked) e.preventDefault()
  })
  wc.on('did-fail-load', (_e, code, desc, url, isMainFrame) => {
    if (isMainFrame && code !== -3) {
      win.loadFile(path.join(__dirname, 'offline.html'), { query: { url: config.serverUrl, error: desc } })
    }
  })
  wc.on('render-process-gone', () => wc.reload())

  win.on('blur', () => {
    if (config.clearClipboardOnBlur !== false) clearClipboard()
    if (!DEV) setTimeout(() => { if (win && !win.isDestroyed()) { win.focus(); win.moveTop() } }, 150)
  })
  win.on('focus', () => { if (config.clearClipboardOnBlur !== false) clearClipboard() })
  win.on('leave-full-screen', () => { if (!DEV) { sendAlert('Left fullscreen'); win.setFullScreen(true) } })
  win.on('close', (e) => { if (!allowQuit && !DEV) e.preventDefault() })

  win.once('ready-to-show', () => win.show())
  win.loadURL(config.serverUrl)
}

// ---------------------------------------------------------------------------
// monitoring
// ---------------------------------------------------------------------------
function listProcesses() {
  const cmd = process.platform === 'win32' ? 'tasklist /fo csv /nh' : 'ps -A -o comm='
  return new Promise((resolve) => {
    exec(cmd, { windowsHide: true, maxBuffer: 4 * 1024 * 1024 }, (err, out) => {
      if (err) return resolve([])
      const names = out.split(/\r?\n/).map((line) => {
        let n = process.platform === 'win32' ? (line.split('","')[0] || '').replace(/^"/, '') : line.trim()
        n = path.basename(n).toLowerCase().replace(/\.(exe|app)$/, '')
        return n
      }).filter(Boolean)
      resolve([...new Set(names)])
    })
  })
}

let lastProcessReport = ''
async function checkProcesses() {
  if (!config.blockedProcesses.length) return
  const own = path.basename(process.execPath).toLowerCase().replace(/\.exe$/, '')
  const running = await listProcesses()
  const hits = running.filter((n) => n !== own && !n.startsWith('labora') && !n.startsWith('electron') &&
    config.blockedProcesses.some((b) => n === b || n.startsWith(b)))
  const report = hits.sort().join(', ')
  if (report && report !== lastProcessReport) sendAlert(`Other programs running: ${report}`)
  lastProcessReport = report
}

function checkDisplays() {
  const n = screen.getAllDisplays().length
  if (n > 1) sendAlert(`${n} displays connected`)
}

// ---------------------------------------------------------------------------
ipcMain.handle('labora:quit', async () => {
  const { response } = await dialog.showMessageBox(win, {
    type: 'question', buttons: ['Cancel', 'Exit'], defaultId: 0, cancelId: 0,
    title: 'Exit LABORA', message: 'Exit the LABORA Secure Browser?',
    detail: 'Your work is saved automatically. Exiting is recorded for your teacher if a practical is open.',
  })
  if (response === 1) { allowQuit = true; app.quit() }
})
ipcMain.handle('labora:retry', () => win && win.loadURL(config.serverUrl))

if (!app.requestSingleInstanceLock()) {
  app.quit()
} else {
  app.on('second-instance', () => { if (win) { win.show(); win.focus() } })
  app.commandLine.appendSwitch('disable-features', 'Translate,AutofillServerCommunication,MediaRouter')
  app.commandLine.appendSwitch('disable-extensions')

  app.whenReady().then(() => {
    Menu.setApplicationMenu(null)
    clearClipboard()
    hardenSession(session.defaultSession)
    createWindow()
    if (!DEV) {
      // swallow common escape shortcuts at the OS level where Electron is allowed to
      for (const acc of ['CommandOrControl+R', 'F5', 'F11', 'F12', 'CommandOrControl+Shift+I', 'CommandOrControl+W', 'CommandOrControl+Q']) {
        try { globalShortcut.register(acc, () => {}) } catch { /* ignore */ }
      }
    }
    screen.on('display-added', () => sendAlert('A display was connected'))
    win.webContents.on('did-finish-load', () => { checkDisplays(); lastProcessReport = ''; checkProcesses() })
    setInterval(checkProcesses, Math.max(10, config.processCheckSeconds || 30) * 1000)
    console.log(`[labora] secure browser ${VERSION} -> ${config.serverUrl} (config: ${config.__file || 'defaults'}${DEV ? ', DEV MODE' : ''})`)
  })

  app.on('before-quit', () => { clearClipboard(); globalShortcut.unregisterAll() })
  app.on('window-all-closed', () => app.quit())
}
