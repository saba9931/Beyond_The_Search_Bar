# Run report 20261103T052228Z-1d5624eb

- Status: **ok**
- Project: Beyond the Search Bar: beauty and skincare, India (pilot: Sephora India)
- Data version: data-v0.9  |  seed: 42
- Config: `configs/beauty_india.yaml` (sha256 `15c25d225826`)
- Code: not under git (no commit recorded)
- Python 3.13.16 on Linux-6.18.44-fc-v230-x86_64-with-glibc2.39

## Inputs

| label | file | rows | sha256 |
|---|---|---|---|
| response_log | `data/processed/response_log.csv` | 238 | `8833d7e5b212` |
| prompt_panel | `data/design/prompt_panel_v2.csv` | 40 | `2b5739f0b72c` |
| run_schedule | `data/design/run_schedule.csv` | 600 | `72207aeec8f0` |

## Data checks

| level | check | message | count |
|---|---|---|---|
| WARN | collector_differs | collector differs from the schedule (allowed, but note why) | 40 |
| WARN | setting_not_recorded | 'memory_personalisation_off' is blank for 160 rows (blank means not recorded, not no) | 160 |
| WARN | setting_not_recorded | 'logged_in' is blank for 160 rows (blank means not recorded, not no) | 160 |
| INFO | html_entities | answer text contains HTML codes such as &#x20; (harmless for the rules used) | 30 |
| INFO | progress | 238 answers logged of 600 planned (40%) | 238 |

## Steps

| step | status | seconds |
|---|---|---|
| load inputs | ok | 0.019 |
| validate data | ok | 0.019 |
| analyse | ok | 0.202 |
| save outputs | ok | 3.425 |

## Key facts

- rows_usable: 238
- rows_excluded: 0
- primary_sample: 222

## Outputs

| label | file | sha256 |
|---|---|---|
| insight_log | `outputs/insight_log.csv` | `4fae33391f3c` |
| results | `outputs/results.json` | `23558d8fb23b` |
| validation | `outputs/validation.json` | `3b98035beef5` |
| excluded_rows | `outputs/excluded_rows.csv` | `7fc94dbbcb94` |
| table_method_counts | `outputs/tables/method_counts.csv` | `f961f8fe1405` |
| table_engine_by_method | `outputs/tables/engine_by_method.csv` | `a0af4d6659da` |
| table_engine_by_intent | `outputs/tables/engine_by_intent.csv` | `cd8463af4824` |
| table_category_by_engine | `outputs/tables/category_by_engine.csv` | `51a41deaed21` |
| table_runs_per_collector | `outputs/tables/runs_per_collector.csv` | `dad6fa44073f` |
| table_planned_vs_collected | `outputs/tables/planned_vs_collected.csv` | `4a3a126416d1` |
| table_bias_engine_method | `outputs/tables/bias_engine_method.csv` | `50de141dd599` |
| table_retailer_share | `outputs/tables/retailer_share.csv` | `e810bd58bcc8` |
| table_H1_table | `outputs/tables/H1_table.csv` | `30225bf4983f` |
| table_H1_rates | `outputs/tables/H1_rates.csv` | `45dd752e3f04` |
| table_H2_rates | `outputs/tables/H2_rates.csv` | `29b78744e83c` |
| table_H3_rates | `outputs/tables/H3_rates.csv` | `9880261c3859` |
| table_H3_comp_rates | `outputs/tables/H3_comp_rates.csv` | `a30529b7d724` |
| table_H4_rates | `outputs/tables/H4_rates.csv` | `b4607cb83978` |
| table_H5_table | `outputs/tables/H5_table.csv` | `3ea62645649e` |
| table_H6_by_engine | `outputs/tables/H6_by_engine.csv` | `404e3b265f0e` |
| table_robust_by_engine_method | `outputs/tables/robust_by_engine_method.csv` | `0fa60d09e66b` |
| table_robust_by_engine | `outputs/tables/robust_by_engine.csv` | `ed3418c1b07c` |
| fig01 | `outputs/figs/fig01.png` | `527f44b94866` |
| fig02 | `outputs/figs/fig02.png` | `eb95aab6d2b1` |
| fig03 | `outputs/figs/fig03.png` | `820959757851` |
| fig04 | `outputs/figs/fig04.png` | `756a2b49595e` |
| fig05 | `outputs/figs/fig05.png` | `165b57000878` |
| fig06 | `outputs/figs/fig06.png` | `9c674b379078` |
| fig07 | `outputs/figs/fig07.png` | `b3243c2bf745` |
| fig08 | `outputs/figs/fig08.png` | `4856eec1dd86` |
| fig09 | `outputs/figs/fig09.png` | `ebed68ae315a` |
| summary_html | `outputs/summary.html` | `d889b56d1466` |
| summary_pdf | `outputs/summary.pdf` | `b0e4858c4ea0` |

Re-run with `python -m beyondsearch run --config configs/beauty_india.yaml`; compare `results.json` hashes to confirm the same result.
