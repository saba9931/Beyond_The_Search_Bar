# Reproducibility guide

## 1. Run the existing study
| Where | Steps |
|---|---|
| Mac / Linux | `python3 -m venv .venv && source .venv/bin/activate`, `pip install -r requirements-dev.txt`, `pip install -e .`, `python -m beyondsearch run` |
| Windows | `py -m venv .venv`, `.venv\Scripts\activate`, then the same pip and python lines |
| Google Colab | `!git clone <repo url>`, `%cd BEYOND-THE-SEARCH-BAR`, `!pip install -r requirements-dev.txt`, `!pip install -e .`, `!python -m beyondsearch run` |

Open `outputs/summary.html` and `outputs/run_report.md`. Run `python -m pytest -q` to check that your computer gives the same numbers as ours (golden files in `tests/golden/`).

## 2. Commands
| Command | What it does |
|---|---|
| `python -m beyondsearch merge` | shared collection workbook becomes `data/processed/response_log.csv` |
| `python -m beyondsearch validate` | checks the inputs; exit code 1 if there is an error |
| `python -m beyondsearch run` | validate, analyse, save tables, figures, insight log, summary, manifest |
| `python -m beyondsearch profile <file>` | quick profile of any csv or xlsx |
| `python -m beyondsearch package --name <folder>` | freeze the latest outputs into `deliverables/<folder>` |

Exit codes: 0 ok, 1 data problem, 2 config problem, 3 unexpected.

## 3. Use it on a similar dataset (another retailer or industry)
1. Copy `configs/beauty_india.yaml` to `configs/<new>.yaml`.
2. Change `paths` to your files and `columns` if your column names differ.
3. Change `entities` (brand name pattern and website domain), `focal` and `comparator`.
4. Rewrite `hypotheses` and `narrative` for your question.
5. Run `python -m beyondsearch --config configs/<new>.yaml validate`. Fix what it reports, then `run`.
No Python code needs editing. Required columns are listed in `schema` in the config and in the data dictionary.

## 4. Four principles mapped to the code
| Principle | How | Where |
|---|---|---|
| Traceability of data | SHA-256 of every input file, data version, config hash | `manifest.py`, `iotools.py` |
| Traceability of code | git commit, library versions, step timings, JSONL log | `manifest.py`, `logsetup.py` |
| Reliability | validation before analysis, atomic writes, clear error classes, manifest written even on failure, 37 tests | `validate.py`, `iotools.py`, `errors.py`, `tests/` |
| Reproducibility | config-driven, fixed seed, pinned versions, golden-file tests, data dictionary | `config.py`, `requirements.txt`, `tests/golden/` |
| Observability | same command on every OS, CI on Linux / Windows / macOS, run report, summary | `.github/workflows/tests.yml`, `report.py` |

## 5. CRISP-DM mapping
See the table in the README. Modelling (D4) will be added as `src/beyondsearch/model.py` with its own config section and tests, reading the same validated data.

## 6. Known limits
- CI is written but has not been run on Windows and macOS yet; the first push will show.
- The `report` PDF needs Playwright with Chromium (`playwright install chromium`); use `--no-pdf` otherwise.
- API collection (Gemini and others) is not part of this package yet; keys must stay in Colab Secrets.
