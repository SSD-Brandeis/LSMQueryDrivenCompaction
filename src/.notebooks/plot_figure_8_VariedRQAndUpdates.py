"""
plot_figure_8.py — standalone slide/paper plotter for figure 8
(varying range-query count).

Fully self-contained: no dependency on the shared plotter/ package.  All
constants, log parsing, styles, metric extraction, and plotting live in this
single file, so it can be copied and run on its own.  Produces the five active
figures: RQ-latency boxplot, normalized throughput, compaction debt, space
amplification, and normalized data movement.
"""

import os
from pathlib import Path
from types import SimpleNamespace
from typing import Dict, List

import matplotlib
matplotlib.use("Agg")
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

# ===================================================================
# Libertine paper format
# ===================================================================

FONT_PROP = font_manager.FontProperties(fname="./plotter/LinLibertine_Mah.ttf")
plt.rcParams["font.family"] = FONT_PROP.get_name()
plt.rcParams["text.usetex"] = True
plt.rcParams["font.weight"] = "bold"
plt.rcParams["font.size"] = 20

# ===================================================================
# Workload / experiment constants
# ===================================================================

TAG               = "selectivityplots"
INSERTS           = 8_388_608
ENTRY_SIZE        = 128
ENTRIES_PER_PAGE  = 32
NUM_PAGE_PER_FILE = 1024
SELECTIVITY       = 0.1
SIZE_RATIO        = 6

# Range-query CSV column names (post-strip).
RQ_TOTAL_TIME      = "RQ Total Time"
TOTAL_ENTRIES_READ = "Total Entries Read"

# ===================================================================
# Range-query sweep + x-axis labels
# ===================================================================

rq_percentages = (
    "0.000003814697265625",
    "0.0000152587890625",
    "0.00006103515625",
    "0.000244140625",
    "0.0009765625",
    "0.00390625",
    "0.015625",
)

rq_perccentage_axises = (
    0.000003814697265625,
    0.0000152587890625,
    0.00006103515625,
    0.000244140625,
    0.0009765625,
    0.00390625,
    0.015625,
)

x_axis_labels = {
    "0.000003814697265625": "$2^{5}$",
    "0.0000152587890625": "$2^{7}$",
    "0.00006103515625": "$2^{9}$",
    "0.000244140625": "$2^{11}$",
    "0.0009765625": "$2^{13}$",
    "0.00390625": "$2^{15}$",
    "0.015625": "$2^{17}$",
}
rotation = 0

# ===================================================================
# Styles (only the approaches this figure draws)
# ===================================================================

_common_line = {"markersize": 12, "markerfacecolor": "none", "linewidth": 2}

line_styles = {
    "RocksDB": {
        **_common_line, "label": "RocksDB", "color": "grey",
        "linestyle": "-", "marker": "^",
    },
    "SuccinctKV": {
        **_common_line, "label": "SuccinctKV", "color": "#0077FF",
        "linestyle": "-.", "marker": "s",
    },
    "RangeReduce[lb=T^-1 & re=1]": {
        **_common_line, "label": "RangeReduce", "color": "#FF1744",
        "linestyle": (0, (5, 2)), "marker": "o",
    },
}

box_styles = {
    "RocksDB": {
        "linewidth": 0.05, "label": "RocksDB", "facecolor": "grey",
        "hatch": "", "edgecolor": "none",
    },
    "SuccinctKV": {
        "linewidth": 0.05, "label": "SuccinctKV", "facecolor": "#0077FF",
        "hatch": "\\\\\\\\", "edgecolor": "none",
    },
    "RangeReduce[lb=T^-1 & re=1]": {
        "linewidth": 0.05, "label": "RangeReduce", "facecolor": "#FF1744",
        "hatch": "xx", "edgecolor": "none",
    },
}

# ===================================================================
# Paths
# ===================================================================

PROJECT_DIR = Path.cwd().parent.parent

OUTPUT_DIR = f"Figures/Fig8"
os.makedirs(OUTPUT_DIR, exist_ok=True)

FILE_SIZE = ENTRY_SIZE * ENTRIES_PER_PAGE * NUM_PAGE_PER_FILE

FIG_SIZE = (5, 3.3)

