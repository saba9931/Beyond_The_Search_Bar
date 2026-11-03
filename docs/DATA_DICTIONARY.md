# Data dictionary

## data/design/prompt_panel_v2.csv (one row per question)
`prompt_id` (B01E = English, B01H = Hinglish, unused), `base_id`, `language` (en or hinglish), `category` (sunscreen, acne_skincare, foundation, lipstick, fragrance, haircare, retailer), `intent` (need, budget, shortlist, where_to_buy, branded comparison), `prompt_text`, `brand_named_in_prompt`, `include_in_primary_unbranded`, `freeze_status`, `drift_wave`.

## data/design/run_schedule.csv (one row per planned run)
`run_id` (S001 to S600), `prompt_id`, `engine`, `run_no`, `collector`.

## data/processed/response_log.csv (one row per collected answer)
| Column | Meaning |
|---|---|
| `run_id` | Links to the schedule |
| `collector`, `engine`, `run_no`, `prompt_id` | Who, which engine, which repeat, which question |
| `run_datetime_ist` | Date and time of collection |
| `full_response_text` | The answer exactly as shown, pasted unedited |
| `citation_urls` | Source links shown with the answer |
| `response_status` | valid, contaminated (batched chat), api_run, or other flags |
| `collection_method` | single_chat, batched_chat or api |
| `fresh_chat` | yes for a single chat, no for a batched chat, n/a for API |
| `model_label_shown` | Model name as shown or stated by the collector |
| `memory_personalisation_off`, `logged_in` | Account settings; blank where not confirmed |
| `web_search_used` | yes if the answer showed sources |
| `notes` | Auto-summary of retailers named and links |
| `screenshot_file` | Optional |
| `key (auto)` | Internal helper column from the sheet; not used in analysis |

Empty cells mean "not recorded", not "no".

## Derived columns (added in `features.py`, never written back to the raw data)
| Column | Meaning |
|---|---|
| `<retailer>_mention` | 1 if the retailer name pattern from the config appears in the answer text |
| `<retailer>_cited` | 1 if any cited link belongs to the retailer's website |
| `first_pos_<retailer>` | position of first mention in the text, 0 = start, 1 = end |
| `n_domains`, `words` | number of distinct cited sites; length of the answer |

## Outputs of a run (`outputs/`, re-creatable)
`insight_log.csv` (one row per insight), `results.json` (every number in the report), `validation.json` (check findings), `excluded_rows.csv`, `tables/*.csv`, `figs/fig01-09.png`, `summary.html`/`summary.pdf`, `run_manifest.json` (inputs hashes, versions, timings), `run_report.md`.
