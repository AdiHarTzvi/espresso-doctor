# ☕ Espresso Doctor

An AI agent web app that helps home baristas dial in espresso. Record a shot (dose, yield, time,
grind, taste, notes) and the agent diagnoses it **using your own shot history**, then recommends
**one** specific change for the next shot. It separates facts from hypotheses and states its uncertainty.

Built for the Yale SOM *AI Agents* course final project.

- **Frontend:** React + Vite
- **Backend:** Python FastAPI
- **Agent:** one PydanticAI agent with two tools: `calculate_brew_ratio` and `get_shot_history`
- **Storage:** SQLite (`data/espresso.db`, created automatically)
- **Model:** OpenAI `gpt-5.6-luna` through the course **Portkey** gateway (`PORTKEY_API_KEY`), or
  `gpt-5-mini` directly from OpenAI (`OPENAI_API_KEY`) as a fallback. Both are configurable.

---

## Quick start (about 10 minutes)

Requirements: **Python 3.11+** and **Node.js 20+** (developed with Python 3.14 and Node 24).

```bash
git clone <this-repo-url> espresso-doctor
cd espresso-doctor

# 1. Python backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# 2. API key: copy the template and paste ONE key (Portkey or OpenAI) into .env
#    (skip this if your key is already in ../.env)
cp .env.example .env

# 3. Frontend (build once)
cd frontend && npm install && npm run build && cd ..

# 4. Run (serves the API and the built frontend together)
.venv/bin/uvicorn backend.app.main:app --port 8000
```

Open **http://localhost:8000**.

On Windows, replace `.venv/bin/` with `.venv\Scripts\` and `cp` with `copy`.

### Where the `.env` file can live

The backend looks for `.env` in **two places**, in this order:

1. the project folder (`espresso-doctor/.env`)
2. one directory above it (`../.env`)

Values from the first file win, and variables already set in your shell win over both. Empty values and the
`.env.example` placeholders are ignored, so an unedited copy cannot hide a real key in `../.env`. Only
one key is required. `.env` is git-ignored; never commit it.

### Which connection is used

| Keys present | Connection | Default model |
|---|---|---|
| `PORTKEY_API_KEY` (with or without `OPENAI_API_KEY`) | Portkey gateway `https://api.portkey.ai/v1` | `gpt-5.6-luna` |
| only `OPENAI_API_KEY` | OpenAI directly (`api.openai.com`) | `gpt-5-mini` |

Both use the OpenAI **Responses API** through the OpenAI Python SDK, which sends the key as
`Authorization: Bearer <key>`. No extra Portkey headers are needed; this is the same setup that worked in
the author's HW5. Set `AI_PROVIDER=openai` to force the direct connection when both keys are present.
The page header shows the active model and connection.

Without a key the app still runs: you can record and review shots, and the UI shows a banner
explaining how to enable diagnosis.

### Development mode (hot reload)

Use two terminals:

```bash
# terminal 1 - backend with auto-reload
.venv/bin/uvicorn backend.app.main:app --port 8000 --reload
```

```bash
# terminal 2 - frontend dev server (proxies /api to port 8000)
cd frontend && npm run dev
```

Then open **http://localhost:5173**.

---

## Final project deliverables

