/**
 * Fake News Detector - News Verification Logic (Live & Evidence-Based)
 */

let selectedNewsFile = null;

document.addEventListener('DOMContentLoaded', () => {
  initVerifyPage();
});

async function initVerifyPage() {
  setupTabs();
  setupTextareaCounter();
  setupFileDropzone();
  checkUrlQueryPrefill();

  const analyzeTextBtn = document.getElementById('analyzeTextBtn');
  const analyzeFileBtn = document.getElementById('analyzeFileBtn');
  const clearTextBtn = document.getElementById('clearTextBtn');

  if (analyzeTextBtn) {
    analyzeTextBtn.addEventListener('click', handleTextVerification);
  }

  if (analyzeFileBtn) {
    analyzeFileBtn.addEventListener('click', handleFileVerification);
  }

  if (clearTextBtn) {
    clearTextBtn.addEventListener('click', () => {
      const textarea = document.getElementById('newsTextarea');
      if (textarea) {
        textarea.value = '';
        updateWordCount('');
      }
      hideResultCard();
    });
  }
}

/**
 * Checks if claim was passed via URL query parameter (e.g. from Live News page)
 */
function checkUrlQueryPrefill() {
  const urlParams = new URLSearchParams(window.location.search);
  const claimParam = urlParams.get('claim');
  if (claimParam) {
    const textarea = document.getElementById('newsTextarea');
    if (textarea) {
      textarea.value = claimParam;
      updateWordCount(claimParam);
      // Switch to text tab if not active
      const tabBtnText = document.getElementById('tabBtnText');
      if (tabBtnText) tabBtnText.click();
      textarea.focus();
    }
  }
}

/**
 * Tab switching (Paste Text vs Upload File)
 */
function setupTabs() {
  const tabBtns = document.querySelectorAll('.tab-btn');
  const tabContents = document.querySelectorAll('.tab-content');

  tabBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      const targetId = btn.getAttribute('data-tab');

      tabBtns.forEach(b => b.classList.remove('active'));
      tabContents.forEach(c => c.classList.remove('active'));

      btn.classList.add('active');
      const targetContent = document.getElementById(targetId);
      if (targetContent) {
        targetContent.classList.add('active');
      }

      hideResultCard();
    });
  });
}

/**
 * Textarea character and word counter
 */
function setupTextareaCounter() {
  const textarea = document.getElementById('newsTextarea');
  if (textarea) {
    textarea.addEventListener('input', () => {
      updateWordCount(textarea.value);
    });
  }
}

function updateWordCount(text) {
  const counter = document.getElementById('wordCharCounter');
  if (!counter) return;

  const trimmed = text.trim();
  const words = trimmed ? trimmed.split(/\s+/).length : 0;
  const chars = text.length;

  counter.innerHTML = `${words} words &bull; ${chars} characters`;
}

/**
 * File dropzone for .txt news files
 */
function setupFileDropzone() {
  const dropzone = document.getElementById('txtDropzone');
  const fileInput = document.getElementById('txtFileInput');
  const browseBtn = document.getElementById('browseTxtBtn');

  if (browseBtn && fileInput) {
    browseBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      fileInput.click();
    });
  }

  if (dropzone && fileInput) {
    dropzone.addEventListener('click', () => fileInput.click());

    ['dragenter', 'dragover'].forEach(name => {
      dropzone.addEventListener(name, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add('dragover');
      });
    });

    ['dragleave', 'drop'].forEach(name => {
      dropzone.addEventListener(name, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove('dragover');
      });
    });

    dropzone.addEventListener('drop', (e) => {
      const files = e.dataTransfer.files;
      if (files && files.length > 0) {
        handleNewsFileSelected(files[0]);
      }
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files && fileInput.files.length > 0) {
        handleNewsFileSelected(fileInput.files[0]);
      }
    });
  }
}