# ===================================================================
# Log parsing (minimal, faithful port of plotter.epochstats)
# ===================================================================

LOG_FILENAME = "workload.log"
RQ_FILENAME  = "range_queries.csv"


def _read_epochs(filepath: str) -> List[List[str]]:
    epochs: List[List[str]] = []
    current: List[str] = []

    with open(filepath) as f:
        for line in f:
            line = line.rstrip()
            if line.startswith("====================="):
                if current:
                    epochs.append(current)
                    current = []
                continue
            if line.startswith("===========END HERE========="):
                break
            current.append(line)

    # Merge trailing workload times into the last epoch.
    for i, line in enumerate(current):
        if line.startswith("Workload Execution Time"):
            epochs[-1].extend(current[i:])
            break

    return epochs[1:]


def _parse_levels(epoch_stats: List[str]) -> Dict:
    cfd: Dict = {"Levels": []}
    for line in epoch_stats:
        if line.startswith("Column Family Name"):
            kv = line.split(",")
            cfd["Size"]        = int(kv[1].split(":")[1].strip().strip(",").strip(" bytes"))
            cfd["Files Count"] = int(kv[2].split(":")[1].strip().strip(","))
        elif line.startswith("Level:"):
            kv = line.split(",")
            cfd["Levels"].append(
                {
                    "Level":           int(kv[0].split(":")[1].strip().strip(",")),
                    "LevelFilesCount": int(kv[1].split(":")[1].strip().strip(",")),
                    "LevelSize":       int(kv[2].split(":")[1].strip().strip(",").strip(" bytes")),
                }
            )
    return cfd


def _sum_lines(epoch_stats: List[str], prefix: str) -> int:
    return sum(
        int(line.split(":")[1]) for line in epoch_stats if line.startswith(prefix)
    )


def _workload_execution_time(epoch_stats: List[str]) -> float:
    for line in epoch_stats:
        if line.startswith("Workload Execution Time"):
            return float(line.split(": ")[1])
    return 0.0


def _max_nonempty_levels(cfd: Dict) -> int:
    sorted_cfd = sorted(cfd["Levels"], key=lambda x: x["Level"])
    while sorted_cfd and sorted_cfd[-1]["LevelSize"] == 0:
        sorted_cfd.pop()
    return len(sorted_cfd)


def _compaction_debt(levels: List[Dict], L: int) -> int:
    sum_of_bytes  = 0
    last_lvl_index = L - 1
    for lvl, data in enumerate(levels):
        if lvl == last_lvl_index:
            break
        sum_of_bytes += data.get("LevelSize", 0) * SIZE_RATIO * (last_lvl_index - lvl + 1)
    return sum_of_bytes + levels[L - 1].get("LevelSize", 0)


class LogStats:
    """Last-epoch workload metrics + range-query stats for one experiment dir."""

    def __init__(self, logdir: str):
        self.epochs = _read_epochs(os.path.join(logdir, LOG_FILENAME))
        self.cfds   = [_parse_levels(e) for e in self.epochs]
        self.max_levels = [_max_nonempty_levels(cfd) for cfd in self.cfds]

        rq = pd.read_csv(os.path.join(logdir, RQ_FILENAME))
        rq = rq.map(lambda x: x.strip() if isinstance(x, str) else x)
        rq.columns = rq.columns.str.strip()
        self.rq = rq

    def last_epoch_stats(self, max_lvls_per_epoch: List[int]) -> SimpleNamespace:
        epoch = len(self.epochs) - 1
        L     = max_lvls_per_epoch[epoch]
        cfd   = self.cfds[epoch]
        es    = self.epochs[epoch]

        sorted_cfd = sorted(cfd["Levels"], key=lambda x: x["Level"])
        n = len(sorted_cfd) - 1
        while sorted_cfd:
            if sorted_cfd[n]["LevelSize"] == 0 and n >= L:
                sorted_cfd.pop()
                n -= 1
            else:
                break

        return SimpleNamespace(
            CompactionDebt          = _compaction_debt(sorted_cfd, L),
            DBSize                  = cfd["Size"],
            CompactionWrittenBytes  = _sum_lines(es, "rocksdb.compact.write.bytes"),
            CompactionReadBytes     = _sum_lines(es, "rocksdb.compact.read.bytes"),
            RangeReduceWrittenBytes = _sum_lines(es, "rocksdb.rangereduce.write.bytes"),
            WorkloadExecutionTime   = _workload_execution_time(es),
        )

