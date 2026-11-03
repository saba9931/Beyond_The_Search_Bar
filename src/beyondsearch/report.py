"""Step 5 (communication): save every result, build the summary page, and write the run report.

Every number in the summary comes from the analysis result, never typed by hand, so the page cannot
disagree with the data.
"""
from __future__ import annotations

import base64
import html
import logging
import math
from pathlib import Path

import numpy as np
import pandas as pd

from .insights import pct, pv
from .iotools import write_csv, write_json, write_text


# ----------------------------------------------------------------------------- helpers
def _clean(obj, nd: int = 6):
    """Make any result JSON-safe and stable: numpy -> python, NaN -> None, floats rounded."""
    if isinstance(obj, dict):
        return {str(k): _clean(v, nd) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [_clean(v, nd) for v in obj]
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating, float)):
        return None if math.isnan(float(obj)) else round(float(obj), nd)
    if isinstance(obj, (np.bool_,)):
        return bool(obj)
    return obj


def results_dict(cfg, res) -> dict:
    return _clean({"data_version": cfg["data_version"], "counts": res.counts, "tests": res.tests,
                   "insight_log": res.insight_log.to_dict("records")})


def elabel(cfg, engine: str) -> str:
    return cfg["analysis"].get("engine_labels", {}).get(engine, engine)


def five_insights(cfg, res) -> list[tuple[str, str]]:
    """The five insights that matter most, as (headline, detail). Used by the summary page and the notebook."""
    c = cfg["columns"]
    S, C = cfg.short(cfg.focal), cfg.short(cfg.comparator)
    T = res.tests
    h1, h2, h3, h5, h6, rb = T["H1"], T["H2"], T["H3"], T["H5"], T["H6"], T["robust"]
    out = []

    hi, lo = (C, cfg.label(cfg.focal)) if h1["comp_rate"] >= h1["focal_rate"] else (S, cfg.label(cfg.comparator))
    ratio = max(h1["comp_rate"], h1["focal_rate"]) / max(min(h1["comp_rate"], h1["focal_rate"]), 1e-9)
    r3, c3 = res.tables["H3_rates"], res.tables["H3_comp_rates"]
    ahead = int((c3.set_index(c["engine"])["rate"] > r3.set_index(c["engine"])["rate"]).sum())
    single = f" and in single fresh chats alone ({pct(rb['comp_rate'])} vs {pct(rb['focal_rate'])})" if rb["n_single"] else ""
    out.append((f"{hi} is named about {ratio:.1f} times as often as {lo}.",
                f"{pct(h1['comp_rate'])} vs {pct(h1['focal_rate'])} of {h1['n']} unbranded answers ({h1['only_comp']} name only {C}, {h1['only_focal']} only {S}; "
                f"McNemar {pv(h1['p'])}). {C} is ahead on {ahead} of {len(r3)} engines{single}."))

    qt = res.tables["H2_rates"].set_index("question_type")
    labels = cfg["analysis"]["question_type"]["labels"]
    rq, pq = qt.loc[labels["retailer"]], qt.loc[labels["other"]]
    head2 = (f"{S} appears when shoppers ask where to buy, not what to buy." if rq["rate"] > pq["rate"]
             else f"{S} is named less on retailer questions than on product questions.")
    out.append((head2, f"{pct(rq['rate'])} of {int(rq['count'])} retailer questions vs {pct(pq['rate'])} of {int(pq['count'])} product questions "
                       f"(Fisher {pv(h2['fisher_p'])}). Fix product-answer visibility first." if rq["rate"] > pq["rate"] else
                f"{pct(rq['rate'])} of {int(rq['count'])} retailer questions vs {pct(pq['rate'])} of {int(pq['count'])} product questions (Fisher {pv(h2['fisher_p'])})."))

    ordered = r3.sort_values("rate", ascending=False)
    out.append(("Engines differ." if h3["chi"] and h3["chi"][1] < 0.05 else "Engines do not differ clearly.",
                f"{S} is named in " + ", ".join(f"{pct(r.rate)} of {elabel(cfg, r.engine)}" for r in ordered.itertuples())
                + f" answers (chi-square {pv(h3['chi'][1])}). {elabel(cfg, ordered.iloc[-1][c['engine']])} names {S} least."))

    if h5["n_linked"]:
        head5 = (f"Engines link to {C} far more than to {S}." if h5["comp_rate"] > h5["focal_rate"] else f"Engines link to {S} at least as often as to {C}.")
        out.append((head5, f"Of {h5['n_linked']} answers with a retailer link, {C} is linked in {pct(h5['comp_rate'])} and {S} in {pct(h5['focal_rate'])}."))
    else:
        out.append(("No retailer links yet.", "No answer in the sample links to a retailer website."))

    if h6["n_pairs"]:
        worst = min(h6["by_engine"].items(), key=lambda kv: kv[1])
        out.append(("One answer is not reliable." if h6["mean"] < 0.8 else "Repeat runs mostly agree.",
                    f"Cited sites overlap {h6['mean']:.2f} (1 = identical) between repeat runs of the same question ({elabel(cfg, worst[0])} {worst[1]:.2f}), "
                    f"so any monitor needs several runs per question."))
    else:
        out.append(("Repeatability not measured yet.", "Collect at least two runs of the same question on the same engine."))
    return out


