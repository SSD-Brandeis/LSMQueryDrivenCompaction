from copy import deepcopy
from enum import Enum
from typing import List, Dict

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from plotter import *
from .plotstyles import (
    bar_styles,
    line_styles_with_abbr,
    line_styles_no_marker_with_abbr,
    line_styles_no_marker,
)
from .dataclass import (
    AdditionalStats,
    PlottingStats,
    RQColumn,
    Approach,
    Metric,
    TABLE_DATA,
)

method_mapping = {
    "RocksDB": "RocksDB",
    "RocksDBTuned": "RocksDBTuned",
    "RangeReduce[lb=0 & smlck=0]": "MergeOnScan",
    "RangeReduce[lb=0]": "FileSizeAwareMergeOnScan",
    "RangeReduce[lb=T^-1]": "BoundedMerge",
    "RangeReduce[lb=T^-1 & re=1]": "RangeReduce[level renaming & bounded merge]",
}


def log_just_metric(approach_data: Dict[str, List[PlottingStats]], metric: Metric):
    if "RocksDB" in approach_data.keys():
        TABLE_DATA[str(Approach.ROCKSDB)][str(metric)] = approach_data["RocksDB"][0]
    if "RocksDB" in approach_data.keys() and "RocksDBTuned" in approach_data.keys():
        TABLE_DATA[str(Approach.ROCKSDB_TUNED)][str(metric)] = approach_data[
            "RocksDBTuned"
        ][0]
    if (
        "RocksDB" in approach_data.keys()
        and "RangeReduce[lb=0 & smlck=0]" in approach_data.keys()
    ):
        TABLE_DATA[str(Approach.RANGE_REDUCE_LB_0_AND_SMLCK_0)][str(metric)] = (
            approach_data["RangeReduce[lb=0 & smlck=0]"][0]
        )
    if (
        "RocksDB" in approach_data.keys()
        and "RangeReduce[lb=0]" in approach_data.keys()
    ):
        TABLE_DATA[str(Approach.RANGE_REDUCE_LB_0)][str(metric)] = approach_data[
            "RangeReduce[lb=0]"
        ][0]
    if "RocksDB" in approach_data.keys() and "SuccinctKV" in approach_data.keys():
        TABLE_DATA[str(Approach.SUCCINCT_KV)][str(metric)] = approach_data[
            "SuccinctKV"
        ][0]
    if (
        "RocksDB" in approach_data.keys()
        and "RangeReduce[lb=T^-1]" in approach_data.keys()
    ):
        TABLE_DATA[str(Approach.RANGE_REDUCE_LB_T_MINUS_1)][str(metric)] = (
            approach_data["RangeReduce[lb=T^-1]"][0]
        )
    if (
        "RocksDB" in approach_data.keys()
        and "RangeReduce[lb=T^-1 & re=1]" in approach_data.keys()
    ):
        TABLE_DATA[str(Approach.RANGE_REDUCE_LB_T_MINUS_1_AND_RE_1)][str(metric)] = (
            approach_data["RangeReduce[lb=T^-1 & re=1]"][0]
        )


def log_metric(approach_data: Dict[str, List[PlottingStats]], metric: Metric):
    if "RocksDB" in approach_data.keys():
        TABLE_DATA[str(Approach.ROCKSDB)][str(metric)] = round(
            approach_data["RocksDB"][0], 2
        )
    if "RocksDB" in approach_data.keys() and "RocksDBTuned" in approach_data.keys():
        TABLE_DATA[str(Approach.ROCKSDB_TUNED)][
            str(metric)
        ] = f'{round(((approach_data["RocksDBTuned"][0] - approach_data["RocksDB"][0])/ approach_data["RocksDB"][0]) * 100,2,)}%'
    if (
        "RocksDB" in approach_data.keys()
        and "RangeReduce[lb=0 & smlck=0]" in approach_data.keys()
    ):
        TABLE_DATA[str(Approach.RANGE_REDUCE_LB_0_AND_SMLCK_0)][
            str(metric)
        ] = f'{round(((approach_data["RangeReduce[lb=0 & smlck=0]"][0] - approach_data["RocksDB"][0]) / approach_data["RocksDB"][0]) * 100,2,)}%'
    if (
        "RocksDB" in approach_data.keys()
        and "RangeReduce[lb=0]" in approach_data.keys()
    ):
        TABLE_DATA[str(Approach.RANGE_REDUCE_LB_0)][
            str(metric)
        ] = f'{round(((approach_data["RangeReduce[lb=0]"][0] - approach_data["RocksDB"][0])/ approach_data["RocksDB"][0]) * 100,2,)}%'
    if "RocksDB" in approach_data.keys() and "SuccinctKV" in approach_data.keys():
        TABLE_DATA[str(Approach.SUCCINCT_KV)][
            str(metric)
        ] = f'{round(((approach_data["SuccinctKV"][0] - approach_data["RocksDB"][0])/ approach_data["RocksDB"][0]) * 100,2,)}%'
    if (
        "RocksDB" in approach_data.keys()
        and "RangeReduce[lb=T^-1]" in approach_data.keys()
    ):
        TABLE_DATA[str(Approach.RANGE_REDUCE_LB_T_MINUS_1)][
            str(metric)
        ] = f'{round(((approach_data["RangeReduce[lb=T^-1]"][0] - approach_data["RocksDB"][0])/ approach_data["RocksDB"][0]) * 100,2,)}%'
    if (
        "RocksDB" in approach_data.keys()
        and "RangeReduce[lb=T^-1 & re=1]" in approach_data.keys()
    ):
        TABLE_DATA[str(Approach.RANGE_REDUCE_LB_T_MINUS_1_AND_RE_1)][
            str(metric)
        ] = f'{round(((approach_data["RangeReduce[lb=T^-1 & re=1]"][0] - approach_data["RocksDB"][0])/ approach_data["RocksDB"][0]) * 100,2,)}%'


