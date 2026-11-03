import pandas as pd

from beyondsearch.features import add_features, domains


def test_domains_extracts_hosts():
    urls = "https://www.nykaa.com/p/1, http://tirabeauty.com/x; https://example.org"
    assert domains(urls) == {"nykaa.com", "tirabeauty.com", "example.org"}


def test_domains_handles_missing():
    assert domains(None) == set() and domains(float("nan")) == set() and domains("") == set()


def _frame(cfg, text, urls=None):
    c = cfg["columns"]
    return pd.DataFrame({c["text"]: [text], c["urls"]: [urls]})


def test_mentions_are_found_case_insensitively(cfg):
    d = add_features(_frame(cfg, "Buy it at SEPHORA or Nykaa"), cfg)
    assert d["sephora_mention"].iloc[0] and d["nykaa_mention"].iloc[0] and not d["tira_mention"].iloc[0]


def test_tira_needs_a_whole_word(cfg):
    assert not add_features(_frame(cfg, "a long tirade about sunscreen"), cfg)["tira_mention"].iloc[0]
    assert add_features(_frame(cfg, "try Tira for makeup"), cfg)["tira_mention"].iloc[0]


def test_citation_means_a_link_to_the_retailer_site(cfg):
    d = add_features(_frame(cfg, "text", "https://www.sephora.in/product"), cfg)
    assert d["sephora_cited"].iloc[0] and not d["nykaa_cited"].iloc[0]


def test_position_is_between_zero_and_one(cfg):
    d = add_features(_frame(cfg, "nykaa is first and sephora is last"), cfg)
    assert d["first_pos_nykaa"].iloc[0] == 0.0 and 0 < d["first_pos_sephora"].iloc[0] < 1


def test_input_frame_is_not_modified(cfg):
    df = _frame(cfg, "nykaa")
    before = df.copy()
    add_features(df, cfg)
    pd.testing.assert_frame_equal(df, before)
