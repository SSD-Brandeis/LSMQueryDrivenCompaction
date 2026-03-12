import os
from pathlib import Path
from typing import Dict, List

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager
import matplotlib

from plotter import *
from plotter.dataclass import PlottingStats, RQColumn
from plotter.epochstats import EpochStats
from plotter.plotstyles import bar_styles

matplotlib.use("Agg")
prop = font_manager.FontProperties(fname="./plotter/LinLibertine_Mah.ttf")
plt.rcParams["font.family"] = prop.get_name()
plt.rcParams["text.usetex"] = True
# plt.rcParams["font.weight"] = "semibold"
plt.rcParams["font.size"] = 26

fig_size = (4, 2.5)
epoch_to_plot = -1

TAG = "newfigure4"

PROJECT_DIR = Path.cwd().parent.parent
SELECTIVITIES = [
    "0.00001",
    "0.0001",
    "0.001",
    # "0.0025",
    "0.003",
    # "0.005",
    "0.007",
    "0.01",
    # "0.1",
]
# sel_map = {
#     "0.00001": "0.00001",
#     "0.0001": "0.0001",
#     "0.001": "0.001",
#     "0.0025": "0.0025",
#     "0.003": "0.003",
#     "0.005": "0.005",
#     "0.007": "0.007",
#     "0.01": "0.01",
#     "0.1": "0.1",
# }
sel_map = {
    "0.00001": 0.00001,
    "0.0001": 0.0001,
    "0.001": 0.001,
    "0.0025": 0.0025,
    "0.003": 0.003,
    "0.005": 0.005,
    "0.007": 0.007,
    "0.01": 0.01,
    "0.1": 0.1,
}

system_stats: Dict[str, Dict[str, List[PlottingStats]]] = {
    "RocksDB": dict(),
    "RangeReduce[lb=0ANDsmlck=0]": dict(),  # MoS
    "RangeReduce[lb=0]": dict(),  # FSMoS
}
system_rq_stats: Dict[str, Dict[str, pd.DataFrame]] = {
    "RocksDB": dict(),
    "RangeReduce[lb=0ANDsmlck=0]": dict(),  # MoS
    "RangeReduce[lb=0]": dict(),  # FSMoS
}

for selectivity in SELECTIVITIES:
    lb = 1 / SIZE_RATIO
    EXPDIRNAME = f"{PROJECT_DIR}/.vstats_old/experiments-{TAG}-U{UPDATES}-E{ENTRY_SIZE}-B{ENTRIES_PER_PAGE}-S{RANGE_QUERIES}-Y{selectivity}-T{SIZE_RATIO}"

    rdb_dirpath = os.path.join(EXPDIRNAME, "RocksDB")
    mos_dirpath = os.path.join(EXPDIRNAME, "RangeReduce[lb=0ANDsmlck=0]")
    fsmos_dirpath = os.path.join(EXPDIRNAME, "RangeReduce[lb=0]")

    filesize = ENTRY_SIZE * ENTRIES_PER_PAGE * NUM_PAGE_PER_FILE
    max_lvl_mtx = []

    rdb = EpochStats(rdb_dirpath, filesize)
    max_lvl_mtx.append(rdb.get_max_levels())
    mos = EpochStats(mos_dirpath, filesize)
    max_lvl_mtx.append(mos.get_max_levels())
    fsmos = EpochStats(fsmos_dirpath, filesize)
    max_lvl_mtx.append(fsmos.get_max_levels())

    max_length_epoch = max([len(num_epochs) for num_epochs in max_lvl_mtx])
    max_lvl_per_epoch = [0] * max_length_epoch

    for col in max_lvl_mtx:
        for idx, row in enumerate(col):
            max_lvl_per_epoch[idx] = max(max_lvl_per_epoch[idx], row)

    system_stats["RocksDB"][selectivity] = rdb.get_plotstats(max_lvl_per_epoch)
    system_stats["RangeReduce[lb=0ANDsmlck=0]"][selectivity] = mos.get_plotstats(
        max_lvl_per_epoch
    )
    system_stats["RangeReduce[lb=0]"][selectivity] = fsmos.get_plotstats(
        max_lvl_per_epoch
    )
    system_rq_stats["RocksDB"][selectivity] = rdb.get_rangequerystats()
    system_rq_stats["RangeReduce[lb=0ANDsmlck=0]"][
        selectivity
    ] = mos.get_rangequerystats()
    system_rq_stats["RangeReduce[lb=0]"][selectivity] = fsmos.get_rangequerystats()


