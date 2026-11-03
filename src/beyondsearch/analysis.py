"""Step 4 (data understanding / EDA): load, prepare and test the hypotheses.

`run_analysis` is a pure function: same inputs and configuration -> same results. It reads nothing but the
data frames it is given, writes nothing, and changes no input. Saving results is done by `report.py`.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency

from .errors import DataError
from .features import add_features
from .stats import chi_test, fisher_test, mcnemar_test, mean_jaccard, rate_table


@dataclass
class AnalysisResult:
    counts: dict = field(default_factory=dict)          # simple numbers (rows, usable, excluded, ...)
    tables: dict = field(default_factory=dict)          # name -> DataFrame (shown in the notebook, saved as CSV)
    tests: dict = field(default_factory=dict)           # hypothesis id -> dict of test results
    frames: dict = field(default_factory=dict)          # valid, primary, linked, repeats, excluded (for figures)
    insight_log: pd.DataFrame | None = None


def prepare(cfg, rl: pd.DataFrame, panel: pd.DataFrame, logger: logging.Logger | None = None):
    """Join answers to the question panel, flag usable rows, add features. Returns (allrows, valid, primary, excluded)."""
    c = cfg["columns"]
    df = rl.merge(panel, on=c["prompt_id"], how="left", validate="m:1")
    if df[c["category"]].isna().any():
        raise DataError("some prompt_id values are not in the prompt panel")
    if df[c["record_id"]].duplicated().any():
        raise DataError("duplicate run_id in response_log")

    genuine = df[c["status"]].isin(cfg["statuses"]["genuine"])
    has_text = df[c["text"]].notna()
    usable = genuine & has_text
    excluded = df.loc[~usable, [c["record_id"], c["status"]]].copy()
    excluded["reason"] = np.where(~genuine[~usable], "status is not a genuine answer", "no answer text")

    allrows = add_features(df, cfg)
    valid = allrows[usable].copy()
    pf = cfg["analysis"]["primary_filter"]
    primary = valid[valid[pf["column"]] == pf["value"]].copy()
    if logger:
        logger.info(f"prepare: {len(df)} rows, {int(usable.sum())} usable, {len(excluded)} excluded, {len(primary)} in primary (unbranded) sample")
    return allrows, valid, primary, excluded


def run_analysis(cfg, rl: pd.DataFrame, panel: pd.DataFrame, sched: pd.DataFrame, logger: logging.Logger | None = None) -> AnalysisResult:
    c, a = cfg["columns"], cfg["analysis"]
    eng, cat, intent, coll, meth, rid, pid = (c[k] for k in ("engine", "category", "intent", "collector", "method", "record_id", "prompt_id"))
    focal, comp = cfg.focal, cfg.comparator
    fm, cm, fc, cc = f"{focal}_mention", f"{comp}_mention", f"{focal}_cited", f"{comp}_cited"
    ents = list(cfg["entities"])

    allrows, valid, primary, excluded = prepare(cfg, rl, panel, logger)
    res = AnalysisResult()
    res.frames.update(valid=valid, primary=primary, excluded=excluded)
    res.counts.update(rows_logged=len(rl), runs_planned=len(sched), rows_usable=len(valid), rows_excluded=len(excluded),
                      primary_n=len(primary), branded_n=len(valid) - len(primary))
    res.tables["method_counts"] = rl[meth].value_counts().rename_axis(meth).reset_index(name="rows")
    res.tables["engine_by_method"] = pd.crosstab(valid[eng], valid[meth], margins=True)

    # ---- representativeness and bias checks (nothing is dropped, only tested) -----------------------------------
    res.tables["engine_by_intent"] = pd.crosstab(valid[eng], valid[intent], margins=True)
    res.tables["category_by_engine"] = pd.crosstab(valid[cat], valid[eng], margins=True)
    res.tables["runs_per_collector"] = valid[coll].value_counts().to_frame("runs")
    plan_share = sched.groupby(a["plan_share_by"]).size() / len(sched)
    got_share = valid.groupby(eng).size() / len(valid)
    res.tables["planned_vs_collected"] = pd.DataFrame({"planned_share": plan_share, "collected_share": got_share}).round(3)
    bias = {}
    for var in (coll, meth):
        tab = pd.crosstab(valid[var], valid[fm])
        if tab.shape[0] > 1 and tab.shape[1] > 1:
            chi2, p, *_ = chi2_contingency(tab)
            bias[var] = {"chi2": float(chi2), "p": float(p)}
    be = a["bias_check_engine"]
    cg = valid[(valid[eng] == be) & (valid[a["primary_filter"]["column"]] == a["primary_filter"]["value"])]
    tm = pd.crosstab(cg[meth], cg[cm]).reindex(columns=[False, True], fill_value=0)
    res.tables["bias_engine_method"] = tm
    bias["engine_method_fisher_p"] = (fisher_test(cg, meth, cm) or (None, None))[1]
    res.tests["bias"] = bias

    # ---- distributions ----------------------------------------------------------------------------------------
    res.tables["retailer_share"] = pd.Series({e: primary[f"{e}_mention"].mean() for e in ents}).sort_values().rename("share").rename_axis("entity").reset_index()

    # ---- H1: comparator vs focal named, same answers ------------------------------------------------------------
    p1, t1 = mcnemar_test(primary[fm], primary[cm])
    res.tables["H1_table"] = t1
    res.tests["H1"] = {"focal_rate": float(primary[fm].mean()), "comp_rate": float(primary[cm].mean()), "n": len(primary), "p": p1,
                       "only_comp": int(((~primary[fm]) & primary[cm]).sum()), "only_focal": int((primary[fm] & ~primary[cm]).sum())}
    g = pd.DataFrame({"retailer": [cfg.label(focal), cfg.label(comp)], "sum": [primary[fm].sum(), primary[cm].sum()], "count": [len(primary)] * 2})
    g["rate"] = g["sum"] / g["count"]
    res.tables["H1_rates"] = _with_ci(g)

    # ---- H2: retailer questions vs product questions --------------------------------------------------------------
    qt = a["question_type"]
    primary["question_type"] = np.where(primary[qt["column"]].isin(qt["retailer_values"]), qt["labels"]["retailer"], qt["labels"]["other"])
    res.tables["H2_rates"] = rate_table(primary, "question_type", fm)
    fish = fisher_test(primary, "question_type", fm)
    res.tests["H2"] = {"chi": chi_test(primary, "question_type", fm), "fisher_odds": fish[0] if fish else None, "fisher_p": fish[1] if fish else None,
                       "n_retailer_q": int((primary["question_type"] == qt["labels"]["retailer"]).sum())}

    # ---- H3: engine ----------------------------------------------------------------------------------------------------
    res.tables["H3_rates"] = rate_table(primary, eng, fm)
    res.tables["H3_comp_rates"] = rate_table(primary, eng, cm)
    res.tests["H3"] = {"chi": chi_test(primary, eng, fm)}

    # ---- H4: category (and again without the retailer category) -----------------------------------------------------
    res.tables["H4_rates"] = rate_table(primary, cat, fm)
    pe = a["product_only_exclude"]
    prod_only = primary[primary[pe["column"]] != pe["value"]]
    res.tests["H4"] = {"chi": chi_test(primary, cat, fm), "chi_product_only": chi_test(prod_only, cat, fm)}

    # ---- H5: links ----------------------------------------------------------------------------------------------------------
    linked = primary[primary[[f"{e}_cited" for e in ents]].any(axis=1)]
    res.frames["linked"] = linked
    h5 = {"n_linked": len(linked), "n_primary": len(primary), "focal_rate": None, "comp_rate": None, "p": None}
    if len(linked):
        p5, t5 = mcnemar_test(linked[fc], linked[cc])
        res.tables["H5_table"] = t5
        h5.update(focal_rate=float(linked[fc].mean()), comp_rate=float(linked[cc].mean()), p=p5)
    res.tests["H5"] = h5

    # ---- H6: repeatability -------------------------------------------------------------------------------------------------
    rep = valid.groupby([pid, eng])["domains"].apply(list).reset_index()
    rep["runs"] = rep["domains"].str.len()
    rep["jaccard"] = rep["domains"].apply(mean_jaccard)
    rep = rep[rep["runs"] >= a["repeat_min_runs"]]
    res.frames["repeats"] = rep
    res.tests["H6"] = {"n_pairs": len(rep), "mean": float(rep["jaccard"].mean()) if len(rep) else None,
                       "by_engine": rep.groupby(eng)["jaccard"].mean().to_dict() if len(rep) else {}}
    if len(rep):
        res.tables["H6_by_engine"] = rep.groupby(eng)["jaccard"].agg(["mean", "median", "count"]).round(2)

    # ---- robustness: does the collection method change the conclusion? ------------------------------------------------
    allp = valid[valid[a["primary_filter"]["column"]] == a["primary_filter"]["value"]].copy()
    res.tables["robust_by_engine_method"] = (allp.groupby([eng, meth]).agg(n=(rid, "count"), focal=(fm, "mean"), comp=(cm, "mean"),
                                             focal_link=(fc, "mean"), comp_link=(cc, "mean")).round(2).reset_index())
    single = allp[allp[meth] == a["single_method_value"]]
    if len(single):
        ps, _ = mcnemar_test(single[fm], single[cm])
        res.tests["robust"] = {"n_single": len(single), "focal_rate": float(single[fm].mean()), "comp_rate": float(single[cm].mean()), "p": ps}
    else:
        res.tests["robust"] = {"n_single": 0, "focal_rate": None, "comp_rate": None, "p": None}
    res.tables["robust_by_engine"] = allp.groupby(eng).agg(n=(rid, "count"), focal=(fm, "mean"), comp=(cm, "mean"))
    res.frames["allp"] = allp
    res.frames["single"] = single

    from .insights import build_insight_log  # local import avoids a circular import
    res.insight_log = build_insight_log(cfg, res)
    if logger:
        logger.info(f"analysis: H1 p={p1:.4g}, primary n={len(primary)}, insight log rows={len(res.insight_log)}")
    return res


def _with_ci(g: pd.DataFrame) -> pd.DataFrame:
    from .stats import wilson
    ci = g.apply(lambda r: wilson(int(r["sum"]), int(r["count"])), axis=1)
    g = g.copy()
    g["lo"] = [x[0] for x in ci]
    g["hi"] = [x[1] for x in ci]
    return g
