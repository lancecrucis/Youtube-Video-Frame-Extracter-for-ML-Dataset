"""Local web interface for YouTube Video Frame Extract."""

from __future__ import annotations

import os
import re
import subprocess
import sys
import threading
import uuid
from pathlib import Path

from flask import Flask, abort, jsonify, render_template, request, send_file


BASE_DIR = Path(__file__).resolve().parent
app = Flask(__name__)

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
    return render_template("index.html", cookies_available=(BASE_DIR / "cookies.txt").exists())


@app.get("/media/hero-animation")
def hero_animation():
    return send_file(BASE_DIR / "design" / "0903.mp4", mimetype="video/mp4", conditional=True)


@app.post("/api/extract")
def start_extraction():
    payload = request.get_json(silent=True) or {}
    try:
        mode = payload.get("mode", "url")
        if mode not in {"url", "search"}:
            raise ValueError("Choose URL or search mode.")

        source = str(payload.get("source", "")).strip()
        if not source:
            raise ValueError("Add a YouTube URL or search phrase.")
        if mode == "url" and not ("youtube.com" in source.lower() or "youtu.be" in source.lower()):
            raise ValueError("Enter a valid YouTube URL.")

        label = _safe_label(str(payload.get("label", "")))
        output_value = str(payload.get("output", "output")).strip() or "output"
        output_dir = Path(output_value).expanduser()
        if not output_dir.is_absolute():
            output_dir = BASE_DIR / output_dir
        output_dir = output_dir.resolve()

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
        f"--{mode}",
        source,
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
    if payload.get("use_cookies") and (BASE_DIR / "cookies.txt").exists():
        command.extend(["--cookies", str(BASE_DIR / "cookies.txt")])

    job_id = uuid.uuid4().hex
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

    label_dir = Path(response["output"]) / response["label"]
    extension = response["format"]
    frame_paths = sorted(label_dir.glob(f"*.{extension}"))[-8:] if label_dir.exists() else []
    response["frames"] = [f"/api/jobs/{job_id}/frames/{path.name}" for path in frame_paths]
    response["frame_count"] = len(list(label_dir.glob(f"*.{extension}"))) if label_dir.exists() else 0
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


if __name__ == "__main__":
    app.run(host="127.0.0.1", port=5000, debug=False)
