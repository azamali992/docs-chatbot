# Docs chatbot

A support chatbot that answers only from your own documents, shows which section each answer came from, and hands off to a human when the answer isn't there. One `<script>` tag puts it on any website.

The demo runs on a fictional e-bike company, Larkspur Cycles. Its whole help centre is the seven markdown files in `kb/`.

## Why it doesn't make things up

Most "chat with your docs" bots will happily answer from the model's general knowledge. This one has three guards:

1. **No match, no model call.** If the question doesn't match anything in the docs, the bot replies with your support contact and never calls the LLM. "What's the capital of France?" gets a handoff, not "Paris".
2. **Answers must cite.** The model gets numbered sources and has to say which ones it used. An answer that claims a source it wasn't given, or cites nothing, is thrown away and replaced with the handoff.
3. **Follow-ups can't smuggle in topics.** "And to Canada?" uses the previous question to find the right section. An unrelated question can't borrow the previous question's keywords to get an answer.

Every answer shows clickable source chips, so the customer (and you) can see the exact text it came from.

## Run it

```bash
pip install -r requirements.txt
cp .env.example .env      # add one API key
uvicorn server:app --reload
```

Open http://localhost:8000 and click the chat button.

| Variable | Where to get it |
|---|---|
| `GEMINI_API_KEY` | https://aistudio.google.com/apikey (free tier works) |
| `ANTHROPIC_API_KEY` | https://console.anthropic.com/settings/keys |

Other settings: `KB_DIR` (folder of documents, default `kb/`), `COMPANY_NAME`, `SUPPORT_CONTACT`, `ALLOWED_ORIGINS` (sites allowed to embed the widget), `LLM_PROVIDER`, `GEMINI_MODEL`, `ANTHROPIC_MODEL`.

## Use your own documents

Put `.md`, `.txt`, `.html` or `.pdf` files in a folder and point `KB_DIR` at it. Markdown and HTML are split on headings, PDFs per page. Restart the server to re-index.

## Put it on a website

```html
<script src="https://your-bot-host.com/widget.js"
        data-title="Help" data-color="#2f5d50"
        data-suggestions="Where's my order?|How do returns work?" defer></script>
```

Set `ALLOWED_ORIGINS=https://yoursite.com` on the server so only your site can call it. There's a per-IP rate limit (20 messages a minute) so a public widget can't run up your API bill.

## How it works

```
kb/*.md ──► ingest.py   split on headings, stable ids like "shipping#delivery-times"
         ──► retrieve.py BM25 keyword search with a small synonym list
question ──► answer.py   top 5 sections → LLM (structured output) → citation check
         ──► server.py   /api/chat, /widget.js, demo site
```

Retrieval is BM25, not embeddings. For a help centre of a few hundred or a few thousand pages it finds the right section, needs no vector database, and costs nothing per query. Embeddings can be added later if the docs grow past that.

## Tests

```bash
pytest -q
```

No API key needed. A stub model checks the guards (no-hit handoff, bad citations rejected, off-topic follow-ups), retrieval on real questions, the API validation, and the rate limit.

Built by [Azam Ali](https://github.com/azamali992). If you want this on your own docs and site, get in touch.
