"""
plot_figure_9.py — fully self-contained slide/paper plotter for figure 9
(varying size ratio).

All plot functions live here.  Changes to axes, ticks, colors, output paths,
or which approaches appear are local to this file and never affect any other
script or the shared plotter/ module.
"""

import os
from pathlib import Path
from typing import Dict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.font_manager as font_manager
import numpy as np
import pandas as pd

from plotter.epochstats import EpochStats
from plotter.plotstyles import line_styles_with_abbr
from plotter.dataclass import RQColumn, PlottingStats

FONT_PROP = font_manager.FontProperties(fname="./plotter/LinLibertine_Mah.ttf")
plt.rcParams.update(
    {
        "font.family": FONT_PROP.get_name(),
        "text.usetex": True,
        "font.weight": "bold",
        "font.size": 22,
    }
)


INSERTS = 8388608
UPDATES = 8388608
RANGE_QUERIES = 9000
ENTRY_SIZE = 128
NUM_PAGE_PER_FILE = 1024
ENTRIES_PER_PAGE = 32
SELECTIVITY = 0.1

# ===================================================================
# SLIDE CONFIG — comment out any approach, size ratio, or plot
# ===================================================================

# Each row: (line_styles/bar_styles key, directory name, bar label).
# Comment out a row to drop that approach from every figure.
APPROACHES = [
    # (style key,                        dir name,                        abr  )
    ("RocksDB",                          "RocksDB",                       "RDB"),
    ("SuccinctKV",                       "SuccinctKV",                    "SKV"),
    # ("RangeReduce[lb=T^-1]",           "RangeReduce[lb=T^-1]",          "BM" ),
    ("RangeReduce[lb=T^-1 & re=1]",      "RangeReduce[lb=T^-1ANDre=1]",  "RR" ),
]

# Comment out any size ratio to hide that group from every figure.
SIZE_RATIOS = [
    2,
    4,
    6,
    8,
    10,
]

# Comment out any plot you don't want generated for this slide set.
ACTIVE_PLOTS = [
    "compaction",
    "range_query",
    "space_amplification",
    "rq_latency",
]

# ===================================================================
# Paths & constants
# ===================================================================

PROJECT_DIR = Path.cwd().parent.parent
TAG         = "diff_size_ratio_exp-1x"

OUTPUT_DIR = f"Figures/Fig9"
os.makedirs(OUTPUT_DIR, exist_ok=True)

FILE_SIZE = ENTRY_SIZE * ENTRIES_PER_PAGE * NUM_PAGE_PER_FILE

# ===================================================================
# Build active sets (do not edit below)
# ===================================================================

APPROACH_KEYS = [key for key, _,   _   in APPROACHES]
APPROACH_DIR  = {key: d   for key, d,   _ in APPROACHES}
APPROACH_ABR  = {key: abr for key, _,   abr in APPROACHES}
_n_approaches = len(APPROACH_KEYS)

SIZE_RATIOS = sorted(SIZE_RATIOS)
_n_srs      = len(SIZE_RATIOS)

# Figure widths scale with number of active size ratios.
# Reference: 5.0 in wide for 5 size ratios.
_FIG_W_PER_SR = 5.0 / 5
FIG_W         = _n_srs * _FIG_W_PER_SR
FIG_SIZE_BAR  = (FIG_W, 3.0)
FIG_SIZE_LINE = (FIG_W - 0.16, 3.0)

BAR_WIDTH = 0.2
# x-offsets for each approach bar, centred around each group tick
_offsets = [(i - (_n_approaches - 1) / 2) * BAR_WIDTH
            for i in range(_n_approaches)]

# ===================================================================
# Data loading
# ===================================================================

# ps[size_ratio][approach_key]  = PlottingStats (last epoch)
# rq[size_ratio][approach_key]  = pd.DataFrame
ps: Dict[int, Dict[str, PlottingStats]] = {}
rq: Dict[int, Dict[str, pd.DataFrame]]  = {}

