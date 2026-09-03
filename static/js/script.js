const form = document.querySelector('#extract-form');
const sourceInput = document.querySelector('#source');
const sourceLabel = document.querySelector('#source-label');
const sourceHelp = document.querySelector('#source-help');
const labelInput = document.querySelector('#label');
const outputPath = document.querySelector('#output-path');
const modeButtons = [...document.querySelectorAll('.mode-button')];
const errorMessage = document.querySelector('#form-error');
const extractButton = document.querySelector('#extract-button');
const extractButtonLabel = document.querySelector('.button-label');
const emptyState = document.querySelector('#empty-state');
const jobState = document.querySelector('#job-state');
const jobMessage = document.querySelector('#job-message');
const jobCount = document.querySelector('#job-count');
const progressBar = document.querySelector('#progress-bar');
const cancelButton = document.querySelector('#cancel-button');
const frameGrid = document.querySelector('#frame-grid');
const activityLog = document.querySelector('#activity-log');
const intervalInput = document.querySelector('#interval');
const intervalValue = document.querySelector('#interval-value');

let currentMode = 'url';
let currentJob = null;
let pollTimer = null;

modeButtons.forEach((button) => {
  button.addEventListener('click', () => {
    currentMode = button.dataset.mode;
    modeButtons.forEach((item) => item.classList.toggle('active', item === button));
    const isSearch = currentMode === 'search';
    sourceLabel.textContent = isSearch ? 'Search phrase' : 'YouTube URLs';
    sourceInput.placeholder = isSearch ? 'e.g. cinematic city night drive' : 'Paste one YouTube URL per line';
    sourceInput.rows = isSearch ? 2 : 4;
    sourceHelp.textContent = isSearch
      ? 'The best matching video will be added to the folder label.'
      : 'Every video will add frames to the same folder label.';
    sourceInput.focus();
  });
});

labelInput.addEventListener('input', () => {
  const folder = labelInput.value.trim() || '<folder label>';
  outputPath.textContent = `output/${folder}/`;
});

intervalInput.addEventListener('input', () => {
  intervalValue.value = `${intervalInput.value}s`;
});

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  errorMessage.textContent = '';

  if (!form.reportValidity()) return;

  const data = new FormData(form);
  const payload = Object.fromEntries(data.entries());
  payload.mode = currentMode;
  payload.use_cookies = data.has('use_cookies');

  try {
    await startExtraction(payload);
  } catch {
    // startExtraction already presents the message beside the form.
  }
});

async function startExtraction(payload) {
  errorMessage.textContent = '';

  extractButton.disabled = true;
  extractButtonLabel.textContent = 'Starting…';

  try {
    const response = await fetch('/api/extract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Could not start extraction.');

    if (pollTimer) window.clearTimeout(pollTimer);
    currentJob = result.job_id;
    frameGrid.replaceChildren();
    frameGrid.dataset.rendered = '0';
    activityLog.textContent = '';
    jobMessage.textContent = 'Preparing your video…';
    jobCount.textContent = '0 frames';
    progressBar.style.width = '2%';
    emptyState.hidden = true;
    jobState.hidden = false;
    cancelButton.hidden = false;
    pollJob();
    return { jobId: currentJob, status: 'started' };
  } catch (error) {
    errorMessage.textContent = error.message;
    resetButton();
    throw error;
  }
}

cancelButton.addEventListener('click', async () => {
  if (!currentJob) return;
  cancelButton.disabled = true;
  await fetch(`/api/jobs/${currentJob}/cancel`, { method: 'POST' });
});

async function pollJob() {
  if (!currentJob) return;
  try {
    const renderedCount = Number(frameGrid.dataset.rendered || 0);
    const response = await fetch(`/api/jobs/${currentJob}?after=${renderedCount}`);
    const job = await response.json();
    if (!response.ok) throw new Error('Could not read extraction status.');

    jobMessage.textContent = job.message;
    jobCount.textContent = `${job.frame_count} frame${job.frame_count === 1 ? '' : 's'}`;
    progressBar.style.width = `${job.progress}%`;
    activityLog.textContent = job.logs.join('\n');
    activityLog.scrollTop = activityLog.scrollHeight;

    job.frames.forEach((source) => {
      const image = document.createElement('img');
      image.src = source;
      image.alt = `Extracted frame from ${job.label}`;
      image.loading = 'lazy';
      frameGrid.append(image);
    });
    frameGrid.dataset.rendered = String(renderedCount + job.frames.length);

    if (job.has_more_frames) {
      pollTimer = window.setTimeout(pollJob, 50);
      return;
    }

    if (job.status === 'complete') {
      cancelButton.hidden = true;
      resetButton();
      return;
    }
    if (job.status === 'error' || job.status === 'cancelled') {
      cancelButton.hidden = true;
      resetButton();
      return;
    }
    pollTimer = window.setTimeout(pollJob, 1200);
  } catch (error) {
    jobMessage.textContent = error.message;
    resetButton();
  }
}

function resetButton() {
  extractButton.disabled = false;
  extractButtonLabel.textContent = 'Extract frames';
  cancelButton.disabled = false;
}

function registerWebMcpTool() {
  const context = document.modelContext;
  if (!context?.registerTool) return;

  try {
    context.registerTool({
      name: 'start_frame_extraction',
      title: 'Start frame extraction',
      description: 'Extract filtered image frames from one or more YouTube URLs into one named local folder.',
      inputSchema: {
        type: 'object',
        properties: {
          source: { type: 'string', description: 'One or more full YouTube URLs separated by new lines.' },
          label: { type: 'string', description: 'The folder label for extracted frames.' },
          interval: { type: 'number', minimum: 0.1, maximum: 60 },
          max_frames: { type: 'integer', minimum: 1, maximum: 10000 },
          format: { type: 'string', enum: ['jpg', 'png'] },
        },
        required: ['source', 'label'],
        additionalProperties: false,
      },
      annotations: { readOnlyHint: false, untrustedContentHint: true },
      async execute(input) {
        sourceInput.value = input.source;
        labelInput.value = input.label;
        outputPath.textContent = `output/${input.label}/`;
        if (input.interval) intervalInput.value = input.interval;
        if (input.max_frames) document.querySelector('#max-frames').value = input.max_frames;
        if (input.format) document.querySelector('#format').value = input.format;
        currentMode = 'url';
        modeButtons.forEach((item) => item.classList.toggle('active', item.dataset.mode === 'url'));
        sourceLabel.textContent = 'YouTube URLs';
        sourceHelp.textContent = 'Every video will add frames to the same folder label.';
        sourceInput.rows = 4;
        document.querySelector('#extractor').scrollIntoView({ behavior: 'smooth' });
        return startExtraction({
          mode: 'url',
          source: input.source,
          label: input.label,
          interval: input.interval || 1.5,
          max_frames: input.max_frames || 500,
          format: input.format || 'jpg',
          brightness: 15,
          sharpness: 50,
          dedup: 0.95,
          use_cookies: false,
        });
      },
    });
  } catch (error) {
    console.warn('WebMCP registration was unavailable.', error);
  }
}

registerWebMcpTool();