# ===================================================================
# Data loading — one last-epoch sample per approach per RQ percentage.
# ===================================================================

vanilla_logs:    List[LogStats] = []
succinctkv_logs: List[LogStats] = []
rqdc_logs:       List[LogStats] = []
op_count:        List[int]      = []

max_lvl_per_epoch: List[int] = []

for percent in rq_percentages:
    range_queries = int(float(percent) * INSERTS)
    updates       = INSERTS - range_queries
    op_count.append(INSERTS + updates + range_queries)

    exp_dir = (
        f"{PROJECT_DIR}/logs/experiments-{TAG}"
        f"-U{updates}-E{ENTRY_SIZE}-B{ENTRIES_PER_PAGE}"
        f"-S{range_queries}-Y{SELECTIVITY}-T{SIZE_RATIO}"
    )

    van  = LogStats(os.path.join(exp_dir, "RocksDB"))
    suc  = LogStats(os.path.join(exp_dir, "RangeReduce[lb=0]"))
    rqdc = LogStats(os.path.join(exp_dir, "RangeReduce[lb=T^-1ANDre=1]"))

    vanilla_logs.append(van)
    succinctkv_logs.append(suc)
    rqdc_logs.append(rqdc)

    # Shared max non-empty level scaling across approaches for this percentage.
    mtx     = [van.max_levels, suc.max_levels, rqdc.max_levels]
    max_len = max(len(m) for m in mtx)
    max_lvl_per_epoch = [0] * max_len
    for m in mtx:
        for i, lvl in enumerate(m):
            max_lvl_per_epoch[i] = max(max_lvl_per_epoch[i], lvl)

# The original applies the final percentage's level scaling to every series.
_vanilla    = [l.last_epoch_stats(max_lvl_per_epoch) for l in vanilla_logs]
_succinctkv = [l.last_epoch_stats(max_lvl_per_epoch) for l in succinctkv_logs]
_rqdc       = [l.last_epoch_stats(max_lvl_per_epoch) for l in rqdc_logs]

_vanilla_rq    = [l.rq for l in vanilla_logs]
_succinctkv_rq = [l.rq for l in succinctkv_logs]
_rqdc_rq       = [l.rq for l in rqdc_logs]

# ===================================================================
# Plot functions
# ===================================================================

def _x_axis(ax, step=2):
    ax.set_xscale("log", base=2)
    ax.set_xlabel("range query count")
    ax.set_xticks(rq_perccentage_axises[::step])
    ax.set_xticklabels(
        [f"{x_axis_labels[per]}" for per in rq_percentages[::step]], rotation=rotation
    )


