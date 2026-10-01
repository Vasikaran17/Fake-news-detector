/**
 * Fake News Detector - Model Training Logic
 */

let selectedFile = null;

document.addEventListener('DOMContentLoaded', () => {
  initTrainPage();
});

function initTrainPage() {
  const dropzone = document.getElementById('csvDropzone');
  const fileInput = document.getElementById('csvFileInput');
  const browseBtn = document.getElementById('browseCsvBtn');
  const trainBtn = document.getElementById('startTrainBtn');

  // Check existing model status on load
  checkExistingModel();

  // Click on dropzone or browse button opens file picker
  if (browseBtn && fileInput) {
    browseBtn.addEventListener('click', (e) => {
      e.stopPropagation();
      fileInput.click();
    });
  }

  if (dropzone && fileInput) {
    dropzone.addEventListener('click', () => fileInput.click());

    // Drag and Drop
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
        handleFileSelected(files[0]);
      }
    });

    fileInput.addEventListener('change', () => {
      if (fileInput.files && fileInput.files.length > 0) {
        handleFileSelected(fileInput.files[0]);
      }
    });
  }

  // Train button click
  if (trainBtn) {
    trainBtn.addEventListener('click', executeTraining);
  }
}

/**
 * Checks if a model was already trained and displays its performance
 */
async function checkExistingModel() {
  const statusContainer = document.getElementById('currentModelStatusBox');
  if (!statusContainer) return;

  try {
    const res = await fetch(`${API_BASE}/api/model-status`);
    const data = await res.json();

    if (data.is_trained) {
      statusContainer.innerHTML = `
        <div class="notice-box success">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0;">
            <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
            <polyline points="22 4 12 14.01 9 11.01"></polyline>
          </svg>
          <div>
            <strong>Model Currently Ready</strong>: Trained on <strong>${data.total_samples}</strong> articles with 
            <strong>${data.performance.accuracy}%</strong> accuracy (${data.algorithm}). 
            You can retrain anytime by uploading a new dataset below, or <a href="/verify" style="color:var(--primary); font-weight:600; text-decoration:underline;">proceed to Verify News &rarr;</a>
          </div>
        </div>
      `;
      // Also render performance metrics if available
      renderPerformanceMetrics(data);
    } else {
      statusContainer.innerHTML = `
        <div class="notice-box warn">
          <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink:0;">
            <circle cx="12" cy="12" r="10"></circle>
            <line x1="12" y1="8" x2="12" y2="12"></line>
            <line x1="12" y1="16" x2="12.01" y2="16"></line>
          </svg>
          <div>
            <strong>Model Not Trained</strong>: No model found on the server. Please upload your labelled CSV dataset below and click <strong>Train Model</strong>.
          </div>
        </div>
      `;
    }
  } catch (err) {
    statusContainer.innerHTML = `
      <div class="notice-box error">
        <strong>Backend Disconnected</strong>: Cannot connect to the Flask server. Please make sure the backend is running at <code>http://127.0.0.1:5000</code>.
      </div>
    `;
  }
}

/**
 * Handles CSV selection, inspects the file, and displays preview metadata
 */
function formatFileSize(bytes) {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  return (bytes / (1024 * 1024 * 1024)).toFixed(2) + ' GB';
}

/**
 * Handles CSV selection, inspects the file, and displays preview metadata.
 * Optimized to handle large datasets (> 600 MB up to 1.5 GB).
 */
