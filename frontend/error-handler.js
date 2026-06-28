// ══════════════════════════════════════════
// Global Error Handler
// Shop Manager System
// Include this in every HTML page
// ══════════════════════════════════════════

// ── Smart API URL Auto-Detector ──────────
// Automatically detects whether app is running
// on localhost or ngrok — no manual changes needed!
const DETECTED_API = (function() {
  const host = window.location.hostname;
  const protocol = window.location.protocol;
  // If running on ngrok or any external URL
  if (host !== 'localhost' && host !== '127.0.0.1') {
    return `${protocol}//${host}`;
  }
  // Running locally
  return 'http://localhost:5000';
})();

// Override API in all pages automatically
if (typeof window !== 'undefined') {
  window.__AUTO_API__ = DETECTED_API;
}

const ErrorHandler = {

  // ── Show toast notification ────────────
  toast(message, type = 'error', duration = 4000) {
    // Remove existing toast
    const existing = document.getElementById('__toast__');
    if (existing) existing.remove();

    const colors = {
      error  : { bg: 'rgba(239,68,68,0.15)',
                 border: 'rgba(239,68,68,0.3)',
                 color: '#f87171', icon: '❌' },
      success: { bg: 'rgba(16,185,129,0.15)',
                 border: 'rgba(16,185,129,0.3)',
                 color: '#34d399', icon: '✅' },
      warning: { bg: 'rgba(245,158,11,0.15)',
                 border: 'rgba(245,158,11,0.3)',
                 color: '#fbbf24', icon: '⚠️' },
      info   : { bg: 'rgba(96,165,250,0.15)',
                 border: 'rgba(96,165,250,0.3)',
                 color: '#60a5fa', icon: 'ℹ️' },
    };

    const c   = colors[type] || colors.error;
    const div = document.createElement('div');
    div.id    = '__toast__';
    div.style.cssText = `
      position: fixed;
      top: 80px;
      right: 24px;
      z-index: 99999;
      background: ${c.bg};
      border: 1px solid ${c.border};
      color: ${c.color};
      padding: 14px 18px;
      border-radius: 12px;
      font-size: 13px;
      font-weight: 600;
      font-family: 'Inter', sans-serif;
      max-width: 380px;
      line-height: 1.5;
      box-shadow: 0 8px 32px rgba(0,0,0,0.3);
      backdrop-filter: blur(10px);
      display: flex;
      align-items: flex-start;
      gap: 10px;
      animation: slideIn 0.3s ease;
      cursor: pointer;
    `;

    div.innerHTML = `
      <span style="font-size:16px;flex-shrink:0;">
        ${c.icon}
      </span>
      <span>${message}</span>
      <span style="margin-left:auto;
           opacity:0.5;font-size:16px;
           flex-shrink:0;">✕</span>
    `;

    // Click to dismiss
    div.addEventListener('click', () => div.remove());

    // Add animation
    const style = document.createElement('style');
    style.textContent = `
      @keyframes slideIn {
        from { transform: translateX(120%); opacity: 0; }
        to   { transform: translateX(0);   opacity: 1; }
      }
      @keyframes slideOut {
        from { transform: translateX(0);   opacity: 1; }
        to   { transform: translateX(120%); opacity: 0; }
      }
    `;
    if (!document.getElementById('__toast_styles__')) {
      style.id = '__toast_styles__';
      document.head.appendChild(style);
    }

    document.body.appendChild(div);

    // Auto remove
    setTimeout(() => {
      if (div.parentNode) {
        div.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => div.remove(), 300);
      }
    }, duration);
  },

  // ── Handle fetch errors ─────────────────
  async handleFetch(url, options = {}) {
    try {
      // Add timeout (10 seconds)
      const controller = new AbortController();
      const timeout    = setTimeout(
        () => controller.abort(), 10000
      );

      const token = localStorage.getItem('token');
      const defaultHeaders = {
        'Content-Type': 'application/json',
        'Accept'      : 'application/json',
      };
      if (token) {
        defaultHeaders['X-Auth-Token'] = token;
      }

      options.headers = {
        ...defaultHeaders,
        ...(options.headers || {})
      };
      options.signal = controller.signal;

      const res = await fetch(url, options);
      clearTimeout(timeout);

      // Handle auth errors
      if (res.status === 401) {
        const json = await res.json();
        if (json.code === 'UNAUTHORIZED') {
          localStorage.clear();
          window.location.href = 'login.html';
          return null;
        }
      }

      // Handle forbidden
      if (res.status === 403) {
        this.toast(
          'You do not have permission for this action!',
          'error'
        );
        return null;
      }

      // Handle server error
      if (res.status === 500) {
        this.toast(
          'Server error! Please try again.',
          'error'
        );
        return null;
      }

      return await res.json();

    } catch(e) {
      if (e.name === 'AbortError') {
        this.toast(
          'Request timed out! Is the server running?',
          'error'
        );
      } else {
        this.toast(
          'Cannot connect to server! Make sure Flask is running on port 5000.',
          'error'
        );
      }
      return null;
    }
  },

  // ── Validate form fields ────────────────
  validate(rules) {
    for (const rule of rules) {
      const el  = document.getElementById(rule.id);
      if (!el) continue;
      const val = el.value.trim();

      // Required check
      if (!val) {
        el.style.borderColor = 'rgba(239,68,68,0.6)';
        el.focus();
        setTimeout(() => {
          el.style.borderColor = '';
        }, 3000);
        return `${rule.label} is required!`;
      }

      // Number check
      if (rule.type === 'number') {
        const num = parseFloat(val);
        if (isNaN(num)) {
          return `${rule.label} must be a number!`;
        }
        if (rule.min !== undefined && num < rule.min) {
          return `${rule.label} must be at least ${rule.min}!`;
        }
        if (rule.max !== undefined && num > rule.max) {
          return `${rule.label} must be at most ${rule.max}!`;
        }
      }

      // Min length check
      if (rule.minLength && val.length < rule.minLength) {
        return `${rule.label} must be at least ${rule.minLength} characters!`;
      }
    }
    return null; // No errors
  },

  // ── Loading state on button ─────────────
  setLoading(btnId, isLoading, loadingText = 'Loading...') {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    if (isLoading) {
      btn._originalText  = btn.innerHTML;
      btn.disabled       = true;
      btn.innerHTML      = `
        <span style="display:inline-flex;
             align-items:center;gap:8px;">
          <span style="width:14px;height:14px;
               border:2px solid rgba(255,255,255,0.3);
               border-top-color:white;
               border-radius:50%;
               animation:spin 0.7s linear infinite;
               display:inline-block;">
          </span>
          ${loadingText}
        </span>`;
    } else {
      btn.disabled  = false;
      btn.innerHTML = btn._originalText || 'Submit';
    }
  },

  // ── Connection monitor ──────────────────
  // Uses auto-detected API URL — works on both
  // localhost AND ngrok automatically!
  startConnectionMonitor() {
    let wasOffline = false;

    const checkConnection = async () => {
      try {
        const res = await fetch(
          `${DETECTED_API}/api/health`,
          { method: 'GET', signal:
            AbortSignal.timeout(3000) }
        );
        if (res.ok && wasOffline) {
          wasOffline = false;
          this.hideBanner();
          this.toast('✅ Server reconnected!', 'success');
        }
        // If online from start — make sure banner hidden
        if (res.ok) this.hideBanner();
      } catch(e) {
        if (!wasOffline) {
          wasOffline = true;
          this.showBanner();
        }
      }
    };

    // Check immediately on load first
    checkConnection();
    // Then check every 30 seconds
    setInterval(checkConnection, 30000);
  },

  showBanner() {
    const existing = document.getElementById(
      '__offline_banner__'
    );
    if (existing) return;

    const banner = document.createElement('div');
    banner.id    = '__offline_banner__';
    banner.style.cssText = `
      position: fixed;
      bottom: 0; left: 0; right: 0;
      background: rgba(239,68,68,0.9);
      color: white;
      text-align: center;
      padding: 10px;
      font-size: 13px;
      font-weight: 600;
      font-family: 'Inter', sans-serif;
      z-index: 99998;
      backdrop-filter: blur(10px);
    `;
    banner.innerHTML = `
      ⚠️ Server connection lost!
      Make sure Flask is running:
      <code style="background:rgba(0,0,0,0.3);
           padding:2px 8px;border-radius:4px;">
        python app.py
      </code>
    `;
    document.body.appendChild(banner);
  },

  hideBanner() {
    const banner = document.getElementById(
      '__offline_banner__'
    );
    if (banner) banner.remove();
  }
};