def plot_range_query_box_plot_latency():
    convert_to_ = 10 ** 9
    vanilla_rq_times     = [df[RQ_TOTAL_TIME] for df in _vanilla_rq]
    succinct_kv_rq_times = [df[RQ_TOTAL_TIME] for df in _succinctkv_rq]
    rqdc_rq_times        = [df[RQ_TOTAL_TIME] for df in _rqdc_rq]

    x_positions = np.arange(len(rq_percentages))
    width   = 0.22
    offset  = -width

    fig, ax = plt.subplots(figsize=(4.6, 3.8))
    mpl.rcParams["hatch.linewidth"] = 0.5

    ax.boxplot(vanilla_rq_times, positions=x_positions - 0.25 + offset, widths=width,
               whis=(0, 95), patch_artist=True, boxprops=box_styles["RocksDB"],
               medianprops=dict(color="black"), showfliers=False)
    ax.boxplot(succinct_kv_rq_times, positions=x_positions + offset, widths=width,
               whis=(0, 95), patch_artist=True, boxprops=box_styles["SuccinctKV"],
               medianprops=dict(color="black"), showfliers=False)
    ax.boxplot(rqdc_rq_times, positions=x_positions + 0.25 + offset, widths=width,
               whis=(0, 95), patch_artist=True,
               boxprops=box_styles["RangeReduce[lb=T^-1 & re=1]"],
               medianprops=dict(color="black"), showfliers=False)

    ax.set_ylabel("RQ latency (sec)")
    ax.yaxis.set_label_coords(-0.12, 0.45)
    ax.set_ylim(bottom=0)

    legend_handles = [
        Patch(facecolor=box_styles["RocksDB"]["facecolor"], hatch=box_styles["RocksDB"]["hatch"], edgecolor="none", label="RocksDB"),
        Patch(facecolor=box_styles["SuccinctKV"]["facecolor"], hatch=box_styles["SuccinctKV"]["hatch"], edgecolor="none", label="SuccinctKV"),
        Patch(facecolor=box_styles["RangeReduce[lb=T^-1 & re=1]"]["facecolor"], hatch=box_styles["RangeReduce[lb=T^-1 & re=1]"]["hatch"], edgecolor="none", label="RangeReduce"),
    ]
    ax.legend(handles=legend_handles, ncol=2, loc=(0.005, -0.01), frameon=False,
              columnspacing=0.2, handletextpad=0.1, handlelength=1.0,
              handleheight=0.7, fontsize=17.5)

    ax.set_xlabel("range query count")
    ax.set_xticks(x_positions)
    ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages], rotation=rotation)

    desired_yticks = [0, 0.5, 1, 1.5]
    ax.set_yticks([x * convert_to_ for x in desired_yticks])
    ax.set_yticklabels([str(x) for x in desired_yticks])

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/range_query_latency_boxplot.pdf", bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)


def plot_throughput():
    convert_to_ = 1000 ** 3
    vanilla_throughput    = [op_count[i] / (v.WorkloadExecutionTime / convert_to_) for i, v in enumerate(_vanilla)]
    succinctkv_throughput = [op_count[i] / (s.WorkloadExecutionTime / convert_to_) for i, s in enumerate(_succinctkv)]
    rqdc_throughput       = [op_count[i] / (r.WorkloadExecutionTime / convert_to_) for i, r in enumerate(_rqdc)]

    vanilla_norm    = [1.0 for _ in vanilla_throughput]
    succinctkv_norm = [succinctkv_throughput[i] / vanilla_throughput[i] for i in range(len(vanilla_throughput))]
    rqdc_norm       = [rqdc_throughput[i] / vanilla_throughput[i] for i in range(len(vanilla_throughput))]

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    _x_axis(ax)

    ax.plot(rq_perccentage_axises, vanilla_norm, **line_styles["RocksDB"])
    ax.plot(rq_perccentage_axises, succinctkv_norm, **line_styles["SuccinctKV"])
    ax.plot(rq_perccentage_axises, rqdc_norm, **line_styles["RangeReduce[lb=T^-1 & re=1]"])
    ax.set_ylabel("norm. throughput")
    ax.set_ylim(bottom=0)

    desired_yticks = [0, 0.5, 1, 1.5]
    ax.set_yticks(desired_yticks)
    ax.set_yticklabels([0] + [f"{x:.1f}" for x in desired_yticks[1:]])

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/throughput.pdf", bbox_inches="tight", pad_inches=0.06)

    # Shared legend figure.
    handles, labels = ax.get_legend_handles_labels()
    legend_fig = plt.figure(figsize=(10, 2))
    legend_fig.legend(handles, labels, loc="center", ncol=4, frameon=False,
                      borderaxespad=0, labelspacing=0, borderpad=0)
    legend_fig.savefig(f"{OUTPUT_DIR}/experimental.pdf", bbox_inches="tight", pad_inches=0.015)
    plt.close(legend_fig)
    plt.close(fig)


