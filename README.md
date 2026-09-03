# YouTube Video Frame Extractor for Datasets

A local browser application that downloads YouTube videos, extracts useful frames, filters low-quality results, and organizes the images into labeled dataset folders.

```text
YouTube videos → frame filtering → output/<label>/
```

## Features

- Paste one or many YouTube URLs into a single extraction run.
- Save frames from every URL under one shared folder label.
- Search YouTube from the interface when you do not have a URL.
- Filter dark, blurry, and near-duplicate frames automatically.
- Choose the capture interval, total frame limit, image format, and filter thresholds.
- Follow extraction progress, logs, and scrollable frame previews in the browser.
- Start a new run with a freshly cleared activity gallery while keeping older images on disk.
- Run entirely on your computer—no hosted website or upload service is required.

## Quick start on Windows

1. Download or clone this repository.
2. Double-click **`setup.bat`** once.
3. Double-click **`start.bat`** whenever you want to use the app.
4. Keep the terminal window open while the app is running. Press `Ctrl+C` to stop it.

The setup script creates an isolated `.venv`, installs the Python packages, and checks for a supported JavaScript runtime. The app opens automatically at a local address such as `http://127.0.0.1:5000`. If that port is busy, it selects another port between `5001` and `5009`.

## Using the browser interface

### Multiple URLs in one dataset folder

1. Select **Paste URL**.
2. Paste one full YouTube URL per line.
3. Enter one **Folder label** for the dataset.
4. Optionally adjust the extraction settings.
5. Select **Extract frames**.

All URLs in the run contribute frames to the same folder:

```text
output/<folder label>/
```

The output location is fixed inside the repository's `output` directory. It cannot be changed from the browser interface. **Maximum frames (total)** applies across all URLs included in that run.

When another extraction starts, the activity gallery clears and displays only frames created by the new run. Existing files in the dataset folder are preserved, and new filenames continue the sequence.

### Search mode

Select **Search YouTube**, enter one search phrase, and provide a folder label. The extractor chooses a suitable result and saves its frames to the same fixed `output/<folder label>/` structure.

## Requirements

- Windows 10 or newer for the included batch-file workflow.
- Python 3.10 or newer.
- Deno 2.3+ or Node.js 22+ for current YouTube extraction.
- FFmpeg is optional but recommended for merged video and audio streams up to 720p.

If no supported JavaScript runtime is found, `setup.bat` offers to install Deno through Windows Package Manager. Without FFmpeg, the app uses a compatible standard-quality single-file stream.

## Output structure

```text
output/
├── cats/
│   ├── cats_00001.jpg
│   ├── cats_00002.jpg
│   └── ...
└── dogs/
    ├── dogs_00001.jpg
    └── ...
```

Temporary downloaded videos are removed after their frames are processed.

## Command-line usage

The browser interface is the simplest way to run the extractor, but the original CLI remains available.

### Search YouTube

```bash
python extract.py --search "cats playing" --label "cats"
```

### Extract one URL

```bash
python extract.py --url "https://youtube.com/watch?v=xxx" --label "dogs"
```

### Extract multiple URLs into one label

Repeat `--url` for every video:

```bash
python extract.py \
  --url "https://youtu.be/aaa" \
  --url "https://youtu.be/bbb" \
  --label "dogs"
```

On Windows Command Prompt, place the command on one line instead of using the `\` continuations.

### Use lossless PNG frames

```bash
python extract.py --url "https://youtube.com/watch?v=xxx" --label "dogs" --format png
```

### Process a JSON configuration

```bash
python extract.py --config categories.json
```

Example `categories.json`:

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

### Process a labels file

```bash
python extract.py --labels labels.txt
```

Provide one search label per line in `labels.txt`.

## CLI options

| Flag | Default | Description |
|---|---:|---|
| `--search` | — | Search YouTube for one phrase |
| `--url` | — | YouTube URL; repeat for multiple videos in one label |
| `--config` | — | JSON file containing labels and URLs |
| `--labels` | — | Text file containing one search label per line |
| `--label` | — | Dataset folder label; required with `--url` |
| `--output` | `./output` | CLI output directory; the browser UI always uses `./output` |
| `--interval` | `1.5` | Seconds between capture attempts |
| `--max-frames` | `500` | Maximum frames per label/run |
| `--skip-start` | `5` | Seconds skipped at the beginning |
| `--skip-end` | `5` | Seconds skipped at the end |
| `--brightness` | `15` | Minimum brightness to keep a frame |
| `--sharpness` | `50` | Minimum sharpness to keep a frame |
| `--dedup` | `0.95` | Duplicate similarity threshold from 0 to 1 |
| `--format` | `jpg` | Output format: `jpg` or `png` |
| `--cookies` | — | Path to `cookies.txt` for videos requiring authentication |
| `--dry-run` | — | Preview search/config selection without downloading |

## Filtering

| Filter | Behavior |
|---|---|
| Brightness | Removes very dark frames such as fades and loading screens |
| Sharpness | Uses Laplacian variance to remove blurry frames |
| Duplicates | Compares consecutive accepted frames to reduce near-duplicates |

Lower the sharpness or brightness value if too many frames are being rejected. Lower the duplicate threshold to filter similar frames more aggressively.

## Troubleshooting

| Problem | Fix |
|---|---|
| `WinError 10013` or socket access denied | Close restricted preview servers and launch the app through `start.bat`. Check that Python is allowed through local firewall/security software. |
| Deno or Node.js is required | Run `setup.bat` again and accept the offered Deno installation. |
| A video returns 403 or asks you to sign in | Export fresh YouTube cookies to `cookies.txt`, then enable cookies in the advanced settings. |
| Only standard-quality video is available | Install FFmpeg and restart the app. |
| The default port is busy | The launcher automatically chooses the next available port. Use the address printed in the terminal. |
| Few or no frames are saved | Reduce the brightness/sharpness filters, increase the frame limit, or choose a shorter interval. |

## Development

The compiled Tailwind stylesheet is committed, so people using the app do not need npm. To change the interface styling:

```bash
npm install
npm run watch:css
```

Run the regression tests with:

```bash
python -m unittest discover -s tests -v
```

## Credits

Created by [Lance Christian C. Crucis](https://lance-crucis.vercel.app).

## License

MIT — see [LICENSE](LICENSE).