def hypothesis_results(cfg, res) -> dict[str, str]:
    """One short verdict per hypothesis, computed from the tests."""
    c, T = cfg["columns"], res.tests
    S, C = cfg.short(cfg.focal), cfg.short(cfg.comparator)
    out = {}
    h1 = T["H1"]
    out["H1"] = f"{'Supported' if h1['p'] < 0.05 and h1['comp_rate'] > h1['focal_rate'] else 'Not supported'}: {pct(h1['comp_rate'])} vs {pct(h1['focal_rate'])}, {pv(h1['p'])}"
    qt = res.tables["H2_rates"].set_index("question_type")
    lab = cfg["analysis"]["question_type"]["labels"]
    rq, pq = qt.loc[lab["retailer"]], qt.loc[lab["other"]]
    out["H2"] = f"{'Supported' if T['H2']['fisher_p'] < 0.05 and rq['rate'] > pq['rate'] else 'Not supported'}: {pct(rq['rate'])} vs {pct(pq['rate'])} (n={int(rq['count'])} vs {int(pq['count'])})"
    r3 = res.tables["H3_rates"]
    out["H3"] = f"{'Supported' if T['H3']['chi'][1] < 0.05 else 'Not supported'}: {pct(r3['rate'].min())} to {pct(r3['rate'].max())} across {len(r3)} engines, {pv(T['H3']['chi'][1])}"
    prod = res.tables["H4_rates"][res.tables["H4_rates"][c["category"]] != cfg["analysis"]["product_only_exclude"]["value"]]
    p4 = T["H4"]["chi_product_only"][1]
    verdict4 = "Supported" if p4 < 0.05 else ("Borderline" if p4 < 0.10 else "Not supported")
    top, bot = prod.sort_values("rate").iloc[-1], prod.sort_values("rate").iloc[0]
    out["H4"] = f"{verdict4} among product categories ({pv(p4)}); {top[c['category']]} {pct(top['rate'])} highest, {bot[c['category']]} {pct(bot['rate'])} lowest"
    h5 = T["H5"]
    out["H5"] = (f"{'Supported' if h5['p'] < 0.05 and h5['comp_rate'] > h5['focal_rate'] else 'Not supported'}: {pct(h5['comp_rate'])} vs {pct(h5['focal_rate'])}, {pv(h5['p'])}"
                 if h5["n_linked"] else "No linked answers yet")
    h6 = T["H6"]
    out["H6"] = (f"{'Supported' if h6['mean'] < 0.8 else 'Not supported'}: mean overlap {h6['mean']:.2f} over {h6['n_pairs']} prompt-engine pairs" if h6["n_pairs"] else "Not enough repeat runs yet")
    return out


def _img(path: Path, width: str) -> str:
    if not path.exists():
        return ""
    return f'<img src="data:image/png;base64,{base64.b64encode(path.read_bytes()).decode()}" style="width:{width}">'


