/**
 * Fake News Detector - Shared Application Logic
 */

// Dynamically determine API Base URL
const API_BASE = (window.location.protocol === 'http:' || window.location.protocol === 'https:') && window.location.port === '5000'
  ? ''
  : 'http://127.0.0.1:5000';

document.addEventListener('DOMContentLoaded', () => {
  setupMobileNav();
  fetchAndRenderSystemStatus();
});

/**
 * Mobile Navigation Toggle
 */
function setupMobileNav() {
  const toggleBtn = document.getElementById('mobileToggle');
  const navGroup = document.getElementById('navGroup');
  if (toggleBtn && navGroup) {
    toggleBtn.addEventListener('click', () => {
      navGroup.classList.toggle('open');
    });
  }
}

/**
 * Fetches dynamic system and continuous learning status
 */
async function fetchAndRenderSystemStatus() {
  const pill = document.getElementById('headerStatusPill');

  try {
    const res = await fetch(`${API_BASE}/api/system-status`);
    if (!res.ok) throw new Error('API unavailable');
    const data = await res.json();

    if (pill) {
      pill.className = 'status-pill trained';
      const version = data.current_model_version || 'v1.0';
      pill.innerHTML = `<span class="dot"></span> LIVE SYSTEM: Connected (${version})`;
      pill.title = `Live Verification System active. Model: ${version}. Verified learning records: ${data.verified_records || 0}.`;
      pill.href = '/live';
    }

    // Update Home page dynamic status widgets if they exist
    renderHomeLiveStatus(data);

  } catch (err) {
    if (pill) {
      pill.className = 'status-pill untrained';
      pill.innerHTML = `<span class="dot"></span> Backend Offline`;
      pill.title = 'Cannot connect to Flask backend. Please make sure python backend/app.py is running.';
      pill.href = '#';
    }
  }
}

/**
 * Updates dynamic status metrics on the Home page
 */
function renderHomeLiveStatus(data) {
  const lastUpdateEl = document.getElementById('liveLastUpdate');
  const articlesCountEl = document.getElementById('liveArticlesCount');
  const verifiedCountEl = document.getElementById('liveVerifiedCount');
  const modelVersionEl = document.getElementById('liveModelVersion');
  const liveStatusBadge = document.getElementById('liveConnectionBadge');

  if (liveStatusBadge) {
    liveStatusBadge.innerHTML = `<span class="dot" style="background:#16a34a; width:8px; height:8px; border-radius:50%; display:inline-block; margin-right:6px;"></span> Connected`;
    liveStatusBadge.style.color = '#15803d';
    liveStatusBadge.style.fontWeight = '600';
  }

  if (lastUpdateEl) {
    if (data.last_update) {
      const d = new Date(data.last_update);
      lastUpdateEl.textContent = isNaN(d.getTime()) ? data.last_update : d.toLocaleString();
    } else {
      lastUpdateEl.textContent = 'Waiting for live data...';
    }
  }

  if (articlesCountEl) {
    articlesCountEl.textContent = (data.articles_checked !== undefined && data.articles_checked !== null) 
      ? data.articles_checked 
      : '0';
  }

  if (verifiedCountEl) {
    verifiedCountEl.textContent = (data.verified_records !== undefined && data.verified_records !== null) 
      ? data.verified_records 
      : '0';
  }

  if (modelVersionEl) {
    modelVersionEl.textContent = data.current_model_version || 'v1.0';
  }
}

/**
 * Helper to escape HTML characters
 */
function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
