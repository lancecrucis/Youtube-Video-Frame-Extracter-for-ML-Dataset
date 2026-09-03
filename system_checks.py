"""Shared local dependency detection for the CLI and web interface."""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path


MINIMUM_RUNTIME_VERSIONS = {
    "deno": (2, 3, 0),
    "node": (22, 0, 0),
}


def _existing_executable(name: str, extra_paths: list[Path] | None = None) -> str | None:
    discovered = shutil.which(name)
    if discovered:
        return discovered

    for candidate in extra_paths or []:
        if candidate.is_file():
            return str(candidate)
    return None


def _supported_runtime(name: str, executable: str | None) -> bool:
    if not executable:
        return False

    try:
        result = subprocess.run(
            [executable, "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False

    match = re.search(r"(\d+)\.(\d+)\.(\d+)", result.stdout or result.stderr)
    if not match:
        return False
    version = tuple(int(part) for part in match.groups())
    return version >= MINIMUM_RUNTIME_VERSIONS[name]


def javascript_runtime() -> tuple[str, str] | None:
    """Return the preferred yt-dlp JavaScript runtime and executable path."""
    deno = _existing_executable(
        "deno",
        [
            Path.home() / ".deno" / "bin" / "deno.exe",
            Path.home() / "AppData" / "Local" / "Microsoft" / "WinGet" / "Links" / "deno.exe",
        ],
    )
    if _supported_runtime("deno", deno):
        return "deno", deno

    node = _existing_executable("node")
    if _supported_runtime("node", node):
        return "node", node
    return None


def javascript_runtime_args() -> list[str]:
    runtime = javascript_runtime()
    if not runtime:
        return []
    name, executable = runtime
    return ["--js-runtimes", f"{name}:{executable}"]


def ffmpeg_path() -> str | None:
    return _existing_executable("ffmpeg")