# ----------------------------------------------------------------------------- summary page
def summary_html(cfg, res, figs_dir: Path) -> str:
    c, nar, T = cfg["columns"], cfg["narrative"], res.tests
    S, C = cfg.short(cfg.focal), cfg.short(cfg.comparator)
    v = res.frames["valid"]
    n_prompts, n_eng = v[c["prompt_id"]].nunique(), v[c["engine"]].nunique()
    esc = html.escape
    insights = "".join(f"<li><b>{esc(h)}</b> {esc(d)}</li>" for h, d in five_insights(cfg, res))
    verdicts = hypothesis_results(cfg, res)
    hyp_rows = "".join(f"<tr><td>{esc(h['id'])}</td><td>{esc(h['statement'])} <i>(expected: {esc(h['expected'])})</i></td><td>{esc(h['question'])}</td><td>{esc(verdicts.get(h['id'], ''))}</td></tr>"
                       for h in cfg["hypotheses"])
    log_rows = "".join(f"<tr><td><b>{esc(r['hypothesis'])}</b></td><td>{esc(r['insight (evidence)'])}</td><td>{esc(r['so what for the decision'])}</td><td>{esc(r['confidence'])}</td></tr>"
                       for r in res.insight_log.to_dict("records"))
    eshare = v[c["engine"]].value_counts(normalize=True)
    methods = v[c["method"]].value_counts()
    bias = T["bias"]
    coll_p, meth_p = bias.get(c["collector"], {}).get("p"), bias.get(c["method"], {}).get("p")
    def verdict(p): return "none detected" if p is None or p >= 0.05 else "detected"
    eng_p = bias.get("engine_method_fisher_p")
    bias_par = (f"<b>Engine mix:</b> " + ", ".join(f"{elabel(cfg, k)} {pct(x)}" for k, x in eshare.items()) + f" of the {len(v)} answers (plan: popularity-weighted). "
                f"<b>Collection method</b> (" + ", ".join(f"{n} {k.replace('_', ' ')}" for k, n in methods.items()) + ") is kept as a variable and tested instead of excluding rows: "
                f"effect on {S} mentions {verdict(meth_p)} (chi-square {'p=%.2f' % meth_p if meth_p is not None else 'n/a'}"
                + (f"; inside {elabel(cfg, cfg['analysis']['bias_check_engine'])} alone p={eng_p:.1f}" if eng_p is not None else "") + "). "
                f"<b>Collector effect:</b> {verdict(coll_p)}{' (p=%.2f)' % coll_p if coll_p is not None else ''}.")
    d4 = "".join(f"<li>{esc(x)}</li>" for x in nar["d4_notes"])
    limits = " &nbsp;&bull;&nbsp; ".join(esc(x) for x in nar["limits"])
    figs = Path(figs_dir)
    return f"""<html><head><meta charset="utf-8"><title>{esc(nar['title'])}</title><style>
@page{{size:A4;margin:11mm 12mm}} body{{font-family:Helvetica,Arial,sans-serif;font-size:8.6pt;line-height:1.28;color:#1b1b1b}}
h1{{font-size:14pt;margin:0 0 2px}} h2{{font-size:10pt;margin:7px 0 3px;color:#c2185b}} .sub{{color:#555;font-size:8pt;margin-bottom:5px}}
table{{border-collapse:collapse;width:100%}} td,th{{border:0.5px solid #bbb;padding:2px 4px;vertical-align:top;font-size:7.4pt}} th{{background:#f1f1f1;text-align:left}}
.box{{background:#faf3f6;border-left:3px solid #c2185b;padding:3px 7px;margin:4px 0}} .two{{display:flex;gap:8px}} .two>div{{flex:1}} ol{{margin:2px 0 2px 16px;padding:0}} li{{margin-bottom:2px}}
.pb{{page-break-before:always}} p{{margin:2px 0}}
</style></head><body>
<h1>{esc(nar['title'])}</h1>
<div class="sub">{esc(nar['team'])} &nbsp;|&nbsp; Data version {esc(cfg['data_version'])}: {res.counts['rows_usable']} usable of {res.counts['runs_planned']} planned answers &nbsp;|&nbsp; Generated by: python -m beyondsearch run</div>
<div class="box"><b>Decision supported:</b> {esc(nar['decision'])} <b>Method:</b> {n_prompts} shopper questions put to {n_eng} AI engines; plain text rules count which retailers are named and linked. {len(cfg['hypotheses'])} hypotheses were written before any chart (page 2).</div>
<h2>The five insights that matter most</h2><ol>{insights}</ol>
<div class="two"><div>{_img(figs / 'fig04.png', '100%')}</div><div>{_img(figs / 'fig05.png', '100%')}</div></div>
<h2>How this shapes modelling (D4)</h2><ul style="margin:2px 0 0 14px;padding:0">{d4}</ul>
<div class="pb"></div>
<h1>Hypotheses, bias checks and insight log</h1>
<h2>Hypotheses stated before analysis, and what we found</h2>
<table><tr><th>#</th><th>Hypothesis</th><th>Business question</th><th>Result</th></tr>{hyp_rows}</table>
<h2>Representativeness and bias checks</h2>
<div class="two"><div>{_img(figs / 'fig01.png', '72%')}</div><div>{_img(figs / 'fig09.png', '72%')}</div></div>
<p>{bias_par}</p>
<h2>Insight log</h2>
<table><tr><th style="width:5%">#</th><th style="width:30%">Insight (evidence)</th><th style="width:40%">So what for the decision</th><th style="width:25%">Confidence</th></tr>{log_rows}</table>
<p style="margin-top:4px"><b>Limits:</b> {limits}</p>
</body></html>"""


