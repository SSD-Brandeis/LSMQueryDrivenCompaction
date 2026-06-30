"""
plot_figure_5.py — fully self-contained slide/paper plotter for figure 5.

All plot functions live here.  Changes to axes, ticks, colors, output paths,
or which approaches appear are local to this file and never affect any other
script or the shared plotter/ module.
"""

import os
from pathlib import Path
from typing import Dict

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import matplotlib.font_manager as font_manager
import numpy as np
import pandas as pd

from plotter import SIZE_RATIO
from plotter.epochstats import EpochStats
from plotter.plotstyles import (
    bar_styles,
    line_styles_no_marker,
    line_styles_no_marker_with_abbr,
)
from plotter.dataclass import RQColumn

matplotlib.use("Agg")

FONT_PROP = font_manager.FontProperties(fname="./plotter/LinLibertine_Mah.ttf")
plt.rcParams.update(
    {
        "font.family": FONT_PROP.get_name(),
        "text.usetex": True,
        "font.weight": "bold",
        "font.size": 24,
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
# SLIDE CONFIG — comment out any approach or plot to hide it
# ===================================================================

# Each row: (display name, directory name, abbreviation).
# Comment out a row to drop that bar/line from every figure.
APPROACHES = [
    # (display name,                  dir name,                       abbr  )
    ("RocksDB",                       "RocksDB",                      "RDB" ),
    ("SuccinctKV",                    "SuccinctKV",                   "SKV" ),
    ("RangeReduce[lb=0 & smlck=0]",   "RangeReduce[lb=0ANDsmlck=0]", "MoS" ),
    ("RangeReduce[lb=0]",             "RangeReduce[lb=0]",            "FSMoS"),
    ("RangeReduce[lb=T^-1]",          "RangeReduce[lb=T^-1]",        "BM"  ),
]

# Comment out any plot you don't want generated for this slide set.
ACTIVE_PLOTS = [
    # "bytes_read_per_rq",
    "bytes_read_per_rq_rolling",
    # "bytes_read_cdf",
    # "latency_per_rq",
    "latency_per_rq_rolling",
    # "latency_cdf",
    # "did_rq_run",
    "total_bytes_written",
    # "total_rq_bytes_written",
    "compaction_debt",
    "space_amplification",
    "total_data_movement",
]

# ===================================================================
# Paths & constants
# ===================================================================

PROJECT_DIR = Path.cwd().parent.parent
TAG         = "rerunning-fig9-1x"

OUTPUT_DIR = f"Figures/Fig5"   # figures for THIS script go here — edit freely
os.makedirs(OUTPUT_DIR, exist_ok=True)

EXPERIMENT_DIR = (
    f"{PROJECT_DIR}/logs/experiments-{TAG}"
    f"-U{UPDATES}-E{ENTRY_SIZE}"
    f"-B{ENTRIES_PER_PAGE}-P{NUM_PAGE_PER_FILE}"
    f"-S{RANGE_QUERIES}-Y{SELECTIVITY}-T{SIZE_RATIO}"
)

FILE_SIZE    = ENTRY_SIZE * ENTRIES_PER_PAGE * NUM_PAGE_PER_FILE
EPOCH_TO_PLOT = -1

BAR_WIDTH   = 0.55
FIG_LINE    = (4.2, 3.0)   # time-series / CDF figures

# Bar-chart figure widths scale with the number of active approaches so
# that each bar stays the same physical width regardless of how many are shown.
# These reference widths are calibrated for 5 approaches.
_N_REF          = len(APPROACHES)
_BAR_W_PER_APP  = 2 / _N_REF   # ~0.24 in per bar (compact bar figures)
_BAR_RQ_W_PER_APP = 2.0 / _N_REF # ~0.40 in per bar (did-rq-run figure)

# ===================================================================
# Build active sets from APPROACHES config (do not edit below)
# ===================================================================

DISPLAY_NAMES = [name for name, _, _    in APPROACHES]
DIR_NAMES     = [d    for _, d,    _    in APPROACHES]
ABBREVIATIONS = [abbr for _, _,    abbr in APPROACHES]

_n = len(DISPLAY_NAMES)
FIG_BAR    = (_n * _BAR_W_PER_APP,    2.5)
FIG_BAR_RQ = (_n * _BAR_RQ_W_PER_APP, 3.0)

DB_DIRS = {
    name: os.path.join(EXPERIMENT_DIR, d)
    for name, d, _ in APPROACHES
}

epoch_stats: Dict[str, EpochStats] = {
    name: EpochStats(path, FILE_SIZE)
    for name, path in DB_DIRS.items()
}

max_levels_by_db     = [s.get_max_levels() for s in epoch_stats.values()]
max_epoch_length     = max(len(lvls) for lvls in max_levels_by_db)
max_levels_per_epoch = [0] * max_epoch_length
for lvls in max_levels_by_db:
    for i, lvl in enumerate(lvls):
        max_levels_per_epoch[i] = max(max_levels_per_epoch[i], lvl)

plot_stats = {
    name: s.get_plotstats(max_levels_per_epoch)
    for name, s in epoch_stats.items()
}
rq_stats = {
    name: s.get_rangequerystats()
    for name, s in epoch_stats.items()
}

active = set(ACTIVE_PLOTS)

# ===================================================================
# Local helper
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

# ===================================================================
# Epoch-level bar plots
# ===================================================================

def plot_total_bytes_written():
    convert  = 1024 ** 4
    yticks   = [0, 0.5, 1]

    data = {
        name: (stats[EPOCH_TO_PLOT].CompactionWrittenBytes
               + stats[EPOCH_TO_PLOT].RangeReduceWrittenBytes) / convert
        for name, stats in plot_stats.items()
    }

    _, ax = plt.subplots(figsize=FIG_BAR)
    for name in DISPLAY_NAMES:
        ax.bar(name, data[name], width=BAR_WIDTH, **bar_styles[name])

    ax.set_ylabel("total write (TB)")
    ax.set_yticks(yticks)
    ax.set_yticklabels([str(v) for v in yticks])
    ax.set_ylim(0, yticks[-1] + 0.05)
    ax.yaxis.set_label_coords(-0.29, 0.45)
    ax.set_xticks(range(len(DISPLAY_NAMES)))
    ax.set_xticklabels(ABBREVIATIONS, rotation=90)

    _save("total-writes.pdf")


def plot_total_rq_bytes_written():
    convert  = 1024 ** 4
    yticks   = [0, 0.5]

    data = {
        name: stats[EPOCH_TO_PLOT].RangeReduceWrittenBytes / convert
        for name, stats in plot_stats.items()
    }

    _, ax = plt.subplots(figsize=FIG_BAR)
    containers = []
    for name in DISPLAY_NAMES:
        bars = ax.bar(name, data[name], width=BAR_WIDTH, **bar_styles[name])
        containers.append(bars)

    ax.set_ylabel("total RQ write (TB)")
    ax.set_yticks(yticks)
    ax.set_yticklabels([str(v) for v in yticks])
    ax.set_ylim(0, yticks[-1] + 0.4)
    ax.yaxis.set_label_coords(-0.26, 0.42)
    ax.set_xticks(range(len(DISPLAY_NAMES)))
    ax.set_xticklabels(ABBREVIATIONS, rotation=90)

    for bars in containers:
        for bar in bars:
            h = bar.get_height()
            if h < 0.5:
                ax.text(bar.get_x() + bar.get_width() / 2, h,
                        f"{h:.2f}", ha="center", va="bottom",
                        fontsize=18, rotation=90)

    _save("total-rq-writes.pdf")


def plot_compaction_debt():
    convert = 1024 ** 3
    yticks  = [0, 5, 10, 15]

    data = {
        name: stats[EPOCH_TO_PLOT].CompactionDebt / convert
        for name, stats in plot_stats.items()
    }

    _, ax = plt.subplots(figsize=FIG_BAR)
    containers = []
    for name in DISPLAY_NAMES:
        bars = ax.bar(name, data[name], width=BAR_WIDTH, **bar_styles[name])
        containers.append(bars)

    ax.set_ylabel("compaction debt (GB)", labelpad=-0.5, y=0.35)
    ax.set_yticks(yticks)
    ax.set_yticklabels([str(v) for v in yticks])
    ax.set_ylim(0, yticks[-1] + 0.001)
    # ax.yaxis.set_label_coords(-0.3, 0.34)
    ax.set_xticks(range(len(DISPLAY_NAMES)))
    ax.set_xticklabels(ABBREVIATIONS, rotation=90)

    for bars in containers:
        for bar in bars:
            h = bar.get_height()
            if h < 0.5:
                ax.text(bar.get_x() + bar.get_width() / 2, h,
                        f"{h:.1f}", ha="center", va="bottom",
                        fontsize=18, rotation=90)

    _save("compaction-debt.pdf")

    handles, labels = ax.get_legend_handles_labels()
    leg = plt.figure(figsize=(8, 2))
    leg.legend(handles, labels, loc="center", ncol=5, frameon=False,
               borderaxespad=0, labelspacing=0, borderpad=0,
               columnspacing=0.4, handletextpad=0.2,
               handlelength=1, handleheight=1)
    _save_close(leg, "bounded-metric-legend.pdf")


def plot_space_amplification():
    yticks = [0, 0.5, 1, 1.5]

    data = {
        name: stats[EPOCH_TO_PLOT].DBSize / (INSERTS * ENTRY_SIZE)
        for name, stats in plot_stats.items()
    }

    _, ax = plt.subplots(figsize=FIG_BAR)
    for name in DISPLAY_NAMES:
        ax.bar(name, data[name], width=BAR_WIDTH, **bar_styles[name])

    ax.set_ylabel("space amplification", loc="top")
    ax.set_yticks(yticks)
    ax.set_yticklabels([str(v) for v in yticks])
    ax.set_ylim(0, yticks[-1])
    # ax.yaxis.set_label_coords(-0.46, 0.34)
    ax.set_xticks(range(len(DISPLAY_NAMES)))
    ax.set_xticklabels(ABBREVIATIONS, rotation=90)

    _save("space-amplification.pdf")

# ===================================================================
# Range-query line / CDF plots
# ===================================================================

def plot_bytes_read_per_rq():
    convert = 1024 ** 2
    yticks  = [0, 50, 100, 150]

    _, ax = plt.subplots(figsize=FIG_LINE)
    for name in DISPLAY_NAMES:
        data = (rq_stats[name][str(RQColumn.TOTAL_ENTRIES_READ)]
                .astype(float) * ENTRY_SIZE / convert).tolist()
        ax.plot(range(len(data)), data, alpha=0.8,
                **line_styles_no_marker[name])

    ax.set_ylabel("bytes read (MB)")
    ax.yaxis.set_major_locator(ticker.FixedLocator(yticks))
    ax.set_yticks(yticks)
    ax.set_yticklabels([str(v) for v in yticks])
    ax.set_ylim(0, yticks[-1] + 25)
    ax.set_xlabel("range query number")

    _save("range-query-bytes-read.pdf")


def plot_bytes_read_per_rq_rolling(window=200):
    convert = 1024 ** 3
    yticks  = [0, 0.1, 0.2]
    xticks  = [1, 3000, 6000, RANGE_QUERIES]

    fig, ax = plt.subplots(figsize=FIG_LINE)
    for name in DISPLAY_NAMES:
        s = (rq_stats[name][str(RQColumn.TOTAL_ENTRIES_READ)]
             .astype(float) * ENTRY_SIZE / convert)
        s = pd.Series(s)
        median = s.rolling(window, min_periods=1).median()
        q05    = s.rolling(window, min_periods=1).quantile(0.05)
        q95    = s.rolling(window, min_periods=1).quantile(0.95)
        style  = {**line_styles_no_marker[name], "linewidth": 2}
        ax.plot(median.values, **style)
        ax.fill_between(range(len(median)), q05, q95,
                        color=line_styles_no_marker[name]["color"],
                        alpha=0.25, linewidth=0, edgecolor="none",
                        rasterized=True)

    # ax.text(0.17, 0.1,
    #         f"rolling window: {window} pts\nline: median\nband: p5–p95",
    #         transform=ax.transAxes, fontsize=16)
    ax.set_ylabel("bytes read (GB)", labelpad=-1)
    ax.set_yticks(yticks)
    ax.set_yticklabels([str(v) for v in yticks])
    ax.set_ylim(bottom=yticks[0])
    ax.set_xlabel("range query number")
    ax.set_xticks(xticks)
    ax.set_xticklabels([str(v) for v in xticks])

    _save_close(fig, "range-query-bytes-read-rolling.pdf")


def plot_bytes_read_cdf():
    convert = 1024 ** 3
    yticks  = [0, 0.5, 1]
    xticks  = [0, 0.2]

    fig, ax = plt.subplots(figsize=FIG_LINE)
    for name in DISPLAY_NAMES:
        data = (rq_stats[name][str(RQColumn.TOTAL_ENTRIES_READ)]
                .astype(float) * ENTRY_SIZE / convert)
        sd = np.sort(data)
        y  = np.arange(1, len(sd) + 1) / len(sd)
        ax.plot(sd, y, **line_styles_no_marker_with_abbr[name])

    ax.yaxis.set_major_locator(ticker.FixedLocator(yticks))
    ax.set_yticks(yticks)
    ax.set_yticklabels(["" for _ in yticks])
    ax.set_ylim(0, 1)
    ax.xaxis.set_major_locator(ticker.FixedLocator(xticks))
    ax.set_xticks(xticks)
    ax.set_xticklabels(["" for _ in xticks])
    ax.set_xlim(0, xticks[-1] + 0.03)

    _save_close(fig, "range-query-bytes-read-cdf.pdf")


def plot_latency_per_rq():
    # convert = 10 ** 9
    # yticks  = [0, 1, 2]

    # fig, ax = plt.subplots(figsize=FIG_LINE)
    # for name in DISPLAY_NAMES:
    #     data = (rq_stats[name][str(RQColumn.RQ_TOTAL_TIME)]
    #             .apply(lambda x: x / convert).tolist())
    #     ax.plot(range(len(data)), data, alpha=0.8,
    #             **line_styles_no_marker_with_abbr[name])

    # ax.set_ylabel("latency (s)")
    # ax.yaxis.set_major_locator(ticker.FixedLocator(yticks))
    # ax.set_yticks(yticks)
    # ax.set_yticklabels([str(v) for v in yticks])
    # ax.set_ylim(bottom=0)
    # ax.set_xlabel("range query number")
    # ax.xaxis.set_major_locator(ticker.FixedLocator(ax.get_xticks()))

    # handles, labels = ax.get_legend_handles_labels()  # capture before close
    # _save_close(fig, "range-query-latency.pdf")

    # workload parameter legend
    legend_text = (
        f"M={round((ENTRY_SIZE*ENTRIES_PER_PAGE*NUM_PAGE_PER_FILE)/(1024*1024))}MB\\hspace{{1cm}}"
        f"E={ENTRY_SIZE}B\\hspace{{1cm}}"
        f"T={SIZE_RATIO}\\hspace{{1cm}}"
        f"I={round(INSERTS/1_000_000, 1)}M\\hspace{{1cm}}"
        f"U={round(UPDATES/1_000_000, 1)}M\\hspace{{1cm}}"
        f"S={round(RANGE_QUERIES/1000)}K\\hspace{{1cm}}"
        f"s={SELECTIVITY}"
    )
    cfg_fig = plt.figure(figsize=(8, 2))
    cfg_fig.text(0.5, 0.85, legend_text, ha="center", va="center")
    _save_close(cfg_fig, "bounded-legend-config.pdf")

    leg = plt.figure(figsize=(8, 2))
    leg.legend(handles, labels, loc="center", ncol=5, frameon=False,
               borderaxespad=0, labelspacing=2, borderpad=0,
               columnspacing=0.4, handletextpad=0.2,
               handlelength=2, handleheight=1)
    _save_close(leg, "bounded-legend.pdf")


def plot_latency_per_rq_rolling(window=200):
    convert = 10 ** 9
    yticks  = [0, 1, 2]
    xticks  = [1, 3000, 6000, 9000]

    fig, ax = plt.subplots(figsize=FIG_LINE)
    for name in DISPLAY_NAMES:
        s = (rq_stats[name][str(RQColumn.RQ_TOTAL_TIME)]
             .astype(float) / convert)
        s = pd.Series(s)
        median = s.rolling(window, min_periods=1).median()
        q05    = s.rolling(window, min_periods=1).quantile(0.05)
        q95    = s.rolling(window, min_periods=1).quantile(0.95)
        style  = {**line_styles_no_marker[name], "linewidth": 2}
        ax.plot(median.values, **style)
        ax.fill_between(range(len(median)), q05, q95,
                        color=line_styles_no_marker[name]["color"],
                        alpha=0.25, linewidth=0, edgecolor="none",
                        rasterized=True)

    # ax.text(0.17, 0.04,
    #         f"rolling window: {window} pts\nline: median\nband: p5–p95",
    #         transform=ax.transAxes, fontsize=16)
    ax.set_ylabel("latency (s)", labelpad=-1)
    ax.set_yticks(yticks)
    ax.set_ylim(bottom=yticks[0])
    ax.set_xlabel("range query number")
    ax.set_xticks(xticks)
    ax.set_xticklabels([str(v) for v in xticks])

    _save_close(fig, "range-query-latency-rolling.pdf")


def plot_latency_cdf():
    convert = 10 ** 9
    yticks  = [0, 0.5, 1]
    xticks  = [0, 2]

    fig, ax = plt.subplots(figsize=FIG_LINE)
    for name in DISPLAY_NAMES:
        data = (rq_stats[name][str(RQColumn.RQ_TOTAL_TIME)]
                .astype(float) / convert)
        sd = np.sort(data)
        y  = np.arange(1, len(sd) + 1) / len(sd)
        ax.plot(sd, y, **line_styles_no_marker_with_abbr[name])

    ax.set_ylabel("cdf")
    ax.yaxis.set_major_locator(ticker.FixedLocator(yticks))
    ax.set_yticks(yticks)
    ax.set_yticklabels([str(v) for v in yticks])
    ax.set_ylim(0, 1)
    ax.xaxis.set_major_locator(ticker.FixedLocator(xticks))
    ax.set_xticks(xticks)
    ax.set_xticklabels(["" for _ in xticks])
    ax.set_xlim(0, xticks[-1] + 0.5)

    _save_close(fig, "range-query-latency-cdf.pdf")


def plot_did_rq_run():
    data = {
        name: rq_stats[name][str(RQColumn.DID_RUN_RR)].sum()
        for name in DISPLAY_NAMES
    }

    _, ax = plt.subplots(figsize=FIG_BAR_RQ)
    for name in DISPLAY_NAMES:
        ax.bar(name, data[name], width=BAR_WIDTH, **bar_styles[name])

    ax.set_ylabel("optimization trigger count")
    ax.yaxis.set_label_coords(-0.42, 0.4)
    ax.set_xticks(range(len(DISPLAY_NAMES)))
    ax.set_xticklabels(ABBREVIATIONS, rotation=90)

    _save("did-optimization-trigger.pdf")


def plot_total_data_movement():
    convert  = 1024 ** 4
    yticks   = [0, 1, 2]
    # fig_size = (BAR_WIDTH, 2.5)

    data: Dict[str, float] = {}
    for name in DISPLAY_NAMES:
        rq_bytes = (rq_stats[name][str(RQColumn.TOTAL_ENTRIES_READ)].sum()
                    * ENTRY_SIZE)
        ep = plot_stats[name][EPOCH_TO_PLOT]
        total = (rq_bytes
                 + ep.CompactionReadBytes
                 + ep.CompactionWrittenBytes
                 + ep.RangeReduceWrittenBytes)
        data[name] = total / convert

    _, ax = plt.subplots(figsize=FIG_BAR)
    containers = []
    for name in DISPLAY_NAMES:
        bars = ax.bar(name, data[name], width=BAR_WIDTH, **bar_styles[name])
        containers.append(bars)

    ax.set_ylabel("data movement (TB)", labelpad=-0.5, y=0.36)
    ax.set_yticks(yticks)
    ax.set_yticklabels([str(v) for v in yticks])
    ax.set_ylim(0, yticks[-1])
    ax.set_xticks(range(len(DISPLAY_NAMES)))
    ax.set_xticklabels(ABBREVIATIONS, rotation=90)

    for bars in containers:
        for bar in bars:
            h = bar.get_height()
            if h < 0.05:
                ax.text(bar.get_x() + bar.get_width() / 2, h,
                        f"{h:.2f}", ha="center", va="bottom",
                        fontsize=18, rotation=90)

    _save("overall-data-movement.pdf")

# ===================================================================
# Dispatch
# ===================================================================

if "total_bytes_written"    in active: plot_total_bytes_written()
if "total_rq_bytes_written" in active: plot_total_rq_bytes_written()
if "compaction_debt"        in active: plot_compaction_debt()
if "space_amplification"    in active: plot_space_amplification()

if "bytes_read_per_rq"         in active: plot_bytes_read_per_rq()
if "bytes_read_per_rq_rolling" in active: plot_bytes_read_per_rq_rolling(window=200)
if "bytes_read_cdf"            in active: plot_bytes_read_cdf()

if "latency_per_rq"         in active: plot_latency_per_rq()
if "latency_per_rq_rolling" in active: plot_latency_per_rq_rolling(window=200)
if "latency_cdf"            in active: plot_latency_cdf()

if "did_rq_run"          in active: plot_did_rq_run()
if "total_data_movement" in active: plot_total_data_movement()