def plot_compaction_debt():
    convert_to_ = 1024 ** 3
    vanilla    = [v.CompactionDebt for v in _vanilla]
    succinctkv = [s.CompactionDebt for s in _succinctkv]
    rqdc       = [r.CompactionDebt for r in _rqdc]

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.plot(rq_perccentage_axises, vanilla, **line_styles["RocksDB"])
    ax.plot(rq_perccentage_axises, succinctkv, **line_styles["SuccinctKV"])
    ax.plot(rq_perccentage_axises, rqdc, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

    ax.set_ylabel("compaction debt (GB)", labelpad=-1, loc="top")
    ax.set_ylim(bottom=0)
    _x_axis(ax)

    desired_yticks = [0, 5, 10, 15]
    ax.set_yticks([x * convert_to_ for x in desired_yticks])
    ax.set_yticklabels([0] + [f"{x}" for x in desired_yticks[1:]])

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/compaction_debt.pdf", bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)


def plot_space_amp():
    vanilla    = [v.DBSize / (INSERTS * ENTRY_SIZE) for v in _vanilla]
    succinctkv = [s.DBSize / (INSERTS * ENTRY_SIZE) for s in _succinctkv]
    rqdc       = [r.DBSize / (INSERTS * ENTRY_SIZE) for r in _rqdc]

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    ax.plot(rq_perccentage_axises, vanilla, **line_styles["RocksDB"])
    ax.plot(rq_perccentage_axises, succinctkv, **line_styles["SuccinctKV"])
    ax.plot(rq_perccentage_axises, rqdc, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

    ax.set_ylabel("space amplification")
    ax.set_ylim(bottom=0, top=max(vanilla) + 0.5)
    _x_axis(ax)

    desired_yticks = [0, 0.5, 1, 1.5, 2]
    ax.set_yticks(desired_yticks)
    ax.set_yticklabels([0] + [f"{x:.1f}" for x in desired_yticks[1:]])

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/space_amplification.pdf", bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)


def plot_overall_datamovement():
    convert_to_ = 1024 ** 4
    vanilla_rq_read    = [df[TOTAL_ENTRIES_READ].sum() * ENTRY_SIZE for df in _vanilla_rq]
    succinctkv_rq_read = [df[TOTAL_ENTRIES_READ].sum() * ENTRY_SIZE for df in _succinctkv_rq]
    rqdc_rq_read       = [df[TOTAL_ENTRIES_READ].sum() * ENTRY_SIZE for df in _rqdc_rq]

    vanilla_comp    = [v.CompactionReadBytes + v.CompactionWrittenBytes for v in _vanilla]
    succinctkv_comp = [s.CompactionReadBytes + s.CompactionWrittenBytes for s in _succinctkv]
    rqdc_comp       = [r.CompactionReadBytes + r.CompactionWrittenBytes for r in _rqdc]
    rqdc_rq_write   = [r.RangeReduceWrittenBytes for r in _rqdc]

    vanilla_datamov    = [(vanilla_rq_read[i] + vanilla_comp[i]) / convert_to_ for i in range(len(vanilla_rq_read))]
    succinctkv_datamov = [(succinctkv_rq_read[i] + succinctkv_comp[i]) / convert_to_ for i in range(len(succinctkv_rq_read))]
    rqdc_datamov       = [(rqdc_rq_read[i] + rqdc_comp[i] + rqdc_rq_write[i]) / convert_to_ for i in range(len(rqdc_rq_write))]

    vanilla_norm    = [1.0 for _ in vanilla_datamov]
    succinctkv_norm = [succinctkv_datamov[i] / vanilla_datamov[i] for i in range(len(vanilla_datamov))]
    rqdc_norm       = [rqdc_datamov[i] / vanilla_datamov[i] for i in range(len(vanilla_datamov))]

    fig, ax = plt.subplots(figsize=FIG_SIZE)
    _x_axis(ax)

    ax.plot(rq_perccentage_axises, vanilla_norm, **line_styles["RocksDB"])
    ax.plot(rq_perccentage_axises, succinctkv_norm, **line_styles["SuccinctKV"])
    ax.plot(rq_perccentage_axises, rqdc_norm, **line_styles["RangeReduce[lb=T^-1 & re=1]"])
    ax.set_ylabel("norm. data movement", labelpad=-1, loc="top")
    ax.set_ylim(bottom=0)

    desired_yticks = [0, 0.5, 1, 1.5]
    ax.set_yticks(desired_yticks)
    ax.set_yticklabels([0] + [f"{x:.1f}" for x in desired_yticks[1:]])

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/overall_data_movement.pdf", bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)

# ===================================================================
# Dispatch
# ===================================================================

# plot_range_query_box_plot_latency()
plot_throughput()
plot_compaction_debt()
plot_space_amp()
plot_overall_datamovement()
