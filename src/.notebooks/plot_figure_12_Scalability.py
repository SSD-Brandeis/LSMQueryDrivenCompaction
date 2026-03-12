import os
from pathlib import Path
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager

from plotter.epochstats import EpochStats
from plotter.dataclass import RQColumn
from plotter.plotstyles import *

# ------------------------------------------------------------------------------
# Global config
# ------------------------------------------------------------------------------

PROJECT_DIR = Path.cwd().parent.parent
tag = "scalability-exp"

size_ratio = 6
base_inserts = 8_388_608
base_updates = 8_388_608
base_range_queries = 200
selectivity = 0.1

entry_size = 128
entries_per_page = 32
num_page_per_file = 1024

scales = (1, 2, 4, 8)
fig_size = (1.7, 2.2)
epoch_to_plot = -1

# ------------------------------------------------------------------------------
# Matplotlib config
# ------------------------------------------------------------------------------

prop = font_manager.FontProperties(fname="./plotter/LinLibertine_Mah.ttf")
plt.rcParams.update({
    "font.family": prop.get_name(),
    "text.usetex": True,
    "font.size": 20,
})

# ------------------------------------------------------------------------------
# Stats containers
# ------------------------------------------------------------------------------

stats = defaultdict(dict)
rq_stats = defaultdict(dict)

per_scale_inserts = {}
per_scale_updates = {}
per_scale_rqs = {}

file_size = entry_size * entries_per_page * num_page_per_file

# ------------------------------------------------------------------------------
# Load experiment data
# ------------------------------------------------------------------------------

for scale in scales:
    inserts = base_inserts * scale
    updates = base_updates * scale
    range_queries = base_range_queries * scale

    per_scale_inserts[scale] = inserts
    per_scale_updates[scale] = updates

    expdir = (
        f"{PROJECT_DIR}/.vstats_old/experiments-{tag}-"
        f"{scale}x-U{updates}-E{entry_size}-B{entries_per_page}-"
        f"S{range_queries}-Y{selectivity}-T{size_ratio}"
    )

    rocksdb_path = os.path.join(expdir, "RocksDB")
    succinct_path = os.path.join(expdir, "SuccinctKV")
    rr_path = os.path.join(expdir, "RangeReduce[lb=T^-1ANDre=1]")

    rocksdb = EpochStats(rocksdb_path, file_size)
    succinct = EpochStats(succinct_path, file_size)
    rr = EpochStats(rr_path, file_size)

    max_lvl_mtx = [
        rocksdb.get_max_levels(),
        succinct.get_max_levels(),
        rr.get_max_levels(),
    ]

    max_epochs = max(len(x) for x in max_lvl_mtx)
    max_lvl_per_epoch = [0] * max_epochs

    for col in max_lvl_mtx:
        for i, lvl in enumerate(col):
            max_lvl_per_epoch[i] = max(max_lvl_per_epoch[i], lvl)

    stats[scale]["RocksDB"] = rocksdb.get_plotstats(max_lvl_per_epoch)
    stats[scale]["SuccinctKV"] = succinct.get_plotstats(max_lvl_per_epoch)
    stats[scale]["RangeReduce[lb=T^-1ANDre=1]"] = rr.get_plotstats(max_lvl_per_epoch)

    rq_stats[scale]["RocksDB"] = rocksdb.get_rangequerystats()
    rq_stats[scale]["SuccinctKV"] = succinct.get_rangequerystats()
    rq_stats[scale]["RangeReduce[lb=T^-1ANDre=1]"] = rr.get_rangequerystats()

# ------------------------------------------------------------------------------
# Plotting functions
# ------------------------------------------------------------------------------

