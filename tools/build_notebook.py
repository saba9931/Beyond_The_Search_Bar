"""Writes notebooks/ANCP_TL_D3_eda.ipynb. The notebook only SHOWS results: every calculation lives in
src/beyondsearch (tested). Text that depends on the data or the study comes from configs/beauty_india.yaml.
Usage: python tools/build_notebook.py   then   jupyter nbconvert --to notebook --execute --inplace notebooks/ANCP_TL_D3_eda.ipynb
"""
from pathlib import Path

import nbformat as nbf

cells = []
md = lambda s: cells.append(nbf.v4.new_markdown_cell(s.strip()))
code = lambda s: cells.append(nbf.v4.new_code_cell(s.strip()))

md("""# D3 EDA: Does Sephora India show up in AI shopping answers?
This notebook only **shows** the analysis. The calculations live in `src/beyondsearch/` (unit-tested), and the study-specific wording lives in `configs/beauty_india.yaml`. That is what makes it traceable, reliable, reproducible and observable.

| CRISP-DM phase | Where it happens |
|---|---|
| Business understanding | Section 0 (decision and question) and the project charter |
| Data understanding | Sections 2, 4, 5 (`validate.py`, `analysis.py`) |
| Data preparation | Section 3 (`ingest.py`, `features.py`) |
| Modelling | Next step (D4): outcome and inputs are fixed in Section 8 |
| Evaluation | Sections 6 and 6b (hypothesis tests, robustness) |
| Deployment / monitoring | `python -m beyondsearch run` (repeatable, logged, with a run manifest) |""")

code("""
# Setup: find the repository root, load the configuration, start a traceable session.
import sys, warnings
from pathlib import Path
ROOT = next(p for p in [Path.cwd(), *Path.cwd().parents] if (p / "configs").exists())
sys.path.insert(0, str(ROOT / "src"))                      # works without installing the package
import matplotlib.pyplot as plt
import pandas as pd
from IPython.display import display, Markdown
from beyondsearch.config import Config
from beyondsearch.iotools import read_csv_checked, sha256_file
from beyondsearch.manifest import environment
from beyondsearch.validate import validate_inputs
from beyondsearch.analysis import run_analysis
from beyondsearch.figures import FIGURES
from beyondsearch.report import five_insights, hypothesis_results
warnings.filterwarnings("ignore")
pd.set_option("display.width", 140); pd.set_option("display.max_columns", 30)
cfg = Config.load(ROOT / "configs" / "beauty_india.yaml")
nar = cfg["narrative"]
print("project:", cfg["project"], "| data version:", cfg["data_version"], "| seed:", cfg["seed"])
""")

md("## 0. Decision, question and honest limit")
code("""
display(Markdown(f"**Team:** {nar['team']}  \\n**Business decision this supports:** {nar['decision']}  \\n\\n**Analytics question:** {nar['question']}  \\n\\n**Status:** {nar['status']}  \\n\\n**Honest limit:** {nar['honest_limit']}"))
""")

md("""## 1. Hypotheses (written before looking at any chart)
Each one is tied to the business decision. The expected direction is written first, so the charts cannot change our minds afterwards. They are stored in the configuration file, so the notebook, the report and the tests all use the same wording.""")
code("""
rows = ["| # | Hypothesis | Business question | Test | Expected |", "|---|---|---|---|---|"]
rows += [f"| {h['id']} | {h['statement']} | {h['question']} | {h['test']} | {h['expected']} |" for h in cfg["hypotheses"]]
display(Markdown("\\n".join(rows)))
""")

md("## 2. Load and validate the data\nNothing is analysed until the data passes the checks. Warnings are shown, not hidden.")
code("""
rl, panel, sched = (read_csv_checked(cfg.path(k), label=k) for k in ("response_log", "prompt_panel", "run_schedule"))
check = validate_inputs(cfg, rl, panel, sched)
display(pd.DataFrame([f.__dict__ for f in check.findings])[["level", "check", "message", "count"]])
check.raise_if_errors()
print("rows logged:", len(rl), "| planned runs:", len(sched), f"| progress: {len(rl)/len(sched):.0%}")
""")

md("""## 3. Build simple features from the raw answers
No AI model is used here. Plain text rules, so anyone can check them (`src/beyondsearch/features.py`):
- `*_mention`: the retailer name appears in the answer text.
- `*_cited`: a link in the answer belongs to that retailer's website.
- `first_pos_*`: how early the retailer appears (0 = start, 1 = end).

These rules count only the retailer name, so product-only answers count as "no retailer named". All genuine answers are used; the collection method is tested as a possible bias in Section 4, not used to throw rows away.""")
code("""
res = run_analysis(cfg, rl, panel, sched)
display(pd.DataFrame({e: {"regular expression": v["pattern"], "link contains": v["domain"]} for e, v in cfg["entities"].items()}).T)
print("answers used:", res.counts["rows_usable"], "| excluded:", res.counts["rows_excluded"],
      "| primary (unbranded):", res.counts["primary_n"], "| branded comparison:", res.counts["branded_n"])
display(res.tables["method_counts"]); display(res.tables["engine_by_method"])
res.frames["valid"][["run_id", "engine", "category", "words", "n_domains", "sephora_mention", "nykaa_mention"]].head()
""")

