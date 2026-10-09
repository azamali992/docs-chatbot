"""Record a ~50 second demo of the chat widget answering real questions.

Start the server with a real API key first:
    uvicorn server:app --port 8000 &
    python scripts/record_demo.py --url http://localhost:8000 --out recordings/demo.mp4

Needs: pip install playwright && playwright install chromium, and ffmpeg.
The last question is deliberately off-topic to show the bot refusing to guess.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

from playwright.sync_api import sync_playwright

QUESTIONS = [
    "Can I take the battery on a plane?",
    "I'm 6'2\" and want to ride trails. Which bike?",
    "and how much does it weigh?",
    "Do you sell electric scooters?",
]


def record(url: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp, sync_playwright() as p:
        browser = p.chromium.launch()
        ctx = browser.new_context(viewport={"width": 1280, "height": 720}, record_video_dir=tmp,
                                  record_video_size={"width": 1280, "height": 720})
        page = ctx.new_page()
        page.goto(url)
        page.wait_for_timeout(2500)
        page.click(".dbw-btn")
        page.wait_for_timeout(1200)
        for q in QUESTIONS:
            before = page.locator(".dbw-bot").count()
            page.locator(".dbw-form input").type(q, delay=45)
            page.wait_for_timeout(400)
            page.keyboard.press("Enter")
            page.wait_for_function(
                f"document.querySelectorAll('.dbw-bot:not(.dbw-typing)').length > {before}", timeout=60_000)
            page.wait_for_timeout(1200)
            chips = page.locator(".dbw-chip")
            if chips.count():
                chips.last.click()
                page.wait_for_timeout(1800)
            page.wait_for_timeout(1500)
        page.wait_for_timeout(2000)
        video = Path(page.video.path())
        ctx.close()
        browser.close()
        if shutil.which("ffmpeg"):
            subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(video), "-c:v", "libx264",
                            "-pix_fmt", "yuv420p", "-movflags", "+faststart", "-crf", "23",
                            str(out.with_suffix(".mp4"))], check=True)
            print(f"Wrote {out.with_suffix('.mp4')}")
        else:
            shutil.copy(video, out.with_suffix(".webm"))
            print(f"Wrote {out.with_suffix('.webm')}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", default="http://localhost:8000")
    ap.add_argument("--out", type=Path, default=Path(__file__).resolve().parent.parent / "recordings" / "demo.mp4")
    args = ap.parse_args()
    record(args.url, args.out)
