from copy import deepcopy
from enum import Enum
from typing import List, Dict

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from plotter import *
from .dataclass import (
    AdditionalStats,
    PlottingStats,
    RQColumn,
    Approach,
    Metric,
    TABLE_DATA,
)

def log_just_metric(approach_data: Dict[str, List[PlottingStats]], metric: Metric):
    if "RocksDB" in approach_data.keys():
        TABLE_DATA[str(Approach.ROCKSDB)][str(metric)] = approach_data["RocksDB"][0]
    if "RocksDB" in approach_data.keys() and "RocksDBTuned" in approach_data.keys():
        TABLE_DATA[str(Approach.ROCKSDB_TUNED)][
            str(metric)
        ] = approach_data["RocksDBTuned"][0]
    if (
        "RocksDBTuned" in approach_data.keys()
        and "RangeReduce[lb=0 & smlck=0]" in approach_data.keys()
    ):
        TABLE_DATA[str(Approach.RANGE_REDUCE_LB_0_AND_SMLCK_0)][
            str(metric)
        ] = approach_data["RangeReduce[lb=0 & smlck=0]"][0]
    if (
        "RocksDBTuned" in approach_data.keys()
        and "RangeReduce[lb=0]" in approach_data.keys()
    ):
        TABLE_DATA[str(Approach.RANGE_REDUCE_LB_0)][
            str(metric)
        ] = approach_data["RangeReduce[lb=0]"][0]
    if (
        "RocksDBTuned" in approach_data.keys()
        and "RangeReduce[lb=T^-1]" in approach_data.keys()
    ):
        TABLE_DATA[str(Approach.RANGE_REDUCE_LB_T_MINUS_1)][
            str(metric)
        ] = approach_data["RangeReduce[lb=T^-1]"][0]
    if (
        "RocksDBTuned" in approach_data.keys()
        and "RangeReduce[lb=T^-1 & re=1]" in approach_data.keys()
    ):
        TABLE_DATA[str(Approach.RANGE_REDUCE_LB_T_MINUS_1_AND_RE_1)][
            str(metric)
        ] = approach_data["RangeReduce[lb=T^-1 & re=1]"][0]

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
        "RocksDBTuned" in approach_data.keys()
        and "RangeReduce[lb=0 & smlck=0]" in approach_data.keys()
    ):
        TABLE_DATA[str(Approach.RANGE_REDUCE_LB_0_AND_SMLCK_0)][
            str(metric)
        ] = f'{round(((approach_data["RangeReduce[lb=0 & smlck=0]"][0] - approach_data["RocksDBTuned"][0]) / approach_data["RocksDBTuned"][0]) * 100,2,)}%'
    if (
        "RocksDBTuned" in approach_data.keys()
        and "RangeReduce[lb=0]" in approach_data.keys()
    ):
        TABLE_DATA[str(Approach.RANGE_REDUCE_LB_0)][
            str(metric)
        ] = f'{round(((approach_data["RangeReduce[lb=0]"][0] - approach_data["RocksDBTuned"][0])/ approach_data["RocksDBTuned"][0]) * 100,2,)}%'
    if (
        "RocksDBTuned" in approach_data.keys()
        and "RangeReduce[lb=T^-1]" in approach_data.keys()
    ):
        TABLE_DATA[str(Approach.RANGE_REDUCE_LB_T_MINUS_1)][
            str(metric)
        ] = f'{round(((approach_data["RangeReduce[lb=T^-1]"][0] - approach_data["RocksDBTuned"][0])/ approach_data["RocksDBTuned"][0]) * 100,2,)}%'
    if (
        "RocksDBTuned" in approach_data.keys()
        and "RangeReduce[lb=T^-1 & re=1]" in approach_data.keys()
    ):
        TABLE_DATA[str(Approach.RANGE_REDUCE_LB_T_MINUS_1_AND_RE_1)][
            str(metric)
        ] = f'{round(((approach_data["RangeReduce[lb=T^-1 & re=1]"][0] - approach_data["RocksDBTuned"][0])/ approach_data["RocksDBTuned"][0]) * 100,2,)}%'


