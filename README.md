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
- **Higher quality downloads** — use `--cookies cookies.txt` for 720p+ streams (auto-falls back to 360p if cookies are invalid)

## Run the local app on Windows

No website hosting is required. Processing and output stay on your computer.

1. Download the repository from GitHub and extract the ZIP.
2. Double-click **`setup.bat`** once. It creates an isolated Python environment, installs the app, and offers to install Deno when a supported JavaScript runtime is missing.
3. Double-click **`start.bat`** whenever you want to use the extractor.
4. Keep the terminal window open while using the app. Press `Ctrl+C` there to stop it.

The interface opens automatically in your browser. Frames are stored in `output/<label>/` unless you choose another output location.

FFmpeg is optional: without it, the app automatically uses compatible standard-quality video streams. Install [FFmpeg](https://ffmpeg.org/download.html) for merged 720p streams.

YouTube extraction requires Deno 2.3+ or Node.js 22+. The setup script checks this automatically and recommends Deno.

### Developer setup

The compiled Tailwind stylesheet is included, so normal users do not need Node.js or npm. Developers changing the design can run:

```bash
npm install
npm run watch:css
```

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

### Higher quality downloads (720p+)
By default, YouTube limits downloads to 360p. For higher quality, export your browser cookies:

1. Install the **"Get cookies.txt LOCALLY"** browser extension
2. Go to YouTube (logged in) and click the extension to export cookies
3. Save the file as `cookies.txt` in the project folder
4. Run with cookies:
```bash
python extract.py --config categories.json --cookies cookies.txt
```

> **Note:** YouTube periodically rotates/invalidates cookies as a security measure. If you see `"cookies are no longer valid"` or 403 errors, re-export fresh cookies from your browser. You don't need to keep YouTube open after exporting — cookies remain valid until YouTube rotates them (usually weeks/months). The script falls back to 360p automatically if cookies are invalid.

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
| `--cookies` | — | Path to cookies.txt for higher quality downloads |
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

## Troubleshooting

| Problem | Cause | Fix |
|---------|-------|-----|
| `"cookies are no longer valid"` or 403 errors | YouTube rotated your cookies | Re-export fresh cookies from browser |
| Only 360p quality despite cookies | Cookies expired or invalid | Re-export cookies while logged into YouTube |
| `"Please sign in"` error | Video requires authentication | Export cookies from a logged-in YouTube session |
| Download hangs/slow | YouTube throttling | Try again later or use different videos |

## License

MIT