function handleNewsFileSelected(file) {
  const fileBadge = document.getElementById('txtFileInfoBadge');
  const analyzeBtn = document.getElementById('analyzeFileBtn');
  const alertContainer = document.getElementById('verifyAlertContainer');

  alertContainer.innerHTML = '';

  const ext = file.name.split('.').pop().toLowerCase();
  if (ext !== 'txt' && ext !== 'text') {
    showAlert('error', 'Please upload a supported text file (.txt).');
    selectedNewsFile = null;
    if (analyzeBtn) analyzeBtn.disabled = true;
    if (fileBadge) fileBadge.style.display = 'none';
    return;
  }

  selectedNewsFile = file;

  if (fileBadge) {
    fileBadge.style.display = 'block';
    const sizeKB = (file.size / 1024).toFixed(1);
    fileBadge.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:center;">
        <div>
          <strong>📄 ${escapeHtml(file.name)}</strong>
          <span style="color:var(--text-muted); font-size:0.85rem; margin-left:8px;">(${sizeKB} KB)</span>
        </div>
        <span style="color:var(--real-color); font-weight:600; font-size:0.85rem;">Ready to Verify</span>
      </div>
    `;
  }

  if (analyzeBtn) {
    analyzeBtn.disabled = false;
  }
}

/**
 * Handles text verification via POST /api/verify
 */
async function handleTextVerification() {
  const textarea = document.getElementById('newsTextarea');
  const btn = document.getElementById('analyzeTextBtn');
  const text = textarea ? textarea.value.trim() : '';

  if (!text) {
    showAlert('error', 'Please enter news content or a claim before verifying.');
    return;
  }

  if (text.length < 15) {
    showAlert('error', 'Please enter a complete sentence or claim (at least 15 characters).');
    return;
  }

  btn.disabled = true;
  const originalHtml = btn.innerHTML;
  btn.innerHTML = `<span class="spinner"></span> Checking Live Sources &amp; Evidence...`;
  hideResultCard();

  try {
    const res = await fetch(`${API_BASE}/api/verify`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text })
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Verification request failed');
    }

    renderVerificationResult(data);
  } catch (err) {
    showAlert('error', `Verification Error: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
  }
}

/**
 * Handles file verification (.txt) via POST /api/verify-file
 */
async function handleFileVerification() {
  if (!selectedNewsFile) {
    showAlert('error', 'Please select or upload a text file containing news content.');
    return;
  }

  const btn = document.getElementById('analyzeFileBtn');
  btn.disabled = true;
  const originalHtml = btn.innerHTML;
  btn.innerHTML = `<span class="spinner"></span> Reading &amp; Verifying File...`;
  hideResultCard();

  const formData = new FormData();
  formData.append('file', selectedNewsFile);

  try {
    const res = await fetch(`${API_BASE}/api/verify-file`, {
      method: 'POST',
      body: formData
    });

    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.error || 'Failed to verify file content');
    }

    renderVerificationResult(data);
  } catch (err) {
    showAlert('error', `File Verification Error: ${err.message}`);
  } finally {
    btn.disabled = false;
    btn.innerHTML = originalHtml;
  }
}

/**
 * Displays the evidence-based verification result card
 */
