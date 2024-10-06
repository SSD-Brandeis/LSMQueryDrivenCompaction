from copy import deepcopy
from typing import Dict, List

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from plotter import *
from .dataclass import PlottingStats, RQColumn, SelectivityVsMetric, SelectivityVsRangeQueryMetric


class PlotSelectivities:
    vanilla_line_kwargs = {
        "label": "vanilla",
        "color": "black",
        "linestyle": "-",
    }

    rqdc_line_kwargs = {
        "label": "RangeReduce",
        "color": "black",
        "linestyle": "--",
    }

    rqdc_rq_same_line_kwargs = {
        "label": "RangeReduce Same RQ",
        "color": "black",
        "linestyle": "-.",
    }

    rqdc_rq_overlap_per_line_kwargs = {
        "label": "RangeReduce Overlapping RQ",
        "color": "black",
        "linestyle": ":",
    }

    def __init__(self, selectivity_vs_metric: Dict[str, SelectivityVsMetric]):
        self._selectivity_vs_metric: Dict[str, SelectivityVsMetric] = deepcopy(
            selectivity_vs_metric
        )

    def _plot_data(
        self,
        ax,
        vanilla: Dict,
        rqdc: Dict,
        rqdc_same_rq: Dict,
        rqdc_overlap_rq: Dict,
    ):
        selectivities = sorted(list(self._selectivity_vs_metric.keys()))
        x_axis = range(len(selectivities))

        data1 = list(dict(sorted(vanilla.items())).values())
        data2 = list(dict(sorted(rqdc.items())).values())
        data3 = list(dict(sorted(rqdc_same_rq.items())).values())
        data4 = list(dict(sorted(rqdc_overlap_rq.items())).values())

        ax.plot(x_axis, data1, **self.vanilla_line_kwargs)
        ax.plot(x_axis, data2, **self.rqdc_line_kwargs)
        ax.plot(x_axis, data3, **self.rqdc_rq_same_line_kwargs)
        ax.plot(x_axis, data4, **self.rqdc_rq_overlap_per_line_kwargs)
        ax.set_xticks(x_axis)
        ax.set_xticklabels([str(selectivity) for selectivity in selectivities])
        ax.set_ylim(bottom=0)
        ax.set_xlabel("selectivity")

    def plot_total_bytes_written(self):
        vanilla_data = dict()
        rqdc_data = dict()
        rqdc_same_rq_data = dict()
        rqdc_overlap_rq_data = dict()

        for selectivity, data in self._selectivity_vs_metric.items():
            vanilla_data[selectivity] = data.Vanilla.TotalWriteBytes
            rqdc_data[selectivity] = data.RangeReduce.TotalWriteBytes
            rqdc_same_rq_data[selectivity] = data.RangeReduceSameRQ.TotalWriteBytes
            rqdc_overlap_rq_data[selectivity] = (
                data.RangeReduceOverlappingRQ.TotalWriteBytes
            )

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        self._plot_data(
            ax, vanilla_data, rqdc_data, rqdc_same_rq_data, rqdc_overlap_rq_data
        )

        ax.set_ylabel("total write (GB)")

        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticklabels(
            [f"{int(i/(1000 ** 3))}" if i != 0 else "0" for i in ax.get_yticks()],
            fontsize=12,
        )

        # ax.set_title("total write (compaction + flushes)", fontsize=12)

        fig.legend(
            loc="upper center",
            ncol=2,
            fontsize=12,
            bbox_to_anchor=(0.5, 0.3),
            frameon=False,
            columnspacing=0.8
        )
        plt.show()

    def plot_compaction_debt(self):
        vanilla_data = dict()
        rqdc_data = dict()
        rqdc_same_rq_data = dict()
        rqdc_overlap_rq_data = dict()

        for selectivity, data in self._selectivity_vs_metric.items():
            vanilla_data[selectivity] = data.Vanilla.CompactionDebt
            rqdc_data[selectivity] = data.RangeReduce.CompactionDebt
            rqdc_same_rq_data[selectivity] = data.RangeReduceSameRQ.CompactionDebt
            rqdc_overlap_rq_data[selectivity] = (
                data.RangeReduceOverlappingRQ.CompactionDebt
            )

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        self._plot_data(
            ax, vanilla_data, rqdc_data, rqdc_same_rq_data, rqdc_overlap_rq_data
        )

        ax.set_ylabel("compaction debt (MB)", fontsize=12)

        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticklabels(
            [f"{int(i/(1000 ** 2))}" if i != 0 else "0" for i in ax.get_yticks()],
            fontsize=12,
        )

        # ax.set_title("compaction debt", fontsize=12)

        fig.legend(
            loc="upper center",
            ncol=2,
            fontsize=12,
            bbox_to_anchor=(0.5, 0.3),
            frameon=False,
            columnspacing=0.8
        )
        plt.show()

    def plot_write_amp_debt(self):
        vanilla_data = dict()
        rqdc_data = dict()
        rqdc_same_rq_data = dict()
        rqdc_overlap_rq_data = dict()

        for selectivity, data in self._selectivity_vs_metric.items():
            vanilla_data[selectivity] = data.Vanilla.WriteAmpDebt
            rqdc_data[selectivity] = data.RangeReduce.WriteAmpDebt
            rqdc_same_rq_data[selectivity] = data.RangeReduceSameRQ.WriteAmpDebt
            rqdc_overlap_rq_data[selectivity] = (
                data.RangeReduceOverlappingRQ.WriteAmpDebt
            )

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        self._plot_data(
            ax, vanilla_data, rqdc_data, rqdc_same_rq_data, rqdc_overlap_rq_data
        )

        ax.set_ylabel("write amp. debt (MB)", fontsize=12)

        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticklabels(
            [f"{int(i/(1000 ** 2))}" if i != 0 else "0" for i in ax.get_yticks()],
            fontsize=12,
        )

        # ax.set_title("compaction debt", fontsize=12)

        fig.legend(
            loc="upper center",
            ncol=2,
            fontsize=12,
            bbox_to_anchor=(0.5, 0.3),
            frameon=False,
            columnspacing=0.8
        )
        plt.show()

    def plot_write_amp_full_debt(self):
        vanilla_data = dict()
        rqdc_data = dict()
        rqdc_same_rq_data = dict()
        rqdc_overlap_rq_data = dict()

        for selectivity, data in self._selectivity_vs_metric.items():
            vanilla_data[selectivity] = data.Vanilla.WriteAmpDebtFull
            rqdc_data[selectivity] = data.RangeReduce.WriteAmpDebtFull
            rqdc_same_rq_data[selectivity] = data.RangeReduceSameRQ.WriteAmpDebtFull
            rqdc_overlap_rq_data[selectivity] = (
                data.RangeReduceOverlappingRQ.WriteAmpDebtFull
            )

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        self._plot_data(
            ax, vanilla_data, rqdc_data, rqdc_same_rq_data, rqdc_overlap_rq_data
        )

        ax.set_ylabel("write amp. full debt (MB)", fontsize=12)

        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticklabels(
            [f"{int(i/(1000 ** 2))}" if i != 0 else "0" for i in ax.get_yticks()],
            fontsize=12,
        )

        # ax.set_title("compaction debt", fontsize=12)

        fig.legend(
            loc="upper center",
            ncol=2,
            fontsize=12,
            bbox_to_anchor=(0.5, 0.3),
            frameon=False,
            columnspacing=0.8
        )
        plt.show()

    def plot_write_amp_partial_debt(self):
        vanilla_data = dict()
        rqdc_data = dict()
        rqdc_same_rq_data = dict()
        rqdc_overlap_rq_data = dict()

        for selectivity, data in self._selectivity_vs_metric.items():
            vanilla_data[selectivity] = data.Vanilla.WriteAmpDebtPartial
            rqdc_data[selectivity] = data.RangeReduce.WriteAmpDebtPartial
            rqdc_same_rq_data[selectivity] = data.RangeReduceSameRQ.WriteAmpDebtPartial
            rqdc_overlap_rq_data[selectivity] = (
                data.RangeReduceOverlappingRQ.WriteAmpDebtPartial
            )

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        self._plot_data(
            ax, vanilla_data, rqdc_data, rqdc_same_rq_data, rqdc_overlap_rq_data
        )

        ax.set_ylabel("write amp. partial debt (MB)", fontsize=12)

        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticklabels(
            [f"{int(i/(1000 ** 2))}" if i != 0 else "0" for i in ax.get_yticks()],
            fontsize=12,
        )

        # ax.set_title("compaction debt", fontsize=12)

        fig.legend(
            loc="upper center",
            ncol=2,
            fontsize=12,
            bbox_to_anchor=(0.5, 0.3),
            frameon=False,
            columnspacing=0.8
        )
        plt.show()

    def plot_space_amplification(self):
        vanilla_data = dict()
        rqdc_data = dict()
        rqdc_same_rq_data = dict()
        rqdc_overlap_rq_data = dict()

        for selectivity, data in self._selectivity_vs_metric.items():
            vanilla_data[selectivity] = data.Vanilla.DBSize / (INSERTS * ENTRY_SIZE)
            rqdc_data[selectivity] = data.RangeReduce.DBSize / (INSERTS * ENTRY_SIZE)
            rqdc_same_rq_data[selectivity] = data.RangeReduceSameRQ.DBSize / (INSERTS * ENTRY_SIZE)
            rqdc_overlap_rq_data[selectivity] = (
                data.RangeReduceOverlappingRQ.DBSize / (INSERTS * ENTRY_SIZE)
            )

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        self._plot_data(
            ax, vanilla_data, rqdc_data, rqdc_same_rq_data, rqdc_overlap_rq_data
        )

        ax.set_ylabel("space amplification", fontsize=12)
        ax.set_ylim(top=2.5)

        # ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        # ax.set_yticklabels(
        #     [f"{float(i):.2f}" if i != 0 else "0" for i in ax.get_yticks()],
        #     fontsize=12,
        # )

        fig.legend(
            loc="upper center",
            ncol=2,
            fontsize=12,
            bbox_to_anchor=(0.5, 0.3),
            frameon=False,
            columnspacing=0.8
        )
        plt.show()

    def plot_compaction_read(self):
        vanilla_data = dict()
        rqdc_data = dict()
        rqdc_same_rq_data = dict()
        rqdc_overlap_rq_data = dict()

        for selectivity, data in self._selectivity_vs_metric.items():
            vanilla_data[selectivity] = data.Vanilla.CompactionReadBytes
            rqdc_data[selectivity] = data.RangeReduce.CompactionReadBytes
            rqdc_same_rq_data[selectivity] = data.RangeReduceSameRQ.CompactionReadBytes
            rqdc_overlap_rq_data[selectivity] = (
                data.RangeReduceOverlappingRQ.CompactionReadBytes
            )

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        self._plot_data(
            ax, vanilla_data, rqdc_data, rqdc_same_rq_data, rqdc_overlap_rq_data
        )

        ax.set_ylabel("compaction read (GB)", fontsize=12)

        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticklabels(
            [f"{int(i/(1000 ** 3))}" if i != 0 else "0" for i in ax.get_yticks()],
            fontsize=12,
        )

        fig.legend(
            loc="upper center",
            ncol=2,
            fontsize=12,
            bbox_to_anchor=(0.5, 0.3),
            frameon=False,
            columnspacing=0.8
        )
        plt.show()

    @staticmethod
    def plot_total_data_movement(
        selectivity_vs_metric: Dict[str, SelectivityVsMetric],
        selectivity_vs_rq_metric: Dict[str, SelectivityVsRangeQueryMetric]
    ):
        vanilla_data = dict()
        rqdc_data = dict()
        rqdc_same_rq_data = dict()
        rqdc_overlap_rq_data = dict()

        for selectivity, data in selectivity_vs_rq_metric.items():
            vanilla_data[selectivity] = data.Vanilla[[str(RQColumn.TOTAL_ENTRIES_READ)]].sum()
            rqdc_data[selectivity] = data.RangeReduce[[str(RQColumn.TOTAL_ENTRIES_READ)]].sum()
            rqdc_same_rq_data[selectivity] = data.RangeReduceSameRQ[[str(RQColumn.TOTAL_ENTRIES_READ)]].sum()
            rqdc_overlap_rq_data[selectivity] = data.RangeReduceOverlappingRQ[[str(RQColumn.TOTAL_ENTRIES_READ)]].sum()

        for selectivity, data in selectivity_vs_metric.items():
            vanilla_data[selectivity] = data.Vanilla.TotalWriteBytes + data.Vanilla.CompactionReadBytes + vanilla_data[selectivity] * ENTRY_SIZE
            rqdc_data[selectivity] = data.RangeReduce.TotalWriteBytes + data.RangeReduce.CompactionReadBytes + rqdc_data[selectivity] * ENTRY_SIZE
            rqdc_same_rq_data[selectivity] = data.RangeReduceSameRQ.TotalWriteBytes + data.RangeReduceSameRQ.CompactionReadBytes + rqdc_same_rq_data[selectivity] * ENTRY_SIZE
            rqdc_overlap_rq_data[selectivity] = data.RangeReduceOverlappingRQ.TotalWriteBytes + data.RangeReduceOverlappingRQ.CompactionReadBytes + rqdc_overlap_rq_data[selectivity] * ENTRY_SIZE

        vanilla_plot_kwargs = {
            "label": "vanilla",
            "color": "saddlebrown",
        }
        rqdc_plot_kwargs = {
            "label": "RangeReduce",
            "color": "steelblue",
        }
        rqdc_rq_same_plot_kwargs = {
            "label": "RangeReduce Same RQ",
            "color": "slateblue",
        }
        rqdc_rq_overlap_per_plot_kwargs = {
            "label": "RangeReduce Overlapping RQ",
            "color": "purple",
        }

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        selectivities = sorted(list(selectivity_vs_rq_metric.keys()))
        x_axis = range(len(selectivities))

        data1 = list(dict(sorted(vanilla_data.items())).values())
        data2 = list(dict(sorted(rqdc_data.items())).values())
        data3 = list(dict(sorted(rqdc_same_rq_data.items())).values())
        data4 = list(dict(sorted(rqdc_overlap_rq_data.items())).values())

        ax.plot(x_axis, data1, **vanilla_plot_kwargs)
        ax.plot(x_axis, data2, **rqdc_plot_kwargs)
        ax.plot(x_axis, data3, **rqdc_rq_same_plot_kwargs)
        ax.plot(x_axis, data4, **rqdc_rq_overlap_per_plot_kwargs)
        ax.set_xticks(x_axis)
        ax.set_xticklabels([str(selectivity) for selectivity in selectivities])
        ax.set_ylim(bottom=0)

        ax.set_ylabel("total datamovement (GB)", fontsize=12)
        ax.set_xlabel("selectivity", fontsize=12)

        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticklabels(
            [f"{int(i/(1000 ** 3))}" if i != 0 else "0" for i in ax.get_yticks()],
            fontsize=12,
        )

        fig.legend(
            loc="upper center",
            ncol=2,
            fontsize=12,
            bbox_to_anchor=(0.5, 0.90),
            frameon=False,
            columnspacing=0.4
        )
        plt.show()


