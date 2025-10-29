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
        tag
    ):
        selectivities = sorted(list(self._selectivity_vs_metric.keys()))
        x_axis = range(len(selectivities))

        data1 = list(dict(sorted(vanilla.items())).values())
        data2 = list(dict(sorted(rqdc.items())).values())

        ax.plot(x_axis, data1, label=self.vanilla_line_kwargs['label'] + f" {tag}", color=self.vanilla_line_kwargs['color'], linestyle=self.vanilla_line_kwargs['linestyle'])
        ax.plot(x_axis, data2, label=self.rqdc_line_kwargs['label'] + f" {tag}", color=self.rqdc_line_kwargs['color'], linestyle=self.rqdc_line_kwargs['linestyle'])
        ax.set_xticks(x_axis)
        ax.set_xticklabels([str(selectivity) for selectivity in selectivities])

        data_max = max(max(data1), max(data2))
        ax.set_ylim(bottom=0, top= data_max + 0.05*data_max)
        ax.set_xlabel("selectivity")

    def plot_total_bytes_written(self, tag=""):
        vanilla_data = dict()
        rqdc_data = dict()

        for selectivity, data in self._selectivity_vs_metric.items():
            vanilla_data[selectivity] = data.Vanilla.CompactionWrittenBytes
            rqdc_data[selectivity] = data.RangeReduce.CompactionWrittenBytes + data.RangeReduce.RangeReduceWrittenBytes

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        self._plot_data(
            ax, vanilla_data, rqdc_data, tag
        )

        ax.set_ylabel("total write (MB)")

        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticklabels(
            [f"{int(i/(1000 ** 2))}" if i != 0 else "0" for i in ax.get_yticks()],
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

    def plot_compaction_debt(self, tag):
        vanilla_data = dict()
        rqdc_data = dict()

        for selectivity, data in self._selectivity_vs_metric.items():
            vanilla_data[selectivity] = data.Vanilla.CompactionDebt
            rqdc_data[selectivity] = data.RangeReduce.CompactionDebt

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        self._plot_data(
            ax, vanilla_data, rqdc_data, tag
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

    def plot_write_amp_debt(self, tag):
        vanilla_data = dict()
        rqdc_data = dict()

        for selectivity, data in self._selectivity_vs_metric.items():
            vanilla_data[selectivity] = data.Vanilla.WriteAmpDebt
            rqdc_data[selectivity] = data.RangeReduce.WriteAmpDebt

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        self._plot_data(
            ax, vanilla_data, rqdc_data, tag
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

    def plot_write_amp_full_debt(self, tag):
        vanilla_data = dict()
        rqdc_data = dict()

        for selectivity, data in self._selectivity_vs_metric.items():
            vanilla_data[selectivity] = data.Vanilla.WriteAmpDebtFull
            rqdc_data[selectivity] = data.RangeReduce.WriteAmpDebtFull

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        self._plot_data(
            ax, vanilla_data, rqdc_data, tag
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

    def plot_write_amp_partial_debt(self, tag):
        vanilla_data = dict()
        rqdc_data = dict()

        for selectivity, data in self._selectivity_vs_metric.items():
            vanilla_data[selectivity] = data.Vanilla.WriteAmpDebtPartial
            rqdc_data[selectivity] = data.RangeReduce.WriteAmpDebtPartial

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        self._plot_data(
            ax, vanilla_data, rqdc_data, tag
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

    def plot_space_amplification(self, tag):
        vanilla_data = dict()
        rqdc_data = dict()

        for selectivity, data in self._selectivity_vs_metric.items():
            vanilla_data[selectivity] = data.Vanilla.DBSize / (INSERTS * ENTRY_SIZE)
            rqdc_data[selectivity] = data.RangeReduce.DBSize / (INSERTS * ENTRY_SIZE)

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        self._plot_data(
            ax, vanilla_data, rqdc_data, tag
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

    def plot_compaction_read(self, tag):
        vanilla_data = dict()
        rqdc_data = dict()

        for selectivity, data in self._selectivity_vs_metric.items():
            vanilla_data[selectivity] = data.Vanilla.CompactionReadBytes
            rqdc_data[selectivity] = data.RangeReduce.CompactionReadBytes

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        self._plot_data(
            ax, vanilla_data, rqdc_data, tag
        )

        ax.set_ylabel("compaction read (MB)", fontsize=12)

        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticklabels(
            [f"{int(i/(1000 ** 2))}" if i != 0 else "0" for i in ax.get_yticks()],
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
        selectivity_vs_rq_metric: Dict[str, SelectivityVsRangeQueryMetric],
        tag
    ):
        vanilla_data = dict()
        rqdc_data = dict()

        for selectivity, data in selectivity_vs_rq_metric.items():
            vanilla_data[selectivity] = data.Vanilla[[str(RQColumn.TOTAL_ENTRIES_READ)]].sum()
            rqdc_data[selectivity] = data.RangeReduce[[str(RQColumn.TOTAL_ENTRIES_READ)]].sum()

        for selectivity, data in selectivity_vs_metric.items():
            vanilla_data[selectivity] = data.Vanilla.CompactionWrittenBytes + data.Vanilla.CompactionReadBytes + vanilla_data[selectivity] * ENTRY_SIZE
            rqdc_data[selectivity] = data.RangeReduce.CompactionWrittenBytes + data.RangeReduce.RangeReduceWrittenBytes + data.RangeReduce.CompactionReadBytes + rqdc_data[selectivity] * ENTRY_SIZE

        vanilla_plot_kwargs = {
            "label": "vanilla",
            "color": "saddlebrown",
        }
        rqdc_plot_kwargs = {
            "label": "RangeReduce",
            "color": "steelblue",
        }

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        selectivities = sorted(list(selectivity_vs_rq_metric.keys()))
        x_axis = range(len(selectivities))

        data1 = list(dict(sorted(vanilla_data.items())).values())
        data2 = list(dict(sorted(rqdc_data.items())).values())

        ax.plot(x_axis, data1, label=vanilla_plot_kwargs['label'] + f" {tag}", color=vanilla_plot_kwargs['color'])
        ax.plot(x_axis, data2, label=rqdc_plot_kwargs['label'] + f" {tag}", color=rqdc_plot_kwargs["color"])
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

    def __init__(self, selectivity_vs_rq_metric: Dict[str, SelectivityVsRangeQueryMetric]):
        self._selectivity_vs_rq_metric: Dict[str, SelectivityVsRangeQueryMetric] = deepcopy(selectivity_vs_rq_metric)

    def _plot_data(
        self,
        ax: plt.Axes,
        vanilla: Dict,
        rqdc: Dict,
        tag
    ):
        selectivities = sorted(list(self._selectivity_vs_rq_metric.keys()))
        x_axis = range(len(selectivities))

        data1 = list(dict(sorted(vanilla.items())).values())
        data2 = list(dict(sorted(rqdc.items())).values())

        ax.plot(x_axis, data1, label=self.vanilla_plot_kwargs['label'] + f" {tag}", color=self.vanilla_plot_kwargs['color'])
        ax.plot(x_axis, data2, label=self.rqdc_plot_kwargs['label'] + f" {tag}", color=self.rqdc_plot_kwargs['color'])
        ax.set_xticks(x_axis)
        ax.set_xticklabels([str(selectivity) for selectivity in selectivities])
        ax.set_ylim(bottom=0)
        ax.set_xlabel("selectivity")

    def avg_bytes_written_for_range_queries(self, tag):
        vanilla_data = dict()
        rqdc_data = dict()

        for selectivity, data in self._selectivity_vs_rq_metric.items():
            vanilla_data[selectivity] = data.Vanilla[[str(RQColumn.DATA_USEFUL_BYTES_WRITTEN), str(RQColumn.DATA_USEFUL_BYTES_WRITTEN) ]].sum(axis=1).mean()
            rqdc_data[selectivity] = data.RangeReduce[[str(RQColumn.DATA_USEFUL_BYTES_WRITTEN), str(RQColumn.DATA_USEFUL_BYTES_WRITTEN) ]].sum(axis=1).mean()

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        self._plot_data(
            ax, vanilla_data, rqdc_data, tag
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

    def avg_bytes_read_for_range_queries(self, tag):
        vanilla_data = dict()
        rqdc_data = dict()

        for selectivity, data in self._selectivity_vs_rq_metric.items():
            vanilla_data[selectivity] = data.Vanilla[[str(RQColumn.TOTAL_ENTRIES_READ)]].apply(lambda x: x * ENTRY_SIZE)[str(RQColumn.TOTAL_ENTRIES_READ)].mean()
            rqdc_data[selectivity] = data.RangeReduce[[str(RQColumn.TOTAL_ENTRIES_READ)]].apply(lambda x: x * ENTRY_SIZE)[str(RQColumn.TOTAL_ENTRIES_READ)].mean()

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        self._plot_data(
            ax, vanilla_data, rqdc_data, tag
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

    def avg_latency_for_range_queries(self, tag):
        vanilla_data = dict()
        rqdc_data = dict()

        for selectivity, data in self._selectivity_vs_rq_metric.items():
            vanilla_data[selectivity] = data.Vanilla[[str(RQColumn.RQ_TOTAL_TIME)]].mean()
            rqdc_data[selectivity] = data.RangeReduce[[str(RQColumn.RQ_TOTAL_TIME)]].mean()

        fig_size = (6.5, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        self._plot_data(
            ax, vanilla_data, rqdc_data, tag
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
