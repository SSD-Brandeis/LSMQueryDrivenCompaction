from copy import deepcopy
from typing import List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

from plotter import *
from .dataclass import HeatMapStat, AdditionalStats, RQColumn

class PlotHeatMaps:
    LAST_EPOCH_INDEX = NUMEPOCHS-1
    FIGSIZE = (12, 7)

    def __init__(self, stats: List[HeatMapStat]):
        self._stats = list(stats)

    def _get_percentiles(self, data: pd.Series, col: str) -> AdditionalStats:
        percentiles = data[col].quantile([0.9, 0.95, 0.99]).to_dict()
        return AdditionalStats(
            min=data[col].min(),
            max=data[col].max(),
            mean=data[col].mean(),
            std=data[col].std(),
            p90th=percentiles[0.9],
            p95th=percentiles[0.95],
            p99th=percentiles[0.99],
        )

    def _plot_percentiles(self, data: AdditionalStats, ax):
        cell_text = [
            [
                f"{data.min:.2f}",
                f"{data.max:.2f}",
                f"{data.mean:.2f}",
                f"{data.std:.2f}",
                f"{data.p90th:.2f}",
                f"{data.p95th:.2f}",
                f"{data.p99th:.2f}",
            ]
        ]
        rows = ["value"]

        # Add a table at the bottom of the axes
        ax.table(
            cellText=cell_text,
            rowLabels=rows,
            colLabels=["Min", "Max", "Mean", "Std", "90th", "95th", "99th"],
            loc="bottom",
            bbox=[0.14, -0.35, 0.9, 0.08],
        )

    def _updated_xlabels(self, labels: List[str]) -> List[str]:
        i = 0
        for _ in range(len(EPSILON_VALUES)+1):
            labels[i] = f"{round(float(labels[i]), 3)}"
            i += 1
        return labels

    def _updated_ylabels(self, labels: List[str]) -> List[str]:
        i = 0
        for _ in range(1):
            labels[i+1] = 'inf'
            # labels[i] = f"{round(float(labels[i]), 3)}"
            i += 1
        return labels

    def _plot_heatmap(self, df: pd.DataFrame, col: str, title: str, vmin, vmax, fmt: str = ".2f"):
        _, ax = plt.subplots(figsize=self.FIGSIZE)

        pivot_table = df.pivot(index="ub", columns="lb", values=col)
        sns.heatmap(
            pivot_table,
            annot=True,
            fmt=fmt,
            linewidths=0.5,
            square=True,
            cmap="Blues",
            ax=ax,
            vmin=vmin,
            vmax=vmax
        )
        ax.set_xlabel("lower bound", fontsize=12)
        ax.set_ylabel("upper bound", fontsize=12)

        ax.set_xticklabels(
            self._updated_xlabels([label.get_text() for label in ax.get_xticklabels()])
        )
        ax.set_yticklabels(
            self._updated_ylabels([label.get_text() for label in ax.get_yticklabels()])
        )

        plt.title(title + f" T [{SIZE_RATIO}] Y {SELECTIVITY}", fontsize=12)
        plt.gca().invert_yaxis()

        # self._plot_percentiles(data=self._get_percentiles(df, col), ax=ax)

    def normalize_plotting_data(self, pltdata, key: str):
        pltdata_copy = deepcopy(pltdata)

        van_val = [val for val in pltdata if val["lb"] == 0 and val["ub"] == 0][0]

        for data in pltdata_copy:
            data[key] = data[key] / van_val[key]
        return pltdata_copy

    def compaction_bytes_written(self):
        plotting = "writebytes"
        plotting_data = [
            {
                "lb": stat["lb"],
                "ub": stat["ub"],
                plotting: stat["plottingStats"][
                    self.LAST_EPOCH_INDEX
                ].CompactionWrittenBytes
                / (1024**2),
            }
            for stat in self._stats
        ]

        # plotting_data = self.normalize_plotting_data(plotting_data, plotting)

        plotting_df = pd.DataFrame.from_dict(plotting_data)
        self._plot_heatmap(
            plotting_df, plotting, "normal compaction writes (MB)", np.floor(plotting_df[plotting].min()), np.ceil(plotting_df[plotting].max())
        )

    def rangereduce_compaction_bytes_written(self):
        plotting = "writebytes"
        plotting_data = [
            {
                "lb": stat["lb"],
                "ub": stat["ub"],
                plotting: stat["plottingStats"][
                    self.LAST_EPOCH_INDEX
                ].RangeReduceWrittenBytes
                / (1024**2),
            }
            for stat in self._stats
        ]

        # plotting_data = self.normalize_plotting_data(plotting_data, plotting)

        plotting_df = pd.DataFrame.from_dict(plotting_data)
        self._plot_heatmap(
            plotting_df, plotting, "rangereduce compaction writes (MB)", np.floor(plotting_df[plotting].min()), np.ceil(plotting_df[plotting].max())
        )

    def total_bytes_written_except_flush(self):
        plotting = "writebytes"
        plotting_data = [
            {
                "lb": stat["lb"],
                "ub": stat["ub"],
                plotting: (stat["plottingStats"][
                    self.LAST_EPOCH_INDEX
                ].RangeReduceWrittenBytes + stat["plottingStats"][
                    self.LAST_EPOCH_INDEX
                ].CompactionWrittenBytes)
                / (1024**2),
            }
            for stat in self._stats
        ]

        # plotting_data = self.normalize_plotting_data(plotting_data, plotting)

        plotting_df = pd.DataFrame.from_dict(plotting_data)
        self._plot_heatmap(
            plotting_df, plotting, "total writes (except flush) (MB)", np.floor(plotting_df[plotting].min()), np.ceil(plotting_df[plotting].max())
        )

    # def total_bytes_written(self):
    #     plotting = "writebytes"
    #     plotting_data = [
    #         {
    #             "lb": stat["lb"],
    #             "ub": stat["ub"],
    #             plotting: (stat["plottingStats"][
    #                 self.LAST_EPOCH_INDEX
    #             ].RangeReduceWrittenBytes + stat["plottingStats"][
    #                 self.LAST_EPOCH_INDEX
    #             ].CompactionWrittenBytes)
    #             / (1024**2),
    #         }
    #         for stat in self._stats
    #     ]

    #     # plotting_data = self.normalize_plotting_data(plotting_data, plotting)

    #     plotting_df = pd.DataFrame.from_dict(plotting_data)
    #     self._plot_heatmap(
    #         plotting_df, plotting, "total writes (except flush) (MB)", np.floor(plotting_df[plotting].min()), np.ceil(plotting_df[plotting].max())
    #     )

    def compaction_debt(self):
        plotting = "compactiondebt"
        plotting_data = [
            {
                "lb": stat["lb"],
                "ub": stat["ub"],
                plotting: stat["plottingStats"][
                    self.LAST_EPOCH_INDEX
                ].CompactionDebt
                / (1024**2),
            }
            for stat in self._stats
        ]

        # plotting_data = self.normalize_plotting_data(plotting_data, plotting)

        plotting_df = pd.DataFrame.from_dict(plotting_data)
        self._plot_heatmap(plotting_df, plotting, "compaction debt (MB)", np.floor(plotting_df[plotting].min()), np.ceil(plotting_df[plotting].max()))

    def writeamp_debt(self):
        plotting = "writeampdebt"
        plotting_data = [
            {
                "lb": stat["lb"],
                "ub": stat["ub"],
                plotting: stat["plottingStats"][
                    self.LAST_EPOCH_INDEX
                ].WriteAmpDebt
                / (1024**2),
            }
            for stat in self._stats
        ]

        # plotting_data = self.normalize_plotting_data(plotting_data, plotting)

        plotting_df = pd.DataFrame.from_dict(plotting_data)
        self._plot_heatmap(plotting_df, plotting, "write amp debt (MB)", np.floor(plotting_df[plotting].min()), np.ceil(plotting_df[plotting].max()))

    def spaceamp_debt(self):
        plotting = "spaceamp"
        plotting_data = [
            {
                "lb": stat["lb"],
                "ub": stat["ub"],
                plotting: stat["plottingStats"][self.LAST_EPOCH_INDEX].DBSize
                / (INSERTS * ENTRY_SIZE),
            }
            for stat in self._stats
        ]

        # plotting_data = self.normalize_plotting_data(plotting_data, plotting)

        plotting_df = pd.DataFrame.from_dict(plotting_data)
        self._plot_heatmap(plotting_df, plotting, "space amp", np.floor(plotting_df[plotting].min()), np.ceil(plotting_df[plotting].max()))

    def compaction_reads(self):
        plotting = "compactionread"
        plotting_data = [
            {
                "lb": stat["lb"],
                "ub": stat["ub"],
                plotting: stat["plottingStats"][
                    self.LAST_EPOCH_INDEX
                ].CompactionReadBytes
                / (1024 * 2),
            }
            for stat in self._stats
        ]

        # plotting_data = self.normalize_plotting_data(plotting_data, plotting)

        # plotting_data = self.normalize_plotting_data(plotting_data, plotting)

        plotting_df = pd.DataFrame.from_dict(plotting_data)
        self._plot_heatmap(plotting_df, plotting, "compaction read (MB)", np.floor(plotting_df[plotting].min()), np.ceil(plotting_df[plotting].max()))

    def avg_bytes_written_for_range_queries(self):
        plotting = "rqbyteswritten"
        plotting_data = [
            {
                "lb": stat["lb"],
                "ub": stat["ub"],
                plotting: stat["rqStats"][
                    [
                        str(RQColumn.DATA_USEFUL_BYTES_WRITTEN),
                        str(RQColumn.DATA_UNUSEFUL_BYTES_WRITTEN),
                    ]
                ]
                .sum(axis=1)
                .mean()
                / (1024**2),
            }
            for stat in self._stats
        ]

        plotting_df = pd.DataFrame.from_dict(plotting_data)
        self._plot_heatmap(
            plotting_df, plotting, "avg. bytes written in range queries (MB)", np.floor(plotting_df[plotting].min()), np.ceil(plotting_df[plotting].max())
        )

    def total_bytes_read_compaction(self):
        plotting = "compactionreadbytes"
        plotting_data = [
            {
                "lb": stat["lb"],
                "ub": stat["ub"],
                plotting: stat["plottingStats"][
                    self.LAST_EPOCH_INDEX
                ].CompactionReadBytes
                / (1024**2),
            }
            for stat in self._stats
        ]

        # plotting_data = self.normalize_plotting_data(plotting_data, plotting)

        plotting_df = pd.DataFrame.from_dict(plotting_data)
        self._plot_heatmap(
            plotting_df, plotting, "bytes read in compactions (MB)", np.floor(plotting_df[plotting].min()), np.ceil(plotting_df[plotting].max())
        )

    def avg_bytes_read_range_query(self):
        plotting = "rqbytesread"
        plotting_data = [
            {
                "lb": stat["lb"],
                "ub": stat["ub"],
                plotting: (
                    stat["rqStats"][[str(RQColumn.TOTAL_ENTRIES_READ)]].mean()[0]
                    * ENTRY_SIZE
                )
                / (1024**2),
            }
            for stat in self._stats
        ]

        # plotting_data = self.normalize_plotting_data(plotting_data, plotting)

        plotting_df = pd.DataFrame.from_dict(plotting_data)
        self._plot_heatmap(
            plotting_df, plotting, "avg. bytes read in range query (MB)", np.floor(plotting_df[plotting].min()), np.ceil(plotting_df[plotting].max()), fmt=".3f"
        )

    def avg_time_of_range_queries(self):
        plotting = "rqqvgtime"
        plotting_data = [
            {
                "lb": stat["lb"],
                "ub": stat["ub"],
                plotting: stat["rqStats"][[str(RQColumn.RQ_TOTAL_TIME)]].mean()[0]
                / (1000**3),
            }
            for stat in self._stats
        ]

        # plotting_data = self.normalize_plotting_data(plotting_data, plotting)

        plotting_df = pd.DataFrame.from_dict(plotting_data)
        self._plot_heatmap(
            plotting_df, plotting, "avg. time of range query (sec)", np.floor(plotting_df[plotting].min()), np.ceil(plotting_df[plotting].max()), fmt=".3f"
        )

    def overall_data_movement(self):
        plotting = "datamovement"
        plotting_data = [
            {
                "lb": stat["lb"],
                "ub": stat["ub"],
                 "datamovement": (
                    stat["plottingStats"][self.LAST_EPOCH_INDEX].CompactionWrittenBytes
                    + stat["plottingStats"][self.LAST_EPOCH_INDEX].CompactionReadBytes + stat["plottingStats"][self.LAST_EPOCH_INDEX].RangeReduceWrittenBytes
                    + (
                        stat["rqStats"][str(RQColumn.TOTAL_ENTRIES_READ)].sum()
                        * ENTRY_SIZE
                    )
                )
                / (1024**3),
            }
            for stat in self._stats
        ]

        # plotting_data = self.normalize_plotting_data(plotting_data, plotting)

        plotting_df = pd.DataFrame.from_dict(plotting_data)
        self._plot_heatmap(
            plotting_df,  "datamovement", "overall datamovement (GB)", np.floor(plotting_df[plotting].min()), np.ceil(plotting_df[plotting].max()), fmt=".3f"
        )

    def all_in_one(self):
        plotting = "allInOne"

        data_movement = "datamovement"
        data_movement_plotting_data = [
            {
                "lb": stat["lb"],
                "ub": stat["ub"],
                 data_movement: (
                    stat["plottingStats"][self.LAST_EPOCH_INDEX].TotalWriteBytes
                    + stat["plottingStats"][self.LAST_EPOCH_INDEX].CompactionReadBytes
                    + (
                        stat["rqStats"][str(RQColumn.TOTAL_ENTRIES_READ)].sum()
                        * ENTRY_SIZE
                    )
                )
                / (1024**3),
            }
            for stat in self._stats
        ]
        plotting_data_a = self.normalize_plotting_data(data_movement_plotting_data, data_movement)

        rqqvgtime = "rqqvgtime"
        range_query_avg_time_plotting_data = [
            {
                "lb": stat["lb"],
                "ub": stat["ub"],
                rqqvgtime: stat["rqStats"][[str(RQColumn.RQ_TOTAL_TIME)]].mean()[0]
                / (1000**3),
            }
            for stat in self._stats
        ]
        plotting_data_b = self.normalize_plotting_data(range_query_avg_time_plotting_data, rqqvgtime)

        spaceamp = "spaceamp"
        spaceamp_plotting_data = [
            {
                "lb": stat["lb"],
                "ub": stat["ub"],
                "spaceamp": stat["plottingStats"][self.LAST_EPOCH_INDEX].DBSize
                / (INSERTS * ENTRY_SIZE),
            }
            for stat in self._stats
        ]
        plotting_data_c = self.normalize_plotting_data(spaceamp_plotting_data, spaceamp)

        compactiondebt = "compactiondebt"
        compactiondebt_plotting_data = [
            {
                "lb": stat["lb"],
                "ub": stat["ub"],
                "compactiondebt": stat["plottingStats"][
                    self.LAST_EPOCH_INDEX
                ].CompactionDebt
                / (1024**2),
            }
            for stat in self._stats
        ]
        plotting_data_d = self.normalize_plotting_data(compactiondebt_plotting_data, compactiondebt)

        all_in_one = [(plotting_data_a, data_movement), (plotting_data_b, rqqvgtime), (plotting_data_c, spaceamp), (plotting_data_d, compactiondebt)]

        all_in_one_plotting_data = list()

        for data in plotting_data_a:
            lb = data['lb']
            ub = data['ub']
            value = 0
            
            for metric_data, metric in all_in_one:
                for _data in metric_data:
                    if _data['lb'] == lb and _data['ub'] == ub:
                        value += _data[metric]
                        break
            
            all_in_one_plotting_data.append(
                {
                    'lb': lb,
                    'ub': ub,
                    plotting: value/4
                }
            )
        plotting_df = pd.DataFrame.from_dict(all_in_one_plotting_data)
        self._plot_heatmap(
            plotting_df, plotting, "compaction debt + space amp + avg. RQ time + datamovement ", fmt=".3f"
        )

