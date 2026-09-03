"""Local web interface for YouTube Video Frame Extract."""

from __future__ import annotations

import os
import re
import socket
import subprocess
import sys
import threading
import uuid
import webbrowser
from pathlib import Path
from urllib.parse import urlparse

from flask import Flask, abort, jsonify, render_template, request, send_file
from system_checks import ffmpeg_path, javascript_runtime


BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True

jobs: dict[str, dict] = {}
jobs_lock = threading.Lock()
active_processes: dict[str, subprocess.Popen] = {}


def _safe_label(value: str) -> str:
    value = value.strip()
    if not value or value in {".", ".."} or any(char in value for char in '<>:"/\\|?*'):
        raise ValueError("Use a label without file-path characters.")
    return value[:80]


def _number(payload: dict, name: str, default: float, minimum: float, maximum: float) -> float:
    try:
        value = float(payload.get(name, default))
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name.replace('_', ' ').title()} must be a number.") from exc
    if not minimum <= value <= maximum:
        raise ValueError(f"{name.replace('_', ' ').title()} must be between {minimum} and {maximum}.")
    return value


def _youtube_urls(value: str) -> list[str]:
    candidates = [part.strip() for part in re.split(r"[\s,]+", value) if part.strip()]
    if not candidates:
        raise ValueError("Add at least one YouTube URL.")
    if len(candidates) > 100:
        raise ValueError("Add no more than 100 YouTube URLs at a time.")

    valid_hosts = {"youtube.com", "www.youtube.com", "m.youtube.com", "music.youtube.com", "youtu.be"}
    invalid = []
    for candidate in candidates:
        parsed = urlparse(candidate)
        if parsed.scheme not in {"http", "https"} or (parsed.hostname or "").lower() not in valid_hosts:
            invalid.append(candidate)
    if invalid:
        raise ValueError(f"Enter full YouTube URLs, one per line. Invalid entry: {invalid[0]}")
    return candidates


def _set_job(job_id: str, **changes) -> None:
    with jobs_lock:
        if job_id in jobs:
            jobs[job_id].update(changes)