for sr in SIZE_RATIOS:
    ps[sr] = {}
    rq[sr] = {}

    exp_dir = (
        f"{PROJECT_DIR}/logs/experiments-{TAG}"
        f"-U{UPDATES}-E{ENTRY_SIZE}-B{ENTRIES_PER_PAGE}"
        f"-S{RANGE_QUERIES}-Y{SELECTIVITY}-T{sr}"
    )

    loaded: Dict[str, EpochStats] = {}
    for key in APPROACH_KEYS:
        path = os.path.join(exp_dir, APPROACH_DIR[key])
        loaded[key] = EpochStats(path, FILE_SIZE)

    # Shared max-level scaling across approaches for this size ratio.
    max_lvls_per_db    = [s.get_max_levels() for s in loaded.values()]
    max_epoch_len      = max(len(lvls) for lvls in max_lvls_per_db)
    max_lvls_per_epoch = [0] * max_epoch_len
    for lvls in max_lvls_per_db:
        for i, lvl in enumerate(lvls):
            max_lvls_per_epoch[i] = max(max_lvls_per_epoch[i], lvl)

    for key, stats in loaded.items():
        ps[sr][key] = stats.get_plotstats(max_lvls_per_epoch)[-1]
        rq[sr][key] = stats.get_rangequerystats()

# ===================================================================
# Local helpers
# ===================================================================

def _save_close(fig, filename: str):
    fig.savefig(
        os.path.join(OUTPUT_DIR, filename),
        bbox_inches="tight",
        pad_inches=0.06,
    )
    plt.close(fig)


def _x_ticks():
    xs     = np.arange(_n_srs)
    labels = [str(sr) for sr in SIZE_RATIOS]
    return xs, labels

# ===================================================================
# Plot functions
# ===================================================================

def plot_compaction():
    """Stacked bar: compaction read + write per approach, grouped by size ratio."""
    convert = 1024 ** 4  # bytes → TB
    fig, ax = plt.subplots(figsize=FIG_SIZE_BAR)
    xs, xlabels = _x_ticks()

    read_patch  = mpatches.Patch(facecolor="None", edgecolor="tab:blue",
                                 hatch="\\\\\\", linewidth=0.5, label="read")
    write_patch = mpatches.Patch(facecolor="None", edgecolor="tab:red",
                                 hatch="///",     linewidth=0.5, label="write")

    for i, key in enumerate(APPROACH_KEYS):
        reads  = [ps[sr][key].CompactionReadBytes    for sr in SIZE_RATIOS]
        writes = [ps[sr][key].CompactionWrittenBytes for sr in SIZE_RATIOS]
        xpos   = [x + _offsets[i] for x in xs]

        ax.bar(xpos, reads,  width=BAR_WIDTH,
               color="None", edgecolor="tab:blue", linewidth=0.5, hatch="\\\\\\")
        ax.bar(xpos, writes, width=BAR_WIDTH, bottom=reads,
               color="None", edgecolor="tab:red",  linewidth=0.5, hatch="///")

        for j, x in enumerate(xs):
            total = reads[j] + writes[j]
            ax.text(x + _offsets[i] + BAR_WIDTH * 0.1, total * 1.015,
                    APPROACH_ABR[key],
                    ha="center", va="bottom", fontsize=11.5, rotation=90)

    desired_yticks = [0, 0.05, 0.1, 0.15]
    ax.set_yticks([v * convert for v in desired_yticks])
    ax.set_yticklabels(["0"] + [f"{v:.2f}" for v in desired_yticks[1:]])
    ax.set_ylabel("comp. work (TB)")
    ax.set_ylim(bottom=0)
    ax.set_xticks(xs)
    ax.set_xticklabels(xlabels)
    ax.set_xlabel("size ratio")
    ax.legend(handles=[read_patch, write_patch], loc="upper right",
              frameon=False, ncol=1, fontsize=16)

    _save_close(fig, f"{TAG}-compaction_data_movement.pdf")