| File | What it is |
|---|---|
| [`report.html`](report.html) | Final report (13 pages when printed on US Letter in Chrome). Self-contained: all screenshots and diagrams are embedded. Open it in any browser. |
| [`slides.html`](slides.html) | 10-slide [reveal.js](https://revealjs.com) deck. Double-click to open. **It needs internet** because reveal.js 6.0.2 is loaded from the jsDelivr CDN. Use the arrow keys or space to navigate. Offline, it falls back to a scrolling page with the same content. All images are embedded. |
| [`evidence/EVIDENCE_SUMMARY.md`](evidence/EVIDENCE_SUMMARY.md) | Measured results vs. estimates: tests, token usage, tool calls, latency, cost, safety evidence, limitations |
| `evidence/live_runs/` | Raw JSON from real model runs, including one full message trace (see its README) |
| `evidence/demo_session/` | Shots, diagnoses, usage and timings exported from the real UI session used for the screenshots |
| `evidence/screenshots/` | Screenshots of the real running app (real backend and model; shot values are test inputs) |
| `evidence/test_results_offline.txt` | Output of the offline test suite |

`report.html` and `slides.html` are generated from `docs/*.src.html` and `docs/diagrams/*.svg`:

```bash
.venv/bin/python scripts/build_docs.py
```

## Configuration

| Variable | Required | Default | Purpose |
|---|---|---|---|
| `PORTKEY_API_KEY` | one of the two keys | – | Course-provided Portkey key (preferred) |
| `PORTKEY_MODEL` | no | `gpt-5.6-luna` | Model used through Portkey (`gpt-6-luna` also works) |
| `OPENAI_API_KEY` | one of the two keys | – | Direct OpenAI key (fallback) |
| `OPENAI_MODEL` | no | `gpt-5-mini` | Model used with the direct OpenAI key |
| `AI_PROVIDER` | no | auto | `portkey` or `openai` to force one |
| `OPENAI_REASONING_EFFORT` | no | `low` | For reasoning models. Set `none` for models without reasoning support |
| `PRICE_INPUT_PER_1M` / `PRICE_CACHED_INPUT_PER_1M` / `PRICE_OUTPUT_PER_1M` | no | built-in for 3 models | USD per 1M tokens, used for the approximate cost display |
| `OPENAI_BASE_URL` | no | api.openai.com | Optional OpenAI-compatible endpoint for the direct connection |
| `ESPRESSO_DB_PATH` | no | `data/espresso.db` | SQLite file location |

Built-in prices are **official OpenAI API list prices** (USD per 1M tokens: input / cached input / output,
from [developers.openai.com/api/docs/pricing](https://developers.openai.com/api/docs/pricing), checked 2026-10-25):
`gpt-5.6-luna` 0.20 / 0.02 / 1.20, `gpt-6-luna` 0.10 / 0.01 / 0.50 (short-context rates), `gpt-5-mini` 0.25 / 0.025 / 2.00.
Through Portkey, the course account may be billed differently; that rate is unknown, so the app's cost is an
estimate at OpenAI list prices. A model without a known price shows cost as "n/a"; tokens are still recorded.

---

## How it works

```
React UI ──HTTP──> FastAPI ──> PydanticAI agent ──> Portkey gateway or OpenAI (Responses API)
                     │              ├─ tool: calculate_brew_ratio(dose, yield)
                     │              └─ tool: get_shot_history(limit)  ──> SQLite
                     └─ SQLite: shots + diagnoses (with token usage and cost)
```

1. **Record**: `POST /api/shots` validates the numbers and stores the shot.
2. **Diagnose**: `POST /api/shots/{id}/diagnose` runs the agent. The agent calls
   `calculate_brew_ratio` and `get_shot_history` (previous shots plus any earlier recommendations),
   then returns a structured `Diagnosis`:
   - `diagnosis`: the most likely explanation, phrased as a hypothesis
   - `recommended_adjustment`: **one** variable (grind / dose / yield / time / temperature / puck prep / none), an action and an optional target
   - `explanation`: why, with reference to your history
   - `facts` and `hypotheses`, kept separate
   - `confidence` (low / medium / high) and an `uncertainty` statement
3. **Review**: the history table lists every shot. Click *View* to reopen a diagnosis.
4. **Compare**: `GET /api/progress` compares the latest shot with the previous one
   (dose, yield, ratio, time, grind, taste). It judges "improving" deterministically from your taste
   ratings and charts time and ratio against common rules of thumb.
5. **Usage**: each AI run stores input/output tokens, request count, tool calls and approximate cost
   (`GET /api/usage`, shown at the bottom of the page). Failed runs are logged too.

### API

| Method | Path | Description |
|---|---|---|
| GET | `/api/health` | Status, model name, whether a key is configured (never the key itself) |
| GET/POST | `/api/shots` | List / create shots |
| GET/DELETE | `/api/shots/{id}` | Shot detail with its latest diagnosis / delete |
| POST | `/api/shots/{id}/diagnose` | Run the AI agent (200 ok, 502 friendly error, 503 no key) |
| GET | `/api/progress` | Latest-vs-previous comparison and chart series |
| GET | `/api/usage` | Token and cost totals and the last 20 runs |

Interactive API docs: http://localhost:8000/docs

---

## Safety and reliability

| Risk | Protection | Where |
|---|---|---|
| Unreasonable numbers | Dose 5–30 g, yield 5–120 g, time 5–120 s, ratio 1:0.5–1:6, notes ≤ 500 chars, taste is an enum. Validated in the browser **and** the backend (422 with a readable message) | `schemas.py`, `ShotForm.jsx` |
| Prompt injection via notes or history | Free text is JSON-encoded inside a labelled *untrusted data* block in the user message and never added to the instructions. Field names end in `_untrusted`. The instructions say data must never be followed. A keyword screen flags suspicious notes, and the UI tells the user | `agent.py` |
| Tool misuse | Tool arguments have hard bounds (for example dose 5–30 g, history limit ≤ 10) | `agent.py` |
| Secret leakage | The key is only read from the environment. `/api/health` reports only whether a key exists. Output is scrubbed for the key. `.env` is git-ignored | `config.py`, `main.py` |
| Runaway cost / loops | Per run: ≤ 4 model requests, ≤ 4 tool calls, ≤ 16k total tokens, ≤ 2,500 output tokens, 1 output retry, 1 HTTP retry, 60 s timeout. At most 2 AI runs at once | `config.py`, `agent.py`, `main.py` |
| API failures | Bad key, unknown model, rate limit, network errors and malformed output all become friendly messages (HTTP 502). The shot is kept and the UI offers *Retry* | `agent.py` |
| Provider content filter | Through Portkey the model runs on Azure OpenAI, whose filter rejects obvious jailbreak text (HTTP 400 `content_filter`). History notes that look like instructions are withheld from the model. If the current shot's notes are blocked, the app retries **once** without them and tells the user | `agent.py` |
| Over-confidence | Confidence is capped at "medium" when there are fewer than 2 previous shots | `agent.py` |

---

## Tests

```bash
.venv/bin/pytest
```

**Offline tests** (no key or network needed, free) use PydanticAI's `FunctionModel`. It scripts only
the model's replies, so the real agent, tools, usage limits, database and API all run. They cover:

- **Agent behaviour**: both tools are called, history excludes the current shot, structured output, and the confidence cap
- **Safety**: input validation (API and model), prompt injection (instructions unchanged, notes stay inside the JSON data block, a fake end-of-data marker cannot escape), history notes labelled untrusted, key never echoed or sent in prompts, runaway tool loops stopped, token budget enforced, API errors turned into friendly messages
- **Token costs**: usage recorded per run (including failed runs) and cost equal to tokens × configured price
- **Config**: `.env` found in the project folder or its parent, with correct precedence

**Live tests** (real model calls, about $0.001 each at list price) are opt-in and use whichever key is configured:

```bash
RUN_LIVE_TESTS=1 .venv/bin/pytest tests/test_live.py -s
```

They run a real diagnosis with history, a real prompt injection in the notes, and an injection stored in
history. They write the actual model output, token usage and approximate cost to `evidence/live_runs/*.json`
(see `evidence/live_runs/README.md`).

---

## Project structure

```
espresso-doctor/
├── backend/app/
│   ├── main.py        FastAPI app and routes (also serves frontend/dist if built)
│   ├── agent.py       PydanticAI agent, tools, safety guards, error handling
│   ├── schemas.py     Input validation and structured output models
│   ├── db.py          SQLite storage (shots, diagnoses with usage)
│   ├── progress.py    Deterministic latest-vs-previous comparison
│   └── config.py      .env discovery, Portkey/OpenAI selection, prices, limits
├── frontend/          React + Vite UI (src/components/*)
├── tests/             pytest suite (offline + opt-in live)
├── evidence/          real-run evidence: live_runs/, demo_session/, screenshots/, summary
├── docs/              report + slides sources and SVG diagrams
├── scripts/build_docs.py  builds report.html and slides.html
├── report.html, slides.html  final deliverables
├── requirements.txt
└── .env.example
```

## Limitations

- Advice is only as good as the inputs. The app cannot see the puck, the beans or the water.
- "Improving" is based on your taste ratings only.
- Single user and local only, by design (no authentication or hosting).
- Cost is approximate: list price × tokens, with no cached-token discounts.