def human_readable_bytes(bytes_val):
    gb = bytes_val / (1024**3)
    if gb < 10:
        return f"{gb:.1f}"
    else:
        return f"{gb:.0f}"
    
def human_readable_tb_to_bytes(bytes_val):
    tb = bytes_val / (1024**4)
    if tb < 10:
        return f"{tb:.2f}"
    else:
        return f"{tb:.0f}"

class PlotEpochStats:
    bar_width = 0.55

    def __init__(self, approaches: Dict[str, List[PlottingStats]], approach_abr_order=List[str]):
        self.approaches_: Dict[str, List[PlottingStats]] = deepcopy(approaches)
        self.approach_abr_order = deepcopy(approach_abr_order)

        avg_bytes_written_by_RR: Dict[str, List[float]] = dict()
        total_files_count: Dict[str, List[float]] = dict()
        avg_file_size: Dict[str, List[float]] = dict()

        for approach, plot_stat in self.approaches_.items():
            # avg_bytes_written_by_RR[approach] = [
            #     plot_stat[-1].RangeReduceWrittenBytes
            #     / (TABLE_DATA[approach][str(Metric.RR_TRIGGERED_COUNT)] * 1024**2)
            # ]
            total_files_count[approach] = [plot_stat[-1].FilesCount]
            avg_file_size[approach] = [
                plot_stat[-1].DBSize / (plot_stat[-1].FilesCount * 1024**2)
            ]
            # log_just_metric(avg_bytes_written_by_RR, Metric.AVG_BYTES_WRITTENT_BY_RR)
            # log_metric(total_files_count, Metric.TOTAL_FILES_COUNT)
            log_just_metric(total_files_count, Metric.TOTAL_FILES_COUNT)
            log_just_metric(avg_file_size, Metric.AVG_FILE_SIZE)

    def plot_total_rq_bytes_written(self):
        convert_to_ = 1024**3
        approach_data: Dict[str, List[PlottingStats]] = dict()
        max_ylim = 0

        for approach, data in self.approaches_.items():
            approach_data[approach] = [
                (stat.RangeReduceWrittenBytes)
                # / convert_to_
                for stat in data
            ]
            # print(approach, " bytes: ", approach_data[approach][-1])
            max_ylim = max(max_ylim, max(approach_data[approach]))

        fig_size = (2.3, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        bar_containers = []

        for approach, data in approach_data.items():
            bars = ax.bar(
                approach,
                data[-1],
                width=self.bar_width,
                **bar_styles[approach],
            )
            bar_containers.append(bars)

        ax.set_ylabel("total RQ write (GB)")
        ax.set_xticks([])

        desired_yticks = [0, 5, 10]
        desired_tb_yticks = [byte * convert_to_ for byte in desired_yticks]
        ax.set_yticks(desired_tb_yticks)
        ax.set_yticklabels([0] + [f"{byte}" for byte in desired_yticks[1:]])

        ax.set_ylim(bottom=0, top=desired_yticks[-1] * convert_to_)
        ax.set_xticks(range(len(approach_data)))
        # ax.set_xticklabels([per for per in ['RDB', 'MOS', 'FSMS', 'BM']], rotation=90)
        ax.set_xticklabels([per for per in self.approach_abr_order], rotation=90)
        ax.yaxis.set_label_coords(x=-0.3, y=0.45)
        # ax.set_title("total write (compaction + RangeReduce compactions)")

        # fig.legend(
        #     loc="upper center",
        #     ncol=2,
        #     fontsize=10,
        #     bbox_to_anchor=(0.51, 0.90),
        #     frameon=False,
        #     columnspacing=0.5,
        # )
        # ax.text(
        #     -0.4, -0.46, "(E)", transform=ax.transAxes, fontweight="bold", va="bottom"
        # )

        for bars in bar_containers:
            for bar in bars:
                height = bar.get_height()
                label = human_readable_tb_to_bytes(height)

                if height < 0.5 * convert_to_:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        height,
                        label,
                        ha="center",
                        va="bottom",
                        fontsize=20,
                        rotation=90,   # vertical labels work better for narrow bars
                        clip_on=False
                    )

        # plt.tight_layout()
        plt.savefig(f"{TAG}-total-rq-writes.pdf", bbox_inches="tight", pad_inches=0.06)
        # plt.show()

    def plot_total_bytes_written(self):
        convert_to_ = 1024**3
        approach_data: Dict[str, List[PlottingStats]] = dict()
        max_ylim = 0

        for approach, data in self.approaches_.items():
            approach_data[approach] = [
                (stat.CompactionWrittenBytes + stat.RangeReduceWrittenBytes)
                # / convert_to_
                for stat in data
            ]
            # print(data)
            # print(" APPROACH: ", approach, " TOTAL: ", approach_data[approach])
            max_ylim = max(max_ylim, max(approach_data[approach]))

        log_metric(approach_data, Metric.TOTAL_WRITES)

        fig_size = (2.3, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        bar_containers = []

        for approach, data in approach_data.items():
            bars = ax.bar(
                approach,
                data[-1],
                width=self.bar_width,
                **bar_styles[approach],
            )
            bar_containers.append(bars)

        ax.set_ylabel("total write (GB)")
        ax.set_xticks([])

        desired_yticks = [0, 10, 20, 30]
        desired_tb_yticks = [byte * convert_to_ for byte in desired_yticks]
        ax.set_yticks(desired_tb_yticks)
        ax.set_yticklabels([0] + [f"{byte}" for byte in desired_yticks[1:]])

        ax.set_ylim(bottom=0, top=(desired_yticks[-1]+5) * convert_to_)
        ax.set_xticks(range(len(approach_data)))
        # ax.set_xticklabels([per for per in ['RDB', 'MOS', 'FSMS', 'BM']], rotation=90)
        ax.set_xticklabels([per for per in self.approach_abr_order], rotation=90)
        ax.yaxis.set_label_coords(x=-0.4, y=0.45)
        # ax.set_title("total write (compaction + RangeReduce compactions)")

        # fig.legend(
        #     loc="upper center",
        #     ncol=2,
        #     fontsize=10,
        #     bbox_to_anchor=(0.51, 0.90),
        #     frameon=False,
        #     columnspacing=0.5,
        # )
        ax.text(
            -0.4, -0.46, "(E)", transform=ax.transAxes, fontweight="bold", va="bottom"
        )

        for bars in bar_containers:
            for bar in bars:
                height = bar.get_height()
                label = human_readable_tb_to_bytes(height)

                if height < 0.5 * convert_to_:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        height,
                        label,
                        ha="center",
                        va="bottom",
                        fontsize=20,
                        rotation=90,   # vertical labels work better for narrow bars
                        clip_on=False
                    )

        # plt.tight_layout()
        plt.savefig(f"{TAG}-total-writes.pdf", bbox_inches="tight", pad_inches=0.06)
        # plt.show()

    def plot_database_size(self):
        convert_to_ = 1024**2
        approach_data: Dict[str, List[PlottingStats]] = dict()
        max_ylim = 0

        for approach, data in self.approaches_.items():
            approach_data[approach] = [stat.DBSize / convert_to_ for stat in data]
            max_ylim = max(max_ylim, max(approach_data[approach]))

        fig_size = (7, 5)
        fig, ax = plt.subplots(figsize=fig_size)

        for approach, data in approach_data.items():
            ax.bar(
                approach,
                data,
                **bar_styles[approach],
            )

        ax.set_ylabel("Database Size (MB)", fontsize=12)
        ax.set_xlabel("system", fontsize=12)
        ax.set_ylim(bottom=0, top=max_ylim + max_ylim * 0.25)
        ax.set_xticks([])

        fig.legend(
            loc="upper center",
            ncol=2,
            fontsize=10,
            bbox_to_anchor=(0.51, 0.90),
            frameon=False,
            columnspacing=0.5,
        )
        # plt.show()

    def plot_compaction_debt(self):
        convert_to_ = 1024**3
        approach_data: Dict[str, List[PlottingStats]] = dict()
        max_ylim = 0

        for approach, data in self.approaches_.items():
            approach_data[approach] = [
                data[-1].CompactionDebt
                # / convert_to_
                # for stat in data
            ]
            max_ylim = max(max_ylim, max(approach_data[approach]))

        # print(approach_data)

        log_metric(approach_data, Metric.COMPACTION_DEBT)

        fig_size = (2.3, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        bar_containers = []

        for approach, data in approach_data.items():
            bars = ax.bar(
                approach,
                data,
                width=self.bar_width,
                **bar_styles[approach],
            )
            bar_containers.append(bars)

        ax.set_ylabel("compaction debt (GB)")
        ax.yaxis.set_label_coords(-0.35, 0.31)
        # ax.set_xlabel("system")

        desired_yticks = [0, 10, 20]
        desired_tb_yticks = [byte * convert_to_ for byte in desired_yticks]
        ax.set_yticks(desired_tb_yticks)
        ax.set_yticklabels([0] + [f"{byte}" for byte in desired_yticks[1:]])

        ax.set_ylim(bottom=0, top=desired_tb_yticks[-1])
        ax.set_xticks(range(len(approach_data)))
        # ax.set_xticklabels([per for per in ['RDB', 'MOS', 'FSMS', 'BM']], rotation=90)
        ax.set_xticklabels([per for per in self.approach_abr_order], rotation=90)

        # fig.legend(
        #     loc="upper center",
        #     ncol=2,
        #     bbox_to_anchor=(0.51, 0.90),
        #     frameon=False,
        #     columnspacing=0.5,
        # )
        ax.text(
            -0.25, -0.46, "(C)", transform=ax.transAxes, fontweight="bold", va="bottom"
        )

        for bars in bar_containers:
            for bar in bars:
                height = bar.get_height()
                label = human_readable_bytes(height)

                if (height < 5*convert_to_):
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        height,
                        label,
                        ha="center",
                        va="bottom",
                        fontsize=20,
                        rotation=90,   # vertical labels work better for narrow bars
                        clip_on=False
                    )

        # plt.tight_layout()
        plt.savefig(f"{TAG}-compaction-debt.pdf", bbox_inches="tight", pad_inches=0.06)

        handles, labels = ax.get_legend_handles_labels()

        # Create a new figure solely for the legend
        legend_fig = plt.figure(figsize=(8, 2))

        # Add legend to the new figure (centered, with 2 columns and desired spacing)
        legend_fig.legend(
            handles,
            labels,
            loc="center",
            ncol=5,
            frameon=False,
            borderaxespad=0,
            labelspacing=0,
            borderpad=0,
            columnspacing=0.4,
            handletextpad=0.2,
            handlelength=1,
            handleheight=1,
        )

        # Save the legend figure separately; bbox_inches='tight' helps crop extra whitespace.
        legend_fig.savefig(
            f"{TAG}-bounded-metric-legend.pdf", bbox_inches="tight", pad_inches=0.015
        )
        # plt.show()

    def plot_write_amp_debt(self):
        convert_to_ = 1024**2
        approach_data: Dict[str, List[PlottingStats]] = dict()
        max_ylim = 0

        for approach, data in self.approaches_.items():
            approach_data[approach] = [stat.WriteAmpDebt / convert_to_ for stat in data]
            max_ylim = max(max_ylim, max(approach_data[approach]))

        fig_size = (7, 5)
        fig, ax = plt.subplots(figsize=fig_size)

        for approach, data in approach_data.items():
            ax.bar(
                approach,
                data,
                **bar_styles[approach],
            )

        ax.set_ylabel("write amp. debt (MB)", fontsize=12)
        ax.set_xlabel("system", fontsize=12)
        ax.set_ylim(bottom=0, top=max_ylim + max_ylim * 0.25)
        ax.set_xticks([])

        fig.legend(
            loc="upper center",
            ncol=2,
            fontsize=10,
            bbox_to_anchor=(0.51, 0.90),
            frameon=False,
            columnspacing=0.5,
        )
        # plt.show()

    def plot_write_amp_full_debt(self):
        convert_to_ = 1024**2
        approach_data: Dict[str, List[PlottingStats]] = dict()
        max_ylim = 0

        for approach, data in self.approaches_.items():
            approach_data[approach] = [
                stat.WriteAmpDebtFull / convert_to_ for stat in data
            ]
            max_ylim = max(max_ylim, max(approach_data[approach]))

        fig_size = (7, 5)
        fig, ax = plt.subplots(figsize=fig_size)

        for approach, data in approach_data.items():
            ax.bar(
                approach,
                data,
                **bar_styles[approach],
            )

        ax.set_ylabel("write amp. full debt (MB)", fontsize=12)
        ax.set_xlabel("system", fontsize=12)
        ax.set_ylim(bottom=0, top=max_ylim + max_ylim * 0.25)
        ax.set_xticks([])

        fig.legend(
            loc="upper center",
            ncol=2,
            fontsize=10,
            bbox_to_anchor=(0.51, 0.90),
            frameon=False,
            columnspacing=0.5,
        )
        # plt.show()

    def plot_write_amp_partial_debt(self):
        convert_to_ = 1024**2
        approach_data: Dict[str, List[PlottingStats]] = dict()
        max_ylim = 0

        for approach, data in self.approaches_.items():
            approach_data[approach] = [
                stat.WriteAmpDebtPartial / convert_to_ for stat in data
            ]
            max_ylim = max(max_ylim, max(approach_data[approach]))

        fig_size = (7, 5)
        fig, ax = plt.subplots(figsize=fig_size)

        for approach, data in approach_data.items():
            ax.bar(
                approach,
                data,
                **bar_styles[approach],
            )

        ax.set_ylabel("write amp. partial debt (MB)", fontsize=12)
        ax.set_xlabel("system", fontsize=12)
        ax.set_ylim(bottom=0, top=max_ylim + max_ylim * 0.25)
        ax.set_xticks([])

        fig.legend(
            loc="upper center",
            ncol=2,
            fontsize=10,
            bbox_to_anchor=(0.51, 0.90),
            frameon=False,
            columnspacing=0.5,
        )
        # plt.show()

    def plot_space_amplification(self):
        approach_data: Dict[str, List[PlottingStats]] = dict()
        max_ylim = 0

        for approach, data in self.approaches_.items():
            print(" Approach: ", approach, " DBSize: ", data[-1].DBSize, " IDEAL SIZE:", (INSERTS * ENTRY_SIZE))
            approach_data[approach] = [data[-1].DBSize / (INSERTS * ENTRY_SIZE)]
            max_ylim = max(max_ylim, max(approach_data[approach]))

        log_metric(approach_data, Metric.SPACE_AMP)

        fig_size = (2.3, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        bar_containers = []
        for approach, data in approach_data.items():
            bars = ax.bar(
                approach,
                data,
                width=self.bar_width,
                **bar_styles[approach],
            )
            bar_containers.append(bars)

        ax.set_ylabel("space amplification")
        ax.yaxis.set_label_coords(-0.35, 0.34)

        # ax.set_xlabel("system")
        ax.set_ylim(bottom=0, top=max_ylim + max_ylim * 0.30)
        ax.set_xticks(range(len(approach_data)))
        # ax.set_xticklabels([per for per in ['RDB', 'MOS', 'FSMS', 'BM']], rotation=90)
        ax.set_xticklabels([per for per in self.approach_abr_order], rotation=90)
        ax.text(
            -0.25, -0.46, "(D)", transform=ax.transAxes, fontweight="bold", va="bottom"
        )

        for bars in bar_containers:
            for bar in bars:
                height = bar.get_height()
                label = f"{height:.2f}"

                if (height < 1.3):
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        height,
                        label,
                        ha="center",
                        va="bottom",
                        fontsize=20,
                        rotation=90,   # vertical labels work better for narrow bars
                        clip_on=False
                    )

        # plt.tight_layout()
        plt.savefig(
            f"{TAG}-space-amplification.pdf", bbox_inches="tight", pad_inches=0.06
        )
        # plt.show()

    def plot_compaction_read(self):
        convert_to_ = 1024**3
        approach_data: Dict[str, List[PlottingStats]] = dict()
        max_ylim = 0

        for approach, data in self.approaches_.items():
            approach_data[approach] = [
                stat.CompactionReadBytes / convert_to_ for stat in data
            ]
            max_ylim = max(max_ylim, max(approach_data[approach]))

        log_metric(approach_data, Metric.TOTAL_COMP_READ_NOT_FOR_RR)

        fig_size = (7, 5)
        fig, ax = plt.subplots(figsize=fig_size)

        for approach, data in approach_data.items():
            ax.bar(
                approach,
                data,
                **bar_styles[approach],
            )

        ax.set_ylabel("compaction read (GB)", fontsize=12)
        ax.set_xlabel("system", fontsize=12)
        ax.set_ylim(bottom=0, top=max_ylim + max_ylim * 0.25)
        ax.set_xticks([])

        fig.legend(
            loc="upper center",
            ncol=2,
            fontsize=10,
            bbox_to_anchor=(0.51, 0.90),
            frameon=False,
            columnspacing=0.5,
        )
        # plt.show()

    def plot_workload_exec_time(self):
        convert_to_ = 1000**3
        to_hours = 1 / (60 * 60)
        approach_data: Dict[str, List[PlottingStats]] = dict()
        max_ylim = 0

        for approach, data in self.approaches_.items():
            approach_data[approach] = [stat.WorkloadExecutionTime for stat in [data[-1]]]
            max_ylim = max(max_ylim, max(approach_data[approach]))

        log_metric(approach_data, Metric.WL_EXECUTION_TIME)

        fig_size = (2.3, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        for approach, data in approach_data.items():
            ax.bar(
                approach,
                data,
                width=self.bar_width,
                **bar_styles[approach],
            )

        ax.set_ylabel("execution time (hr)")
        ax.yaxis.set_label_coords(-0.3, 0.34)
        ax.set_xticks([])

        desired_yticks = [0, 2, 4]
        desired_sec_yticks = [
            (byte / to_hours) * convert_to_ for byte in desired_yticks
        ]
        ax.set_yticks(desired_sec_yticks)
        ax.set_yticklabels([0] + [f"{byte:.1f}" for byte in desired_yticks[1:]])

        ax.set_ylim(bottom=0, top=(5 / to_hours) * convert_to_)
        ax.set_xticks(range(len(approach_data)))
        # ax.set_xticklabels([per for per in ['RDB', 'MOS', 'FSMS', 'BM']], rotation=90)
        ax.set_xticklabels([per for per in self.approach_abr_order], rotation=90)
        # ax.set_title("total write (compaction + RangeReduce compactions)")

        ax.text(
            -0.25, -0.46, "(F)", transform=ax.transAxes, fontweight="bold", va="bottom"
        )
        plt.savefig(
            f"{TAG}-wkl-execution-time.pdf", bbox_inches="tight", pad_inches=0.06
        )
    def plot_levels_state(self):
        vanilla_levels_state = [van.LevelsState for van in self._vanilla]
        rqdc_levels_state = [rqdc.LevelsState for rqdc in self._rqdc]

        fig_size = (7, 5)
        bar_width = 0.3
        # num_bars_per_group = 2
        epochs = NUMEPOCHS
        num_lvls = len(vanilla_levels_state[0])

        colors = [
            "palegreen",
            "steelblue",
            "palevioletred",
            "salmon",
            "darkkhaki",
            "teal",
            "slateblue",
            "goldenrod",
            "mediumorchid",
            "indianred",
            "lightcoral",
            "deepskyblue",
            "limegreen",
            "coral",
            "orchid",
            "crimson",
            "darkseagreen",
            "royalblue",
            "firebrick",
            "turquoise",
            "lavender",
            "navajowhite",
            "sienna",
            "dodgerblue",
            "forestgreen",
            "chocolate",
            "lightblue",
            "thistle",
            "plum",
            "mediumslateblue",
        ]

        index = np.arange(epochs)
        fig, ax = plt.subplots(figsize=fig_size)

        bottom = np.zeros(epochs)

        for lvl in range(num_lvls):
            values = [vanilla_levels_state[j][lvl] for j in range(epochs)]
            ax.bar(
                index - bar_width / 2,
                values,
                bar_width,
                bottom,
                color=colors[lvl],
                label=f"level {lvl}",
                edgecolor="black",
            )
            bottom += values

        bottom = np.zeros(epochs)

        for lvl in range(num_lvls):
            values = [rqdc_levels_state[j][lvl] for j in range(epochs)]
            ax.bar(
                index + bar_width / 2,
                values,
                bar_width,
                bottom,
                color=colors[lvl],
                edgecolor="black",
            )
            bottom += values

        ax.set_ylabel("files count", fontsize=12)
        ax.set_xlabel("epoch", fontsize=12)

        ax.set_xticks(range(epochs))
        ax.set_xticklabels([f"{epoch}" for epoch in range(1, epochs + 1)], fontsize=12)

        fig.legend(
            loc="upper center",
            ncol=4,
            fontsize=12,
            bbox_to_anchor=(0.5, 1.09),
            frameon=False,
        )

        # plt.show()


class PlotRangeQueryStats:

    def __init__(self, approaches: Dict[str, pd.DataFrame]):
        self.approaches_: Dict[str, pd.DataFrame] = deepcopy(approaches)
        self.approaches_order = ["RocksDB", "SuccinctKV","RangeReduce[lb=0]", "RangeReduce[lb=0 & smlck=0]", "RangeReduce[lb=T^-1]"]
        # ["RocksDB", "SuccinctKV", "RangeReduce[lb=0]", "RangeReduce[lb=T^-1]", "RangeReduce[lb=0 & smlck=0]"]

        rr_triggered_count = dict()
        for approach, df in self.approaches_.items():
            rr_triggered_count[approach] = [df[str(RQColumn.DID_RUN_RR)].sum()]
        log_just_metric(rr_triggered_count, Metric.RR_TRIGGERED_COUNT)

    def _get_percentiles(self, data: pd.Series) -> AdditionalStats:
        percentiles = data.quantile([0.9, 0.95, 0.98, 0.99]).to_dict()
        return AdditionalStats(
            min=data.min(),
            max=data.max(),
            mean=data.mean(),
            std=data.std(),
            p90th=percentiles[0.9],
            p95th=percentiles[0.95],
            p98th=percentiles[0.98],
            p99th=percentiles[0.99],
        )

    def _plot_percentiles(self, data: Dict[str, AdditionalStats], ax):
        cell_text = list()
        rows = list()

        for approach, d in data.items():
            cell_text.append(
                [
                    f"{d.min:.2f}",
                    f"{d.mean:.2f}",
                    f"{d.std:.2f}",
                    f"{d.p90th:.2f}",
                    f"{d.p95th:.2f}",
                    f"{d.p98th:.2f}",
                    f"{d.p99th:.2f}",
                    f"{d.max:.2f}",
                ]
            )
            rows.append(approach)

        # Add a table at the bottom of the axes
        ax.table(
            cellText=cell_text,
            rowLabels=rows,
            colLabels=["Min", "Mean", "Std", "90th", "95th", "98th", "99th", "Max"],
            loc="bottom",
            bbox=[0.28, -0.55, 0.6, 0.35],
        )

        plt.show()

    def plot_did_rq_run(self):
        convert_to = 1
        approach_data = dict()

        for appraoch, data in self.approaches_.items():
            approach_data[appraoch] = data[str(RQColumn.DID_RUN_RR)].sum()
        
        fig_size = (2.3, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        for approach, data in approach_data.items():
            ax.bar(approach, data, width=0.55, **bar_styles[approach])

        ax.set_ylabel("count")

        # desired_yticks = [0, 2, 4, 6, 8]
        # desired_tb_yticks = [num * convert_to for num in desired_yticks]
        # ax.set_yticks(desired_tb_yticks)
        # ax.set_yticklabels([f"{num}" for num in desired_yticks])

        ax.set_xticks(range(len(approach_data)))
        # ax.set_xticklabels([per for per in ['RDB', 'MOS', 'FSMS', 'BM']], rotation=90)
        ax.set_xticklabels([per for per in ["RDB", "SKV", "MoS", "FSMoS", "BM"]], rotation=90)

        plt.savefig(f"{TAG}-did-optimization-trigger.pdf", bbox_inches="tight", pad_inches=0.06)

    def bytes_read_for_each_range_query(self, range_query_pattern=""):
        convert_to_ = 1024**2
        approach_data = dict()

        for approach, data in self.approaches_.items():
            approach_data[approach] = (
                data[[str(RQColumn.TOTAL_ENTRIES_READ)]]
                .apply(lambda x: x * ENTRY_SIZE)[str(RQColumn.TOTAL_ENTRIES_READ)]
                .to_list()
            )

        fig_size = (5, 4.3)
        fig, ax = plt.subplots(figsize=fig_size)

        step = 30
        for approach in self.approaches_order: #, ]:
            data = [d / convert_to_ for d in approach_data[approach]]
            ax.plot(
                range(len(data)),
                data,
                # label=method_mapping[approach],
                alpha=0.8,
                **line_styles_no_marker[approach],
            )
            # print(approach, "mean: ", f"{sum(data)/len(data):.2f}", " min: ", f"{min(data):.2f}", " max: ", f"{max(data):.2f}" )

            # Compute and plot the rolling average
            # series_data = pd.Series(data)
            # rolling_avg = series_data.rolling(window=500, min_periods=1).mean()
            # ax.plot(
            #     range(0, len(data), step),
            #     rolling_avg[::step],
            #     # label=method_mapping[approach],
            #     alpha=0.8,
            #     **line_styles_no_marker[approach],
            # )

        ax.set_ylabel("bytes read (MB)")
        ax.set_xlabel("range query number")
        ax.yaxis.set_label_coords(-0.15, 0.42)

        ax.set_ylim(bottom=0)

        # ax.xaxis.set_major_locator(ticker.FixedLocator(ax.get_xticks()))
        # ax.set_xticklabels([f"{int(tick)}" for tick in ax.get_xticks()])

        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))

        desired_mb_ticks = [0, 100]
        desired_byte_ticks = [mb for mb in desired_mb_ticks]
        ax.set_yticks(desired_byte_ticks)
        ax.set_yticklabels([0] + [str(round(mb)) for mb in desired_mb_ticks[1:]])
        ax.set_ylim(0, desired_mb_ticks[-1] + 25)
        # ax.set_yticklabels(
        #     [f"{int(i/convert_to_)}" if i != 0 else "0" for i in ax.get_yticks()]
        # )

        # desired_xticks = [0, 2250, 4500, 6750, 9000]
        # ax.set_xticks(desired_xticks)
        # ax.set_xticklabels([str(x) for x in desired_xticks])

        ax.text(
            -0.15, -0.3, "(A)", transform=ax.transAxes, fontweight="bold", va="bottom"
        )
        # ax.text(
        #     0.2,
        #     0.1,
        #     "500-point rolling average",
        #     transform=ax.transAxes,
        #     fontweight="bold",
        #     va="bottom",
        #     fontsize=20,
        # )

        # fig.legend(
        #     loc="lower center",
        #     ncol=5,
        #     fontsize=12,
        #     bbox_to_anchor=(0.5, 0.1),
        #     frameon=False,
        # )
        plt.tight_layout()
        plt.savefig(
            f"{TAG}-range-query-bytes-read.pdf", bbox_inches="tight", pad_inches=0.06
        )

        additional_stats: Dict[str, AdditionalStats] = dict()
        log_metric_stats: Dict[str, List[float]] = dict()

        for approach, data in approach_data.items():
            additional_stats[approach] = self._get_percentiles(
                pd.Series([x / convert_to_ for x in data])
            )
            log_metric_stats[approach] = [additional_stats[approach].mean]

        # # log_metric(log_metric_stats, Metric.AVG_BYTES_READ_RQ)
        log_just_metric(log_metric_stats, Metric.AVG_BYTES_READ_RQ)
        log_just_metric(log_metric_stats, Metric.AVG_BYTES_READ_RQ)
        # self._plot_percentiles(additional_stats, ax)

        # plt.show()

    def latency_for_each_range_query(self, range_query_pattern=""):
        plotting_column = str(RQColumn.RQ_TOTAL_TIME)
        convert_to_ = 1000**3
        approach_data = dict()

        for approach, data in self.approaches_.items():
            approach_data[approach] = data[plotting_column].to_list()

        fig_size = (5, 4.3)
        fig, ax = plt.subplots(figsize=fig_size)

        step = 30

        for approach in self.approaches_order:
            data = [d / convert_to_ for d in approach_data[approach]]
            ax.plot(
                range(len(data)),
                data,
                # label=approach,
                alpha=0.8,
                **line_styles_no_marker_with_abbr[approach],
            )
            # print(approach, "latency mean: ", f"{sum(data)/len(data):.2f}", " min: ", f"{min(data):.2f}", " max: ", f"{max(data):.2f}" )
            # Compute and plot the rolling average
            # series_data = pd.Series(data)
            # rolling_avg = series_data.rolling(window=500, min_periods=1).mean()
            # ax.plot(
            #     range(0, len(data), step),
            #     rolling_avg[::step],
            #     # label=method_mapping[approach],
            #     alpha=0.8,
            #     **line_styles_no_marker_with_abbr[approach],
            # )

        ax.set_ylabel("latency (s)")  # µ
        ax.set_xlabel("range query number")

        ax.xaxis.set_major_locator(ticker.FixedLocator(ax.get_xticks()))
        ax.set_xticklabels([f"{int(tick)}" for tick in ax.get_xticks()])
        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))

        # desired_ticks = [0, 0.1]
        # desired_sec_ticks = [mb * convert_to_ for mb in desired_ticks]
        # ax.set_yticks(desired_sec_ticks)
        # ax.set_yticklabels([0] + [str(round(mb)) for mb in desired_ticks[1:]])
        # ax.set_yticklabels(
        #     [f"{i/convert_to_}" if i != 0 else "0" for i in ax.get_yticks()]
        # )
        # ax.set_ylim(bottom=0, top=desired_sec_ticks[-1])

        # desired_xticks = [0, 2250, 4500, 6750, 9000]
        # ax.set_xticks(desired_xticks)
        # ax.set_xticklabels([str(x) for x in desired_xticks])

        ax.text(
            -0.18, -0.3, "(B)", transform=ax.transAxes, fontweight="bold", va="bottom"
        )
        # ax.text(
        #     0.2,
        #     0.1,
        #     "500-point rolling average",
        #     transform=ax.transAxes,
        #     fontweight="bold",
        #     va="bottom",
        #     fontsize=20,
        # )

        # fig.legend(
        #     loc="lower center",
        #     ncol=5,
        #     fontsize=12,
        #     bbox_to_anchor=(0.5, 0.1),
        #     frameon=False,
        # )

        plt.tight_layout()
        plt.savefig(
            f"{TAG}-range-query-latency.pdf", bbox_inches="tight", pad_inches=0.04
        )
        plt.close(fig)

        # Create a new figure solely for the legend
        legend_fig = plt.figure(figsize=(8, 2))

        # Add your custom text above the legend
        # legend_text = r"E=128\hspace{1cm}I=8388608\hspace{1cm}U=8388608\hspace{1cm}S=900\hspace{1cm}T=6\hspace{1cm}B=32\hspace{1cm}P=1024"
        legend_text = (
            f"M={round((ENTRY_SIZE*ENTRIES_PER_PAGE*NUM_PAGE_PER_FILE)/(1024*1024))}MB\\hspace{{1cm}}"
            f"E={ENTRY_SIZE}B\\hspace{{1cm}}"
            f"T={SIZE_RATIO}\\hspace{{1cm}}"
            f"I={round(INSERTS/1000000, 1)}M\\hspace{{1cm}}"
            f"U={round(UPDATES/1000000, 1)}M\\hspace{{1cm}}"
            f"S={round(RANGE_QUERIES/1000)}K\\hspace{{1cm}}"
            f"s={SELECTIVITY}\\hspace{{1cm}}"
            # f"B={ENTRIES_PER_PAGE}\\hspace{{1cm}}"
            # f"P={NUM_PAGE_PER_FILE}"
        )
        legend_fig.text(0.5, 0.85, legend_text, ha="center", va="center")
        legend_fig.savefig(
            f"{TAG}-bounded-legend-config.pdf", bbox_inches="tight", pad_inches=0.015
        )
        plt.close(legend_fig)

        handles, labels = ax.get_legend_handles_labels()

        # Create a new figure solely for the legend
        legend_fig = plt.figure(figsize=(8, 2))

        # Add legend to the new figure (centered, with 2 columns and desired spacing)
        legend_fig.legend(
            handles,
            labels,
            loc="center",
            ncol=5,
            frameon=False,
            borderaxespad=0,
            labelspacing=2,
            borderpad=0,
            columnspacing=0.4,
            handletextpad=0.2,
            handlelength=2,
            handleheight=1,
        )

        # Save the legend figure separately; bbox_inches='tight' helps crop extra whitespace.
        legend_fig.savefig(
            f"{TAG}-bounded-legend.pdf", bbox_inches="tight", pad_inches=0.015
        )
        plt.close(legend_fig)

        additional_stats: Dict[str, AdditionalStats] = dict()
        log_metric_stats: Dict[str, List[float]] = dict()
        log_metric_stats_98: Dict[str, List[float]] = dict()
        log_metric_stats_100: Dict[str, List[float]] = dict()

        for approach, data in approach_data.items():
            additional_stats[approach] = self._get_percentiles(
                pd.Series([x / convert_to_ for x in data])
            )
            log_metric_stats[approach] = [additional_stats[approach].mean]
            log_metric_stats_98[approach] = [additional_stats[approach].p98th]
            log_metric_stats_100[approach] = [additional_stats[approach].max]

        log_metric(log_metric_stats, Metric.AVG_RQ_LATENCY)
        log_metric(log_metric_stats_98, Metric.TAIL_RQ_LATENCY_98)
        log_metric(log_metric_stats_100, Metric.TAIL_RQ_LATENCY_100)
        # self._plot_percentiles(additional_stats, ax)

        # plt.show()

    def plot_instructions_executed_per_range_query(self):
        approach_data = dict()
        convert_to_ = 10**9  # Convert to billions for easier readability

        for approach, data in self.approaches_.items():
            approach_data[approach] = (
                data[[str(RQColumn.INSTRUCTIONS)]]
                .apply(lambda x: x / convert_to_)[str(RQColumn.INSTRUCTIONS)]
                .to_list()
            )

        fig_size = (6, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        for approach, data in approach_data.items():
            # Compute and plot the rolling average
            series_data = pd.Series(data)
            rolling_avg = series_data.rolling(window=500, min_periods=1).mean()
            ax.plot(
                range(len(data)),
                rolling_avg,
                # label=method_mapping[approach],
                alpha=0.8,
                **line_styles_with_abbr[approach],
            )
        ax.set_ylabel("instructions count (B)")
        ax.set_xlabel("range query number")
        ax.set_ylim(bottom=0, top=5)

        desired_xticks = [0, 2250, 4500, 6750, 9000]
        ax.set_xticks(desired_xticks)
        ax.set_xticklabels([str(x) for x in desired_xticks])
        plt.tight_layout()
        plt.savefig(
            f"{TAG}-instrcutions-per-range-query.pdf",
            bbox_inches="tight",
            pad_inches=0.04,
        )

    def plot_CPU_cycles_spent_per_range_query(self):
        approach_data = dict()
        convert_to_ = 10**9  # Convert to billions for easier readability

        for approach, data in self.approaches_.items():
            approach_data[approach] = (
                data[[str(RQColumn.CYCLES)]]
                .apply(lambda x: x / convert_to_)[str(RQColumn.CYCLES)]
                .to_list()
            )

        fig_size = (6, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        for approach, data in approach_data.items():
            # Compute and plot the rolling average
            series_data = pd.Series(data)
            rolling_avg = series_data.rolling(window=500, min_periods=1).mean()
            ax.plot(
                range(len(data)),
                rolling_avg,
                # label=method_mapping[approach],
                alpha=0.8,
                **line_styles_with_abbr[approach],
            )
        ax.set_ylabel("CPU cycles (B)")
        ax.set_xlabel("range query number")
        ax.set_ylim(bottom=0)

        desired_xticks = [0, 2250, 4500, 6750, 9000]
        ax.set_xticks(desired_xticks)
        ax.set_xticklabels([str(x) for x in desired_xticks])
        plt.tight_layout()
        plt.savefig(
            f"{TAG}-cpu-cycles-per-range-query.pdf",
            bbox_inches="tight",
            pad_inches=0.04,
        )

        plt.show()

    def cummulative_latency_for_range_queries(self, range_query_pattern=""):
        plotting_column = str(RQColumn.RQ_TOTAL_TIME)
        convert_to_ = 1000**3
        approach_data = dict()

        for approach, data in self.approaches_.items():
            approach_data[approach] = (
                pd.Series(data[plotting_column].to_list()).cumsum() / convert_to_
            )

        fig_size = (16, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        for approach, data in approach_data.items():
            ax.plot(
                range(len(data)),
                data,
                label=approach,
                alpha=0.8,
                **bar_styles[approach],
            )

        ax.set_ylabel("Cumulative latency (sec)", fontsize=12)
        ax.set_xlabel("range query number", fontsize=12)
        ax.legend(
            loc="lower center",
            ncol=5,
            fontsize=12,
            bbox_to_anchor=(0.5, 0.85),
            frameon=False,
        )

        plt.tight_layout()
        # plt.show()


def plot_total_data_movement(
    approaches_plotting_stats: Dict[str, List[PlottingStats]],
    approaches_rq_stats: Dict[str, pd.DataFrame],
    approach_abr_order: List[str],
):
    bar_width = 0.55

    convert_to_ = 1024**4
    plotting_stats = deepcopy(approaches_plotting_stats)
    rq_stats = deepcopy(approaches_rq_stats)
    max_ylim = 0

    approach_data: Dict[str, int] = dict()
    log_metric_stats: Dict[str, List] = dict()

    for approach, data in rq_stats.items():
        approach_data[approach] = (
            data[str(RQColumn.TOTAL_ENTRIES_READ)].sum() * ENTRY_SIZE
        )

    for approach, data in plotting_stats.items():
        approach_data[approach] += (
            data[-1].CompactionReadBytes
            + data[-1].CompactionWrittenBytes
            + data[-1].RangeReduceWrittenBytes
        )

    fig_size = (2.3, 4)
    fig, ax = plt.subplots(figsize=fig_size)

    bar_containers = []

    for approach, data in approach_data.items():
        bars = ax.bar(
            approach,
            data,
            width=bar_width,
            # / convert_to_,
            **bar_styles[approach],
        )
        bar_containers.append(bars)
        max_ylim = max(max_ylim, (data / convert_to_))
        log_metric_stats[approach] = [data / convert_to_]

    log_metric(log_metric_stats, Metric.OVERALL_DATA_MOVEMENT)

    ax.set_ylabel("data movement (TB)")
    ax.yaxis.set_label_coords(-0.30, 0.30)
    # ax.set_xlabel("system")

    desired_ticks = [0, 0.05, 0.1]
    desired_tb_ticks = [byte * convert_to_ for byte in desired_ticks]
    ax.set_yticks(desired_tb_ticks)
    ax.set_yticklabels([0] + [str(f"{tb:.1f}") for tb in desired_ticks[1:]])

    ax.set_ylim(bottom=0, top=desired_ticks[-1] * convert_to_)
    ax.set_xticks(range(len(approach_data)))
    # ax.set_xticklabels([per for per in ['RDB', 'MOS', 'FSMS', 'BM']], rotation=90)
    ax.set_xticklabels([per for per in approach_abr_order], rotation=90)

    # fig.legend(
    #     loc="upper center",
    #     ncol=2,
    #     fontsize=10,
    #     bbox_to_anchor=(0.51, 0.90),
    #     frameon=False,
    #     columnspacing=0.5,
    # )
    ax.text(-0.25, -0.46, "(E)", transform=ax.transAxes, fontweight="bold", va="bottom")

    for bars in bar_containers:
        for bar in bars:
            height = bar.get_height()
            label = human_readable_tb_to_bytes(height)

            if height < 1.1 * convert_to_:

                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    height,
                    label,
                    ha="center",
                    va="bottom",
                    fontsize=20,
                    rotation=90,   # vertical labels work better for narrow bars
                    clip_on=False
                )

    # plt.tight_layout()
    plt.savefig(
        f"{TAG}-overall-data-movement.pdf", bbox_inches="tight", pad_inches=0.06
    )
    # plt.show()
