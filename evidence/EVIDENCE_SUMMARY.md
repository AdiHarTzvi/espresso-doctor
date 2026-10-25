# Espresso Doctor — evidence summary

Everything below comes from files in this `evidence/` folder, collected on **2026-10-25**. Each item is
labelled **MEASURED** (observed in a real run) or **ESTIMATE** (calculated from measurements plus stated
assumptions). No users were studied, and no real espresso was brewed for these tests. Shot values were
entered as test inputs.

## 1. Setup used for every live run

- **Model:** `gpt-5.6-luna` via the course Portkey gateway (`https://api.portkey.ai/v1`), OpenAI Responses API.
  The gateway reported the served model as `gpt-5.6-luna-global`, running on Azure OpenAI (seen in the
  content-filter error text).
- **Agent:** one PydanticAI agent with two tools, `calculate_brew_ratio` and `get_shot_history`. Limits per run:
  ≤ 4 requests, ≤ 4 tool calls, ≤ 16,000 total tokens, ≤ 2,500 output tokens per response.

## 2. Automated tests (MEASURED)

| Suite | Result | File |
|---|---|---|
| Offline (scripted model, no network) | **57 passed**, 3 skipped (the skipped ones are the live tests) | `test_results_offline.txt` |
| Live, first run | 1 passed, **1 failed** (provider content filter, HTTP 400) | `live_runs/20261025-1913*` |
| Live, after the fix | **3 passed** | `live_runs/20261025-1914*` |

## 3. Live diagnoses (MEASURED)

There were 11 real diagnosis attempts: 6 from live tests and API calls, 4 through the real browser UI, and 1 full
message trace. **10 succeeded and 1 failed.** The failure was the first prompt-injection test, blocked by the
provider before the fix. A cached replay is excluded (see section 6).

| Source | Scenario | OK | Input tok | Output tok | Requests | Tool calls | Est. cost* |
|---|---|---|---|---|---|---|---|
| e2e API | 18→36 g, 20 s, grind 12, sour, no history | ✓ | 2,162 | 417 | 2 | 2 | $0.000933 |
| live test 1 | sour, 2-shot history | ✓ | 2,318 | 548 | 2 | 2 | $0.001121 |
| live test 1 | prompt injection in notes | ✗ | 0 | 0 | 0 | 0 | $0 |
| live test 2 | sour, 2-shot history | ✓ | 2,318 | 567 | 2 | 2 | $0.001144 |
| live test 2 | prompt injection in notes (filter → retry without notes) | ✓ | 2,342 | 586 | 2 | 2 | $0.001172 |
| live test 2 | injection stored in history | ✓ | 2,416 | 564 | 2 | 2 | $0.001160 |
| UI shot 1 | 20 s, grind 12, sour, no history | ✓ | 2,186 | 429 | 2 | 2 | $0.000952 |
| UI shot 2 | 25 s, grind 11, sour, 1 in history | ✓ | 2,302 | 502 | 2 | 2 | $0.001063 |
| UI shot 3 | 29 s, grind 10, balanced, 2 in history | ✓ | 2,456 | 525 | 2 | 2 | $0.001121 |
| UI shot 4 | 38 s, grind 9, bitter, injection notes, 3 in history | ✓ | 2,538 | 567 | 2 | 2 | $0.001188 |
| trace | 31 s, grind 10, balanced, 4 in history | ✓ | 2,652 | 560 | 2 | 2 | $0.001202 |

\*Est. cost = measured tokens × **official OpenAI list price** for gpt-5.6-luna ($0.20 input / $0.02 cached input /
$1.20 output per 1M tokens, developers.openai.com/api/docs/pricing, checked 2026-10-25). This is an **ESTIMATE**:
what the course Portkey account is actually billed is unknown. No cached input tokens were reported in any run.