def plot_compaction_debt():
    convert_to = 1024**3

    rdb, skv, rr = [], [], []

    for scale in scales:
        rdb.append(stats[scale]["RocksDB"][epoch_to_plot].CompactionDebt / convert_to)
        skv.append(stats[scale]["SuccinctKV"][epoch_to_plot].CompactionDebt / convert_to)
        rr.append(stats[scale]["RangeReduce[lb=T^-1ANDre=1]"][epoch_to_plot].CompactionDebt / convert_to)

    # print("compaction debt")
    # print(rdb)
    # print(skv)
    # print(rr)

    _, ax = plt.subplots(figsize=fig_size)
    ax.plot(scales, rdb, **line_styles["RocksDB"])
    ax.plot(scales, skv, **line_styles["SuccinctKV"])
    ax.plot(scales, rr, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

    ax.set_ylabel("compaction debt (GB)", labelpad=-2)
    ax.set_xlabel("db size (GB)")
    ax.set_yticks([0, 10, 20, 30, 40])
    ax.set_yscale('log')
    ax.set_ylim(1e0)
    ax.yaxis.set_label_coords(-0.30, 0.34)
    ax.set_xscale("log", base=2)
    x_ticks = [1, 2, 4, 8]
    ax.set_xticks(x_ticks)
    from matplotlib.ticker import ScalarFormatter
    ax.xaxis.set_major_formatter(ScalarFormatter())

    plt.savefig(f"{tag}/compaction-debt.pdf", bbox_inches="tight", pad_inches=0.06)


def plot_space_amp():
    rdb, skv, rr = [], [], []

    for scale in scales:
        logical_size = per_scale_inserts[scale] * (entry_size + 10)
        rdb.append(stats[scale]["RocksDB"][epoch_to_plot].DBSize / logical_size)
        skv.append(stats[scale]["SuccinctKV"][epoch_to_plot].DBSize / logical_size)
        rr.append(stats[scale]["RangeReduce[lb=T^-1ANDre=1]"][epoch_to_plot].DBSize / logical_size)

    # print("space amp")
    # print("Rocksdb", rdb)
    # print("SuccinctKV", skv)
    # print("RangeReduce", rr)

    _, ax = plt.subplots(figsize=fig_size)
    ax.plot(scales, rdb, **line_styles["RocksDB"])
    ax.plot(scales, skv, **line_styles["SuccinctKV"])
    ax.plot(scales, rr, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

    ax.set_ylabel("space amplification")
    ax.yaxis.set_label_coords(-0.34, 0.34)
    ax.set_xlabel("db size (GB)")
    ax.set_ylim(0, 1.5)
    ax.set_yticks([0, 0.5, 1, 1.5])
    ax.set_yticklabels([0, 0.5, 1, 1.5])
    ax.set_xscale("log", base=2)
    x_ticks = [1, 2, 4, 8]
    ax.set_xticks(x_ticks)
    from matplotlib.ticker import ScalarFormatter
    ax.xaxis.set_major_formatter(ScalarFormatter())

    plt.savefig(f"{tag}/space-amp.pdf", bbox_inches="tight", pad_inches=0.06)


def plot_rq_bytes_read():
    convert_to = 1024**3

    rdb, skv, rr = [], [], []

    for scale in scales:
        rdb.append(
            (rq_stats[scale]["RocksDB"][str(RQColumn.TOTAL_ENTRIES_READ)]
             .astype(float).mean() * entry_size) / convert_to
        )
        skv.append(
            (rq_stats[scale]["SuccinctKV"][str(RQColumn.TOTAL_ENTRIES_READ)]
             .astype(float).mean() * entry_size) / convert_to
        )
        rr.append(
            (rq_stats[scale]["RangeReduce[lb=T^-1ANDre=1]"][str(RQColumn.TOTAL_ENTRIES_READ)]
             .astype(float).mean() * entry_size) / convert_to
        )

    _, ax = plt.subplots(figsize=fig_size)
    ax.plot(scales, rdb, **line_styles["RocksDB"])
    ax.plot(scales, skv, **line_styles["SuccinctKV"])
    ax.plot(scales, rr, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

    ax.set_ylabel("RQ bytes read (GB)")
    ax.set_xlabel("db size (GB)")
    ax.set_yticks([0, 0.2, 0.4, 0.6])
    ax.set_yticklabels(["0", "0.2", "0.4", "0.6"])
    ax.set_ylim(0, 0.6)
    ax.yaxis.set_label_coords(-0.33, 0.4)
    ax.set_xscale("log", base=2)
    x_ticks = [1, 2, 4, 8]
    ax.set_xticks(x_ticks)
    from matplotlib.ticker import ScalarFormatter
    ax.xaxis.set_major_formatter(ScalarFormatter())

    plt.savefig(f"{tag}/rq-bytes.pdf", bbox_inches="tight", pad_inches=0.06)


def plot_rq_latency():
    convert_to = 1e9

    rdb, skv, rr = [], [], []

    for scale in scales:
        rdb.append(
            rq_stats[scale]["RocksDB"][str(RQColumn.RQ_TOTAL_TIME)].astype(float).mean() / convert_to
        )
        skv.append(
            rq_stats[scale]["SuccinctKV"][str(RQColumn.RQ_TOTAL_TIME)].astype(float).mean() / convert_to
        )
        rr.append(
            rq_stats[scale]["RangeReduce[lb=T^-1ANDre=1]"][str(RQColumn.RQ_TOTAL_TIME)]
            .astype(float).mean() / convert_to
        )

    # print("RQ latency")
    # print("Rocksdb", rdb)
    # print("SuccinctKV", skv)
    # print("RangeReduce", rr)

    _, ax = plt.subplots(figsize=fig_size)
    ax.plot(scales, rdb, **line_styles["RocksDB"])
    ax.plot(scales, skv, **line_styles["SuccinctKV"])
    ax.plot(scales, rr, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

    ax.set_ylabel("RQ latency (s)")
    ax.set_xlabel("db size (GB)")
    ax.set_yticks([0, 2, 4, 6, 8])
    ax.set_ylim(0, 8)
    ax.yaxis.set_label_coords(-0.16, 0.45)
    ax.set_xscale("log", base=2)
    x_ticks = [1, 2, 4, 8]
    ax.set_xticks(x_ticks)
    from matplotlib.ticker import ScalarFormatter
    ax.xaxis.set_major_formatter(ScalarFormatter())

    plt.savefig(f"{tag}/rq-latency.pdf", bbox_inches="tight", pad_inches=0.06)

def plot_total_data_movement_normalized():
    convert_to = 1024**4

    rdb, skv, rr = [], [], []

    # Collect absolute data movement
    for scale in scales:
        for name, lst in [
            ("RocksDB", rdb),
            ("SuccinctKV", skv),
            ("RangeReduce[lb=T^-1ANDre=1]", rr),
        ]:
            total = (
                stats[scale][name][epoch_to_plot].CompactionReadBytes +
                stats[scale][name][epoch_to_plot].CompactionWrittenBytes +
                stats[scale][name][epoch_to_plot].RangeReduceWrittenBytes +
                rq_stats[scale][name][str(RQColumn.TOTAL_ENTRIES_READ)].sum() * entry_size
            )
            lst.append(total / convert_to)

    # Normalize over RocksDB
    rdb_norm = [1.0 for _ in rdb]
    skv_norm = [s / r for s, r in zip(skv, rdb)]
    rr_norm  = [r_ / r for r_, r in zip(rr, rdb)]

    print("data movement")
    print("Rocksdb", rdb)
    print("SuccinctKV", skv)
    print("RangeReduce", rr)

    # Plot
    _, ax = plt.subplots(figsize=fig_size)
    ax.plot(scales, rdb_norm, **line_styles["RocksDB"])
    ax.plot(scales, skv_norm, **line_styles["SuccinctKV"])
    ax.plot(scales, rr_norm, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

    ax.set_ylabel("nrom. data movement")
    ax.set_xlabel("db size (GB)")

    ax.set_xscale("log", base=2)
    x_ticks = [1, 2, 4, 8]
    ax.set_xticks(x_ticks)

    from matplotlib.ticker import ScalarFormatter
    ax.xaxis.set_major_formatter(ScalarFormatter())

    ax.set_ylim(0)
    ax.set_yticks([0, 0.5, 1.0, 1.5])
    ax.set_yticklabels(["0", "0.5", "1", "1.5"])

    ax.yaxis.set_label_coords(-0.3, 0.32)

    plt.savefig(
        f"{tag}/overall-data-movement-normalized.pdf",
        bbox_inches="tight",
        pad_inches=0.06,
    )


def plot_total_data_movement():
    convert_to = 1024**4

    rdb, skv, rr = [], [], []

    for scale in scales:
        for name, lst in [
            ("RocksDB", rdb),
            ("SuccinctKV", skv),
            ("RangeReduce[lb=T^-1ANDre=1]", rr),
        ]:
            total = (
                stats[scale][name][epoch_to_plot].CompactionReadBytes +
                stats[scale][name][epoch_to_plot].CompactionWrittenBytes +
                stats[scale][name][epoch_to_plot].RangeReduceWrittenBytes +
                rq_stats[scale][name][str(RQColumn.TOTAL_ENTRIES_READ)].sum() * entry_size
            )
            lst.append(total / convert_to)

    _, ax = plt.subplots(figsize=fig_size)
    ax.plot(scales, rdb, **line_styles["RocksDB"])
    ax.plot(scales, skv, **line_styles["SuccinctKV"])
    ax.plot(scales, rr, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

    ax.set_ylabel("data movement (TB)")
    ax.set_xlabel("db size (GB)")
    ax.set_yticks([0, 1, 2])
    ax.set_yticklabels(["0", "1", "2"])
    ax.set_ylim(0, 2.5)
    ax.yaxis.set_label_coords(-0.18, 0.32)
    ax.set_xscale("log", base=2)
    x_ticks = [1, 2, 4, 8]
    ax.set_xticks(x_ticks)
    from matplotlib.ticker import ScalarFormatter
    ax.xaxis.set_major_formatter(ScalarFormatter())

    plt.savefig(f"{tag}/overall-data-movement.pdf", bbox_inches="tight", pad_inches=0.06)


def plot_compaction_work():
    convert_to = 1024**4

    rdb, skv, rr = [], [], []

    for scale in scales:
        rdb.append(
            (stats[scale]["RocksDB"][epoch_to_plot].CompactionReadBytes +
             stats[scale]["RocksDB"][epoch_to_plot].CompactionWrittenBytes) / convert_to
        )
        skv.append(
            (stats[scale]["SuccinctKV"][epoch_to_plot].CompactionReadBytes +
             stats[scale]["SuccinctKV"][epoch_to_plot].CompactionWrittenBytes) / convert_to
        )
        rr.append(
            (stats[scale]["RangeReduce[lb=T^-1ANDre=1]"][epoch_to_plot].CompactionReadBytes +
             stats[scale]["RangeReduce[lb=T^-1ANDre=1]"][epoch_to_plot].CompactionWrittenBytes) / convert_to
        )

    _, ax = plt.subplots(figsize=fig_size)
    ax.plot(scales, rdb, **line_styles["RocksDB"])
    ax.plot(scales, skv, **line_styles["SuccinctKV"])
    ax.plot(scales, rr, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

    ax.set_ylabel("compaction work (TB)")
    ax.set_xlabel("db size (GB)")
    ax.set_yticks([0, 0.2, 0.4])
    ax.set_ylim(0, 0.4)
    ax.yaxis.set_label_coords(-0.32, 0.34)
    ax.set_xscale("log", base=2)
    x_ticks = [1, 2, 4, 8]
    ax.set_xticks(x_ticks)
    from matplotlib.ticker import ScalarFormatter
    ax.xaxis.set_major_formatter(ScalarFormatter())

    plt.savefig(f"{tag}/compaction-work.pdf", bbox_inches="tight", pad_inches=0.06)


# ------------------------------------------------------------------------------
# Run all plots
# ------------------------------------------------------------------------------

plot_compaction_debt()
plot_space_amp()
plot_rq_bytes_read()
plot_rq_latency()
plot_total_data_movement()
plot_compaction_work()
plot_total_data_movement_normalized()