// ── Start monitoring when page loads ─────
window.addEventListener('load', () => {
  ErrorHandler.startConnectionMonitor();
});

  // ── Show toast notification ────────────
  toast(message, type = 'error', duration = 4000) {
    // Remove existing toast
    const existing = document.getElementById('__toast__');
    if (existing) existing.remove();

    const colors = {
      error  : { bg: 'rgba(239,68,68,0.15)',
                 border: 'rgba(239,68,68,0.3)',
                 color: '#f87171', icon: '❌' },
      success: { bg: 'rgba(16,185,129,0.15)',
                 border: 'rgba(16,185,129,0.3)',
                 color: '#34d399', icon: '✅' },
      warning: { bg: 'rgba(245,158,11,0.15)',
                 border: 'rgba(245,158,11,0.3)',
                 color: '#fbbf24', icon: '⚠️' },
      info   : { bg: 'rgba(96,165,250,0.15)',
                 border: 'rgba(96,165,250,0.3)',
                 color: '#60a5fa', icon: 'ℹ️' },
    };

    const c   = colors[type] || colors.error;
    const div = document.createElement('div');
    div.id    = '__toast__';
    div.style.cssText = `
      position: fixed;
      top: 80px;
      right: 24px;
      z-index: 99999;
      background: ${c.bg};
      border: 1px solid ${c.border};
      color: ${c.color};
      padding: 14px 18px;
      border-radius: 12px;
      font-size: 13px;
      font-weight: 600;
      font-family: 'Inter', sans-serif;
      max-width: 380px;
      line-height: 1.5;
      box-shadow: 0 8px 32px rgba(0,0,0,0.3);
      backdrop-filter: blur(10px);
      display: flex;
      align-items: flex-start;
      gap: 10px;
      animation: slideIn 0.3s ease;
      cursor: pointer;
    `;

    div.innerHTML = `
      <span style="font-size:16px;flex-shrink:0;">
        ${c.icon}
      </span>
      <span>${message}</span>
      <span style="margin-left:auto;
           opacity:0.5;font-size:16px;
           flex-shrink:0;">✕</span>
    `;

    // Click to dismiss
    div.addEventListener('click', () => div.remove());

    // Add animation
    const style = document.createElement('style');
    style.textContent = `
      @keyframes slideIn {
        from { transform: translateX(120%); opacity: 0; }
        to   { transform: translateX(0);   opacity: 1; }
      }
      @keyframes slideOut {
        from { transform: translateX(0);   opacity: 1; }
        to   { transform: translateX(120%); opacity: 0; }
      }
    `;
    if (!document.getElementById('__toast_styles__')) {
      style.id = '__toast_styles__';
      document.head.appendChild(style);
    }

    document.body.appendChild(div);

    // Auto remove
    setTimeout(() => {
      if (div.parentNode) {
        div.style.animation = 'slideOut 0.3s ease';
        setTimeout(() => div.remove(), 300);
      }
    }, duration);
  },

  // ── Handle fetch errors ─────────────────
  async handleFetch(url, options = {}) {
    try {
      // Add timeout (10 seconds)
      const controller = new AbortController();
      const timeout    = setTimeout(
        () => controller.abort(), 10000
      );

      const token = localStorage.getItem('token');
      const defaultHeaders = {
        'Content-Type': 'application/json',
        'Accept'      : 'application/json',
      };
      if (token) {
        defaultHeaders['X-Auth-Token'] = token;
      }

      options.headers = {
        ...defaultHeaders,
        ...(options.headers || {})
      };
      options.signal = controller.signal;

      const res = await fetch(url, options);
      clearTimeout(timeout);

      // Handle auth errors
      if (res.status === 401) {
        const json = await res.json();
        if (json.code === 'UNAUTHORIZED') {
          localStorage.clear();
          window.location.href = 'login.html';
          return null;
        }
      }

      // Handle forbidden
      if (res.status === 403) {
        this.toast(
          'You do not have permission for this action!',
          'error'
        );
        return null;
      }

      // Handle server error
      if (res.status === 500) {
        this.toast(
          'Server error! Please try again.',
          'error'
        );
        return null;
      }

      return await res.json();

    } catch(e) {
      if (e.name === 'AbortError') {
        this.toast(
          'Request timed out! Is the server running?',
          'error'
        );
      } else {
        this.toast(
          'Cannot connect to server! Make sure Flask is running on port 5000.',
          'error'
        );
      }
      return null;
    }
  },

  // ── Validate form fields ────────────────
  validate(rules) {
    /*
    Usage:
    const err = ErrorHandler.validate([
      { id: 'name',  label: 'Product name' },
      { id: 'price', label: 'Price', type: 'number', min: 0 },
      { id: 'qty',   label: 'Quantity', type: 'number', min: 1 },
    ]);
    if (err) { ErrorHandler.toast(err); return; }
    */
    for (const rule of rules) {
      const el  = document.getElementById(rule.id);
      if (!el) continue;
      const val = el.value.trim();

      // Required check
      if (!val) {
        el.style.borderColor = 'rgba(239,68,68,0.6)';
        el.focus();
        setTimeout(() => {
          el.style.borderColor = '';
        }, 3000);
        return `${rule.label} is required!`;
      }

      // Number check
      if (rule.type === 'number') {
        const num = parseFloat(val);
        if (isNaN(num)) {
          return `${rule.label} must be a number!`;
        }
        if (rule.min !== undefined && num < rule.min) {
          return `${rule.label} must be at least ${rule.min}!`;
        }
        if (rule.max !== undefined && num > rule.max) {
          return `${rule.label} must be at most ${rule.max}!`;
        }
      }

      // Min length check
      if (rule.minLength && val.length < rule.minLength) {
        return `${rule.label} must be at least ${rule.minLength} characters!`;
      }
    }
    return null; // No errors
  },

  // ── Loading state on button ─────────────
  setLoading(btnId, isLoading, loadingText = 'Loading...') {
    const btn = document.getElementById(btnId);
    if (!btn) return;
    if (isLoading) {
      btn._originalText  = btn.innerHTML;
      btn.disabled       = true;
      btn.innerHTML      = `
        <span style="display:inline-flex;
             align-items:center;gap:8px;">
          <span style="width:14px;height:14px;
               border:2px solid rgba(255,255,255,0.3);
               border-top-color:white;
               border-radius:50%;
               animation:spin 0.7s linear infinite;
               display:inline-block;">
          </span>
          ${loadingText}
        </span>`;
    } else {
      btn.disabled  = false;
      btn.innerHTML = btn._originalText || 'Submit';
    }
  },

  // ── Connection monitor ──────────────────
  startConnectionMonitor() {
    let wasOffline = false;

    const checkConnection = async () => {
      try {
        const res = await fetch(
          'http://localhost:5000/api/health',
          { method: 'GET', signal:
            AbortSignal.timeout(3000) }
        );
        if (wasOffline) {
          wasOffline = false;
          this.hideBanner();
          this.toast(
            '✅ Server reconnected!', 'success'
          );
        }
      } catch(e) {
        if (!wasOffline) {
          wasOffline = true;
          this.showBanner();
        }
      }
    };

    // Check every 30 seconds
    setInterval(checkConnection, 30000);
  },

  showBanner() {
    const existing = document.getElementById(
      '__offline_banner__'
    );
    if (existing) return;

    const banner = document.createElement('div');
    banner.id    = '__offline_banner__';
    banner.style.cssText = `
      position: fixed;
      bottom: 0; left: 0; right: 0;
      background: rgba(239,68,68,0.9);
      color: white;
      text-align: center;
      padding: 10px;
      font-size: 13px;
      font-weight: 600;
      font-family: 'Inter', sans-serif;
      z-index: 99998;
      backdrop-filter: blur(10px);
    `;
    banner.innerHTML = `
      ⚠️ Server connection lost!
      Make sure Flask is running:
      <code style="background:rgba(0,0,0,0.3);
           padding:2px 8px;border-radius:4px;">
        python app.py
      </code>
    `;
    document.body.appendChild(banner);
  },

  hideBanner() {
    const banner = document.getElementById(
      '__offline_banner__'
    );
    if (banner) banner.remove();
  }
};

// ── Add health check endpoint reminder ───
// Start monitoring when page loads
window.addEventListener('load', () => {
  ErrorHandler.startConnectionMonitor();
});