def html_to_pdf(html_path: Path, pdf_path: Path, logger: logging.Logger | None = None) -> bool:
    """Optional: needs `pip install playwright` and `playwright install chromium`. Returns False (not an error) if unavailable."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        if logger:
            logger.warning("playwright is not installed: summary.pdf skipped (summary.html is still written)")
        return False
    try:
        with sync_playwright() as p:
            b = p.chromium.launch()
            pg = b.new_page()
            pg.goto(Path(html_path).resolve().as_uri())
            pg.pdf(path=str(pdf_path), format="A4", print_background=True, prefer_css_page_size=True)
            b.close()
        return True
    except Exception as exc:  # browser missing, sandbox, etc.
        if logger:
            logger.warning(f"summary.pdf skipped ({type(exc).__name__}: {exc})")
        return False


# ----------------------------------------------------------------------------- save everything
def save_outputs(cfg, res, validation, out_dir: Path, make_pdf: bool = True, logger: logging.Logger | None = None) -> dict[str, Path]:
    from .figures import save_all
    out_dir = Path(out_dir)
    files: dict[str, Path] = {}
    files["insight_log"] = write_csv(out_dir / "insight_log.csv", res.insight_log)
    files["results"] = write_json(out_dir / "results.json", results_dict(cfg, res))
    files["validation"] = write_json(out_dir / "validation.json", validation.to_dict())
    files["excluded_rows"] = write_csv(out_dir / "excluded_rows.csv", res.frames["excluded"])
    for name, t in res.tables.items():
        files[f"table_{name}"] = write_csv(out_dir / "tables" / f"{name}.csv", t.reset_index() if (t.index.name or isinstance(t.index, pd.MultiIndex) or not isinstance(t.index, pd.RangeIndex)) else t)
    for p in save_all(res, cfg, out_dir / "figs"):
        files[p.stem] = p
    page = write_text(out_dir / "summary.html", summary_html(cfg, res, out_dir / "figs"))
    files["summary_html"] = page
    if make_pdf and html_to_pdf(page, out_dir / "summary.pdf", logger):
        files["summary_pdf"] = out_dir / "summary.pdf"
    return files


def run_report_md(manifest: dict, validation) -> str:
    """Human-readable record of one run (the manifest is the machine-readable one)."""
    lines = [f"# Run report {manifest['run_id']}", "",
             f"- Status: **{manifest['status']}**", f"- Project: {manifest['project']}", f"- Data version: {manifest['data_version']}  |  seed: {manifest['seed']}",
             f"- Config: `{manifest['config']['file']}` (sha256 `{manifest['config']['sha256'][:12]}`)",
             f"- Code: " + (f"commit `{manifest['code']['commit'][:12]}`, uncommitted changes: {manifest['code']['uncommitted_changes']}" if manifest['code']['commit'] else "not under git (no commit recorded)"),
             f"- Python {manifest['environment']['python']} on {manifest['environment']['platform']}", "",
             "## Inputs", "", "| label | file | rows | sha256 |", "|---|---|---|---|"]
    for k, v in manifest["inputs"].items():
        lines.append(f"| {k} | `{v['path']}` | {v['rows']} | `{v['sha256'][:12]}` |")
    lines += ["", "## Data checks", "", "| level | check | message | count |", "|---|---|---|---|"]
    for f in validation.findings:
        lines.append(f"| {f.level} | {f.check} | {f.message} | {f.count} |")
    lines += ["", "## Steps", "", "| step | status | seconds |", "|---|---|---|"]
    for s in manifest["steps"]:
        lines.append(f"| {s['name']} | {s['status']} | {s['seconds']} |")
    lines += ["", "## Key facts", ""] + [f"- {k}: {v}" for k, v in manifest["facts"].items()]
    lines += ["", "## Outputs", "", "| label | file | sha256 |", "|---|---|---|"]
    for k, v in manifest["outputs"].items():
        lines.append(f"| {k} | `{v['path']}` | `{v['sha256'][:12]}` |")
    lines += ["", "Re-run with `python -m beyondsearch run --config " + manifest["config"]["file"] + "`; compare `results.json` hashes to confirm the same result.", ""]
    return "\n".join(lines)
