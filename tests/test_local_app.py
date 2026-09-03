import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import app as web_app
import extract


class LocalAppTests(unittest.TestCase):
    def setUp(self):
        web_app.jobs.clear()
        web_app.active_processes.clear()
        self.client = web_app.app.test_client()

    def tearDown(self):
        web_app.jobs.clear()
        web_app.active_processes.clear()

    @patch.object(web_app.threading, "Thread")
    @patch.object(web_app, "javascript_runtime", return_value=("node", "node"))
    def test_multiple_urls_use_one_label_and_fixed_output(self, _runtime, thread):
        response = self.client.post(
            "/api/extract",
            json={
                "mode": "url",
                "source": "https://youtu.be/first\nhttps://www.youtube.com/watch?v=second",
                "label": "shared dataset",
                "output": "C:/should-not-be-used",
                "max_frames": 20,
            },
        )

        self.assertEqual(response.status_code, 202)
        job_id = response.get_json()["job_id"]
        self.assertEqual(web_app.jobs[job_id]["output"], str(web_app.BASE_DIR / "output"))

        command = thread.call_args.kwargs["args"][1]
        self.assertEqual(command.count("--url"), 2)
        self.assertIn("https://youtu.be/first", command)
        self.assertIn("https://www.youtube.com/watch?v=second", command)
        self.assertNotIn("C:/should-not-be-used", command)

    def test_job_gallery_excludes_frames_from_older_runs(self):
        with tempfile.TemporaryDirectory(dir=web_app.BASE_DIR) as temporary_output:
            label_dir = Path(temporary_output) / "same label"
            label_dir.mkdir()
            for name in ("same label_00001.jpg", "same label_00002.jpg", "same label_00003.jpg"):
                (label_dir / name).write_bytes(b"frame")

            web_app.jobs["test-job"] = {
                "id": "test-job",
                "status": "running",
                "message": "Extracting",
                "progress": 50,
                "logs": [],
                "label": "same label",
                "output": temporary_output,
                "format": "jpg",
                "initial_frames": {"same label_00001.jpg"},
            }

            first_page = self.client.get("/api/jobs/test-job?after=0").get_json()
            second_page = self.client.get("/api/jobs/test-job?after=1").get_json()

            self.assertEqual(first_page["frame_count"], 2)
            self.assertEqual(len(first_page["frames"]), 2)
            self.assertNotIn("00001", " ".join(first_page["frames"]))
            self.assertEqual(len(second_page["frames"]), 1)

    @patch.object(extract, "process_urls", return_value=0)
    def test_cli_accepts_repeated_url_flags(self, process_urls):
        with tempfile.TemporaryDirectory() as temporary_output:
            arguments = [
                "extract.py",
                "--url",
                "https://youtu.be/first",
                "--url",
                "https://youtu.be/second",
                "--label",
                "shared dataset",
                "--output",
                temporary_output,
            ]
            with patch.object(sys, "argv", arguments):
                extract.main()

        entries = process_urls.call_args.args[0]
        self.assertEqual(entries[0]["label"], "shared dataset")
        self.assertEqual(entries[0]["url"], ["https://youtu.be/first", "https://youtu.be/second"])

    def test_shared_url_produces_a_windows_safe_video_key(self):
        self.assertEqual(extract.video_key("https://youtu.be/abc-123?si=tracking"), "abc-123")


if __name__ == "__main__":
    unittest.main()
