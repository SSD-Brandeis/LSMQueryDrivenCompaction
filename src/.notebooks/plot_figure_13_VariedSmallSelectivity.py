import os
from pathlib import Path
from typing import List

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager

from plotter.epochstats import EpochStats
from plotter.dataclass import RQColumn
from plotter.plotstyles import line_styles, bar_styles

# ---------------------------
# Global config
# ---------------------------
PROJECT_DIR = Path.cwd().parent.parent

prop = font_manager.FontProperties(fname="./plotter/LinLibertine_Mah.ttf")
plt.rcParams["font.family"] = prop.get_name()
plt.rcParams["text.usetex"] = True
plt.rcParams["font.weight"] = "bold"
plt.rcParams["font.size"] = 22

tag = "diffselectivity"
OUTPUT_DIR = f"Figures/Fig13"
os.makedirs(OUTPUT_DIR, exist_ok=True)

inserts = 8_388_608
updates = 8_388_608
range_queries = 9000

entry_size = 128
num_page_per_file = 1024
entries_per_page = 32
size_ratio = 6

fig_size = (4, 3.5)
bar_width = 0.2
epoch_to_plot = -1

selectivities = (0.003, 0.01, 0.03, 0.1, 0.3)

# ---------------------------
# Stats containers
# ---------------------------
rocksdb_stats = {}
succinct_stats = {}
rangereduce_stats = {}

rocksdb_rq_stats = {}
succinct_rq_stats = {}
rangereduce_rq_stats = {}

# ---------------------------
# Load experiment data
# ---------------------------
for selectivity in selectivities:
    exp_dir = (
        f"{PROJECT_DIR}/logs/experiments-{tag}"
        f"-U{updates}-E{entry_size}-B{entries_per_page}"
        f"-S{range_queries}-Y{selectivity}-T{size_ratio}"
    )

    filesize = entry_size * entries_per_page * num_page_per_file

    rocksdb = EpochStats(os.path.join(exp_dir, "RocksDB"), filesize)
    succinct = EpochStats(os.path.join(exp_dir, "SuccinctKV"), filesize)
    rangereduce = EpochStats(
        os.path.join(exp_dir, "RangeReduce[lb=T^-1ANDre=1]"),
        filesize,
    )

    max_levels = []
    max_levels.append(rocksdb.get_max_levels())
    max_levels.append(succinct.get_max_levels())
    max_levels.append(rangereduce.get_max_levels())

    max_len = max(len(x) for x in max_levels)
    max_lvl_per_epoch = [0] * max_len

    for levels in max_levels:
        for i, lvl in enumerate(levels):
            max_lvl_per_epoch[i] = max(max_lvl_per_epoch[i], lvl)

    rocksdb_stats[selectivity] = rocksdb.get_plotstats(max_lvl_per_epoch)
    succinct_stats[selectivity] = succinct.get_plotstats(max_lvl_per_epoch)
    rangereduce_stats[selectivity] = rangereduce.get_plotstats(max_lvl_per_epoch)

    rocksdb_rq_stats[selectivity] = rocksdb.get_rangequerystats()
    succinct_rq_stats[selectivity] = succinct.get_rangequerystats()
    rangereduce_rq_stats[selectivity] = rangereduce.get_rangequerystats()

# ============================================================
# Plotting functions
# ============================================================

