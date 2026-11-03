"""Turn test results into the insight log: evidence (computed) + so-what and confidence (analyst wording from the YAML)."""
from __future__ import annotations

import pandas as pd


def pct(x: float) -> str:
    return f"{x:.0%}"


def pv(p: float) -> str:
    return "p<0.001" if p < 0.001 else f"p={p:.3f}"


def build_insight_log(cfg, res) -> pd.DataFrame:
    c, a, nar = cfg["columns"], cfg["analysis"], cfg["narrative"]
    eng, cat = c["engine"], c["category"]
    S, C = cfg.short(cfg.focal), cfg.short(cfg.comparator)
    T, f = res.tests, res.frames
    h1, h2, h3, h4, h5, h6, rb = T["H1"], T["H2"], T["H3"], T["H4"], T["H5"], T["H6"], T["robust"]
    qlab = a["question_type"]["labels"]

    r3 = res.tables["H3_rates"]
    c3 = res.tables["H3_comp_rates"]
    ahead = int((c3.set_index(eng)["rate"] > r3.set_index(eng)["rate"]).sum())
    best, worst = r3.sort_values("rate").iloc[-1][eng], r3.sort_values("rate").iloc[0][eng]
    qt = res.tables["H2_rates"].set_index("question_type")
    cat_rates = res.tables["H4_rates"]
    eshare = f["valid"][eng].value_counts(normalize=True)
    methods = f["valid"][c["method"]].value_counts()
    fill = dict(ahead=ahead, n_engines=len(r3), n_retailer_q=h2["n_retailer_q"], min_cell=int(r3["count"].min()), max_cell=int(r3["count"].max()),
                best=best, worst=worst, bias_engine=a.get("engine_labels", {}).get(a["bias_check_engine"], a["bias_check_engine"]),
                method_p=f"p={T['bias'][c['method']]['p']:.2f}" if c["method"] in T["bias"] else "p=n/a",
                engine_p=f"p={T['bias']['engine_method_fisher_p']:.1f}" if T["bias"].get("engine_method_fisher_p") is not None else "p=n/a")
    so, conf = nar["so_what"], nar["confidence"]

    def lead(rate_a, rate_b, name_a, name_b):
        hi, lo = (name_a, name_b) if rate_a >= rate_b else (name_b, name_a)
        ratio = max(rate_a, rate_b) / max(min(rate_a, rate_b), 1e-9)
        return f"{hi} is named about {ratio:.1f} times as often as {lo}."

    rows = []
    rows.append(["H1", f"{S} named in {pct(h1['focal_rate'])} vs {C} {pct(h1['comp_rate'])} of {h1['n']} unbranded answers; {h1['only_comp']} name only {C}, "
                       f"{h1['only_focal']} only {S} (McNemar {pv(h1['p'])})", "Figure 4",
                 f"{lead(h1['comp_rate'], h1['focal_rate'], C, cfg.label(cfg.focal))} {so['H1']}", conf["H1"].format(**fill)])
    rows.append(["H2", f"{S} mention rate by question type: " + ", ".join(f"{i} {pct(r['rate'])} (n={int(r['count'])})" for i, r in qt.iterrows())
                       + f" (Fisher {pv(h2['fisher_p'])})", "Figure 5", so["H2"], conf["H2"].format(**fill)])
    rows.append(["H3", f"{S} mention rate by engine: " + ", ".join(f"{r.engine} {pct(r.rate)} (n={r.count})" for r in r3.itertuples())
                       + f" (chi-square {pv(h3['chi'][1])})", "Figure 6", so["H3"].format(**fill), conf["H3"].format(**fill)])
    prod_chi = h4["chi_product_only"]
    rows.append(["H4", f"{S} mention rate by category: " + ", ".join(f"{r.category} {pct(r.rate)}" for r in cat_rates.itertuples())
                       + f". Product categories only: chi-square {pv(prod_chi[1])}.", "Figure 7", so["H4"], conf["H4"].format(**fill)])
    if h5["n_linked"]:
        ev5 = (f"Among {h5['n_linked']} answers that link to a retailer: {S} linked in {pct(h5['focal_rate'])}, "
               f"{C} in {pct(h5['comp_rate'])} (McNemar {pv(h5['p'])})")
    else:
        ev5 = "No answers link to a retailer yet"
    rows.append(["H5", ev5, "Table in H5", so["H5"], conf["H5"].format(**fill)])
    if h6["n_pairs"]:
        ev6 = (f"Mean overlap of cited sites across repeat runs: {h6['mean']:.2f} (" + ", ".join(f"{k} {v:.2f}" for k, v in h6["by_engine"].items())
               + f") over {h6['n_pairs']} prompt-engine pairs")
    else:
        ev6 = "not enough repeat runs yet"
    rows.append(["H6", ev6, "Figure 8", so["H6"], conf["H6"].format(**fill)])
    rows.append(["Bias", "Engine mix collected: " + ", ".join(f"{k} {pct(v)}" for k, v in eshare.items()) + ". Collection method: "
                       + ", ".join(f"{k} {v}" for k, v in methods.items()) + ".", "Figure 1", so["Bias"], conf["Bias"].format(**fill)])
    if rb["n_single"]:
        evr = (f"Single fresh chats only (n={rb['n_single']}): {S} {pct(rb['focal_rate'])} vs {C} {pct(rb['comp_rate'])} (McNemar {pv(rb['p'])}); "
               f"all genuine rows: {S} {pct(f['allp'][f'{cfg.focal}_mention'].mean())} vs {C} {pct(f['allp'][f'{cfg.comparator}_mention'].mean())}")
    else:
        evr = "No single fresh chats in the data yet"
    rows.append(["Robust", evr, "Figure 9", so["Robust"].format(**fill), conf["Robust"].format(**fill)])
    return pd.DataFrame(rows, columns=["hypothesis", "insight (evidence)", "figure", "so what for the decision", "confidence"])
