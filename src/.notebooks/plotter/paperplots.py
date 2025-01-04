from copy import deepcopy
from typing import List

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from plotter import *
from plotter.epochstats import EpochStats
from plotter.dataclass import AdditionalStats, PlottingStats, RQColumn


class PaperPlots:
    vanilla_bar_kwargs = {
        "label": "vanilla",
        "color": "None",
        "hatch": "",
        "edgecolor": "black",
    }
    rqdc_bar_kwargs = {
        "label": "rangereduce",
        "color": "None",
        "hatch": "--",
        "edgecolor": "black",
    }
    vanilla_line_kwargs = {
        "label": "vanilla",
        "linestyle": "-",
        "linewidth": 1.5,
        "marker": "o",
        "markersize": 4,
        "color": "black",
    }

    rqdc_line_kwargs = {
        "label": "rangereduce",
        "linestyle": "--",
        "linewidth": 1.5,
        "marker": "s",
        "markersize": 4,
        "color": "black",
    }
    vanilla_boxplot_kwargs = {
        "label": "vanilla",
        "showfliers": False,
        "notch": True,
        "patch_artist": True,
        "boxprops": dict(facecolor="none", edgecolor="black", linewidth=1.5, hatch=""),
        "medianprops": dict(color="black", linewidth=1.5),
        "whiskerprops": dict(color="black", linewidth=1),
        "capprops": dict(color="black", linewidth=1),
    }
    rqdc_boxplot_kwargs = {
        "label": "rangereduce",
        "showfliers": False,
        "notch": True,
        "patch_artist": True,
        "boxprops": dict(
            facecolor="none", edgecolor="black", linewidth=1.5, hatch="////"
        ),
        "medianprops": dict(color="black", linewidth=1.5),
        "whiskerprops": dict(color="black", linewidth=1),
        "capprops": dict(color="black", linewidth=1),
    }

    fig_size = (6, 4)

    def __init__(
        self,
        vanilla: List[EpochStats],
        rqdc: List[EpochStats],
        operation_count: int = 0,
    ):

        if len(vanilla) != len(rqdc):
            raise Exception("lengths of vanilla and rqdc stats are not the same")
        self._vanilla: List[PlottingStats] = deepcopy(
            [van.get_plotstats()[0] for van in vanilla]
        )
        self._rqdc: List[PlottingStats] = deepcopy(
            [rqd.get_plotstats()[0] for rqd in rqdc]
        )
        self._vanilla_rq: List[pd.DataFrame] = [
            van.get_rangequerystats().copy(deep=True) for van in vanilla
        ]
        self._rqdc_rq: List[pd.DataFrame] = [
            rqd.get_rangequerystats().copy(deep=True) for rqd in rqdc
        ]
        self._op_count = operation_count

    def plot_throughput(self):
        convert_to_ = 1000**3
        vanilla_throughput = [
            self._op_count / (van.WorkloadExecutionTime / convert_to_)
            for van in self._vanilla
        ]
        rqdc_throughput = [
            self._op_count / (rqdc.WorkloadExecutionTime / convert_to_)
            for rqdc in self._rqdc
        ]

        x_points = range(len(RANGE_QUERY_PERCENTAGES))
        fig, ax = plt.subplots(figsize=self.fig_size)

        ax.plot(x_points, vanilla_throughput, **self.vanilla_line_kwargs)
        ax.plot(x_points, rqdc_throughput, **self.rqdc_line_kwargs)

        ax.set_ylabel("throughput (operations/sec)", fontsize=12)
        ax.set_xlabel("range queries/updates (%)", fontsize=12)
        ax.set_yscale("log")
        ax.set_ylim(bottom=1e-0)

        ax.set_xticks(x_points)
        ax.set_xticklabels([f"{per}" for per in RANGE_QUERY_PERCENTAGES], fontsize=12)

        fig.legend(
            loc="upper right",
            fontsize=12,
            ncol=2,
            frameon=False,
            bbox_to_anchor=(0.9, 0.88),
        )
        plt.show()

    def plot_range_query_latency(self):
        convert_to_ = 1000**2
        vanilla_rq_times = [
            df[str(RQColumn.RQ_TOTAL_TIME)] / convert_to_ for df in self._vanilla_rq
        ]
        rqdc_rq_times = [
            df[str(RQColumn.RQ_TOTAL_TIME)] / convert_to_ for df in self._rqdc_rq
        ]

        n = len(vanilla_rq_times)
        x_positions = np.arange(n)
        offset = 0.2
        width = 0.35

        fig, ax = plt.subplots(figsize=self.fig_size)

        # Boxplots
        ax.boxplot(
            vanilla_rq_times,
            positions=x_positions - offset,
            widths=width,
            **self.vanilla_boxplot_kwargs,
        )

        ax.boxplot(
            rqdc_rq_times,
            positions=x_positions + offset,
            widths=width,
            **self.rqdc_boxplot_kwargs,
        )

        # Calculate means for each box plot
        vanilla_means = [np.mean(data) for data in vanilla_rq_times]
        rqdc_means = [np.mean(data) for data in rqdc_rq_times]

        # Plot lines through the means
        van_kwargs = deepcopy(self.vanilla_line_kwargs)
        rr_kwargs = deepcopy(self.rqdc_line_kwargs)
        del van_kwargs["label"]
        del rr_kwargs["label"]

        ax.plot(x_positions - offset, vanilla_means, **van_kwargs)
        ax.plot(x_positions + offset, rqdc_means, **rr_kwargs)

        # Set labels and legend
        ax.set_xticks(x_positions)
        ax.set_xticklabels([f"{i}" for i in RANGE_QUERY_PERCENTAGES], fontsize=12)
        ax.set_ylabel("range query latency (μs)", fontsize=12)
        ax.set_xlabel("range queries/updates (%)", fontsize=12)
        ax.set_ylim(bottom=0)

        ax.legend(loc="lower center", frameon=False, fontsize=12, ncol=2)

        plt.tight_layout()
        plt.show()

    def plot_compaction_debt(self):
        convert_to_ = 1024**2
        vanilla_compaction_debt = [
            van.CompactionDebt / convert_to_ for van in self._vanilla
        ]
        rqdc_compaction_debt = [rqd.CompactionDebt / convert_to_ for rqd in self._rqdc]

        x_points = range(len(RANGE_QUERY_PERCENTAGES))
        fig, ax = plt.subplots(figsize=self.fig_size)
        ax.plot(x_points, vanilla_compaction_debt, **self.vanilla_line_kwargs)
        ax.plot(x_points, rqdc_compaction_debt, **self.rqdc_line_kwargs)

        ax.set_ylabel("compaction debt (MB)", fontsize=12)
        ax.set_xlabel("range queries/updates (%)", fontsize=12)
        ax.set_ylim(bottom=0)

        ax.set_xticks(x_points)
        ax.set_xticklabels([f"{per}" for per in RANGE_QUERY_PERCENTAGES], fontsize=12)

        fig.legend(
            loc="lower center",
            fontsize=12,
            ncol=2,
            frameon=False,
            bbox_to_anchor=(0.5, 0.1),
        )
        plt.show()

    def plot_wkl_exec_time(self):
        convert_to_ = 1000**3
        to_minutes = 60
        vanilla_wkl_exec_time = [
            (van.WorkloadExecutionTime / convert_to_) / to_minutes
            for van in self._vanilla
        ]
        rqdc_wkl_exec_time = [
            (rqd.WorkloadExecutionTime / convert_to_) / to_minutes for rqd in self._rqdc
        ]

        x_points = range(len(RANGE_QUERY_PERCENTAGES))
        fig, ax = plt.subplots(figsize=self.fig_size)
        ax.plot(x_points, vanilla_wkl_exec_time, **self.vanilla_line_kwargs)
        ax.plot(x_points, rqdc_wkl_exec_time, **self.rqdc_line_kwargs)

        ax.set_ylabel("execution time (minutes)", fontsize=12)
        ax.set_xlabel("range queries/updates (%)", fontsize=12)
        ax.set_ylim(bottom=0)

        ax.set_xticks(x_points)
        ax.set_xticklabels([f"{per}" for per in RANGE_QUERY_PERCENTAGES], fontsize=12)

        fig.legend(
            loc="upper center",
            fontsize=12,
            ncol=2,
            frameon=False,
            bbox_to_anchor=(0.5, 0.9),
        )
        plt.show()

    def plot_space_amp(self):
        vanilla_space_amp = [
            van.DBSize / (INSERTS * (ENTRY_SIZE + META_WITH_ENTRY_SIZE))
            for van in self._vanilla
        ]
        rqdc_space_amp = [
            rqd.DBSize / (INSERTS * (ENTRY_SIZE + META_WITH_ENTRY_SIZE))
            for rqd in self._rqdc
        ]

        x_points = range(len(RANGE_QUERY_PERCENTAGES))
        fig, ax = plt.subplots(figsize=self.fig_size)
        ax.plot(x_points, vanilla_space_amp, **self.vanilla_line_kwargs)
        ax.plot(x_points, rqdc_space_amp, **self.rqdc_line_kwargs)

        ax.set_ylabel("space amp", fontsize=12)
        ax.set_xlabel("range queries/updates (%)", fontsize=12)
        ax.set_ylim(bottom=0, top=max(vanilla_space_amp) + 0.5)

        ax.set_xticks(x_points)
        ax.set_xticklabels([f"{per}" for per in RANGE_QUERY_PERCENTAGES], fontsize=12)

        fig.legend(
            loc="lower center",
            fontsize=12,
            ncol=2,
            frameon=False,
            bbox_to_anchor=(0.5, 0.1),
        )
        plt.show()

    def plot_space_amp(self):
        vanilla_space_amp = [
            van.DBSize / (INSERTS * (ENTRY_SIZE + META_WITH_ENTRY_SIZE))
            for van in self._vanilla
        ]
        rqdc_space_amp = [
            rqd.DBSize / (INSERTS * (ENTRY_SIZE + META_WITH_ENTRY_SIZE))
            for rqd in self._rqdc
        ]

        x_points = range(len(RANGE_QUERY_PERCENTAGES))
        fig, ax = plt.subplots(figsize=self.fig_size)
        ax.plot(x_points, vanilla_space_amp, **self.vanilla_line_kwargs)
        ax.plot(x_points, rqdc_space_amp, **self.rqdc_line_kwargs)

        ax.set_ylabel("space amp", fontsize=12)
        ax.set_xlabel("range queries/updates (%)", fontsize=12)
        ax.set_ylim(bottom=0, top=max(vanilla_space_amp) + 0.5)

        ax.set_xticks(x_points)
        ax.set_xticklabels([f"{per}" for per in RANGE_QUERY_PERCENTAGES], fontsize=12)

        fig.legend(
            loc="lower center",
            fontsize=12,
            ncol=2,
            frameon=False,
            bbox_to_anchor=(0.5, 0.1),
        )
        plt.show()

    def plot_total_bytes_written(self):
        convert_to_ = 1024**3
        vanilla_writes = [
            (van.CompactionWrittenBytes + van.RangeReduceWrittenBytes) / convert_to_
            for van in self._vanilla
        ]
        rqdc_writes = [
            (rqdc.CompactionWrittenBytes + rqdc.RangeReduceWrittenBytes) / convert_to_
            for rqdc in self._rqdc
        ]

        x_points = range(len(RANGE_QUERY_PERCENTAGES))
        fig, ax = plt.subplots(figsize=self.fig_size)
        ax.plot(x_points, vanilla_writes, **self.vanilla_line_kwargs)
        ax.plot(x_points, rqdc_writes, **self.rqdc_line_kwargs)

        ax.set_ylabel("total writes (GB)", fontsize=12)
        ax.set_xlabel("range queries/updates (%)", fontsize=12)
        ax.set_ylim(bottom=0, top=max(vanilla_writes) + 0.5)

        ax.set_xticks(x_points)
        ax.set_xticklabels([f"{per}" for per in RANGE_QUERY_PERCENTAGES], fontsize=12)

        fig.legend(
            loc="lower center",
            fontsize=12,
            ncol=2,
            frameon=False,
            bbox_to_anchor=(0.5, 0.1),
        )
        plt.show()

    def plot_overall_datamovement(self):
        convert_to_ = 1024**3
        vanilla_rq_read = [
            df[str(RQColumn.TOTAL_ENTRIES_READ)].sum() * ENTRY_SIZE
            for df in self._vanilla_rq
        ]
        rqdc_rq_read = [
            df[str(RQColumn.TOTAL_ENTRIES_READ)].sum() * ENTRY_SIZE
            for df in self._rqdc_rq
        ]
        vanilla_comp_read_write = [
            (van.CompactionReadBytes + van.CompactionWrittenBytes)
            for van in self._vanilla
        ]
        rqdc_comp_read_write = [
            (rqdc.CompactionReadBytes + rqdc.CompactionWrittenBytes)
            for rqdc in self._rqdc
        ]
        rqdc_rq_write = [rqdc.RangeReduceWrittenBytes for rqdc in self._rqdc]

        vanilla_datamov = [
            (vanilla_rq_read[i] + vanilla_comp_read_write[i]) / convert_to_
            for i in range(len(vanilla_rq_read))
        ]
        rqdc_datamov = [
            (rqdc_rq_read[i] + rqdc_comp_read_write[i] + rqdc_rq_write[i]) / convert_to_
            for i in range(len(rqdc_rq_write))
        ]

        x_points = range(len(RANGE_QUERY_PERCENTAGES))
        fig, ax = plt.subplots(figsize=self.fig_size)
        ax.plot(x_points, vanilla_datamov, **self.vanilla_line_kwargs)
        ax.plot(x_points, rqdc_datamov, **self.rqdc_line_kwargs)

        ax.set_ylabel("overall datamovement (GB)", fontsize=12)
        ax.set_xlabel("range queries/updates (%)", fontsize=12)
        ax.set_ylim(bottom=0, top=max(vanilla_datamov) + max(vanilla_datamov) * 0.02)

        ax.set_xticks(x_points)
        ax.set_xticklabels([f"{per}" for per in RANGE_QUERY_PERCENTAGES], fontsize=12)

        fig.legend(
            loc="upper center",
            fontsize=12,
            ncol=2,
            frameon=False,
            bbox_to_anchor=(0.5, 0.9),
        )
        plt.show()

    def plot_total_bytes_written_in_compactions(self):
        convert_to_ = 1024**3
        vanilla_writes = [
            (van.CompactionWrittenBytes) / convert_to_ for van in self._vanilla
        ]
        rqdc_writes = [
            (rqdc.CompactionWrittenBytes) / convert_to_ for rqdc in self._rqdc
        ]

        x_points = range(len(RANGE_QUERY_PERCENTAGES))
        fig, ax = plt.subplots(figsize=self.fig_size)
        ax.plot(x_points, vanilla_writes, **self.vanilla_line_kwargs)
        ax.plot(x_points, rqdc_writes, **self.rqdc_line_kwargs)

        ax.set_ylabel("writes (GB)", fontsize=12)
        ax.set_xlabel("range queries/updates (%)", fontsize=12)
        ax.set_ylim(bottom=0, top=max(vanilla_writes) + 0.5)
        ax.set_title("compactions triggered on level saturation")

        ax.set_xticks(x_points)
        ax.set_xticklabels([f"{per}" for per in RANGE_QUERY_PERCENTAGES], fontsize=12)

        fig.legend(
            loc="lower center",
            fontsize=12,
            ncol=2,
            frameon=False,
            bbox_to_anchor=(0.5, 0.1),
        )
        plt.show()
