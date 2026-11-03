# Hypotheses and analysis plan (v1, 30 Oct 2026)

Status: these six hypotheses are the ones tested in the D3 notebook (`deliverables/d3_eda_part_submission/ANCP_TL_D3_eda.ipynb`). They were written in the notebook before the charts, but the team had already seen early partial data, so they are **stated before this analysis, not pre-registered**. The fair test is the updated data: this file is tagged `hypotheses-v1` before the new data arrives, and the same tests are re-run on it without changing the wording.

| # | Hypothesis (expected direction) | Business question | Test | D3 result on 238 answers |
|---|---|---|---|---|
| H1 | In unbranded prompts Nykaa is named in more answers than Sephora India | Are we behind the main competitor? | Paired McNemar | Supported: 32% vs 10% |
| H2 | Sephora India is named more on retailer ("where to buy") questions than product questions | Retailer problem or product problem? | Fisher exact | Supported: 83% vs 6% (n=12 vs 210) |
| H3 | Sephora India mention rate differs by engine | Which engine first? | Chi-square | Supported: 3% to 22%, p=0.016 |
| H4 | Mention rate differs by category (higher for fragrance and premium than haircare) | Strongest and weakest category? | Chi-square | Borderline (p=0.058 among product categories); fragrance 8% vs haircare 3%, so the second half is weak |
| H5 | Links go to Nykaa more than Sephora India | Who gets the traffic? | Paired McNemar | Supported: 74% vs 23% |
| H6 | Cited sites differ across repeat runs | How many runs per question? | Jaccard overlap | Supported: mean overlap 0.30 |

## Limits to keep in mind
- Observational sample of 238 of 600 planned answers; engine and category cells are small.
- Nothing here shows a cause or a revenue effect.
- Counting retailer names in text is a simple rule; it does not judge recommendation quality.

## Analysis sequence
1. Validate the data (required fields, duplicates, valid IDs).
2. Representativeness and bias checks: engine mix, collector, collection method.
3. Rates with 95% Wilson intervals, then the six tests above.
4. Robustness: repeat the headline comparison on single fresh chats only.
5. D4 model (planned): outcome is Sephora India named (yes/no); inputs are question type, category, engine, collection method, early position; folds grouped by prompt; report precision-recall, not accuracy.
