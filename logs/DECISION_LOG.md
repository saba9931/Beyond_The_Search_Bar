# Decision log
| Date | Decision | Why |
|---|---|---|
| Oct 2026 | English prompts only; Hinglish panel kept unused | Time and sample size |
| Oct 2026 | Five engines, weighted 10/8/6/4/2 per prompt | Reach in India (see research foundation) |
| Oct 2026 | Branded comparison prompt B20E excluded from primary analysis | It names the retailers in the question |
| 28 Oct 2026 | Keep batched-chat and API answers; track collection method and test it | They are genuine outputs; no significant method effect found |
| 28 Oct 2026 | Do not load Saurav's reference file or Agnik's ChatGPT rows | Not real engine outputs |
| 28 Oct 2026 | D3 is a part submission; data and analysis updated later | Remaining runs not collected yet |
| 30 Oct 2026 | Project named BEYOND THE SEARCH BAR: a reusable GEO intelligence platform, Sephora India as pilot, Nykaa and Tira as benchmarks | Capstone should build a usable tool, not only a study (see project charter) |
| 31 Oct 2026 | Main data = real app answers from 10 to 15 accounts; API answers = scale-up and comparison sample | API answers can differ from what shoppers see in the apps |
| 31 Oct 2026 | Gemini API test: works (gemini-3.8-flash), free plan 5 requests per minute and 20 per day; one search-enabled call returned a quota error (429), cause still being checked | Plan runs at about 20 per day on the free plan; no paid spend for now |
| 31 Oct 2026 | Hand-label check reduced to about 60 to 100 answers: AI first pass, human verification | Time; will be disclosed in the report |
| 31 Oct 2026 | New data plan workbook with 120 questions (20 existing + 100 new draft) | Machine learning needs many different questions; the 100 new ones need team review |
| 3 Nov 2026 | Code refactored into a tested package `src/beyondsearch` (config-driven, CRISP-DM layout); one-off scripts retired; only refactored code stays in the repository | Faculty instruction: traceability, reliability, reproducibility, observability |
| 3 Nov 2026 | Refactored output must match the original D3 insight log (checked by a golden-file test) | Refactor must not change results; only the H1 wording changed to "about 3.0 times" |