def plot_compaction_debt():
    convert_to = 1024 ** 3
    fig, ax = plt.subplots(figsize=fig_size)

    rdb, skv, rr = [], [], []

    for sel in selectivities:
        rdb.append(rocksdb_stats[sel][epoch_to_plot].CompactionDebt)
        skv.append(succinct_stats[sel][epoch_to_plot].CompactionDebt)
        rr.append(rangereduce_stats[sel][epoch_to_plot].CompactionDebt)

    ax.plot(selectivities, rdb, **line_styles["RocksDB"])
    ax.plot(selectivities, skv, **line_styles["SuccinctKV"])
    ax.plot(selectivities, rr, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

    ax.set_ylabel("compaction debt (GB)")
    ax.yaxis.set_label_coords(-0.25, 0.36)
    ax.set_xlabel("selectivity")
    ax.set_ylim(bottom=0)

    yticks = [0, 5, 10, 15]
    ax.set_yticks([y * convert_to for y in yticks])
    ax.set_yticklabels([0] + [f"{y:.1f}" for y in yticks[1:]])

    ax.set_xscale("log")
    ax.set_xticks(selectivities[::2])
    ax.set_xticklabels([str(s) for s in selectivities[::2]])

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/size-ratio-compaction_debt.pdf", bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)


def plot_space_amplification():
    fig, ax = plt.subplots(figsize=fig_size)

    rdb, skv, rr = [], [], []

    for sel in selectivities:
        denom = inserts * entry_size
        rdb.append(rocksdb_stats[sel][epoch_to_plot].DBSize / denom)
        skv.append(succinct_stats[sel][epoch_to_plot].DBSize / denom)
        rr.append(rangereduce_stats[sel][epoch_to_plot].DBSize / denom)

    ax.plot(selectivities, rdb, **line_styles["RocksDB"])
    ax.plot(selectivities, skv, **line_styles["SuccinctKV"])
    ax.plot(selectivities, rr, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

    ax.set_ylabel("space amplification")
    ax.yaxis.set_label_coords(-0.18, 0.4)
    ax.set_xlabel("selectivity")
    ax.set_ylim(0, 2)

    ax.set_yticks([0, 0.5, 1, 1.5, 2])
    ax.set_yticklabels(["0", "0.5", "1.0", "1.5", "2.0"])

    ax.set_xscale("log")
    ax.set_xticks(selectivities[::2])
    ax.set_xticklabels([str(s) for s in selectivities[::2]])

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/size-ratio-space_amplification.pdf", bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)


def plot_range_query_latency():
    fig, ax = plt.subplots(figsize=fig_size)

    rdb, skv, rr = [], [], []

    for sel in selectivities:
        base = range_queries / rocksdb_stats[sel][epoch_to_plot].RangeQueriesExecutionTime
        rdb.append(1.0)
        skv.append(
            (range_queries / succinct_stats[sel][epoch_to_plot].RangeQueriesExecutionTime) / base
        )
        rr.append(
            (range_queries / rangereduce_stats[sel][epoch_to_plot].RangeQueriesExecutionTime) / base
        )

    ax.plot(selectivities, rdb, **line_styles["RocksDB"])
    ax.plot(selectivities, skv, **line_styles["SuccinctKV"])
    ax.plot(selectivities, rr, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

    ax.set_ylabel("norm. RQ throughput")
    ax.yaxis.set_label_coords(-0.2, 0.38)
    ax.set_xlabel("selectivity")
    ax.set_ylim(bottom=0, top=1.5)

    ax.set_xscale("log")
    ax.set_xticks(selectivities[::2])
    ax.set_xticklabels([str(s) for s in selectivities[::2]])

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/size-ratio-range_query_latency.pdf", bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)


def plot_total_count_RQ_compaction_triggered_per_selectivity():
    fig, ax = plt.subplots(figsize=fig_size)

    rdb, skv, rr = [], [], []

    for sel in selectivities:
        rdb.append(rocksdb_rq_stats[sel][str(RQColumn.DID_RUN_RR)].sum())
        skv.append(succinct_rq_stats[sel][str(RQColumn.DID_RUN_RR)].sum())
        rr.append(rangereduce_rq_stats[sel][str(RQColumn.DID_RUN_RR)].sum())

    x = np.arange(len(selectivities))

    ax.bar(x - bar_width, rdb, bar_width, **bar_styles["RocksDB"])
    ax.bar(x, skv, bar_width, **bar_styles["SuccinctKV"])
    ax.bar(x + bar_width, rr, bar_width, **bar_styles["RangeReduce[lb=T^-1 & re=1]"])

    ax.set_ylabel("triggered")
    ax.set_xlabel("selectivity")
    ax.set_ylim(bottom=0)

    ax.set_xticks(x)
    ax.set_xticklabels([str(s) for s in selectivities], rotation=45)

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/rr-triggered.pdf", bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)


def plot_avg_data_compacted_per_selectivity():
    fig, ax = plt.subplots(figsize=fig_size)

    rdb, skv, rr = [], [], []

    for sel in selectivities:
        denom = range_queries * (1024 ** 2)
        rdb.append(rocksdb_stats[sel][epoch_to_plot].RangeReduceWrittenBytes / denom)
        skv.append(succinct_stats[sel][epoch_to_plot].RangeReduceWrittenBytes / denom)
        rr.append(rangereduce_stats[sel][epoch_to_plot].RangeReduceWrittenBytes / denom)

    x = np.arange(len(selectivities))

    ax.bar(x - bar_width, rdb, bar_width, **bar_styles["RocksDB"])
    ax.bar(x, skv, bar_width, **bar_styles["SuccinctKV"])
    ax.bar(x + bar_width, rr, bar_width, **bar_styles["RangeReduce[lb=T^-1 & re=1]"])

    ax.set_ylabel("avg. RQ MB written")
    ax.yaxis.set_label_coords(-0.12, 0.26)
    ax.set_xlabel("selectivity")
    ax.set_ylim(bottom=0)

    ax.set_xticks(x)
    ax.set_xticklabels([str(s) for s in selectivities], rotation=45)

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/avg-RQ-data-compacted.pdf", bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)


def plot_avg_data_read_per_selectivity():
    fig, ax = plt.subplots(figsize=fig_size)

    rdb, skv, rr = [], [], []

    for sel in selectivities:
        denom = range_queries * (1024 ** 2)
        rdb.append(rocksdb_rq_stats[sel][str(RQColumn.TOTAL_ENTRIES_READ)].sum() / denom)
        skv.append(succinct_rq_stats[sel][str(RQColumn.TOTAL_ENTRIES_READ)].sum() / denom)
        rr.append(rangereduce_rq_stats[sel][str(RQColumn.TOTAL_ENTRIES_READ)].sum() / denom)

    x = np.arange(len(selectivities))

    ax.bar(x - bar_width, rdb, bar_width, **bar_styles["RocksDB"])
    ax.bar(x, skv, bar_width, **bar_styles["SuccinctKV"])
    ax.bar(x + bar_width, rr, bar_width, **bar_styles["RangeReduce[lb=T^-1 & re=1]"])

    ax.set_ylabel("avg. RQ MB read")
    ax.yaxis.set_label_coords(-0.12, 0.35)
    ax.set_xlabel("selectivity")
    ax.set_ylim(bottom=0)

    ax.set_xticks(x)
    ax.set_xticklabels([str(s) for s in selectivities], rotation=45)

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/avg-RQ-data-read.pdf", bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)


def plot_RQ_read_amp_per_selectivity():
    fig, ax = plt.subplots(figsize=fig_size)

    rdb, skv, rr = [], [], []

    for sel in selectivities:
        rdb.append(
            rocksdb_rq_stats[sel][str(RQColumn.TOTAL_ENTRIES_READ)].mean()
            / rocksdb_rq_stats[sel][str(RQColumn.TOTAL_ENTRIES_RETURNED)].mean()
        )
        skv.append(
            succinct_rq_stats[sel][str(RQColumn.TOTAL_ENTRIES_READ)].mean()
            / succinct_rq_stats[sel][str(RQColumn.TOTAL_ENTRIES_RETURNED)].mean()
        )
        rr.append(
            rangereduce_rq_stats[sel][str(RQColumn.TOTAL_ENTRIES_READ)].mean()
            / rangereduce_rq_stats[sel][str(RQColumn.TOTAL_ENTRIES_RETURNED)].mean()
        )

    x = np.arange(len(selectivities))

    ax.bar(x - bar_width, rdb, bar_width, **bar_styles["RocksDB"])
    ax.bar(x, skv, bar_width, **bar_styles["SuccinctKV"])
    ax.bar(x + bar_width, rr, bar_width, **bar_styles["RangeReduce[lb=T^-1 & re=1]"])

    ax.set_ylabel("avg. RQ read amp.")
    ax.yaxis.set_label_coords(-0.12, 0.32)
    ax.set_xlabel("selectivity")
    ax.set_ylim(bottom=0)

    ax.set_xticks(x)
    ax.set_xticklabels([str(s) for s in selectivities], rotation=45)

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/avg-RQ-read-amp.pdf", bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)


def plot_RQ_latency_per_selectivity():
    fig, ax = plt.subplots(figsize=fig_size)

    rdb, skv, rr = [], [], []

    for sel in selectivities:
        rdb.append(rocksdb_rq_stats[sel][str(RQColumn.RQ_TOTAL_TIME)].mean() / 1e9)
        skv.append(succinct_rq_stats[sel][str(RQColumn.RQ_TOTAL_TIME)].mean() / 1e9)
        rr.append(rangereduce_rq_stats[sel][str(RQColumn.RQ_TOTAL_TIME)].mean() / 1e9)

    ax.plot(selectivities, rdb, **line_styles["RocksDB"])
    ax.plot(selectivities, skv, **line_styles["SuccinctKV"])
    ax.plot(selectivities, rr, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

    ax.set_ylabel("avg. RQ latency (s)")
    ax.set_xlabel("selectivity")
    ax.set_ylim(bottom=0)

    ax.set_xscale("log")
    ax.set_xticks(selectivities)
    ax.set_xticklabels([str(s) for s in selectivities], rotation=45)

    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/avg-RQ-latency.pdf", bbox_inches="tight", pad_inches=0.06)
    plt.close(fig)


# ---------------------------
# Run plots
# ---------------------------
plot_compaction_debt()
plot_space_amplification()
plot_range_query_latency()
# plot_total_count_RQ_compaction_triggered_per_selectivity()
# plot_avg_data_compacted_per_selectivity()
# plot_RQ_read_amp_per_selectivity()
# plot_RQ_latency_per_selectivity()
# plot_avg_data_read_per_selectivity()
