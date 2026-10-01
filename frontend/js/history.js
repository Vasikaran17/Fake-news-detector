/**
 * Fake News Detector - Analysis History Logic
 */

let allHistoryRecords = [];
let currentFilter = 'ALL';

document.addEventListener('DOMContentLoaded', () => {
  setupFilterButtons();
  loadHistory();
});

/**
 * Filter button click handling
 */
function setupFilterButtons() {
  const filterBtns = document.querySelectorAll('.filter-btn');
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      currentFilter = btn.getAttribute('data-filter') || 'ALL';
      renderHistoryList();
    });
  });
}

/**
 * Fetches real user verification history from GET /api/history
 */
async function loadHistory() {
  const container = document.getElementById('historyListContainer');
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/api/history`);
    if (!res.ok) {
      throw new Error('Failed to retrieve history');
    }

    const data = await res.json();
    allHistoryRecords = data.history || [];
    renderHistoryList();

  } catch (err) {
    container.innerHTML = `
      <div class="notice-box error">
        Failed to load analysis history. Please ensure the backend server is active.
      </div>
    `;
  }
}

/**
 * Renders the filtered history records
 */
function renderHistoryList() {
  const container = document.getElementById('historyListContainer');
  if (!container) return;

  const filtered = allHistoryRecords.filter(item => {
    if (currentFilter === 'ALL') return true;
    return item.result === currentFilter;
  });

  if (filtered.length === 0) {
    if (allHistoryRecords.length === 0) {
      // Empty state when no verifications performed yet
      container.innerHTML = `
        <div class="card" style="text-align:center; padding:48px 24px; color:var(--text-muted);">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" style="margin-bottom:12px; color:var(--text-muted);">
            <circle cx="12" cy="12" r="10"></circle>
            <polyline points="12 6 12 12 16 14"></polyline>
          </svg>
          <h3 style="font-size:1.15rem; color:var(--text-main); margin-bottom:6px;">Run your first verification to see results here.</h3>
          <p style="margin-bottom:18px; font-size:0.92rem;">Analyses will be saved locally in the database along with verified evidence and confidence metrics.</p>
          <a href="/verify" class="btn btn-primary btn-sm">
            Verify a Claim &rarr;
          </a>
        </div>
      `;
    } else {
      // Filter returned empty
      container.innerHTML = `
        <div class="card" style="text-align:center; padding:32px 16px; color:var(--text-muted);">
          <p style="margin-bottom:0;">No records matching <strong>${escapeHtml(currentFilter)}</strong>.</p>
        </div>
      `;
    }
    return;
  }

  // Render cards
  let html = '<div>';
  filtered.forEach(rec => {
    const result = rec.result || 'UNCERTAIN';
    const resultLower = result.toLowerCase();
    const conf = rec.confidence !== undefined ? `${rec.confidence}%` : '--';
    const textSnippet = escapeHtml(rec.article_text || 'No text snippet');
    const sourcesCount = rec.sources_checked_count !== undefined ? rec.sources_checked_count : 0;
    const sourcesLabel = `${sourcesCount} source${sourcesCount === 1 ? '' : 's'} checked`;

    // Date formatting
    let dateStr = rec.created_at || 'Recent';
    if (rec.created_at) {
      const d = new Date(rec.created_at);
      if (!isNaN(d.getTime())) {
        dateStr = d.toLocaleDateString('en-GB', { day: '2-digit', month: 'short', year: 'numeric', hour: '2-digit', minute: '2-digit' });
      }
    }

    const reVerifyUrl = `/verify?claim=${encodeURIComponent(rec.article_text || '')}`;

    html += `
      <div class="history-card">
        <div style="flex:1; min-width:260px;">
          <div class="history-excerpt">"${textSnippet}"</div>
          <div class="history-meta">
            <span>📅 ${escapeHtml(dateStr)}</span>
            <span>&bull;</span>
            <span>🔍 ${sourcesLabel}</span>
          </div>
        </div>

        <div style="display:flex; align-items:center; gap:14px;">
          <div style="text-align:right;">
            <span class="badge-verdict ${resultLower}">${result}</span>
            <div style="font-size:0.85rem; font-weight:700; color:var(--text-main); margin-top:2px;">
              ${conf}
            </div>
          </div>
          <a href="${reVerifyUrl}" class="btn btn-secondary btn-sm" style="padding:6px 10px; font-size:0.8rem;" title="Re-verify this claim">
            Re-verify
          </a>
        </div>
      </div>
    `;
  });
  html += '</div>';

  container.innerHTML = html;
}