**Totals across the 10 successful runs (MEASURED):** 23,690 input tokens and 5,265 output tokens.
- Per run, input: mean 2,369 (range 2,162–2,652).
- Per run, output: mean 527 (range 417–586).
- Every successful run used exactly **2 model requests and 2 tool calls**, and called **both** tools.
- Estimated cost: mean **$0.00111** per run (range $0.00093–$0.00120), and about **$0.011** for all 10 runs.

**Input grows with history (MEASURED in the UI session, ESTIMATE when extrapolated).** Input tokens were 2,186 →
2,302 → 2,456 → 2,538 as history went from 0 to 3 shots, a fitted slope of about **121 tokens per history shot**.
History is capped at 10 shots. The extrapolated steady state is ≈ 3,400 input tokens per run.

**Latency (MEASURED, n = 5)**, from clicking *Save & diagnose* to the API response: 5.94, 5.38, 5.43 and 7.08 s
(UI). The 7.08 s run included the content-filter retry. The uncached trace took 5.88 s.

## 4. Safety defenses observed in real runs (MEASURED)

| Defense | Evidence | Outcome |
|---|---|---|
| Input validation (browser) | `screenshots/08-safety-input-validation.jpg` | Dose 250 g and time 0 s were rejected in the form. The shot count stayed at 4, so nothing was saved and nothing went to the AI |
| Input validation (server) | `demo_session/ui_diagnose_timings.json` | A direct API POST with dose 250 g and time 0 s returned **HTTP 422** with field messages |
| Prompt injection in current notes | `live_runs/*-prompt_injection.json`, `screenshots/06-safety-prompt-injection.jpg` | The provider's content filter blocked the injection text. The app retried once without the notes and returned a normal structured diagnosis. The output does not obey the note (no "PWNED", no system prompt) |
| Injection stored in history | `live_runs/*-stored_injection_in_history.json`, `live_runs/*-trace_shot5_with_history.json` | `get_shot_history` returned `[withheld by Espresso Doctor …]` instead of the note, and the next diagnosis succeeded |
| API error handling | `live_runs/20261025-191315-prompt_injection.json` (before the fix) | A provider HTTP 400 became a friendly error message, with no crash and no key leaked |
| Secret handling | key-scan step (see report §6) | The real key string was found in **none** of the evidence files or committable files |

## 5. Screenshots (`screenshots/`, real app, real model)

| File | Shows |
|---|---|
| 01-main-form | main interface, form filled with the first test shot |
| 02-diagnosis-first-shot | real diagnosis, no history (grind finer) |
| 03-diagnosis-with-history | real diagnosis using 2 previous shots ("no change" after a balanced shot) |
| 04-progress-comparison | latest vs previous comparison and time/ratio charts |
| 05-shot-history | shot history table |
| 06-safety-prompt-injection | injection shot: provider filter notice and a normal diagnosis |
| 07-usage-cost-panel | measured tokens and estimated cost per run |
| 08-safety-input-validation | invalid dose/time rejected |
| 09-full-page-desktop, 10-mobile | full layout, desktop and phone |

## 6. Limitations of this evidence

- **Small sample:** 10 successful real runs and one model. These numbers say nothing about accuracy at scale.
- **Test inputs:** shot values are test inputs, not real brewed shots. We did not measure whether the advice
  improves real coffee, and we did not test with users.
- **Portkey response cache:** the gateway caches identical requests. A repeated identical request
  returned `x-portkey-cache-status: HIT` with the original call's usage numbers
  (`live_runs/*-trace_shot3_PORTKEY_CACHE_HIT.json`, excluded from statistics). Cache status was not recorded for
  the earlier runs. Each of those had a unique prompt, and their latency (≈5–7 s) is consistent with cache misses.
  The fresh trace recorded `MISS` on both requests.
- **Cost is an estimate:** official OpenAI list prices × measured tokens. Course Portkey billing is unknown, and
  the app does not discount gateway cache hits.
- **Model behaviour varies:** the injection note was blocked by the provider filter in all three injection runs.
  So the evidence shows the filter-plus-retry path and the history-withholding path. It does not show the
  model reading and ignoring an injection on its own; that is covered only by offline tests.
