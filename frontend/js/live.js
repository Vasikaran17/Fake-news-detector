/**
 * Fake News Detector - Live News Feed Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  loadLiveNews();

  const refreshBtn = document.getElementById('refreshNewsBtn');
  if (refreshBtn) {
    refreshBtn.addEventListener('click', handleRefreshFeeds);
  }
});

/**
 * Loads live articles from GET /api/live-news
 */
async function loadLiveNews() {
  const container = document.getElementById('liveNewsContainer');
  const alertContainer = document.getElementById('liveAlertContainer');
  if (!container) return;

  try {
    const res = await fetch(`${API_BASE}/api/live-news`);
    if (!res.ok) {
      throw new Error('Live news service is currently unavailable.');
    }

    const data = await res.json();
    const articles = data.articles || [];

    if (articles.length === 0) {
      container.innerHTML = `
        <div class="card" style="text-align:center; padding:48px 24px; color:var(--text-muted);">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" style="margin-bottom:12px; color:var(--text-muted);">
            <path d="M4 11a9 9 0 0 1 9 9"></path>
            <path d="M4 4a16 16 0 0 1 16 16"></path>
            <circle cx="5" cy="19" r="1"></circle>
          </svg>
          <h3 style="font-size:1.15rem; color:var(--text-main); margin-bottom:6px;">No live news available.</h3>
          <p style="margin-bottom:16px; font-size:0.92rem;">The local feed repository has not retrieved articles yet. Click "Refresh Feeds" to poll configured sources.</p>
        </div>
      `;
      return;
    }

    // Render articles list
    let html = '<div class="live-news-grid">';
    articles.forEach(art => {
      const title = escapeHtml(art.title || 'Untitled Report');
      const source = escapeHtml(art.source || 'Live Source');
      const dateStr = art.published_at ? escapeHtml(art.published_at) : 'Recent';
      const desc = escapeHtml(art.content || '');
      const url = art.url ? escapeHtml(art.url) : '#';

      // Text passed to verification
      const verifyClaim = encodeURIComponent(`${art.title}. ${art.content || ''}`);

      html += `
        <div class="live-card">
          <div class="live-card-header">
            <span class="evidence-source-tag">${source}</span>
            <span class="evidence-date">${dateStr}</span>
          </div>
          <h3 class="live-card-title">${title}</h3>
          <p class="live-card-desc">${desc}</p>
          <div class="live-card-actions">
            <div>
              ${url !== '#' ? `
                <a href="${url}" target="_blank" rel="noopener noreferrer" class="evidence-link">
                  Open Source &rarr;
                </a>
              ` : ''}
            </div>
            <a href="/verify?claim=${verifyClaim}" class="btn btn-primary btn-sm">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <circle cx="11" cy="11" r="8"></circle>
                <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
              </svg>
              Verify Claim
            </a>
          </div>
        </div>
      `;
    });
    html += '</div>';

    container.innerHTML = html;

  } catch (err) {
    container.innerHTML = `
      <div class="notice-box error" style="padding:20px;">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <circle cx="12" cy="12" r="10"></circle>
          <line x1="12" y1="8" x2="12" y2="12"></line>
          <line x1="12" y1="16" x2="12.01" y2="16"></line>
        </svg>
        <div>
          <strong>Live news service is currently unavailable.</strong>
          <p style="font-size:0.85rem; margin-top:4px;">Cannot retrieve news feeds from backend. Please ensure the local server is running and configured news feeds are accessible.</p>
        </div>
      </div>
    `;
  }
}

/**
 * Triggers on-demand background fetch of news feeds
 */
async function handleRefreshFeeds() {
  const btn = document.getElementById('refreshNewsBtn');
  const alertContainer = document.getElementById('liveAlertContainer');
  if (!btn) return;

  const originalHtml = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner spinner-dark" style="width:14px; height:14px; margin-right:6px;"></span> Fetching...`;

  try {
    const res = await fetch(`${API_BASE}/api/update-news`, { method: 'POST' });
    const data = await res.json();

    if (alertContainer) {
      alertContainer.innerHTML = `
        <div class="notice-box success" style="margin-bottom:16px;">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="20 6 9 17 4 12"></polyline>
          </svg>
          <div>
            <strong>Feeds Updated:</strong> ${data.articles_collected || 0} news items processed, ${data.verified_records_collected || 0} verified fact-check records collected.
          </div>
        </div>
      `;
    }

    await loadLiveNews();

  } catch (err) {
    if (alertContainer) {
      alertContainer.innerHTML = `
        <div class="notice-box error" style="margin-bottom:16px;">
          Failed to refresh live feeds. Please check network connection.
        </div>
      `;
    }
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
  }
}