class PlotSelectivitiesRangeQuery:
    vanilla_plot_kwargs = {
        "label": "vanilla",
        "color": "saddlebrown",
    }
    rqdc_plot_kwargs = {
        "label": "RangeReduce",
        "color": "steelblue",
    }
    rqdc_rq_same_plot_kwargs = {
        "label": "RangeReduce Same RQ",
        "color": "slateblue",
    }
    rqdc_rq_overlap_per_plot_kwargs = {
        "label": "RangeReduce Overlapping RQ",
        "color": "purple",
    }

    def __init__(self, selectivity_vs_rq_metric: Dict[str, SelectivityVsRangeQueryMetric]):
        self._selectivity_vs_rq_metric: Dict[str, SelectivityVsRangeQueryMetric] = deepcopy(selectivity_vs_rq_metric)

    def _plot_data(
        self,
        ax: plt.Axes,
        vanilla: Dict,
        rqdc: Dict,
        rqdc_same_rq: Dict,
        rqdc_overlap_rq: Dict,
    ):
        selectivities = sorted(list(self._selectivity_vs_rq_metric.keys()))
        x_axis = range(len(selectivities))

        data1 = list(dict(sorted(vanilla.items())).values())
        data2 = list(dict(sorted(rqdc.items())).values())
        data3 = list(dict(sorted(rqdc_same_rq.items())).values())
        data4 = list(dict(sorted(rqdc_overlap_rq.items())).values())

        ax.plot(x_axis, data1, **self.vanilla_plot_kwargs)
        ax.plot(x_axis, data2, **self.rqdc_plot_kwargs)
        ax.plot(x_axis, data3, **self.rqdc_rq_same_plot_kwargs)
        ax.plot(x_axis, data4, **self.rqdc_rq_overlap_per_plot_kwargs)
        ax.set_xticks(x_axis)
        ax.set_xticklabels([str(selectivity) for selectivity in selectivities])
        ax.set_ylim(bottom=0)
        ax.set_xlabel("selectivity")

    def avg_bytes_written_for_range_queries(self):
        vanilla_data = dict()
        rqdc_data = dict()
        rqdc_same_rq_data = dict()
        rqdc_overlap_rq_data = dict()

        for selectivity, data in self._selectivity_vs_rq_metric.items():
            vanilla_data[selectivity] = data.Vanilla[[str(RQColumn.DATA_USEFUL_BYTES_WRITTEN), str(RQColumn.DATA_USEFUL_BYTES_WRITTEN) ]].sum(axis=1).mean()
            rqdc_data[selectivity] = data.RangeReduce[[str(RQColumn.DATA_USEFUL_BYTES_WRITTEN), str(RQColumn.DATA_USEFUL_BYTES_WRITTEN) ]].sum(axis=1).mean()
            rqdc_same_rq_data[selectivity] = data.RangeReduceSameRQ[[str(RQColumn.DATA_USEFUL_BYTES_WRITTEN), str(RQColumn.DATA_USEFUL_BYTES_WRITTEN) ]].sum(axis=1).mean()
            rqdc_overlap_rq_data[selectivity] = data.RangeReduceOverlappingRQ[[str(RQColumn.DATA_USEFUL_BYTES_WRITTEN), str(RQColumn.DATA_USEFUL_BYTES_WRITTEN) ]].sum(axis=1).mean()

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        self._plot_data(
            ax, vanilla_data, rqdc_data, rqdc_same_rq_data, rqdc_overlap_rq_data
        )

        ax.set_ylabel("avg. write (KB)", fontsize=12)

        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticklabels(
            [f"{int(i/(1000))}" if i != 0 else "0" for i in ax.get_yticks()],
            fontsize=12,
        )
        ax.set_title("avg. write (RangeReduce range query)", fontsize=12)

        fig.legend(
            loc="lower center",
            ncol=2,
            fontsize=12,
            bbox_to_anchor=(0.5, 0.70),
            frameon=False,
            columnspacing=0.4
        )

        plt.show()

    def avg_bytes_read_for_range_queries(self):
        vanilla_data = dict()
        rqdc_data = dict()
        rqdc_same_rq_data = dict()
        rqdc_overlap_rq_data = dict()

        for selectivity, data in self._selectivity_vs_rq_metric.items():
            vanilla_data[selectivity] = data.Vanilla[[str(RQColumn.TOTAL_ENTRIES_READ)]].apply(lambda x: x * ENTRY_SIZE)[str(RQColumn.TOTAL_ENTRIES_READ)].mean()
            rqdc_data[selectivity] = data.RangeReduce[[str(RQColumn.TOTAL_ENTRIES_READ)]].apply(lambda x: x * ENTRY_SIZE)[str(RQColumn.TOTAL_ENTRIES_READ)].mean()
            rqdc_same_rq_data[selectivity] = data.RangeReduceSameRQ[[str(RQColumn.TOTAL_ENTRIES_READ)]].apply(lambda x: x * ENTRY_SIZE)[str(RQColumn.TOTAL_ENTRIES_READ)].mean()
            rqdc_overlap_rq_data[selectivity] = data.RangeReduceOverlappingRQ[[str(RQColumn.TOTAL_ENTRIES_READ)]].apply(lambda x: x * ENTRY_SIZE)[str(RQColumn.TOTAL_ENTRIES_READ)].mean()

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        self._plot_data(
            ax, vanilla_data, rqdc_data, rqdc_same_rq_data, rqdc_overlap_rq_data
        )

        ax.set_ylabel("avg. read (MB)", fontsize=12)

        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticklabels(
            [f"{int(i/(1000 ** 2))}" if i != 0 else "0" for i in ax.get_yticks()],
            fontsize=12,
        )

        fig.legend(
            loc="lower center",
            ncol=2,
            fontsize=12,
            bbox_to_anchor=(0.5, 0.70),
            frameon=False,
            columnspacing=0.4
        )

        plt.show()

    def avg_latency_for_range_queries(self):
        vanilla_data = dict()
        rqdc_data = dict()
        rqdc_same_rq_data = dict()
        rqdc_overlap_rq_data = dict()

        for selectivity, data in self._selectivity_vs_rq_metric.items():
            vanilla_data[selectivity] = data.Vanilla[[str(RQColumn.RQ_TOTAL_TIME)]].mean()
            rqdc_data[selectivity] = data.RangeReduce[[str(RQColumn.RQ_TOTAL_TIME)]].mean()
            rqdc_same_rq_data[selectivity] = data.RangeReduceSameRQ[[str(RQColumn.RQ_TOTAL_TIME)]].mean()
            rqdc_overlap_rq_data[selectivity] = data.RangeReduceOverlappingRQ[[str(RQColumn.RQ_TOTAL_TIME)]].mean()

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        self._plot_data(
            ax, vanilla_data, rqdc_data, rqdc_same_rq_data, rqdc_overlap_rq_data
        )
        ax.set_ylabel("avg. latency (ms)", fontsize=12)

        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticklabels(
            [f"{int(i/(1000 ** 2))}" if i != 0 else "0" for i in ax.get_yticks()],
            fontsize=12,
        )

        fig.legend(
            loc="lower center",
            ncol=2,
            fontsize=12,
            bbox_to_anchor=(0.5, 0.70),
            frameon=False,
            columnspacing=0.4
        )
        plt.show()
