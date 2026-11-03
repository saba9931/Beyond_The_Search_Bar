"""Step 3 (data preparation): simple, checkable features from the raw answers.

No AI model is used here. Plain text rules (regular expressions) so anyone can read and test them.
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

_URL = re.compile(r"https?://(?:www\.)?([^/\s,;]+)")


def domains(urls) -> set[str]:
    """Set of website names found in a block of text that contains links."""
    if urls is None or (isinstance(urls, float) and np.isnan(urls)) or pd.isna(urls):
        return set()
    return {d.lower() for d in _URL.findall(str(urls))}


def add_features(df: pd.DataFrame, cfg) -> pd.DataFrame:
    """Add, for every entity: <e>_mention (name in text), <e>_cited (link to its site), first_pos_<e> (0=start, 1=end)."""
    c, ents = cfg["columns"], cfg["entities"]
    d = df.copy()
    d["text"] = d[c["text"]].fillna("").str.lower()
    d["words"] = d["text"].str.split().str.len()
    d["domains"] = d[c["urls"]].apply(domains)
    d["n_domains"] = d["domains"].str.len()
    for name, e in ents.items():
        pat = re.compile(e["pattern"])
        d[f"{name}_mention"] = d["text"].apply(lambda t, p=pat: bool(p.search(t)))
        d[f"{name}_cited"] = d["domains"].apply(lambda s, k=e["domain"]: any(k in x for x in s))
        d[f"first_pos_{name}"] = d["text"].apply(lambda t, p=pat: (m.start() / max(len(t), 1)) if (m := p.search(t)) else np.nan)
    d["any_retailer_mention"] = d[[f"{n}_mention" for n in ents]].any(axis=1)
    return d