def plot_avg_files_sizes():
    convert_to_ = 1024**2
    ylabel = "avg. file size (MB)"
    desired_yticks = [0, 2, 4]

    file_sizes = dict()
    for approach, data in system_stats.items():
        file_sizes[approach] = {
            sel: (
                (stat[epoch_to_plot].DBSize / stat[epoch_to_plot].FilesCount)
                / convert_to_
            )
            for sel, stat in data.items()
        }
        # print(file_sizes[approach])

    x = np.arange(len(SELECTIVITIES))
    width = 0.25
    x_points = range(len(SELECTIVITIES))
    _, ax = plt.subplots(figsize=fig_size)

    ax.bar(
        x - width,
        [file_sizes["RocksDB"][sel] for sel in SELECTIVITIES],
        width,
        **bar_styles["RocksDB"],
    )
    ax.bar(
        x,
        [file_sizes["RangeReduce[lb=0ANDsmlck=0]"][sel] for sel in SELECTIVITIES],
        width,
        **bar_styles["RangeReduce[lb=0 & smlck=0]"],
    )
    ax.bar(
        x + width,
        [file_sizes["RangeReduce[lb=0]"][sel] for sel in SELECTIVITIES],
        width,
        **bar_styles["RangeReduce[lb=0]"],
    )

    ax.set_ylabel(ylabel)
    ax.set_yticks(desired_yticks)
    ax.set_yticklabels([str(tick) for tick in desired_yticks])
    ax.set_ylim(bottom=0, top=4.5)
    ax.yaxis.set_label_coords(-0.09, 0.35)

    ax.set_xlabel("selectivity")
    ax.set_xticks(x_points)
    ax.set_xticklabels(
        [f"{sel_map[str(per)]}" for per in SELECTIVITIES],
        rotation=90,
    )

    plt.savefig(f"{TAG}-avg-files-size.pdf", bbox_inches="tight", pad_inches=0.06)


def plot_files_count():
    convert_to_ = 1000
    ylabel = "file count"
    desired_yticks = [0, 0.5, 1]

    file_counts = dict()
    for approach, data in system_stats.items():
        file_counts[approach] = {
            sel: (stat[epoch_to_plot].FilesCount / convert_to_)
            for sel, stat in data.items()
        }
        # print(file_counts)

    x = np.arange(len(SELECTIVITIES))
    width = 0.25
    x_points = range(len(SELECTIVITIES))
    _, ax = plt.subplots(figsize=fig_size)

    ax.bar(
        x - width,
        [file_counts["RocksDB"][sel] for sel in SELECTIVITIES],
        width,
        **bar_styles["RocksDB"],
    )
    ax.bar(
        x,
        [file_counts["RangeReduce[lb=0ANDsmlck=0]"][sel] for sel in SELECTIVITIES],
        width,
        **bar_styles["RangeReduce[lb=0 & smlck=0]"],
    )
    ax.bar(
        x + width,
        [file_counts["RangeReduce[lb=0]"][sel] for sel in SELECTIVITIES],
        width,
        **bar_styles["RangeReduce[lb=0]"],
    )

    ax.set_ylabel(ylabel)
    ax.set_yticks(desired_yticks)
    ax.set_yticklabels([str(tick) for tick in desired_yticks])
    ax.set_ylim(bottom=0, top=desired_yticks[-1]+0.2)

    ax.set_xlabel("selectivity")
    ax.set_xticks(x_points)
    ax.set_xticklabels(
        [f"{sel_map[str(per)]}" for per in SELECTIVITIES],
        rotation=90,
    )

    plt.savefig(f"{TAG}-avg-files-count.pdf", bbox_inches="tight", pad_inches=0.06)

    handles, labels = ax.get_legend_handles_labels()
    legend_fig = plt.figure(figsize=(3.8, 0.4))

    legend_fig.legend(
        handles,
        labels,
        loc="center",
        ncol=3,
        frameon=False,
        columnspacing=1.2,
        handletextpad=0.4,
        borderaxespad=0,
    )

    legend_fig.subplots_adjust(left=0, right=1, top=1, bottom=0)
    legend_fig.savefig(f"{TAG}-legend.pdf", bbox_inches="tight", pad_inches=0)
    plt.close(legend_fig)


def avg_rq_read_amp():
    ylabel = "RQ avg. read amp."
    desired_yticks = [0, 0.5, 1]

    read_amp = dict()
    for approach, data in system_rq_stats.items():
        read_amp[approach] = {
            sel: (
                (df[str(RQColumn.TOTAL_ENTRIES_READ)].mean())
                / (sel_map[sel] * INSERTS)
            )
            for sel, df in data.items()
        }
        print(read_amp[approach])

    x = np.arange(len(SELECTIVITIES))
    width = 0.25
    x_points = range(len(SELECTIVITIES))
    _, ax = plt.subplots(figsize=fig_size)

    ax.bar(
        x - width,
        [read_amp["RocksDB"][sel] for sel in SELECTIVITIES],
        width,
        **bar_styles["RocksDB"],
    )
    ax.bar(
        x,
        [read_amp["RangeReduce[lb=0ANDsmlck=0]"][sel] for sel in SELECTIVITIES],
        width,
        **bar_styles["RangeReduce[lb=0 & smlck=0]"],
    )
    ax.bar(
        x + width,
        [read_amp["RangeReduce[lb=0]"][sel] for sel in SELECTIVITIES],
        width,
        **bar_styles["RangeReduce[lb=0]"],
    )

    ax.set_ylabel(ylabel)
    ax.set_yticks(desired_yticks)
    ax.set_yticklabels([str(tick) for tick in desired_yticks])
    ax.yaxis.set_label_coords(-0.15, 0.29)
    ax.set_ylim(bottom=0, top=1.5)

    ax.set_xlabel("selectivity")
    ax.set_xticks(x_points)
    ax.set_xticklabels(
        [f"{sel_map[str(per)]}" for per in SELECTIVITIES],
        rotation=90,
    )

    plt.savefig(
        f"{TAG}-avg-bytes-read-per-rq.pdf", bbox_inches="tight", pad_inches=0.06
    )


plot_avg_files_sizes()
plot_files_count()
avg_rq_read_amp()