function renderVerificationResult(data) {
  const card = document.getElementById('predictionResultCard');
  if (!card) return;

  const result = data.result || 'UNCERTAIN';
  const resultLower = result.toLowerCase(); // 'real', 'fake', or 'uncertain'

  card.className = `result-card ${resultLower}`;

  // Verdict Badge
  const badge = document.getElementById('verdictBadge');
  badge.className = `verdict-badge ${resultLower}`;

  let badgeIcon = '';
  let meaningText = '';

  if (result === 'REAL') {
    badgeIcon = `
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
        <polyline points="9 12 11 14 15 10"></polyline>
      </svg>
    `;
    meaningText = 'Available evidence supports the claim.';
  } else if (result === 'FAKE') {
    badgeIcon = `
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="15" y1="9" x2="9" y2="15"></line>
        <line x1="9" y1="9" x2="15" y2="15"></line>
      </svg>
    `;
    meaningText = 'Available reliable evidence contradicts the claim.';
  } else {
    badgeIcon = `
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
        <circle cx="12" cy="12" r="10"></circle>
        <line x1="12" y1="8" x2="12" y2="12"></line>
        <line x1="12" y1="16" x2="12.01" y2="16"></line>
      </svg>
    `;
    meaningText = 'Available evidence is insufficient or conflicting.';
  }

  badge.innerHTML = `${badgeIcon} ${result}`;

  const meaningEl = document.getElementById('statusMeaning');
  if (meaningEl) meaningEl.textContent = meaningText;

  // Confidence Score
  const confValue = document.getElementById('confidenceValue');
  confValue.className = `confidence-value ${resultLower}`;
  confValue.textContent = `${data.confidence}%`;

  // Sources checked count
  const sourcesCheckedEl = document.getElementById('sourcesCheckedCount');
  const srcCount = data.sources_checked_count || 0;
  if (sourcesCheckedEl) {
    sourcesCheckedEl.textContent = `${srcCount} source${srcCount === 1 ? '' : 's'} checked`;
  }

  // Progress Bar
  const progressFill = document.getElementById('progressFill');
  progressFill.className = `progress-fill ${resultLower}`;
  setTimeout(() => {
    progressFill.style.width = `${data.confidence}%`;
  }, 50);

  // Evidence Summary Banner
  const summaryBanner = document.getElementById('evidenceSummaryBanner');
  if (summaryBanner) {
    summaryBanner.innerHTML = `
      <strong>Evidence Summary:</strong> ${escapeHtml(data.evidence_summary || 'Evidence analysis complete.')}
    `;
  }

  // Render "Why?" Evidence Lists
  const allEv = (data.evidence && data.evidence.length > 0)
    ? data.evidence
    : (data.supporting_evidence || []).concat(data.contradicting_evidence || []).concat(data.context_evidence || []);
  renderEvidenceBreakdown(allEv);

  // Pipeline Signals
  const mlPrior = document.getElementById('mlPriorDisplay');
  const mlProb = document.getElementById('mlProbDisplay');
  if (mlPrior) mlPrior.textContent = data.ml_prediction || 'N/A';
  if (mlProb) mlProb.textContent = data.ml_confidence ? `${data.ml_confidence}% statistical confidence` : '--';

  const claimExtracted = document.getElementById('claimExtractedDisplay');
  if (claimExtracted) claimExtracted.textContent = data.claim_extracted || 'Full text query';

  const entitiesDisplay = document.getElementById('entitiesDisplay');
  if (entitiesDisplay) {
    const ents = data.entities || {};
    const entParts = [];
    if (ents.people && ents.people.length) entParts.push(`People: ${ents.people.join(', ')}`);
    if (ents.organizations && ents.organizations.length) entParts.push(`Orgs: ${ents.organizations.join(', ')}`);
    if (ents.locations && ents.locations.length) entParts.push(`Locations: ${ents.locations.join(', ')}`);
    entitiesDisplay.textContent = entParts.length > 0 ? entParts.join(' | ') : 'No prominent named entities';
  }

  card.style.display = 'block';
  card.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

/**
 * Populates supporting, contradicting, and context evidence cards
 */
function renderEvidenceBreakdown(evidenceList) {
  const supContainer = document.getElementById('supportingEvidenceContainer');
  const supList = document.getElementById('supportingList');
  const conContainer = document.getElementById('contradictingEvidenceContainer');
  const conList = document.getElementById('contradictingList');
  const ctxContainer = document.getElementById('contextEvidenceContainer');
  const ctxList = document.getElementById('contextList');
  const noEvidenceNotice = document.getElementById('noEvidenceNotice');

  supList.innerHTML = '';
  conList.innerHTML = '';
  ctxList.innerHTML = '';

  let supportingCount = 0;
  let contradictingCount = 0;
  let contextCount = 0;

  evidenceList.forEach(item => {
    const cardEl = createEvidenceCard(item);
    if (item.evidence_type === 'supporting') {
      supList.appendChild(cardEl);
      supportingCount++;
    } else if (item.evidence_type === 'contradicting') {
      conList.appendChild(cardEl);
      contradictingCount++;
    } else {
      ctxList.appendChild(cardEl);
      contextCount++;
    }
  });

  if (supContainer) supContainer.style.display = supportingCount > 0 ? 'block' : 'none';
  if (conContainer) conContainer.style.display = contradictingCount > 0 ? 'block' : 'none';
  if (ctxContainer) ctxContainer.style.display = contextCount > 0 ? 'block' : 'none';

  if (noEvidenceNotice) {
    noEvidenceNotice.style.display = (evidenceList.length === 0) ? 'flex' : 'none';
  }
}

/**
 * Creates a single evidence item DOM element
 */
function createEvidenceCard(item) {
  const card = document.createElement('div');
  const typeClass = item.evidence_type || 'context';
  card.className = `evidence-card ${typeClass}`;

  const sourceName = escapeHtml(item.source || 'Configured Source');
  const title = escapeHtml(item.title || 'Untitled Report');
  const dateStr = item.published_at ? escapeHtml(item.published_at) : 'Recent';
  const snippet = escapeHtml(item.summary || 'Relevant matching coverage.');
  const url = item.url ? item.url : '#';

  card.innerHTML = `
    <div class="evidence-top">
      <span class="evidence-source-tag">${sourceName}</span>
      <span class="evidence-date">${dateStr}</span>
    </div>
    <div class="evidence-title">${title}</div>
    <div class="evidence-snippet">${snippet}</div>
    ${url !== '#' ? `
      <a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer" class="evidence-link">
        View Source Coverage &rarr;
      </a>
    ` : ''}
  `;

  return card;
}

function hideResultCard() {
  const card = document.getElementById('predictionResultCard');
  if (card) card.style.display = 'none';
}

function showAlert(type, message) {
  const container = document.getElementById('verifyAlertContainer');
  if (!container) return;
  container.innerHTML = `
    <div class="notice-box ${type}">
      ${escapeHtml(message)}
    </div>
  `;
}