class PlotEpochStats:
    kw_args = {
        "RocksDB": {
            "label": "RocksDB",
            "color": "None",
            "edgecolor": "black",
            "hatch": "",
        },
        "RocksDBTuned": {
            "label": "RocksDBTuned",
            "color": "None",
            "edgecolor": "black",
            "hatch": "/",
        },
        "RangeReduce[lb=0]": {
            "label": "RangeReduce[lb=0]",
            "color": "None",
            "edgecolor": "black",
            "hatch": "\\",
        },
        "RangeReduce[lb=T^-1]": {
            "label": "RangeReduce[lb=T^-1]",
            "color": "None",
            "edgecolor": "black",
            "hatch": "x",
        },
        "RangeReduce[lb=T^-1 & re=1]": {
            "label": "RangeReduce[lb=T^-1 & re=1]",
            "color": "None",
            "edgecolor": "black",
            "hatch": "+",
        },
        "RangeReduce[lb=0 & smlck=0]": {
            "label": "RangeReduce[lb=0 & smlck=0]",
            "color": "None",
            "edgecolor": "black",
            "hatch": "*",
        },
    }

    def __init__(self, approaches: Dict[str, List[PlottingStats]]):
        self.approaches_: Dict[str, List[PlottingStats]] = deepcopy(approaches)

        avg_bytes_written_by_RR: Dict[str, List[float]] = dict()
        total_files_count: Dict[str, List[float]] = dict()
        avg_file_size: Dict[str, List[float]] = dict()
        for approach, plot_stat in self.approaches_.items():
            avg_bytes_written_by_RR[approach] = [plot_stat[0].RangeReduceWrittenBytes / (TABLE_DATA[approach][str(Metric.RR_TRIGGERED_COUNT)] * 1024**2)]
            total_files_count[approach] = [plot_stat[0].FilesCount]
            avg_file_size[approach] = [plot_stat[0].DBSize / (plot_stat[0].FilesCount * 1024**2)]
        log_just_metric(avg_bytes_written_by_RR, Metric.AVG_BYTES_WRITTENT_BY_RR)
        # log_metric(total_files_count, Metric.TOTAL_FILES_COUNT)
        log_just_metric(total_files_count, Metric.TOTAL_FILES_COUNT)
        log_just_metric(avg_file_size, Metric.AVG_FILE_SIZE)


    def plot_total_bytes_written(self):
        convert_to_ = 1024**3
        approach_data: Dict[str, List[PlottingStats]] = dict()
        max_ylim = 0

        for approach, data in self.approaches_.items():
            approach_data[approach] = [
                (stat.CompactionWrittenBytes + stat.RangeReduceWrittenBytes)
                / convert_to_
                for stat in data
            ]
            max_ylim = max(max_ylim, max(approach_data[approach]))

        log_metric(approach_data, Metric.TOTAL_WRITES)

        fig_size = (7, 5)

        fig, ax = plt.subplots(figsize=fig_size)

        for approach, data in approach_data.items():
            ax.bar(
                approach,
                data,
                **self.kw_args[approach],
            )

        ax.set_ylabel("total write (GB)", fontsize=12)
        ax.set_xlabel("system", fontsize=12)
        ax.set_xticks([])

        ax.set_ylim(bottom=0, top=max_ylim + max_ylim * 0.18)

        ax.set_title("total write (compaction + RangeReduce compactions)", fontsize=12)

        fig.legend(
            loc="upper center",
            ncol=2,
            fontsize=10,
            bbox_to_anchor=(0.51, 0.90),
            frameon=False,
            columnspacing=0.5,
        )
        plt.show()

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
                **self.kw_args[approach],
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
        plt.show()

    def plot_compaction_debt(self):
        convert_to_ = 1024**2
        approach_data: Dict[str, List[PlottingStats]] = dict()
        max_ylim = 0

        for approach, data in self.approaches_.items():
            approach_data[approach] = [
                stat.CompactionDebt / convert_to_ for stat in data
            ]
            max_ylim = max(max_ylim, max(approach_data[approach]))

        log_metric(approach_data, Metric.COMPACTION_DEBT)

        fig_size = (7, 5)
        fig, ax = plt.subplots(figsize=fig_size)

        for approach, data in approach_data.items():
            ax.bar(
                approach,
                data,
                **self.kw_args[approach],
            )

        ax.set_ylabel("compaction debt (MB)", fontsize=12)
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
        plt.show()

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
                **self.kw_args[approach],
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
        plt.show()

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
                **self.kw_args[approach],
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
        plt.show()

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
                **self.kw_args[approach],
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
        plt.show()

    def plot_space_amplification(self):
        approach_data: Dict[str, List[PlottingStats]] = dict()
        max_ylim = 0

        for approach, data in self.approaches_.items():
            approach_data[approach] = [
                stat.DBSize / (INSERTS * ENTRY_SIZE) for stat in data
            ]
            max_ylim = max(max_ylim, max(approach_data[approach]))

        log_metric(approach_data, Metric.SPACE_AMP)

        fig_size = (7, 5)
        fig, ax = plt.subplots(figsize=fig_size)

        for approach, data in approach_data.items():
            ax.bar(
                approach,
                data,
                **self.kw_args[approach],
            )

        ax.set_ylabel("space amplification", fontsize=12)
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
        plt.show()

    # def plot_total_data_movement(self):
    #     vanilla_datamovement = [van.TotalWriteBytes + van.CompactionReadBytes for van in self._vanilla]
    #     rqdc_datamovement = [rqdc.TotalWriteBytes + rqdc.CompactionReadBytes for rqdc in self._rqdc]

    #     fig_size = (7, 5)
    #     bar_width = 0.35
    #     num_bars_per_group = 2
    #     epochs = NUMEPOCHS

    #     index = np.arange(epochs)
    #     fig, ax = plt.subplots(figsize=fig_size)

    #     ax.bar(
    #         index - (bar_width / num_bars_per_group),
    #         vanilla_datamovement,
    #         bar_width,
    #         **self.vanilla_bar_kwargs,
    #     )
    #     ax.bar(
    #         index + (bar_width / num_bars_per_group),
    #         rqdc_datamovement,
    #         bar_width,
    #         **self.rqdc_bar_kwargs,
    #     )

    #     ax.set_ylabel("total datamovement (GB)", fontsize=12)
    #     ax.set_xlabel("epoch", fontsize=12)

    #     ax.set_ylim(bottom=0)

    #     ax.set_xticks(range(epochs))
    #     ax.set_xticklabels([f"{epoch}" for epoch in range(1, epochs + 1)], fontsize=12)

    #     ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
    #     ax.set_yticklabels(
    #         [f"{int(i/(1000 ** 3))}" if i != 0 else "0" for i in ax.get_yticks()],
    #         fontsize=12,
    #     )

    #     fig.legend(
    #         loc="upper center",
    #         ncol=2,
    #         fontsize=12,
    #         bbox_to_anchor=(0.5, 0.90),
    #         frameon=False,
    #     )
    #     plt.show()

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
                **self.kw_args[approach],
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
        plt.show()

    def plot_workload_exec_time(self):
        convert_to_ = 1000**3
        approach_data: Dict[str, List[PlottingStats]] = dict()
        max_ylim = 0

        for approach, data in self.approaches_.items():
            approach_data[approach] = [
                stat.WorkloadExecutionTime / convert_to_ for stat in data
            ]
            max_ylim = max(max_ylim, max(approach_data[approach]))

        log_metric(approach_data, Metric.WL_EXECUTION_TIME)

        fig_size = (7, 5)
        fig, ax = plt.subplots(figsize=fig_size)

        for approach, data in approach_data.items():
            ax.bar(
                approach,
                data,
                **self.kw_args[approach],
            )

        ax.set_ylabel("workload execution time (sec)", fontsize=12)
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
        plt.show()

    def plot_levels_state(self):
        vanilla_levels_state = [van.LevelsState for van in self._vanilla]
        rqdc_levels_state = [rqdc.LevelsState for rqdc in self._rqdc]

        fig_size = (7, 5)
        bar_width = 0.35
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

        plt.show()