def _run_job(job_id: str, command: list[str]) -> None:
    try:
        process = subprocess.Popen(
            command,
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding="utf-8",
            errors="replace",
            bufsize=1,
        )
        active_processes[job_id] = process
        _set_job(job_id, status="running", message="Preparing your video…", progress=6)

        assert process.stdout is not None
        for raw_line in process.stdout:
            line = raw_line.strip()
            if not line:
                continue
            with jobs_lock:
                job = jobs[job_id]
                job["logs"] = (job["logs"] + [line])[-80:]

            lowered = line.lower()
            if "searching youtube" in lowered:
                _set_job(job_id, message="Searching YouTube…", progress=12)
            elif "selected:" in lowered:
                _set_job(job_id, message="Found a video. Starting download…", progress=22)
            elif "downloading" in lowered:
                _set_job(job_id, message="Downloading the video…", progress=32)
            elif re.search(r"\d+x\d+.*fps", lowered):
                _set_job(job_id, message="Extracting clean frames…", progress=48)
            elif "frames..." in lowered:
                match = re.search(r"(\d+)\s+frames", lowered)
                count = int(match.group(1)) if match else 0
                _set_job(
                    job_id,
                    message=f"Extracting frames… {count} saved",
                    progress=min(92, 48 + count // 8),
                )
            elif "extracted" in lowered:
                _set_job(job_id, message=line, progress=96)

        return_code = process.wait()
        with jobs_lock:
            was_cancelled = jobs[job_id].get("status") == "cancelled"

        if was_cancelled:
            return
        if return_code == 0:
            _set_job(job_id, status="complete", message="Your frames are ready.", progress=100)
        else:
            _set_job(
                job_id,
                status="error",
                message="Extraction stopped. Open the activity log for details.",
            )
    except Exception as exc:  # Keep failures visible to the local UI.
        _set_job(job_id, status="error", message=str(exc))
    finally:
        active_processes.pop(job_id, None)


@app.get("/")
def index():
    runtime = javascript_runtime()
    return render_template(
        "index.html",
        cookies_available=(BASE_DIR / "cookies.txt").exists(),
        javascript_runtime=runtime[0].title() if runtime else None,
        ffmpeg_available=ffmpeg_path() is not None,
    )


@app.get("/media/hero-animation")
def hero_animation():
    return send_file(BASE_DIR / "design" / "0903.mp4", mimetype="video/mp4", conditional=True)


@app.get("/media/youtube-icon")
def youtube_icon():
    return send_file(BASE_DIR / "design" / "yt_icon_red_digital.png", mimetype="image/png", conditional=True)


@app.get("/media/youtube-wordmark")
def youtube_wordmark():
    return send_file(
        BASE_DIR / "design" / "yt_logo_fullcolor_white_digital.png",
        mimetype="image/png",
        conditional=True,
    )


@app.post("/api/extract")
def start_extraction():
    payload = request.get_json(silent=True) or {}
    if javascript_runtime() is None:
        return jsonify({"error": "Deno 2.3+ or Node.js 22+ is required for YouTube. Run setup.bat first."}), 503
    try:
        mode = payload.get("mode", "url")
        if mode not in {"url", "search"}:
            raise ValueError("Choose URL or search mode.")

        source = str(payload.get("source", "")).strip()
        if not source:
            raise ValueError("Add a YouTube URL or search phrase.")
        urls = _youtube_urls(source) if mode == "url" else []
        if mode == "search" and any(char in source for char in "\r\n"):
            raise ValueError("Enter one search phrase.")

        label = _safe_label(str(payload.get("label", "")))
        output_dir = (BASE_DIR / "output").resolve()

        interval = _number(payload, "interval", 1.5, 0.1, 60)
        max_frames = int(_number(payload, "max_frames", 500, 1, 10000))
        brightness = _number(payload, "brightness", 15, 0, 255)
        sharpness = _number(payload, "sharpness", 50, 0, 5000)
        dedup = _number(payload, "dedup", 0.95, 0, 1)
        image_format = payload.get("format", "jpg")
        if image_format not in {"jpg", "png"}:
            raise ValueError("Choose JPG or PNG format.")
    except ValueError as exc:
        return jsonify({"error": str(exc)}), 400

    with jobs_lock:
        if any(job["status"] in {"queued", "running"} for job in jobs.values()):
            return jsonify({"error": "An extraction is already running."}), 409

    output_dir.mkdir(parents=True, exist_ok=True)
    command = [
        sys.executable,
        "-u",
        str(BASE_DIR / "extract.py"),
    ]
    if mode == "url":
        for url in urls:
            command.extend(["--url", url])
    else:
        command.extend(["--search", source])
    command.extend(
        [
            "--label",
            label,
            "--output",
            str(output_dir),
            "--interval",
            str(interval),
            "--max-frames",
            str(max_frames),
            "--brightness",
            str(brightness),
            "--sharpness",
            str(sharpness),
            "--dedup",
            str(dedup),
            "--format",
            image_format,
        ]
    )
    if payload.get("use_cookies") and (BASE_DIR / "cookies.txt").exists():
        command.extend(["--cookies", str(BASE_DIR / "cookies.txt")])

    job_id = uuid.uuid4().hex
    label_dir = output_dir / label
    initial_frames = {
        path.name for path in label_dir.glob(f"*.{image_format}")
    } if label_dir.exists() else set()

    with jobs_lock:
        jobs[job_id] = {
            "id": job_id,
            "status": "queued",
            "message": "Queued…",
            "progress": 2,
            "logs": [],
            "label": label,
            "output": str(output_dir),
            "format": image_format,
            "initial_frames": initial_frames,
        }

    threading.Thread(target=_run_job, args=(job_id, command), daemon=True).start()
    return jsonify({"job_id": job_id}), 202


@app.get("/api/jobs/<job_id>")
def job_status(job_id: str):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            abort(404)
        response = dict(job)

    initial_frames = response.pop("initial_frames", set())
    label_dir = Path(response["output"]) / response["label"]
    extension = response["format"]
    frame_paths = (
        sorted(
            path for path in label_dir.glob(f"*.{extension}")
            if path.name not in initial_frames
        )
        if label_dir.exists()
        else []
    )
    try:
        after = max(0, int(request.args.get("after", 0)))
    except ValueError:
        after = 0
    next_paths = frame_paths[after:after + 100]
    response["frames"] = [f"/api/jobs/{job_id}/frames/{path.name}" for path in next_paths]
    response["frame_count"] = len(frame_paths)
    response["has_more_frames"] = after + len(next_paths) < len(frame_paths)
    return jsonify(response)


@app.get("/api/jobs/<job_id>/frames/<filename>")
def job_frame(job_id: str, filename: str):
    with jobs_lock:
        job = jobs.get(job_id)
        if not job:
            abort(404)
        label_dir = (Path(job["output"]) / job["label"]).resolve()

    frame_path = (label_dir / Path(filename).name).resolve()
    if frame_path.parent != label_dir or not frame_path.is_file():
        abort(404)
    return send_file(frame_path, conditional=True)


@app.post("/api/jobs/<job_id>/cancel")
def cancel_job(job_id: str):
    with jobs_lock:
        if job_id not in jobs:
            abort(404)
        if jobs[job_id]["status"] not in {"queued", "running"}:
            return jsonify({"ok": True})
        jobs[job_id].update(status="cancelled", message="Extraction cancelled.")

    process = active_processes.get(job_id)
    if process and process.poll() is None:
        process.terminate()
    return jsonify({"ok": True})


def _available_port(start: int = 5000, attempts: int = 10) -> int:
    for port in range(start, start + attempts):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as candidate:
            try:
                candidate.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise RuntimeError("No available local port found between 5000 and 5009.")


if __name__ == "__main__":
    port = _available_port()
    local_url = f"http://127.0.0.1:{port}"
    print(f"Opening YouTube Video Frame Extractor at {local_url}")
    if "--open-browser" in sys.argv:
        threading.Timer(1.0, webbrowser.open, args=(local_url,)).start()
    app.run(host="127.0.0.1", port=port, debug=False, use_reloader=False)