def plot_range_query():
    """Stacked bar: RQ read + RQ write per approach, grouped by size ratio."""
    convert = 1024 ** 4
    fig, ax = plt.subplots(figsize=FIG_SIZE_BAR)
    xs, xlabels = _x_ticks()

    ideal_val = INSERTS * ENTRY_SIZE * SELECTIVITY * RANGE_QUERIES

    read_patch  = mpatches.Patch(facecolor="None", edgecolor="tab:blue",
                                 hatch="\\\\\\", linewidth=0.3, label="read")
    write_patch = mpatches.Patch(facecolor="None", edgecolor="tab:red",
                                 hatch="///",     linewidth=0.3, label="write")

    for i, key in enumerate(APPROACH_KEYS):
        reads  = [rq[sr][key][str(RQColumn.TOTAL_ENTRIES_READ)].sum() * ENTRY_SIZE
                  for sr in SIZE_RATIOS]
        writes = [ps[sr][key].RangeReduceWrittenBytes for sr in SIZE_RATIOS]
        xpos   = [x + _offsets[i] for x in xs]

        ax.bar(xpos, reads,  width=BAR_WIDTH,
               color="None", edgecolor="tab:blue", linewidth=0.3, hatch="\\\\\\")
        ax.bar(xpos, writes, width=BAR_WIDTH, bottom=reads,
               color="None", edgecolor="tab:red",  linewidth=0.3, hatch="///")

        for j, x in enumerate(xs):
            total = reads[j] + writes[j]
            ax.text(x + _offsets[i] + BAR_WIDTH * 0.05, total * 1.01,
                    APPROACH_ABR[key],
                    ha="center", va="bottom", fontsize=12, rotation=90)

    ax.axhline(y=ideal_val, color="black", linestyle="-.", linewidth=1)

    desired_yticks = [0, 0.5, 1.0, 1.5]
    ax.set_yticks([v * convert for v in desired_yticks])
    ax.set_yticklabels(["0"] + [f"{v:.1f}" for v in desired_yticks[1:]])
    ax.set_ylabel("RQ work (TB)")
    ax.set_ylim(bottom=0)
    ax.set_xticks(xs)
    ax.set_xticklabels(xlabels)
    ax.set_xlabel("size ratio")
    # ax.legend(handles=[read_patch, write_patch], loc="upper right",
    #           frameon=False, ncol=1, fontsize=16)

    _save_close(fig, f"{TAG}-rangequery_data_movement.pdf")


def plot_space_amplification():
    fig, ax = plt.subplots(figsize=FIG_SIZE_LINE)
    xs, xlabels = _x_ticks()

    for key in APPROACH_KEYS:
        y = [ps[sr][key].DBSize / (INSERTS * ENTRY_SIZE) for sr in SIZE_RATIOS]
        ax.plot(xs, y, **line_styles_with_abbr[key])

    ax.set_ylabel("space amplification")
    ax.set_xlabel("size ratio")
    ax.set_ylim(bottom=0, top=2)
    ax.set_yticks([0, 0.5, 1.0, 1.5, 2.0])
    ax.set_yticklabels(["0", "0.5", "1.0", "1.5", "2.0"])
    ax.set_xticks(xs)
    ax.set_xticklabels(xlabels)

    _save_close(fig, f"{TAG}-size-ratio-space_amplification.pdf")


def plot_rq_latency():
    convert = 10 ** 9  # ns → s
    fig, ax = plt.subplots(figsize=FIG_SIZE_LINE)
    xs, xlabels = _x_ticks()

    for key in APPROACH_KEYS:
        y = [rq[sr][key][str(RQColumn.RQ_TOTAL_TIME)].astype(float).mean()
             for sr in SIZE_RATIOS]
        ax.plot(xs, y, **line_styles_with_abbr[key])

    desired_yticks = [0, 0.5, 1.0, 1.5]
    ax.set_yticks([v * convert for v in desired_yticks])
    ax.set_yticklabels(["0"] + [str(v) for v in desired_yticks[1:]])
    ax.set_ylabel("avg. RQ latency (s)")
    ax.set_xlabel("size ratio")
    ax.set_ylim(bottom=0)
    ax.set_xticks(xs)
    ax.set_xticklabels(xlabels)
    ax.legend(loc="lower center", frameon=False, ncol=1,
              fontsize=20, handlelength=1, handleheight=1,
              handletextpad=0.2, labelspacing=0.1, columnspacing=0.1)

    _save_close(fig, f"{TAG}-size-ratio-range_query_latency.pdf")

# ===================================================================
# Dispatch
# ===================================================================

active = set(ACTIVE_PLOTS)

if "compaction"          in active: plot_compaction()
if "range_query"         in active: plot_range_query()
if "space_amplification" in active: plot_space_amplification()
if "rq_latency"          in active: plot_rq_latency()
