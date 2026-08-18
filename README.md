# YouTube Video Frame Extract

Extract frames from YouTube videos and organize them into labeled folders — perfect for building ML datasets.

```
YouTube Video → Download → Extract Frames → Organized Dataset
```

## Features

- **Search YouTube** directly or provide URLs
- **Auto-organize** frames into labeled folders
- **Configurable** interval, max frames, brightness filter
- **Smart filtering** — skips dark/transition frames automatically
- **Batch processing** — process multiple videos via JSON config
- **High quality** — extracts at native resolution (up to 1080p)

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

### Batch processing (JSON config)
```bash
python extract.py --config categories.json
```

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

## Options

| Flag | Default | Description |
|------|---------|-------------|
| `--search` | — | Search YouTube for this query |
| `--url` | — | Direct YouTube URL |
| `--config` | — | JSON config file |
| `--label` | — | Label name (required with `--url`) |
| `--output` | `./output` | Output directory |
| `--interval` | `1.5` | Seconds between frame captures |
| `--max-frames` | `500` | Max frames per label |
| `--skip-start` | `5` | Skip first N seconds |
| `--skip-end` | `5` | Skip last N seconds |
| `--brightness` | `15` | Min brightness to keep frame |
| `--dry-run` | — | Search only, don't download |

## Output Structure

```
output/
├── cats/
│   ├── cats_00001.jpg
│   ├── cats_00002.jpg
│   └── ...
├── dogs/
│   ├── dogs_00001.jpg
│   └── ...
└── birds/
    └── ...
```

## Use Cases

- **ML datasets** — Build image classification datasets
- **Data augmentation** — Extract training data from gameplay/showcase videos
- **Research** — Collect visual data for computer vision projects
- **Content analysis** — Sample frames from videos for analysis

## License

MIT
