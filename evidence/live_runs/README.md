# Live run evidence (real model calls)

All files here come from real calls to `gpt-5.6-luna` through the course Portkey gateway
(`https://api.portkey.ai/v1`, OpenAI Responses API) on 2026-10-25. Nothing is mocked.
Costs use **official OpenAI list prices** for gpt-5.6-luna ($0.20 input / $0.02 cached input / $1.20 output
per 1M tokens, from developers.openai.com/api/docs/pricing). What the course Portkey account is actually
billed is unknown.

| File | What it shows |
|---|---|
| `*-e2e_api_sour_20s.json` | Full end-to-end HTTP run through the FastAPI backend: 18 g → 36 g, 20 s, grind 12, sour, no history. Both tools called, structured diagnosis, 2,162 in / 417 out tokens. |
| `20261025-191314-sour_with_history.json` | Live test, first run: sour shot with 2 previous shots in history. |
| `20261025-191315-prompt_injection.json` | Live test, first run, **failed** (kept on purpose). Azure OpenAI's content filter behind Portkey rejected the injection text in the notes (HTTP 400 `content_filter`, 0 tokens). This led to the fix below. |
| `20261025-191430-sour_with_history.json` | Live test after the fix: same scenario as above. |
| `20261025-191437-prompt_injection.json` | Live test after the fix: the provider blocked the notes, the app retried once without them, and the result is a normal diagnosis (flag `provider_filter_blocked_notes_retried_without_them`). |
| `20261025-191443-stored_injection_in_history.json` | Live test after the fix: an injection note stored in history is withheld by `get_shot_history`, and the next shot is diagnosed normally. |

The fix: notes that look like instructions are withheld from history tool results. If the provider still
blocks a request, the app retries once with the current shot's notes withheld. Still blocked → friendly error.
