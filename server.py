"""FastAPI server: the chat API, the embeddable widget, and a demo site.

Run:  uvicorn server:app --reload
Then open http://localhost:8000

Config (environment or .env):
    KB_DIR          folder of documents to answer from (default: kb/)
    COMPANY_NAME    shown to the model and in the widget (default: Larkspur Cycles)
    SUPPORT_CONTACT where unanswered questions get sent (default: support@larkspur.example)
    ALLOWED_ORIGINS comma-separated sites allowed to embed the widget (default: *)
    plus the LLM keys described in bot/llm.py
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

ROOT = Path(__file__).parent


def _load_dotenv() -> None:
    env = ROOT / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


_load_dotenv()

from bot.answer import Bot  # noqa: E402
from bot.ingest import load_folder  # noqa: E402
from bot.retrieve import Index  # noqa: E402

COMPANY = os.environ.get("COMPANY_NAME", "Larkspur Cycles")
CONTACT = os.environ.get("SUPPORT_CONTACT", "support@larkspur.example")
KB_DIR = Path(os.environ.get("KB_DIR", ROOT / "kb"))

app = FastAPI(title=f"{COMPANY} help bot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in os.environ.get("ALLOWED_ORIGINS", "*").split(",")],
    allow_methods=["POST", "GET"],
    allow_headers=["Content-Type"],
)

index = Index(load_folder(KB_DIR))
_bot: Bot | None = None


def get_bot() -> Bot:
    """Built lazily so the site and widget load even before an API key is set."""
    global _bot
    if _bot is None:
        from bot.llm import from_env

        _bot = Bot(index, from_env(), COMPANY, CONTACT)
    return _bot


# Simple per-IP limit so a public demo can't run up an API bill.
WINDOW, LIMIT = 60.0, 20
_hits: dict[str, deque] = defaultdict(deque)


def _rate_limited(ip: str) -> bool:
    now, q = time.monotonic(), _hits[ip]
    while q and now - q[0] > WINDOW:
        q.popleft()
    q.append(now)
    return len(q) > LIMIT


class Turn(BaseModel):
    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(max_length=2000)


class ChatIn(BaseModel):
    message: str = Field(min_length=1, max_length=1000)
    history: list[Turn] = Field(default_factory=list, max_length=20)


@app.post("/api/chat")
def chat(body: ChatIn, request: Request):
    if _rate_limited(request.client.host if request.client else "?"):
        raise HTTPException(429, "Too many messages, try again in a minute.")
    try:
        bot = get_bot()
    except RuntimeError as exc:
        raise HTTPException(503, f"Bot not configured: {exc}")
    reply = bot.ask(body.message, [t.model_dump() for t in body.history])
    return {
        "answer": reply.answer,
        "found": reply.found,
        "sources": [{"id": s.id, "title": s.title, "snippet": s.snippet} for s in reply.sources],
    }


@app.get("/api/config")
def config():
    return {"company": COMPANY, "sections": len(index.chunks)}


@app.get("/widget.js")
def widget():
    return FileResponse(ROOT / "static" / "widget.js", media_type="application/javascript")


@app.get("/")
def home():
    return FileResponse(ROOT / "static" / "index.html")