async function handleFileSelected(file) {
  const fileInfoCard = document.getElementById('fileInfoCard');
  const alertContainer = document.getElementById('trainAlertContainer');
  const trainBtn = document.getElementById('startTrainBtn');

  alertContainer.innerHTML = '';

  if (!file.name.toLowerCase().endsWith('.csv')) {
    showAlert('error', 'Unsupported file format. Please upload a standard comma-separated (.csv) file.');
    selectedFile = null;
    if (trainBtn) trainBtn.disabled = true;
    if (fileInfoCard) fileInfoCard.style.display = 'none';
    return;
  }

  // Maximum allowed size: 1.5 GB (1500 MB)
  const maxLimit = 1500 * 1024 * 1024;
  if (file.size > maxLimit) {
    showAlert('error', `Selected file (${formatFileSize(file.size)}) exceeds the maximum upload limit of 1.5 GB.`);
    selectedFile = null;
    if (trainBtn) trainBtn.disabled = true;
    if (fileInfoCard) fileInfoCard.style.display = 'none';
    return;
  }

  selectedFile = file;

  // Show preliminary file info while inspecting
  if (fileInfoCard) {
    fileInfoCard.style.display = 'block';
    fileInfoCard.innerHTML = `
      <div style="display:flex; align-items:center; gap:10px; color:var(--text-muted);">
        <span class="spinner spinner-dark"></span> Inspecting CSV dataset structure (${formatFileSize(file.size)})...
      </div>
    `;
  }

  // For very large files (> 20 MB up to 1.5 GB), perform fast instant client-side header inspection
  // to avoid uploading hundreds of megabytes twice
  if (file.size > 20 * 1024 * 1024) {
    try {
      const slice = file.slice(0, 1024 * 1024); // Read first 1MB
      const reader = new FileReader();
      reader.onload = function(e) {
        const textChunk = e.target.result;
        const lines = textChunk.split(/\r?\n/).filter(l => l.trim() !== '');
        if (lines.length === 0) {
          showAlert('error', 'The uploaded CSV file appears to be empty.');
          return;
        }

        const headerLine = lines[0].toLowerCase();
        const hasText = headerLine.includes('text') || headerLine.includes('news') || headerLine.includes('article');
        const hasLabel = headerLine.includes('label') || headerLine.includes('class') || headerLine.includes('target');

        if (!hasText || !hasLabel) {
          showAlert('error', "CSV header must contain 'text' and 'label' columns. Detected header: " + lines[0]);
          if (trainBtn) trainBtn.disabled = true;
          return;
        }

        // Estimate row count based on average bytes per line
        const sampleLines = lines.slice(1, Math.min(lines.length, 100));
        const avgLineBytes = sampleLines.reduce((acc, l) => acc + l.length + 1, 0) / sampleLines.length;
        const estimatedRows = Math.round(file.size / (avgLineBytes || 200));

        fileInfoCard.innerHTML = `
          <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px; margin-bottom:12px;">
            <div>
              <h4 style="font-size:1.05rem; font-weight:600; color:var(--text-main); margin-bottom:4px;">
                📄 ${escapeHtml(file.name)}
              </h4>
              <span style="font-size:0.85rem; color:var(--text-muted);">${formatFileSize(file.size)} &bull; Verified Large CSV Dataset</span>
            </div>
            <span class="badge" style="background:#e0f2fe; color:#0369a1; padding:4px 10px; border-radius:4px; font-weight:600; font-size:0.82rem;">
              Ready to Train
            </span>
          </div>

          <div class="file-meta-list">
            <div class="file-meta-item">File Size: <strong>${formatFileSize(file.size)}</strong></div>
            <div class="file-meta-item">Estimated Articles: <strong>~${estimatedRows.toLocaleString()}</strong></div>
            <div class="file-meta-item">Header Verified: <strong style="color:var(--real-color);">text, label detected</strong></div>
            <div class="file-meta-item">Upload Mode: <strong>High-Throughput Parallel Pipeline</strong></div>
          </div>
        `;

        if (trainBtn) {
          trainBtn.disabled = false;
          trainBtn.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      };
      reader.readAsText(slice);
      return;
    } catch (sliceErr) {
      console.warn('Client slice inspect failed, falling back to server preview', sliceErr);
    }
  }

  // Standard server-side preview for files under 20 MB
  const formData = new FormData();
  formData.append('file', file);

  try {
    const res = await fetch(`${API_BASE}/api/preview-dataset`, {
      method: 'POST',
      body: formData
    });

    const result = await res.json();

    if (!res.ok) {
      throw new Error(result.error || 'Failed to inspect CSV file');
    }

    const d = result.data;
    const formattedSize = formatFileSize(file.size);

    fileInfoCard.innerHTML = `
      <div style="display:flex; justify-content:space-between; align-items:flex-start; flex-wrap:wrap; gap:12px; margin-bottom:12px;">
        <div>
          <h4 style="font-size:1.05rem; font-weight:600; color:var(--text-main); margin-bottom:4px;">
            📄 ${escapeHtml(file.name)}
          </h4>
          <span style="font-size:0.85rem; color:var(--text-muted);">${formattedSize} &bull; Verified CSV structure</span>
        </div>
        <span class="badge" style="background:#e0f2fe; color:#0369a1; padding:4px 10px; border-radius:4px; font-weight:600; font-size:0.82rem;">
          Ready to Train
        </span>
      </div>

      <div class="file-meta-list">
        <div class="file-meta-item">Rows: <strong>${d.total_rows.toLocaleString()}</strong></div>
        <div class="file-meta-item">Detected Columns: <strong>${d.columns.join(', ')}</strong></div>
        <div class="file-meta-item">REAL Articles: <strong style="color:var(--real-color);">${d.label_distribution.REAL.toLocaleString()}</strong></div>
        <div class="file-meta-item">FAKE Articles: <strong style="color:var(--fake-color);">${d.label_distribution.FAKE.toLocaleString()}</strong></div>
      </div>
    `;

    if (trainBtn) {
      trainBtn.disabled = false;
      trainBtn.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }

  } catch (err) {
    selectedFile = null;
    if (trainBtn) trainBtn.disabled = true;
    if (fileInfoCard) fileInfoCard.style.display = 'none';
    showAlert('error', err.message);
  }
}

/**
 * Executes model training via POST /api/train
 */
async function executeTraining() {
  if (!selectedFile) {
    showAlert('error', 'Please select a CSV dataset file first.');
    return;
  }

  const trainBtn = document.getElementById('startTrainBtn');
  const alertContainer = document.getElementById('trainAlertContainer');
  const resultsCard = document.getElementById('trainingResultsCard');

  alertContainer.innerHTML = '';
  if (resultsCard) resultsCard.style.display = 'none';

  // Set loading state with informative progress
  trainBtn.disabled = true;
  const originalBtnText = trainBtn.innerHTML;
  const isLarge = selectedFile.size > 50 * 1024 * 1024;

  trainBtn.innerHTML = `<span class="spinner"></span> ${isLarge ? 'Processing Large Dataset...' : 'Training Model...'}`;

  if (isLarge) {
    showAlert('warn', `Uploading and training on large dataset (${formatFileSize(selectedFile.size)}). The backend is streaming the file, running parallel NLTK preprocessing, and extracting TF-IDF features. Please wait...`);
  } else {
    showAlert('warn', 'Starting training pipeline: cleaning text with NLTK &rarr; extracting TF-IDF features &rarr; fitting Logistic Regression...');
  }

  const formData = new FormData();
  formData.append('file', selectedFile);

  try {
    const res = await fetch(`${API_BASE}/api/train`, {
      method: 'POST',
      body: formData
    });

    const result = await res.json();

    if (!res.ok) {
      throw new Error(result.error || 'Failed to train model');
    }

    // Success!
    const note = result.metadata?.dataset_sampling_note ? `<br><small style="color:var(--text-muted);">${result.metadata.dataset_sampling_note}</small>` : '';
    showAlert('success', `Model trained successfully! Preprocessing pipeline, TF-IDF vectorizer, and Logistic Regression model saved locally.${note}`);

    renderPerformanceMetrics(result.metadata);

    // Refresh header status
    if (typeof fetchAndRenderModelStatus === 'function') {
      fetchAndRenderModelStatus();
    }

    // Scroll to results
    if (resultsCard) {
      resultsCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

  } catch (err) {
    showAlert('error', err.message);
  } finally {
    trainBtn.disabled = false;
    trainBtn.innerHTML = originalBtnText;
  }
}

/**
 * Renders the Model Performance card with accuracy, precision, recall, F1, and confusion matrix
 */
function renderPerformanceMetrics(meta) {
  const resultsCard = document.getElementById('trainingResultsCard');
  if (!resultsCard || !meta || !meta.performance) return;

  const perf = meta.performance;
  const cm = meta.confusion_matrix;

  document.getElementById('metricAccuracy').textContent = `${perf.accuracy}%`;
  document.getElementById('metricPrecision').textContent = `${perf.precision}%`;
  document.getElementById('metricRecall').textContent = `${perf.recall}%`;
  document.getElementById('metricF1').textContent = `${perf.f1_score}%`;

  document.getElementById('metaTotalSamples').textContent = meta.total_samples || '-';
  document.getElementById('metaTrainSamples').textContent = meta.training_samples || '-';
  document.getElementById('metaTestSamples').textContent = meta.testing_samples || '-';
  document.getElementById('metaTrainDate').textContent = meta.training_date || 'Just now';

  // Render Confusion Matrix
  const cmContainer = document.getElementById('confusionMatrixTableContainer');
  if (cmContainer && cm) {
    cmContainer.innerHTML = `
      <table class="cm-table">
        <thead>
          <tr>
            <th rowspan="2" style="background:#f8fafc; font-size:0.8rem; color:var(--text-muted); vertical-align:middle;">
              Actual &darr; \\ Pred &rarr;
            </th>
            <th colspan="2">Predicted Label</th>
          </tr>
          <tr>
            <th>REAL</th>
            <th>FAKE</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th style="text-align:left; background:#f8fafc;">Actual REAL</th>
            <td class="cm-cell-tp" title="True Real: correctly classified as REAL">
              <strong>${cm.actual_real_pred_real}</strong>
              <div style="font-size:0.75rem; color:var(--real-dark);">True Real</div>
            </td>
            <td class="cm-cell-fp" title="False Fake: Real news wrongly classified as Fake">
              <strong>${cm.actual_real_pred_fake}</strong>
              <div style="font-size:0.75rem; color:var(--fake-dark);">False Fake</div>
            </td>
          </tr>
          <tr>
            <th style="text-align:left; background:#f8fafc;">Actual FAKE</th>
            <td class="cm-cell-fn" title="False Real: Fake news wrongly classified as Real">
              <strong>${cm.actual_fake_pred_real}</strong>
              <div style="font-size:0.75rem; color:var(--fake-dark);">False Real</div>
            </td>
            <td class="cm-cell-tn" title="True Fake: correctly classified as FAKE">
              <strong>${cm.actual_fake_pred_fake}</strong>
              <div style="font-size:0.75rem; color:var(--real-dark);">True Fake</div>
            </td>
          </tr>
        </tbody>
      </table>
    `;
  }

  resultsCard.style.display = 'block';
}

function showAlert(type, message) {
  const container = document.getElementById('trainAlertContainer');
  if (!container) return;
  container.innerHTML = `
    <div class="notice-box ${type}">
      ${escapeHtml(message)}
    </div>
  `;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}
