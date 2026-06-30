"""
plot_figure_4.py — fully self-contained slide/paper plotter for figure 4.

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
import matplotlib.font_manager as font_manager
import numpy as np

from plotter import SIZE_RATIO

from plotter.epochstats import EpochStats
from plotter.plotstyles import bar_styles
from plotter.dataclass import RQColumn

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

# ===================================================================
# SLIDE CONFIG — comment out any approach, selectivity, or plot
# ===================================================================

# Each row: (display name for bar_styles key, legend label, abbreviation).
# Comment out a row to drop that bar from every figure.
APPROACHES = [
    # (bar_styles key,                 abbr            )
    ("RocksDB",                        "RDB"           ),
    ("RangeReduce[lb=0 & smlck=0]",    "MoS"           ),
    ("RangeReduce[lb=0]",              "FSMoS"         ),
]

# Map each approach's bar_styles key to its experiment directory name.
APPROACH_DIR = {
    "RocksDB":                      "RocksDB",
    "RangeReduce[lb=0 & smlck=0]":  "RangeReduce[lb=0ANDsmlck=0]",
    "RangeReduce[lb=0]":            "RangeReduce[lb=0]",
}

# Comment out any selectivity to hide that group from every figure.
SELECTIVITIES = [
    0.00001,
    0.0001,
    0.001,
    0.003,
    0.007,
    # 0.005,
    # 0.0025,
    0.01,
]

# Label shown on the x-axis for each selectivity value.
SELECTIVITY_LABELS: Dict[float, str] = {
    0.00001: "0.00001",
    0.0001:  "0.0001",
    0.01:   "0.01",
    0.001:  "0.001",
    0.0025: "0.0025",
    0.003:  "0.003",
    0.005:  "0.005",
    0.007:  "0.007",
}

# Comment out any plot you don't want generated for this slide set.
ACTIVE_PLOTS = [
    "avg_file_sizes",
    "files_count",
    "avg_read_amp",
]

# ===================================================================
# Paths & constants
# ===================================================================

PROJECT_DIR = Path.cwd().parent.parent
TAG         = "newfigure4"

OUTPUT_DIR = f"Figures/Fig4"   # figures for THIS script go here — edit freely
os.makedirs(OUTPUT_DIR, exist_ok=True)

FILE_SIZE = ENTRY_SIZE * ENTRIES_PER_PAGE * NUM_PAGE_PER_FILE
EPOCH_TO_PLOT = -1

BAR_WIDTH = 0.25

# Figure width scales with number of active selectivities so bars keep
# the same physical width regardless of how many groups are shown.
# Reference: 4.4 in wide for 6 selectivities.
_FIG_W_PER_SEL = 4.4 / 6

# ===================================================================
# Build active sets (do not edit below)
# ===================================================================

APPROACH_KEYS = [key  for key, _    in APPROACHES]
ABBREVIATIONS = [abbr for _,   abbr in APPROACHES]
_n_approaches = len(APPROACH_KEYS)

SELECTIVITIES = sorted(SELECTIVITIES)   # always ascending regardless of list order above
_n_sels       = len(SELECTIVITIES)

FIG_SIZE = (_n_sels * _FIG_W_PER_SEL, 3.0)

# Bar x-offsets centred around each group tick.
_offsets = [(i - (_n_approaches - 1) / 2) * BAR_WIDTH
            for i in range(_n_approaches)]

# ===================================================================
# Data loading
# ===================================================================

# avg_file_size_mb[sel][approach_key]  = float (MB)
# files_count[sel][approach_key]       = int
# avg_bytes_per_rq[sel][approach_key]  = float (bytes)

avg_file_size_mb: Dict[float, Dict[str, float]] = {}
files_count:      Dict[float, Dict[str, float]] = {}
avg_bytes_per_rq: Dict[float, Dict[str, float]] = {}

for sel in SELECTIVITIES:
    avg_file_size_mb[sel] = {}
    files_count[sel]      = {}
    avg_bytes_per_rq[sel] = {}

    exp_dir = (
        f"{PROJECT_DIR}/logs/experiments-{TAG}"
        f"-U{UPDATES}-E{ENTRY_SIZE}-B{ENTRIES_PER_PAGE}"
        f"-S{RANGE_QUERIES}-Y{"0.00001" if sel == 0.00001 else str(sel)}-T{SIZE_RATIO}"
    )

    # Load each approach and compute per-selectivity stats.
    loaded: Dict[str, EpochStats] = {}
    for key in APPROACH_KEYS:
        path = os.path.join(exp_dir, APPROACH_DIR[key])
        loaded[key] = EpochStats(path, FILE_SIZE)

    # Shared y-axis level scaling across approaches for this selectivity.
    max_lvls_per_db  = [s.get_max_levels() for s in loaded.values()]
    max_epoch_len    = max(len(lvls) for lvls in max_lvls_per_db)
    max_lvls_per_epoch = [0] * max_epoch_len
    for lvls in max_lvls_per_db:
        for i, lvl in enumerate(lvls):
            max_lvls_per_epoch[i] = max(max_lvls_per_epoch[i], lvl)

    for key, stats in loaded.items():
        ps   = stats.get_plotstats(max_lvls_per_epoch)[EPOCH_TO_PLOT]
        rq   = stats.get_rangequerystats()

        avg_file_size_mb[sel][key] = (
            ps.DBSize / max(ps.FilesCount, 1) / (1024 ** 2)
        )
        files_count[sel][key] = ps.FilesCount
        avg_bytes_per_rq[sel][key] = (
            rq[str(RQColumn.TOTAL_ENTRIES_READ)].astype(float).mean()
            * ENTRY_SIZE
        )

# ===================================================================
# Local helpers
# ===================================================================

def _save(filename: str):
    plt.savefig(
        os.path.join(OUTPUT_DIR, filename),
        bbox_inches="tight",
        pad_inches=0.06,
    )


def _save_close(fig, filename: str):
    fig.savefig(
        os.path.join(OUTPUT_DIR, filename),
        bbox_inches="tight",
        pad_inches=0.06,
    )
    plt.close(fig)


def _x_ticks():
    """Return (x positions, labels) for the active selectivities."""
    xs     = np.arange(_n_sels)
    labels = [SELECTIVITY_LABELS.get(s, str(s)) for s in SELECTIVITIES]
    return xs, labels

# ===================================================================
# Plot functions
# ===================================================================

def plot_avg_file_sizes():
    xs, xlabels = _x_ticks()
    fig, ax = plt.subplots(figsize=FIG_SIZE)

    for i, key in enumerate(APPROACH_KEYS):
        vals = [avg_file_size_mb[sel][key] for sel in SELECTIVITIES]
        ax.bar(xs + _offsets[i], vals, BAR_WIDTH, **bar_styles[key])

    ax.set_ylabel("avg. file size (MB)")
    ax.set_xlabel(r"selectivity (\%)")
    ax.yaxis.set_label_coords(-0.09, 0.31)
    ax.set_ylim(bottom=0, top=4.4)
    ax.set_yticks([0, 2, 4])
    ax.set_yticklabels(["0", "2", "4"])
    ax.set_xticks(xs)
    ax.set_xticklabels(xlabels, rotation=90)

    _save("avg-files-size.pdf")
    plt.close(fig)


def plot_files_count():
    xs, xlabels = _x_ticks()
    fig, ax = plt.subplots(figsize=FIG_SIZE)

    for i, key in enumerate(APPROACH_KEYS):
        vals = [files_count[sel][key] for sel in SELECTIVITIES]
        ax.bar(xs + _offsets[i], vals, BAR_WIDTH, **bar_styles[key])

    ax.set_ylabel("file count")
    ax.set_xlabel(r"selectivity (\%)")
    ax.set_ylim(bottom=0)
    ax.set_xticks(xs)
    ax.set_xticklabels(xlabels, rotation=90)

    yticks = ax.get_yticks()
    ax.set_yticks(yticks[:3])
    ax.set_yticklabels(["0"] + [f"{t/1000:.1f}" for t in yticks[1:3]])

    handles, labels = ax.get_legend_handles_labels()
    _save("avg-files-count.pdf")
    plt.close(fig)

    leg = plt.figure(figsize=(3.8, 0.4))
    leg.legend(handles, labels, loc="center", ncol=_n_approaches,
               frameon=False, columnspacing=1.2, handletextpad=0.4,
               borderaxespad=0)
    leg.subplots_adjust(left=0, right=1, top=1, bottom=0)
    _save_close(leg, "legend.pdf")


def plot_avg_read_amp():
    xs, xlabels = _x_ticks()
    fig, ax = plt.subplots(figsize=FIG_SIZE)

    for i, key in enumerate(APPROACH_KEYS):
        vals = [
            avg_bytes_per_rq[sel][key] / (UPDATES * ENTRY_SIZE * float(sel))
            for sel in SELECTIVITIES
        ]
        ax.bar(xs + _offsets[i], vals, BAR_WIDTH, **bar_styles[key])

    ax.set_ylabel("RQ avg. read amp.")
    ax.set_xlabel(r"selectivity (\%)")
    ax.yaxis.set_label_coords(-0.15, 0.29)
    ax.set_yticks([0, 0.5, 1.0])
    ax.set_yticklabels(["0", "0.5", "1.0"])

    all_vals = [
        avg_bytes_per_rq[sel][key] / (UPDATES * ENTRY_SIZE * float(sel))
        for sel in SELECTIVITIES
        for key in APPROACH_KEYS
    ]
    ax.set_ylim(bottom=0, top=max(all_vals) * 1.2)
    ax.set_xticks(xs)
    ax.set_xticklabels(xlabels, rotation=90)

    _save("avg-bytes-read-per-rq.pdf")
    plt.close(fig)

# ===================================================================
# Dispatch
# ===================================================================

active = set(ACTIVE_PLOTS)

if "avg_file_sizes" in active: plot_avg_file_sizes()
if "files_count"    in active: plot_files_count()
if "avg_read_amp"   in active: plot_avg_read_amp()
