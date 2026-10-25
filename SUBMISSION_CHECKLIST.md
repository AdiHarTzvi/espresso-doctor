# Final submission checklist — Espresso Doctor

Deadline: **26 Oct 2026, 6:00 PM ET.** Checked on 25 Oct 2026.

## Deliverables

| Item | Status | How it was checked |
|---|---|---|
| Source code (frontend, backend, agent, tests) | ✅ | Fresh-clone simulation: install → build → 57 tests pass → server starts and serves the UI |
| `README.md` with setup, `.env` lookup (project folder, then parent), Portkey/OpenAI choice and startup | ✅ | Reviewed; the clone simulation followed its steps |
| `requirements.txt`, `.env.example` | ✅ | Placeholders only; placeholder values are ignored by the app |
| `report.html` in the project root, 10–15 printed pages | ✅ **13 pages** (US Letter, Chrome print to PDF) | Playwright + Chrome `page.pdf(format="Letter")`; 9 embedded images and 3 inline SVGs, 0 broken, 0 external resources |
| Report section order: Title + links → Motivation → What is new here → The agents → Tokenomics → Safety → Impact → Limits + next steps | ✅ | Section headings 1–8 in that order |
| `slides.html` in the project root, ≤ 10 slides, reveal.js | ✅ **10 slides** | Reveal loads (6.0.2 from jsDelivr). ArrowRight steps through slides 1→10 and Home returns to 1. No console errors, no content overflow, 5 embedded images, 0 broken |
| Slides open by double-click; CDN dependency documented | ✅ | Comment in the file plus README. Offline fallback tested: CDN blocked → all 10 slides shown as a scrolling page with a notice |
| Real tests (agent behaviour, safety, token cost) | ✅ | `evidence/test_results_offline.txt` (57 passed); live: 3 of 3 passed after the fix (`evidence/live_runs/`) |
| Screenshots from real app sessions | ✅ | `evidence/screenshots/` (10 files): real backend, gpt-5.6-luna via Portkey |
| Evidence summary separating measured from estimated | ✅ | `evidence/EVIDENCE_SUMMARY.md` |
| No secrets or real `.env` committed | ✅ | No `.env` files in the project. The real key string is in 0 of the 72 committable files, and no other key-like strings were found |
| HW5 and other projects untouched | ✅ | `hw5` git status clean |

## Claims check

- Token counts, request and tool-call counts, latencies and the trace step numbers in `report.html` and
  `slides.html` were cross-checked by script against `evidence/` JSON: all match. (Mean output is exactly
  526.5; we report 527, rounding half up.)
- Prices are labelled as **official OpenAI list prices** (developers.openai.com/api/docs/pricing, checked
  25 Oct 2026). All dollar figures are labelled **estimate / hypothetical**, because course Portkey billing is unknown.
- Competitor statements are limited to what each vendor's own page says (Beanconqueror, Decent/Visualizer,
  Dial In Coffee, Tampio, Breville guide), and the report does not claim novelty. One web-search result, a
  ChatGPT app called "ShotPulled", could not be verified (HTTP 403), so it is **not** cited.
- No users, time savings or coffee-quality improvements are claimed.

## Remaining issues / to do before submitting

1. **Publish the GitHub repository** (not done, as requested). Then:
   - replace "GitHub link to be added at submission" on the cover of `docs/report.src.html`, and the
     `<this-repo-url>` in README's clone command;
   - run `.venv/bin/python scripts/build_docs.py` to rebuild `report.html` and `slides.html`.
2. **Make the first git commit.** The repository is initialized but has **no commits yet**. Check
   `git status` first: `.env`, `data/`, `.venv/` and `node_modules/` are ignored.
3. **The direct-OpenAI fallback has not been tested live.** Only the Portkey path was exercised with real calls,
   because there is no `OPENAI_API_KEY` on this machine. Offline tests cover the fallback's settings logic only.
4. **Page count checked in Chrome only.** Safari or Firefox may paginate slightly differently. 13 pages leaves
   room before the 15-page limit.
5. **Course Portkey billing is unknown.** If the course publishes its rate, update the cost tables (or set
   `PRICE_*` env vars) and rebuild.
6. **Gateway caching:** Portkey served an identical repeat request from its cache. The app does not yet record cache
   status, so it would overstate the cost of cache hits (documented in report §5 and §8).
7. **Fresh-clone time:** the 12-second simulation used warm pip and npm caches. A cold machine needs a few minutes
   for the downloads, which is still within the 10-minute target, but this was not measured on a clean machine.
8. Optional: open both HTML files once in your own browser and print `report.html` to confirm the page count on
   your printer settings.