class PlotRangeQueryStats:
    kw_args = {
        "RocksDB": {
            "color": "saddlebrown",
        },
        "RocksDBTuned": {
            "color": "steelblue",
        },
        "RangeReduce[lb=0]": {
            "color": "#1B9E77",  # Teal
        },
        "RangeReduce[lb=T^-1]": {
            "color": "#D95F02",  # Burnt Orange
        },
        "RangeReduce[lb=T^-1 & re=1]": {
            "color": "#7570B3",  # Muted Purple
        },
        "RangeReduce[lb=0 & smlck=0]": {
            "color": "#E7298A",
        },
    }

    def __init__(self, approaches: Dict[str, pd.DataFrame]):
        self.approaches_: Dict[str, pd.DataFrame] = deepcopy(approaches)

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

    # def bytes_written_for_each_range_query(self):
    #     convert_to_ = (1000 ** 1)
    #     vanilla_rq_bytes = (
    #         self._vanilla[
    #             [
    #                 str(RQColumn.DATA_USEFUL_BYTES_WRITTEN),
    #                 str(RQColumn.DATA_UNUSEFUL_BYTES_WRITTEN),
    #             ]
    #         ]
    #         .sum(axis=1)
    #         .to_list()
    #     )
    #     rqdc_rq_bytes = (
    #         self._rqdc[
    #             [
    #                 str(RQColumn.DATA_USEFUL_BYTES_WRITTEN),
    #                 str(RQColumn.DATA_UNUSEFUL_BYTES_WRITTEN),
    #             ]
    #         ]
    #         .sum(axis=1)
    #         .to_list()
    #     )

    #     if len(vanilla_rq_bytes) != len(rqdc_rq_bytes):
    #         raise Exception("found different number of range queries")

    #     fig_size = (20, 4)
    #     fig, ax = plt.subplots(figsize=fig_size)

    #     # ax.plot(range(len(vanilla_rq_bytes)), vanilla_rq_bytes)
    #     ax.bar(range(len(rqdc_rq_bytes)), rqdc_rq_bytes, color="black")

    #     ax.set_ylabel("total write (MB)", fontsize=12)
    #     ax.set_xlabel("range query number", fontsize=12)

    #     ax.set_ylim(bottom=0)

    #     ax.xaxis.set_major_locator(ticker.FixedLocator(ax.get_xticks()))
    #     ax.set_xticklabels([f"{int(tick)}" for tick in ax.get_xticks()], fontsize=12)

    #     ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
    #     ax.set_yticklabels(
    #         [f"{int(i/convert_to_)}" if i != 0 else "0" for i in ax.get_yticks()],
    #         fontsize=12,
    #     )
    #     ax.set_title("total write (RQDC range query)", fontsize=12)

    #     ax.annotate(
    #         f"success count: {sum([x > 0 for x in rqdc_rq_bytes])}",
    #         xy=(int(len(rqdc_rq_bytes) * 0.10), int(max(rqdc_rq_bytes) * 0.95)),
    #         fontsize=12,
    #     )
    #     ax.annotate(
    #         f"total bytes written: {sum(rqdc_rq_bytes):_.2f} bytes",
    #         xy=(int(len(rqdc_rq_bytes) * 0.75), int(max(rqdc_rq_bytes) * 0.95)),
    #         fontsize=12,
    #     )

    #     plt.show()

    def bytes_read_for_each_range_query(self, range_query_pattern=""):
        convert_to_ = 1024**2
        approach_data = dict()

        for approach, data in self.approaches_.items():
            approach_data[approach] = (
                data[[str(RQColumn.TOTAL_ENTRIES_READ)]]
                .apply(lambda x: x * ENTRY_SIZE)[str(RQColumn.TOTAL_ENTRIES_READ)]
                .to_list()
            )

        fig_size = (20, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        for approach, data in approach_data.items():
            ax.plot(
                range(len(data)),
                data,
                label=approach,
                alpha=0.8,
                **self.kw_args[approach],
            )

        ax.set_ylabel("total read (MB)", fontsize=12)
        ax.set_xlabel("range query number", fontsize=12)

        ax.set_ylim(bottom=0)

        ax.xaxis.set_major_locator(ticker.FixedLocator(ax.get_xticks()))
        ax.set_xticklabels([f"{int(tick)}" for tick in ax.get_xticks()], fontsize=12)

        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticklabels(
            [f"{int(i/convert_to_)}" if i != 0 else "0" for i in ax.get_yticks()],
            fontsize=12,
        )
        ax.set_title("total read", fontsize=12)

        fig.legend(
            loc="lower center",
            ncol=5,
            fontsize=12,
            bbox_to_anchor=(0.5, 0.1),
            frameon=False,
        )

        additional_stats: Dict[str, AdditionalStats] = dict()
        log_metric_stats: Dict[str, List[float]] = dict()

        for approach, data in approach_data.items():
            additional_stats[approach] = self._get_percentiles(
                pd.Series([x / convert_to_ for x in data])
            )
            log_metric_stats[approach] = [additional_stats[approach].mean]

        # log_metric(log_metric_stats, Metric.AVG_BYTES_READ_RQ)
        log_just_metric(log_metric_stats, Metric.AVG_BYTES_READ_RQ)
        self._plot_percentiles(additional_stats, ax)

        plt.show()

    def latency_for_each_range_query(self, range_query_pattern=""):
        plotting_column = str(RQColumn.RQ_TOTAL_TIME)
        convert_to_ = 1000**2
        approach_data = dict()

        for approach, data in self.approaches_.items():
            approach_data[approach] = data[plotting_column].to_list()

        fig_size = (20, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        for approach, data in approach_data.items():
            ax.plot(
                range(len(data)),
                data,
                label=approach,
                alpha=0.8,
                **self.kw_args[approach],
            )

        ax.set_ylabel("latency (ms)", fontsize=12)  # µ
        ax.set_xlabel("range query number", fontsize=12)

        ax.set_ylim(bottom=0)

        ax.xaxis.set_major_locator(ticker.FixedLocator(ax.get_xticks()))
        ax.set_xticklabels([f"{int(tick)}" for tick in ax.get_xticks()], fontsize=12)

        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticklabels(
            [f"{int(i/convert_to_)}" if i != 0 else "0" for i in ax.get_yticks()],
            fontsize=12,
        )

        fig.legend(
            loc="lower center",
            ncol=5,
            fontsize=12,
            bbox_to_anchor=(0.5, 0.1),
            frameon=False,
        )

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
        self._plot_percentiles(additional_stats, ax)

        plt.show()

    # def plot_cpu_cycles(self, range_query_pattern=""):

    #     plotting_column = str(RQColumn.CPU_CYCLES)
    #     convert_to_ = 1

    #     vanilla_rq_time = self._vanilla[plotting_column].to_list()
    #     rqdc_rq_time = self._rqdc[plotting_column].to_list()

    #     if len(vanilla_rq_time) != len(rqdc_rq_time):
    #         raise Exception("found different number of range queries")

    #     fig_size = (20, 4)
    #     fig, ax = plt.subplots(figsize=fig_size)

    #     ax.plot(
    #         range(len(vanilla_rq_time)),
    #         vanilla_rq_time,
    #         label=f"{self.vanilla_plot_kwargs['label']} {range_query_pattern}",
    #         color=self.vanilla_plot_kwargs["color"],
    #         alpha=0.8,
    #     )
    #     ax.plot(
    #         range(len(rqdc_rq_time)),
    #         rqdc_rq_time,
    #         label=f"{self.rqdc_plot_kwargs['label']} {range_query_pattern}",
    #         color=self.rqdc_plot_kwargs["color"],
    #         alpha=0.8,
    #     )

    #     ax.set_ylabel("cpu cycles", fontsize=12)
    #     ax.set_xlabel("range query number", fontsize=12)

    #     ax.set_ylim(bottom=0)

    #     ax.xaxis.set_major_locator(ticker.FixedLocator(ax.get_xticks()))
    #     ax.set_xticklabels([f"{int(tick)}" for tick in ax.get_xticks()], fontsize=12)

    #     ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
    #     ax.set_yticklabels(
    #         [f"{int(i/convert_to_)}" if i != 0 else "0" for i in ax.get_yticks()],
    #         fontsize=12,
    #     )

    #     fig.legend(
    #         loc="lower center",
    #         ncol=2,
    #         fontsize=12,
    #         bbox_to_anchor=(0.5, 0.1),
    #         frameon=False,
    #     )

    #     ax.annotate(
    #         f"avg vanilla: {self._vanilla[plotting_column].mean()/convert_to_:_.2f} ms",
    #         xy=(int(len(rqdc_rq_time) * 0.10), int(max(rqdc_rq_time) * 0.05)),
    #         fontsize=12,
    #     )
    #     ax.annotate(
    #         f"avg RQDC: {self._rqdc[plotting_column].mean()/convert_to_:_.2f} ms",
    #         xy=(int(len(rqdc_rq_time) * 0.80), int(max(rqdc_rq_time) * 0.05)),
    #         fontsize=12,
    #     )

    #     self._plot_percentiles(
    #         self._get_percentiles(
    #             pd.Series([x / convert_to_ for x in vanilla_rq_time])
    #         ),
    #         self._get_percentiles(pd.Series([x / convert_to_ for x in rqdc_rq_time])),
    #         ax,
    #     )

    #     plt.show()

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
                **self.kw_args[approach],
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
        plt.show()


def plot_total_data_movement(
    approaches_plotting_stats: Dict[str, List[PlottingStats]],
    approaches_rq_stats: Dict[str, pd.DataFrame],
):
    kw_args = {
        "RocksDB": {
            "label": "RocksDB",
            "color": "None",
            "edgecolor": "black",
            "hatch": "",
        },
        "RocksDBTuned": {
            "label": "RocksDBTuned",
            "color": "None",
            "edgecolor": "black",
            "hatch": "/",
        },
        "RangeReduce[lb=0]": {
            "label": "RangeReduce[lb=0]",
            "color": "None",
            "edgecolor": "black",
            "hatch": "\\",
        },
        "RangeReduce[lb=T^-1]": {
            "label": "RangeReduce[lb=T^-1]",
            "color": "None",
            "edgecolor": "black",
            "hatch": "x",
        },
        "RangeReduce[lb=T^-1 & re=1]": {
            "label": "RangeReduce[lb=T^-1 & re=1]",
            "color": "None",
            "edgecolor": "black",
            "hatch": "+",
        },
        "RangeReduce[lb=0 & smlck=0]": {
            "label": "RangeReduce[lb=0 & smlck=0]",
            "color": "None",
            "edgecolor": "black",
            "hatch": "*",
        },
    }

    convert_to_ = 1024**3
    plotting_stats = deepcopy(approaches_plotting_stats)
    rq_stats = deepcopy(approaches_rq_stats)
    max_ylim = 0

    if NUMEPOCHS > 1:
        raise Exception("Can't handle more than one epochs data")

    approach_data: Dict[str, int] = dict()
    log_metric_stats: Dict[str, List] = dict()

    for approach, data in rq_stats.items():
        approach_data[approach] = (
            data[str(RQColumn.TOTAL_ENTRIES_READ)].sum() * ENTRY_SIZE
        )

    for approach, data in plotting_stats.items():
        approach_data[approach] += (
            data[0].CompactionReadBytes
            + data[0].CompactionWrittenBytes
            + data[0].RangeReduceWrittenBytes
        )

    fig_size = (7, 5)
    fig, ax = plt.subplots(figsize=fig_size)

    for approach, data in approach_data.items():
        ax.bar(
            approach,
            data / convert_to_,
            **kw_args[approach],
        )
        max_ylim = max(max_ylim, (data / convert_to_))
        log_metric_stats[approach] = [data / convert_to_]

    log_metric(log_metric_stats, Metric.OVERALL_DATA_MOVEMENT)

    ax.set_ylabel("total datamovement (GB)", fontsize=12)
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
    plt.show()
