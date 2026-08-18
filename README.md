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
