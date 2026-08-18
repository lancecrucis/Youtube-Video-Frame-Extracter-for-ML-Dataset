"""
YouTube Video Frame Extract
===========================
Extract frames from YouTube videos and organize them into folders.

Features:
  - Search YouTube or provide direct URLs
  - Extract frames at configurable intervals
  - Filter out dark/blurry/duplicate frames automatically
  - Organize output by category/label name
  - Supports single URLs or batch processing via JSON config or labels file

Usage:
    # Search YouTube and extract
    python extract.py --search "cats playing" --label "cats"

    # Single URL
    python extract.py --url "https://youtube.com/watch?v=xxx" --label "cats"

    # Batch from JSON config
    python extract.py --config categories.json

    # Batch from text file (one label per line)
    python extract.py --labels labels.txt

    # Higher quality with cookies
    python extract.py --config categories.json --cookies cookies.txt
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

try:
    import cv2
except ImportError:
    print("ERROR: opencv-python not installed. Run: pip install opencv-python-headless")
    sys.exit(1)


def search_youtube(query: str, max_results: int = 5) -> list[dict]:
    """Search YouTube and return video info."""
    cmd = [
        sys.executable, "-m", "yt_dlp",
        f"ytsearch{max_results}:{query}",
        "--flat-playlist",
        "-j",
        "--js-runtimes", "node",
    ]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
        videos = []
        for line in result.stdout.strip().split("\n"):
            if line:
                data = json.loads(line)
                videos.append({
                    "id": data.get("id"),
                    "title": data.get("title", "N/A"),
                    "url": f"https://youtube.com/watch?v={data['id']}",
                    "duration": data.get("duration", 0),
                })
        return videos
    except Exception as e:
        print(f"  Search error: {e}")
        return []


def pick_best_video(videos: list[dict]) -> dict | None:
    """Pick the best video from search results."""
    if not videos:
        return None
    scored = []
    for v in videos:
        dur = v.get("duration", 0) or 0
        score = 0
        if 60 <= dur <= 600:
            score += 10
        elif dur > 300:
            score += 5
        if dur < 30:
            score -= 10
        scored.append((score, v))
    scored.sort(key=lambda x: x[0], reverse=True)
    return scored[0][1]


def download_video(url: str, output_dir: str, name: str,
                   cookies: str | None = None) -> str | None:
    """Download a YouTube video using yt-dlp."""
    output_path = os.path.join(output_dir, f"{name}.mp4")
    cmd = [
        sys.executable, "-m", "yt_dlp",
        "-f", "bestvideo[height<=720][ext=mp4]+bestaudio[ext=m4a]/bestvideo[height<=720]+bestaudio/best[height<=720]",
        "--merge-output-format", "mp4",
        "--js-runtimes", "node",
        "--extractor-args", "youtube:player_client=mweb",
        "-o", output_path,
        "--no-playlist",
        "--socket-timeout", "30",
        "--retries", "3",
    ]
    if cookies:
        cmd.extend(["--cookies", cookies])

    cmd.append(url)

    print(f"  Downloading...")
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if os.path.exists(output_path):
            return output_path
        for f in os.listdir(output_dir):
            if f.startswith(name) and f.endswith(".mp4"):
                return os.path.join(output_dir, f)
        if result.returncode != 0:
            if cookies and ("403" in result.stderr or "cookies" in result.stderr.lower()):
                print(f"  Cookies invalid, retrying without cookies...")
                cmd_no_cookies = [c for c in cmd if c != cookies and c != "--cookies"]
                result = subprocess.run(cmd_no_cookies, capture_output=True, text=True, timeout=600)
                if os.path.exists(output_path):
                    return output_path
                for f in os.listdir(output_dir):
                    if f.startswith(name) and f.endswith(".mp4"):
                        return os.path.join(output_dir, f)
            print(f"  ERROR: {result.stderr[:200]}")
            return None
        return None
    except subprocess.TimeoutExpired:
        print(f"  ERROR: Download timed out")
        return None


def extract_frames(
    video_path: str,
    output_dir: str,
    label: str,
    interval: float = 1.0,
    max_frames: int = 500,
    skip_start: float = 5.0,
    skip_end: float = 5.0,
    brightness_thresh: float = 15.0,
    sharpness_thresh: float = 50.0,
    dedup_thresh: float = 0.95,
    fmt: str = "jpg",
) -> int:
    """Extract frames from a video and save to label folder."""
    label_dir = os.path.join(output_dir, label)
    os.makedirs(label_dir, exist_ok=True)

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"  ERROR: Cannot open video")
        return 0

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps if fps > 0 else 0
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    print(f"  {width}x{height}, {fps:.0f} FPS, {duration:.0f}s")

    frame_interval = max(1, int(fps * interval))
    start_frame = int(fps * skip_start)
    end_frame = total_frames - int(fps * skip_end)

    ext = "png" if fmt == "png" else "jpg"
    existing = [f for f in os.listdir(label_dir) if f.endswith(f".{ext}")]
    idx = len(existing) + 1
    count = 0
    pos = start_frame
    prev_frame = None
    skipped_blur = 0
    skipped_dup = 0

    while pos < end_frame and count < max_frames:
        cap.set(cv2.CAP_PROP_POS_FRAMES, pos)
        ret, frame = cap.read()
        if not ret:
            break

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

        # Filter dark frames
        if gray.mean() < brightness_thresh:
            pos += frame_interval
            continue

        # Filter blurry frames
        sharpness = cv2.Laplacian(gray, cv2.CV_64F).var()
        if sharpness < sharpness_thresh:
            skipped_blur += 1
            pos += frame_interval
            continue

        # Filter duplicate/similar frames
        if prev_frame is not None:
            similarity = cv2.matchTemplate(gray, prev_frame, cv2.TM_CCOEFF_NORMED)[0][0]
            if similarity > dedup_thresh:
                skipped_dup += 1
                pos += frame_interval
                continue
        prev_frame = gray.copy()

        # Save frame
        fname = f"{label}_{idx + count:05d}.{ext}"
        params = [cv2.IMWRITE_PNG_COMPRESSION, 1] if fmt == "png" else [cv2.IMWRITE_JPEG_QUALITY, 100]
        cv2.imwrite(os.path.join(label_dir, fname), frame, params)
        count += 1

        if count % 50 == 0:
            print(f"    {count} frames...")

        pos += frame_interval

    cap.release()
    skipped_total = skipped_blur + skipped_dup
    skip_info = f" (skipped {skipped_blur} blurry, {skipped_dup} duplicates)" if skipped_total > 0 else ""
    print(f"  Extracted {count} frames -> {label_dir}{skip_info}")
    return count


def process_urls(entries: list[dict], output_dir: str, interval: float,
                 max_frames: int, skip_start: float, skip_end: float,
                 brightness_thresh: float, sharpness_thresh: float,
                 dedup_thresh: float, fmt: str = "jpg",
                 cookies: str | None = None):
    """Process a list of {label, url/list} entries."""
    temp_dir = os.path.join(output_dir, "_temp")
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)

    total = 0
    for i, entry in enumerate(entries):
        label = entry["label"]
        url = entry["url"]

        urls = [url] if isinstance(url, str) else url
        urls = [u for u in urls if u and ("youtube" in u.lower() or "youtu.be" in u.lower())]

        if not urls:
            print(f"  Skipping '{label}' — no valid URLs")
            continue

        print(f"\n[{i+1}/{len(entries)}] {label} ({len(urls)} video(s))")
        label_frames = 0

        for j, u in enumerate(urls):
            if len(urls) > 1:
                print(f"  Video {j+1}/{len(urls)}: {u}")

            safe = label.replace(" ", "_").replace("/", "_")
            vid = u.split("v=")[-1].split("&")[0] if "v=" in u else u.split("/")[-1]
            name = f"{safe}_{vid[:8]}"
            video_path = download_video(u, temp_dir, name, cookies=cookies)

            if not video_path:
                continue

            n = extract_frames(
                video_path, output_dir, label,
                interval=interval,
                max_frames=max_frames,
                skip_start=skip_start,
                skip_end=skip_end,
                brightness_thresh=brightness_thresh,
                sharpness_thresh=sharpness_thresh,
                dedup_thresh=dedup_thresh,
                fmt=fmt,
            )
            label_frames += n

            try:
                os.remove(video_path)
            except:
                pass

        total += label_frames

    try:
        os.rmdir(temp_dir)
    except:
        pass

    return total


def main():
    parser = argparse.ArgumentParser(
        description="Extract frames from YouTube videos and organize by label",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python extract.py --search "cats playing" --label "cats"
  python extract.py --url "https://youtube.com/watch?v=xxx" --label "dogs"
  python extract.py --config categories.json
  python extract.py --labels labels.txt
  python extract.py --config categories.json --cookies cookies.txt
        """,
    )

    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--search", type=str, help="Search YouTube for this query")
    input_group.add_argument("--url", type=str, help="Direct YouTube URL")
    input_group.add_argument("--config", type=str, help="JSON config file with labels + URLs")
    input_group.add_argument("--labels", type=str, help="Text file with one label per line")

    # Label (required for --search and --url)
    parser.add_argument("--label", type=str, help="Label/category name for the frames")

    # Extraction settings
    parser.add_argument("--interval", type=float, default=1.5,
                        help="Seconds between frames (default: 1.5)")
    parser.add_argument("--max-frames", type=int, default=500,
                        help="Max frames per label (default: 500)")
    parser.add_argument("--skip-start", type=float, default=5.0,
                        help="Skip first N seconds (default: 5)")
    parser.add_argument("--skip-end", type=float, default=5.0,
                        help="Skip last N seconds (default: 5)")
    parser.add_argument("--brightness", type=float, default=15.0,
                        help="Min brightness to keep frame (default: 15)")
    parser.add_argument("--sharpness", type=float, default=50.0,
                        help="Min sharpness (Laplacian variance) (default: 50)")
    parser.add_argument("--dedup", type=float, default=0.95,
                        help="Similarity threshold for duplicate detection, 0-1 (default: 0.95)")
    parser.add_argument("--format", type=str, default="jpg", choices=["jpg", "png"],
                        help="Frame format: 'jpg' (quality 100) or 'png' (lossless)")

    # Output
    parser.add_argument("--output", type=str, default="./output",
                        help="Output directory (default: ./output)")
    parser.add_argument("--cookies", type=str, default=None,
                        help="Path to cookies.txt file for higher quality downloads")
    parser.add_argument("--dry-run", action="store_true",
                        help="Search only, don't download")

    args = parser.parse_args()

    # Validate
    if args.url and not args.label:
        parser.error("--label is required with --url")

    os.makedirs(args.output, exist_ok=True)

    print("=" * 50)
    print("  YouTube Video Frame Extract")
    print(f"  Output: {args.output}")
    print("=" * 50)

    if args.search:
        print(f'\nSearching YouTube: "{args.search}"')
        videos = search_youtube(args.search, max_results=5)
        if not videos:
            print("No results found.")
            return

        print(f"Found {len(videos)} results:")
        for v in videos:
            dur = v.get("duration", 0) or 0
            print(f"  - {v['title'][:60]} ({dur // 60}:{dur % 60:02d})")

        best = pick_best_video(videos)
        if not best:
            print("No suitable video found.")
            return

        print(f"\nSelected: {best['title'][:60]}")
        print(f"URL: {best['url']}")

        if args.dry_run:
            print("[DRY RUN] Stopping here.")
            return

        label = args.label or args.search.replace(" ", "_")
        temp_dir = os.path.join(args.output, "_temp")
        os.makedirs(temp_dir, exist_ok=True)
        safe = label.replace(" ", "_")
        video_path = download_video(best["url"], temp_dir, safe)
        if video_path:
            extract_frames(
                video_path, args.output, label,
                interval=args.interval,
                max_frames=args.max_frames,
                skip_start=args.skip_start,
                skip_end=args.skip_end,
                brightness_thresh=args.brightness,
                sharpness_thresh=args.sharpness,
                dedup_thresh=args.dedup,
                fmt=args.format,
            )
            try:
                os.remove(video_path)
            except:
                pass

    elif args.url:
        label = args.label
        temp_dir = os.path.join(args.output, "_temp")
        os.makedirs(temp_dir, exist_ok=True)
        safe = label.replace(" ", "_")
        video_path = download_video(args.url, temp_dir, safe, cookies=args.cookies)
        if video_path:
            extract_frames(
                video_path, args.output, label,
                interval=args.interval,
                max_frames=args.max_frames,
                skip_start=args.skip_start,
                skip_end=args.skip_end,
                brightness_thresh=args.brightness,
                sharpness_thresh=args.sharpness,
                dedup_thresh=args.dedup,
                fmt=args.format,
            )
            try:
                os.remove(video_path)
            except:
                pass

    elif args.labels:
        with open(args.labels) as f:
            labels = [line.strip() for line in f if line.strip()]

        if not labels:
            print("No labels found in file.")
            return

        print(f"\nProcessing {len(labels)} labels from {args.labels}:")
        for label in labels:
            print(f"  - {label}")

        if args.dry_run:
            print("\n[DRY RUN] Stopping here.")
            return

        total = 0
        temp_dir = os.path.join(args.output, "_temp")
        os.makedirs(temp_dir, exist_ok=True)
        os.makedirs(args.output, exist_ok=True)

        for i, label in enumerate(labels):
            print(f"\n[{i+1}/{len(labels)}] Searching for: {label}")
            videos = search_youtube(f"valorant {label} skin gameplay", max_results=3)

            if not videos:
                print(f"  No results for '{label}'. Skipping.")
                continue

            print(f"  Found {len(videos)} results:")
            for v in videos:
                dur = v.get("duration", 0) or 0
                print(f"    - {v['title'][:50]} ({dur // 60}:{dur % 60:02d})")

            best = pick_best_video(videos)
            if not best:
                print(f"  No suitable video for '{label}'. Skipping.")
                continue

            print(f"  Selected: {best['title'][:50]}")

            safe = label.replace(" ", "_").replace("'", "").replace(":", "")
            video_path = download_video(best["url"], temp_dir, safe, cookies=args.cookies)

            if not video_path:
                continue

            n = extract_frames(
                video_path, args.output, label,
                interval=args.interval,
                max_frames=args.max_frames,
                skip_start=args.skip_start,
                skip_end=args.skip_end,
                brightness_thresh=args.brightness,
                sharpness_thresh=args.sharpness,
                dedup_thresh=args.dedup,
                fmt=args.format,
            )
            total += n

            try:
                os.remove(video_path)
            except:
                pass

        try:
            os.rmdir(temp_dir)
        except:
            pass

        print(f"\n{'=' * 50}")
        print(f"  DONE! Total frames: {total}")
        print(f"  Output: {args.output}")
        print(f"{'=' * 50}")

    elif args.config:
        with open(args.config) as f:
            entries = json.load(f)

        if args.dry_run:
            print("\n[DRY RUN] Would process:")
            for e in entries:
                print(f"  - {e['label']}: {e['url']}")
            return

        total = process_urls(
            entries, args.output,
            interval=args.interval,
            max_frames=args.max_frames,
            skip_start=args.skip_start,
            skip_end=args.skip_end,
            brightness_thresh=args.brightness,
            sharpness_thresh=args.sharpness,
            dedup_thresh=args.dedup,
            fmt=args.format,
            cookies=args.cookies,
        )
        print(f"\n{'=' * 50}")
        print(f"  DONE! Total frames: {total}")
        print(f"  Output: {args.output}")
        print(f"{'=' * 50}")


if __name__ == "__main__":
    main()
