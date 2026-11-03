import numpy as np
import pandas as pd

from beyondsearch.stats import chi_test, fisher_test, mcnemar_test, mean_jaccard, rate_table, wilson


def test_wilson_known_value():
    lo, hi = wilson(50, 100)
    assert round(lo, 3) == 0.404 and round(hi, 3) == 0.596


def test_wilson_empty_is_nan():
    assert all(np.isnan(x) for x in wilson(0, 0))


def test_rate_table():
    d = pd.DataFrame({"g": ["a", "a", "b", "b"], "flag": [True, False, True, True]})
    t = rate_table(d, "g", "flag").set_index("g")
    assert t.loc["a", "rate"] == 0.5 and t.loc["b", "rate"] == 1.0 and t.loc["a", "count"] == 2
    assert (t["lo"] <= t["rate"]).all() and (t["rate"] <= t["hi"]).all()


def test_mcnemar_equal_disagreements_gives_p_one():
    a = pd.Series([True, False, True, False])
    b = pd.Series([False, True, True, False])      # one disagreement each way
    p, table = mcnemar_test(a, b)
    assert p == 1.0 and table.shape == (2, 2)


def test_mcnemar_keeps_2x2_when_a_value_is_missing():
    p, table = mcnemar_test(pd.Series([True, True]), pd.Series([True, True]))
    assert table.shape == (2, 2)


def test_chi_and_fisher_return_none_when_too_small():
    d = pd.DataFrame({"g": ["a", "a"], "flag": [True, True]})
    assert chi_test(d, "g", "flag") is None and fisher_test(d, "g", "flag") is None


def test_fisher_detects_strong_difference():
    d = pd.DataFrame({"g": ["a"] * 20 + ["b"] * 20, "flag": [True] * 18 + [False] * 2 + [False] * 18 + [True] * 2})
    _, p = fisher_test(d, "g", "flag")
    assert p < 0.001


def test_mean_jaccard():
    assert mean_jaccard([{"x"}, {"x"}]) == 1.0
    assert mean_jaccard([{"x"}, {"y"}]) == 0.0
    assert np.isnan(mean_jaccard([{"x"}]))
    assert np.isnan(mean_jaccard([set(), set()]))
