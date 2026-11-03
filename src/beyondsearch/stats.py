"""Small, tested statistical helpers. Nothing here knows about beauty, retailers or this project."""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import chi2_contingency, fisher_exact
from statsmodels.stats.contingency_tables import mcnemar
from statsmodels.stats.proportion import proportion_confint


def wilson(k: int, n: int) -> tuple[float, float]:
    """95% Wilson confidence interval for a share k/n."""
    if not n:
        return (np.nan, np.nan)
    lo, hi = proportion_confint(k, n, method="wilson")
    return (float(lo), float(hi))


def rate_table(d: pd.DataFrame, by: str, flag: str) -> pd.DataFrame:
    """Share of rows where `flag` is true, per group, with Wilson interval."""
    g = d.groupby(by)[flag].agg(["sum", "count"]).reset_index()
    g["rate"] = g["sum"] / g["count"]
    ci = g.apply(lambda r: wilson(int(r["sum"]), int(r["count"])), axis=1)
    g["lo"] = [x[0] for x in ci]
    g["hi"] = [x[1] for x in ci]
    return g


def chi_test(d: pd.DataFrame, by: str, flag: str):
    """Chi-square test of independence. Returns (chi2, p, dof) or None if the table is too small."""
    tab = pd.crosstab(d[by], d[flag])
    if tab.shape[0] < 2 or tab.shape[1] < 2:
        return None
    chi2, p, dof, _ = chi2_contingency(tab)
    return float(chi2), float(p), int(dof)


def fisher_test(d: pd.DataFrame, by: str, flag: str):
    """Fisher exact test on a 2x2 table. Returns (odds_ratio, p) or None."""
    t = pd.crosstab(d[by], d[flag]).reindex(columns=[False, True], fill_value=0)
    if t.shape != (2, 2):
        return None
    odds, p = fisher_exact(t.values)
    return float(odds), float(p)


def mcnemar_test(a: pd.Series, b: pd.Series):
    """Exact paired test: do two yes/no flags on the SAME rows differ? Returns (pvalue, 2x2 table)."""
    t = pd.crosstab(a, b).reindex(index=[False, True], columns=[False, True], fill_value=0)
    return float(mcnemar(t.values, exact=True).pvalue), t


def mean_jaccard(sets: list[set]) -> float:
    """Average overlap (0 to 1) between every pair of sets. 1 = identical."""
    if len(sets) < 2:
        return np.nan
    vals = []
    for i in range(len(sets)):
        for j in range(i + 1, len(sets)):
            u = sets[i] | sets[j]
            vals.append(len(sets[i] & sets[j]) / len(u) if u else np.nan)
    finite = [v for v in vals if not np.isnan(v)]
    return float(np.mean(finite)) if finite else np.nan   # no warning when every pair is empty
