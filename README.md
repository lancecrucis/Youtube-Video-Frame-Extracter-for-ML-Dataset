# YouTube Video Frame Extract

Extract frames from YouTube videos and organize them into labeled folders — perfect for building ML datasets.

```
YouTube Video → Download → Extract Frames → Organized Dataset
```

## Features

- **Search YouTube** directly or provide URLs
- **Auto-organize** frames into labeled folders
- **Configurable** interval, max frames, brightness filter
- **Smart filtering** — skips dark, blurry, and duplicate frames automatically
- **Batch processing** — process multiple videos via JSON config or labels file
- **High quality frames** — JPEG quality 100, or lossless PNG with `--format png`
- **Browser auth** — use `--cookies-from-browser chrome` for higher quality streams

## Installation

```bash
pip install yt-dlp opencv-python-headless
```

> `ffmpeg` is also required for video merging. [Install ffmpeg](https://ffmpeg.org/download.html)

## Quick Start

### Search YouTube and extract frames
```bash
python extract.py --search "cats playing" --label "cats"
```

### Single YouTube URL
```bash
python extract.py --url "https://youtube.com/watch?v=xxx" --label "dogs"
```

### Lossless frames
```bash
python extract.py --url "https://youtube.com/watch?v=xxx" --label "dogs" --format png
```

### Batch from labels file
```bash
python extract.py --labels labels.txt
```

`labels.txt` format — one label per line:
```
Reaver
Spectrum
Oni
Prime
Gaia's Vengeance
```

The tool searches YouTube for each label (e.g., "valorant Reaver skin gameplay") and extracts frames from the best match.

### Batch processing (JSON config)
```bash
python extract.py --config categories.json
```

---

## 🔥 Getting Higher Quality (720p / 1080p)

By default, YouTube only allows **360p** downloads without authentication. For higher quality, use your browser cookies:

### Step-by-step:

1. **Open your browser** (Chrome, Edge, or Firefox) and **log into YouTube**
2. **Find the videos you want** — search for skin showcases, gameplay, etc.
3. **Copy the video URLs** into a `categories.json` file:

```json
[
    {
        "label": "Reaver",
        "url": "https://youtube.com/watch?v=ABC123"
    },
    {
        "label": "Oni",
        "url": [
            "https://youtube.com/watch?v=DEF456",
            "https://youtube.com/watch?v=GHI789"
        ]
    },
    {
        "label": "Spectrum",
        "url": "https://youtube.com/watch?v=JKL012"
    }
]
```

4. **Run with your browser cookies**:

```bash
python extract.py --config categories.json --cookies-from-browser chrome
```

Supported browsers: `chrome`, `edge`, `firefox`

### Why this works

| Mode | Quality | How |
|------|---------|-----|
| Auto (no cookies) | 360p | YouTube blocks higher quality for unauthenticated requests |
| Manual + cookies | 720p–1080p | Your logged-in session is trusted by YouTube |

> **Note:** Higher quality is not guaranteed even with cookies — YouTube may still restrict some videos. But it significantly improves your chances.

### Alternative: Use local videos

If cookies don't work, download videos yourself (browser extensions, online converters) and process them locally:

```bash
python extract.py --url "file:///C:/Users/you/Videos/reaver_showcase.mp4" --label "Reaver"
```

---

## Config File Format

Create a `categories.json`:

```json
[
    {
        "label": "cats",
        "url": "https://youtube.com/watch?v=xxx"
    },
    {
        "label": "dogs",
        "url": [
            "https://youtube.com/watch?v=yyy",
            "https://youtube.com/watch?v=zzz"
        ]
    }
]
```

Each entry can have a single URL string or an array of URLs for the same label.

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--search` | — | Search YouTube for this query |
| `--url` | — | Direct YouTube URL (or local file path) |
| `--config` | — | JSON config file with labels + URLs |
| `--labels` | — | Text file with one label per line |
| `--label` | — | Label name (required with `--url`) |
| `--output` | `./output` | Output directory |
| `--interval` | `1.5` | Seconds between frame captures |
| `--max-frames` | `500` | Max frames per label |
| `--skip-start` | `5` | Skip first N seconds |
| `--skip-end` | `5` | Skip last N seconds |
| `--brightness` | `15` | Min brightness to keep frame |
| `--sharpness` | `50` | Min sharpness to keep frame (higher = sharper) |
| `--dedup` | `0.95` | Duplicate similarity threshold, 0-1 (lower = stricter) |
| `--cookies-from-browser` | — | Extract cookies for higher quality (e.g., `chrome`) |
| `--format` | `jpg` | Frame format: `jpg` (quality 100) or `png` (lossless) |
| `--dry-run` | — | Search only, don't download |

## Filtering

Frames are automatically filtered to keep only high-quality images:

| Filter | Default | What it does |
|--------|---------|-------------|
| **Brightness** | `15` | Skips dark/underexposed frames (loading screens, transitions) |
| **Sharpness** | `50` | Skips blurry frames using Laplacian variance detection |
| **Duplicates** | `0.95` | Skips frames too similar to the previous one (reduces redundancy) |

Adjust with `--brightness`, `--sharpness`, and `--dedup` flags.

## Output Structure

```
output/
├── Reaver/
│   ├── Reaver_00001.jpg
│   ├── Reaver_00002.jpg
│   └── ...
├── Oni/
│   ├── Oni_00001.jpg
│   └── ...
└── Spectrum/
    └── ...
```

## Use Cases

- **ML datasets** — Build image classification datasets
- **Data augmentation** — Extract training data from gameplay/showcase videos
- **Research** — Collect visual data for computer vision projects
- **Content analysis** — Sample frames from videos for analysis

## License

MIT
