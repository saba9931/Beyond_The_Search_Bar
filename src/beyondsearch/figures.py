"""Figures. Each function takes the analysis result and returns a matplotlib Figure (so it works in a notebook and in the CLI)."""
from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

PINK, GREY, BLUE = "#c2185b", "#9aa5b1", "#4a6fa5"
plt.rcParams.update({"figure.dpi": 110, "axes.spines.top": False, "axes.spines.right": False})


def _rate_bars(g, by, title, ylabel):
    fig, ax = plt.subplots(figsize=(6.5, 3.2))
    ax.bar(g[by].astype(str), g["rate"], color=PINK, yerr=[g["rate"] - g["lo"], g["hi"] - g["rate"]], capsize=4)
    ax.set_ylim(0, 1)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    plt.xticks(rotation=20)
    return fig


def fig01_planned_vs_collected(res, cfg):
    fig, ax = plt.subplots(figsize=(6, 3.2))
    res.tables["planned_vs_collected"].plot.bar(ax=ax, color=[GREY, PINK], rot=0)
    ax.set_ylabel("share of runs")
    ax.set_title("Figure 1. Planned vs collected share of runs by engine")
    return fig


def fig02_length_and_sources(res, cfg):
    eng = cfg.col("engine")
    v = res.frames["valid"]
    fig, ax = plt.subplots(1, 2, figsize=(10, 3.3))
    v.boxplot(column="words", by=eng, ax=ax[0], grid=False)
    ax[0].set_title("Answer length"); ax[0].set_ylabel("words"); ax[0].set_xlabel("")
    v.boxplot(column="n_domains", by=eng, ax=ax[1], grid=False)
    ax[1].set_title("Distinct source websites per answer"); ax[1].set_xlabel("")
    plt.suptitle("Figure 2. Answer length and number of cited sites, by engine")
    plt.tight_layout()
    return fig


def fig03_retailers_named(res, cfg):
    t = res.tables["retailer_share"]
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.barh(t["entity"], t["share"], color=PINK)
    ax.set_xlabel("share of unbranded answers")
    ax.set_title("Figure 3. Which retailers do AI answers name?")
    return fig


def fig04_h1(res, cfg):
    return _rate_bars(res.tables["H1_rates"], "retailer", "Figure 4. H1: share of unbranded answers naming each retailer (95% CI)", "share of answers")


def fig05_h2(res, cfg):
    return _rate_bars(res.tables["H2_rates"], "question_type", f"Figure 5. H2: {cfg.short(cfg.focal)} mention rate by question type (95% CI)", f"share naming {cfg.short(cfg.focal)}")


def fig06_h3(res, cfg):
    return _rate_bars(res.tables["H3_rates"], cfg.col("engine"), f"Figure 6. H3: {cfg.short(cfg.focal)} mention rate by engine (95% CI)", f"share naming {cfg.short(cfg.focal)}")


def fig07_h4(res, cfg):
    return _rate_bars(res.tables["H4_rates"], cfg.col("category"), f"Figure 7. H4: {cfg.short(cfg.focal)} mention rate by category (95% CI)", f"share naming {cfg.short(cfg.focal)}")


def fig08_h6(res, cfg):
    rep = res.frames["repeats"]
    if not len(rep):
        return None
    ax = rep.boxplot(column="jaccard", by=cfg.col("engine"), grid=False, figsize=(5.5, 3.2))
    plt.suptitle("")
    plt.title("Figure 8. H6: overlap of cited sites across repeat runs (1 = identical)")
    plt.ylabel("Jaccard overlap")
    return ax.figure


def fig09_by_engine(res, cfg):
    t = res.tables["robust_by_engine"].rename(columns={"focal": cfg.short(cfg.focal), "comp": cfg.short(cfg.comparator)})
    ax = t[[cfg.short(cfg.focal), cfg.short(cfg.comparator)]].plot.bar(figsize=(7, 3.2), color=[PINK, BLUE], rot=0)
    ax.set_ylim(0, 1)
    ax.set_ylabel("share of unbranded answers naming the retailer")
    ax.set_title("Figure 9. Retailer mention rate by engine, all genuine answers")
    return ax.figure


FIGURES = [fig01_planned_vs_collected, fig02_length_and_sources, fig03_retailers_named, fig04_h1, fig05_h2,
           fig06_h3, fig07_h4, fig08_h6, fig09_by_engine]


def save_all(res, cfg, out_dir: Path) -> list[Path]:
    """Save every figure as figNN.png. Returns the files written."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for n, fn in enumerate(FIGURES, 1):
        fig = fn(res, cfg)
        if fig is None:
            continue
        path = out_dir / f"fig{n:02d}.png"
        fig.savefig(path, dpi=130, bbox_inches="tight")
        plt.close(fig)
        written.append(path)
    return written
