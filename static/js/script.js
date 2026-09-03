const form = document.querySelector('#extract-form');
const sourceInput = document.querySelector('#source');
const sourceLabel = document.querySelector('#source-label');
const modeButtons = [...document.querySelectorAll('.mode-button')];
const errorMessage = document.querySelector('#form-error');
const extractButton = document.querySelector('#extract-button');
const emptyState = document.querySelector('#empty-state');
const jobState = document.querySelector('#job-state');
const jobMessage = document.querySelector('#job-message');
const jobCount = document.querySelector('#job-count');
const progressBar = document.querySelector('#progress-bar');
const statusDot = document.querySelector('#status-dot');
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
    sourceLabel.textContent = isSearch ? 'Search phrase' : 'YouTube URL';
    sourceInput.type = isSearch ? 'text' : 'url';
    sourceInput.placeholder = isSearch ? 'e.g. cinematic city night drive' : 'https://youtube.com/watch?v=…';
    sourceInput.focus();
  });
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
  extractButton.lastChild.textContent = ' Starting…';

  try {
    const response = await fetch('/api/extract', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    const result = await response.json();
    if (!response.ok) throw new Error(result.error || 'Could not start extraction.');

    currentJob = result.job_id;
    emptyState.hidden = true;
    jobState.hidden = false;
    cancelButton.hidden = false;
    statusDot.className = 'status-dot running';
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
    const response = await fetch(`/api/jobs/${currentJob}`);
    const job = await response.json();
    if (!response.ok) throw new Error('Could not read extraction status.');

    jobMessage.textContent = job.message;
    jobCount.textContent = `${job.frame_count} frame${job.frame_count === 1 ? '' : 's'}`;
    progressBar.style.width = `${job.progress}%`;
    activityLog.textContent = job.logs.join('\n');
    activityLog.scrollTop = activityLog.scrollHeight;

    const knownSources = new Set([...frameGrid.querySelectorAll('img')].map((img) => img.getAttribute('src')));
    job.frames.forEach((source) => {
      if (knownSources.has(source)) return;
      const image = document.createElement('img');
      image.src = source;
      image.alt = `Extracted frame from ${job.label}`;
      image.loading = 'lazy';
      frameGrid.append(image);
    });

    if (job.status === 'complete') {
      statusDot.className = 'status-dot complete';
      cancelButton.hidden = true;
      resetButton();
      return;
    }
    if (job.status === 'error' || job.status === 'cancelled') {
      statusDot.className = 'status-dot';
      cancelButton.hidden = true;
      resetButton();
      return;
    }
    pollTimer = window.setTimeout(pollJob, 1200);
  } catch (error) {
    jobMessage.textContent = error.message;
    statusDot.className = 'status-dot';
    resetButton();
  }
}

function resetButton() {
  extractButton.disabled = false;
  extractButton.lastChild.textContent = ' Extract frames';
  cancelButton.disabled = false;
}

function registerWebMcpTool() {
  const context = document.modelContext;
  if (!context?.registerTool) return;

  try {
    context.registerTool({
      name: 'start_frame_extraction',
      title: 'Start frame extraction',
      description: 'Start extracting filtered image frames from a YouTube URL into a named local folder.',
      inputSchema: {
        type: 'object',
        properties: {
          source: { type: 'string', description: 'A full YouTube video URL.' },
          label: { type: 'string', description: 'The folder label for extracted frames.' },
          output: { type: 'string', description: 'A local output path, relative to the project by default.' },
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
        document.querySelector('#label').value = input.label;
        if (input.output) document.querySelector('#output').value = input.output;
        if (input.interval) intervalInput.value = input.interval;
        if (input.max_frames) document.querySelector('#max-frames').value = input.max_frames;
        if (input.format) document.querySelector('#format').value = input.format;
        currentMode = 'url';
        modeButtons.forEach((item) => item.classList.toggle('active', item.dataset.mode === 'url'));
        sourceLabel.textContent = 'YouTube URL';
        sourceInput.type = 'url';
        document.querySelector('#extractor').scrollIntoView({ behavior: 'smooth' });
        return startExtraction({
          mode: 'url',
          source: input.source,
          label: input.label,
          output: input.output || 'output',
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