md("## 4. Representativeness and bias checks\nThree things could bias the sample: the engine mix, who collected, and how the answer was collected. We test each one instead of dropping data.")
code("""
for name in ("engine_by_intent", "category_by_engine", "runs_per_collector", "planned_vs_collected"):
    print(name.replace("_", " ")); display(res.tables[name])
fig = FIGURES[0](res, cfg); plt.show()
b = res.tests["bias"]
for var, r in b.items():
    if isinstance(r, dict): print(f"{var} vs Sephora mention: chi2={r['chi2']:.2f}, p={r['p']:.3f}")
print("\\nChatGPT only, Nykaa named by collection method:"); display(res.tables["bias_engine_method"])
print("Fisher exact p =", None if b['engine_method_fisher_p'] is None else round(b['engine_method_fisher_p'], 3))
""")

md("## 5. Distributions: what do the answers look like?")
code("""
FIGURES[1](res, cfg); plt.show()
FIGURES[2](res, cfg); plt.show()
""")

md("## 6. Hypothesis tests")
code("""
# H1: Nykaa vs Sephora named, same answers (paired test)
t = res.tests["H1"]
display(res.tables["H1_table"].rename_axis(index="Sephora named", columns="Nykaa named"))
print(f"Sephora named in {t['focal_rate']:.1%}, Nykaa in {t['comp_rate']:.1%} of unbranded answers; McNemar p = {t['p']:.4g}")
FIGURES[3](res, cfg); plt.show()
""")
code("""
# H2: retailer question ("where to buy") vs product question (need, budget, shortlist)
display(res.tables["H2_rates"]); t = res.tests["H2"]
print("chi-square (chi2, p, dof):", t["chi"])
print(f"Fisher exact (use this one: only {t['n_retailer_q']} retailer-question answers): odds ratio {t['fisher_odds']:.1f}, p = {t['fisher_p']:.5f}")
FIGURES[4](res, cfg); plt.show()
""")
code("""
# H3: engine
display(res.tables["H3_rates"]); print("chi-square (chi2, p, dof):", res.tests["H3"]["chi"])
FIGURES[5](res, cfg); plt.show()
""")
code("""
# H4: category (and again without the retailer category, because it drives the first result)
display(res.tables["H4_rates"]); t = res.tests["H4"]
print("chi-square, all categories:", t["chi"]); print("chi-square, product categories only:", t["chi_product_only"], "(small expected counts: indicative)")
FIGURES[6](res, cfg); plt.show()
""")
code("""
# H5: links, among answers that link to at least one retailer site
t = res.tests["H5"]; print("answers with a retailer link:", t["n_linked"], "of", t["n_primary"])
if t["n_linked"]:
    display(res.tables["H5_table"].rename_axis(index="Sephora linked", columns="Nykaa linked"))
    print(f"Sephora linked in {t['focal_rate']:.1%}, Nykaa in {t['comp_rate']:.1%}; McNemar p = {t['p']:.4g}")
""")
code("""
# H6: repeatability, Jaccard overlap of cited sites between runs of the same prompt and engine
t = res.tests["H6"]; print("prompt-engine pairs with 2+ runs:", t["n_pairs"], "| mean overlap:", None if t["mean"] is None else round(t["mean"], 2))
if t["n_pairs"]:
    display(res.tables["H6_by_engine"]); FIGURES[7](res, cfg); plt.show()
else:
    print("Not enough repeat runs yet: collect at least 2 runs of the same prompt on the same engine.")
""")

md("## 6b. Robustness: does the collection method change the conclusion?\nAnswers from one fresh chat per question are the cleanest. We repeat the headline comparison on that subset and by method. Nothing is removed from the main analysis.")
code("""
display(res.tables["robust_by_engine_method"]); t = res.tests["robust"]
if t["n_single"]:
    print(f"Single fresh chats only (n={t['n_single']}): Sephora {t['focal_rate']:.0%}, Nykaa {t['comp_rate']:.0%}, McNemar p = {t['p']:.4g}")
FIGURES[8](res, cfg); plt.show()
""")

md("## 7. Insight log\nEvidence numbers come from the code. The so-what and confidence wording is the analyst's, kept in the configuration file.")
code("""
pd.set_option("display.max_colwidth", 200)
display(res.insight_log)
""")

md("## 8. Summary and effect on modelling")
code("""
verdicts = hypothesis_results(cfg, res)
lines = ["**What we found, hypothesis by hypothesis**", ""] + [f"- **{h['id']}**: {verdicts[h['id']]}" for h in cfg["hypotheses"]]
lines += ["", "**The five insights that matter most**", ""] + [f"{i}. **{h}** {d}" for i, (h, d) in enumerate(five_insights(cfg, res), 1)]
lines += ["", "**How this shapes D4 (modelling)**", ""] + [f"- {x}" for x in nar["d4_notes"]]
display(Markdown("\\n".join(lines)))
""")

md("## 9. Limits of this exploration")
code("""
display(Markdown("\\n".join(f"- {x}" for x in nar["limits"])))
""")

md("## 10. Traceability: what exactly produced these numbers")
code("""
trace = {"data version": cfg["data_version"], "configuration sha256": cfg.sha256[:16], "seed": cfg["seed"]}
for k in ("response_log", "prompt_panel", "run_schedule"):
    trace[f"{k} sha256"] = sha256_file(cfg.path(k))[:16]
display(pd.Series(trace, name="value").to_frame())
env = environment(); display(pd.Series({"python": env["python"], **env["packages"]}, name="version").to_frame())
print("To reproduce on any computer:  pip install -r requirements.txt  &&  python -m beyondsearch run")
""")

nb = nbf.v4.new_notebook()
nb["cells"] = cells
nb.metadata["kernelspec"] = {"display_name": "Python 3", "language": "python", "name": "python3"}
out = Path(__file__).resolve().parents[1] / "notebooks" / "ANCP_TL_D3_eda.ipynb"
out.parent.mkdir(exist_ok=True)
nbf.write(nb, out)
print("wrote", out)
