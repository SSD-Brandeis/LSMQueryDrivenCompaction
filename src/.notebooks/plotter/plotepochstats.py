from copy import deepcopy
from typing import List

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from plotter import *
from .dataclass import PlottingStats, RQColumn


class PlotEpochStats:
    vanilla_bar_kwargs = {
        "label": "vanilla",
        "color": "None",
        "hatch": "",
        "edgecolor": "black",
    }
    rqdc_bar_kwargs = {
        "label": "RangeReduce",
        "color": "None",
        "hatch": "--",
        "edgecolor": "black",
    }

    def __init__(self, vanilla: List[PlottingStats], rqdc: List[PlottingStats]):
        if len(vanilla) != len(rqdc):
            raise Exception("lengths of vanilla and rqdc stats are not the same")
        self._vanilla: List[PlottingStats] = deepcopy(vanilla)
        self._rqdc: List[PlottingStats] = deepcopy(rqdc)

    def plot_total_bytes_written(self):
        vanilla_writes = [van.TotalWriteBytes for van in self._vanilla]
        rqdc_writes = [rqdc.TotalWriteBytes for rqdc in self._rqdc]

        fig_size = (6, 4)
        bar_width = 0.35
        num_bars_per_group = 2
        epochs = NUMEPOCHS

        index = np.arange(epochs)
        fig, ax = plt.subplots(figsize=fig_size)

        ax.bar(
            index - (bar_width / num_bars_per_group),
            vanilla_writes,
            bar_width,
            **self.vanilla_bar_kwargs,
        )
        ax.bar(
            index + (bar_width / num_bars_per_group),
            rqdc_writes,
            bar_width,
            **self.rqdc_bar_kwargs,
        )

        ax.set_ylabel("total write (GB)", fontsize=12)
        ax.set_xlabel("epoch", fontsize=12)

        ax.set_ylim(bottom=0)

        ax.set_xticks(range(epochs))
        ax.set_xticklabels([f"{epoch}" for epoch in range(1, epochs + 1)], fontsize=12)

        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticklabels(
            [f"{int(i/(1000 ** 3))}" if i != 0 else "0" for i in ax.get_yticks()],
            fontsize=12,
        )

        ax.set_title("total write (compaction + flushes)", fontsize=12)

        fig.legend(
            loc="upper center",
            ncol=2,
            fontsize=12,
            bbox_to_anchor=(0.5, 0.90),
            frameon=False,
        )
        plt.show()

    def plot_compaction_debt(self):
        vanilla_compaction_debt = [van.CompactionDebt for van in self._vanilla]
        rqdc_compaction_debt = [rqdc.CompactionDebt for rqdc in self._rqdc]

        fig_size = (6, 4)
        bar_width = 0.35
        num_bars_per_group = 2
        epochs = NUMEPOCHS

        index = np.arange(epochs)
        fig, ax = plt.subplots(figsize=fig_size)

        ax.bar(
            index - (bar_width / num_bars_per_group),
            vanilla_compaction_debt,
            bar_width,
            **self.vanilla_bar_kwargs,
        )
        ax.bar(
            index + (bar_width / num_bars_per_group),
            rqdc_compaction_debt,
            bar_width,
            **self.rqdc_bar_kwargs,
        )

        ax.set_ylabel("compaction debt (MB)", fontsize=12)
        ax.set_xlabel("epoch", fontsize=12)

        ax.set_ylim(bottom=0)

        ax.set_xticks(range(epochs))
        ax.set_xticklabels([f"{epoch}" for epoch in range(1, epochs + 1)], fontsize=12)

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
            bbox_to_anchor=(0.5, 0.98),
            frameon=False,
        )
        plt.show()

    def plot_write_amp_debt(self):
        vanilla_compaction_debt = [van.WriteAmpDebt for van in self._vanilla]
        rqdc_compaction_debt = [rqdc.WriteAmpDebt for rqdc in self._rqdc]

        fig_size = (6, 4)
        bar_width = 0.35
        num_bars_per_group = 2
        epochs = NUMEPOCHS

        index = np.arange(epochs)
        fig, ax = plt.subplots(figsize=fig_size)

        ax.bar(
            index - (bar_width / num_bars_per_group),
            vanilla_compaction_debt,
            bar_width,
            **self.vanilla_bar_kwargs,
        )
        ax.bar(
            index + (bar_width / num_bars_per_group),
            rqdc_compaction_debt,
            bar_width,
            **self.rqdc_bar_kwargs,
        )

        ax.set_ylabel("write amp. debt (MB)", fontsize=12)
        ax.set_xlabel("epoch", fontsize=12)

        ax.set_ylim(bottom=0)

        ax.set_xticks(range(epochs))
        ax.set_xticklabels([f"{epoch}" for epoch in range(1, epochs + 1)], fontsize=12)

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
            bbox_to_anchor=(0.5, 0.98),
            frameon=False,
        )
        plt.show()

    def plot_write_amp_full_debt(self):
        vanilla_compaction_debt = [van.WriteAmpDebtFull for van in self._vanilla]
        rqdc_compaction_debt = [rqdc.WriteAmpDebtFull for rqdc in self._rqdc]

        fig_size = (6, 4)
        bar_width = 0.35
        num_bars_per_group = 2
        epochs = NUMEPOCHS

        index = np.arange(epochs)
        fig, ax = plt.subplots(figsize=fig_size)

        ax.bar(
            index - (bar_width / num_bars_per_group),
            vanilla_compaction_debt,
            bar_width,
            **self.vanilla_bar_kwargs,
        )
        ax.bar(
            index + (bar_width / num_bars_per_group),
            rqdc_compaction_debt,
            bar_width,
            **self.rqdc_bar_kwargs,
        )

        ax.set_ylabel("write amp. full debt (MB)", fontsize=12)
        ax.set_xlabel("epoch", fontsize=12)

        ax.set_ylim(bottom=0)

        ax.set_xticks(range(epochs))
        ax.set_xticklabels([f"{epoch}" for epoch in range(1, epochs + 1)], fontsize=12)

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
            bbox_to_anchor=(0.5, 0.98),
            frameon=False,
        )
        plt.show()

    def plot_write_amp_partial_debt(self):
        vanilla_compaction_debt = [van.WriteAmpDebtPartial for van in self._vanilla]
        rqdc_compaction_debt = [rqdc.WriteAmpDebtPartial for rqdc in self._rqdc]

        fig_size = (6, 4)
        bar_width = 0.35
        num_bars_per_group = 2
        epochs = NUMEPOCHS

        index = np.arange(epochs)
        fig, ax = plt.subplots(figsize=fig_size)

        ax.bar(
            index - (bar_width / num_bars_per_group),
            vanilla_compaction_debt,
            bar_width,
            **self.vanilla_bar_kwargs,
        )
        ax.bar(
            index + (bar_width / num_bars_per_group),
            rqdc_compaction_debt,
            bar_width,
            **self.rqdc_bar_kwargs,
        )

        ax.set_ylabel("write amp. partial debt (MB)", fontsize=12)
        ax.set_xlabel("epoch", fontsize=12)

        ax.set_ylim(bottom=0)

        ax.set_xticks(range(epochs))
        ax.set_xticklabels([f"{epoch}" for epoch in range(1, epochs + 1)], fontsize=12)

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
            bbox_to_anchor=(0.5, 0.98),
            frameon=False,
        )
        plt.show()

    def plot_space_amplification(self):
        vanilla_dbsize = [van.DBSize / (INSERTS * ENTRY_SIZE) for van in self._vanilla]
        rqdc_dbsize = [rqdc.DBSize / (INSERTS * ENTRY_SIZE) for rqdc in self._rqdc]

        fig_size = (6, 4)
        bar_width = 0.35
        num_bars_per_group = 2
        epochs = NUMEPOCHS

        index = np.arange(epochs)
        fig, ax = plt.subplots(figsize=fig_size)

        ax.bar(
            index - (bar_width / num_bars_per_group),
            vanilla_dbsize,
            bar_width,
            **self.vanilla_bar_kwargs,
        )
        ax.bar(
            index + (bar_width / num_bars_per_group),
            rqdc_dbsize,
            bar_width,
            **self.rqdc_bar_kwargs,
        )

        ax.set_ylabel("space amplification", fontsize=12)
        ax.set_xlabel("epoch", fontsize=12)

        ax.set_ylim(bottom=0)

        ax.set_xticks(range(epochs))
        ax.set_xticklabels([f"{epoch}" for epoch in range(1, epochs + 1)], fontsize=12)

        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticklabels(
            [f"{float(i):.2f}" if i != 0 else "0" for i in ax.get_yticks()],
            fontsize=12,
        )

        fig.legend(
            loc="upper center",
            ncol=2,
            fontsize=12,
            bbox_to_anchor=(0.5, 0.98),
            frameon=False,
        )
        plt.show()

    # def plot_total_data_movement(self):
    #     vanilla_datamovement = [van.TotalWriteBytes + van.CompactionReadBytes for van in self._vanilla]
    #     rqdc_datamovement = [rqdc.TotalWriteBytes + rqdc.CompactionReadBytes for rqdc in self._rqdc]

    #     fig_size = (6, 4)
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
        vanilla_compaction_read = [van.CompactionReadBytes for van in self._vanilla]
        rqdc_compaction_read = [rqdc.CompactionReadBytes for rqdc in self._rqdc]

        fig_size = (6, 4)
        bar_width = 0.35
        num_bars_per_group = 2
        epochs = NUMEPOCHS

        index = np.arange(epochs)
        fig, ax = plt.subplots(figsize=fig_size)

        ax.bar(
            index - (bar_width / num_bars_per_group),
            vanilla_compaction_read,
            bar_width,
            **self.vanilla_bar_kwargs,
        )
        ax.bar(
            index + (bar_width / num_bars_per_group),
            rqdc_compaction_read,
            bar_width,
            **self.rqdc_bar_kwargs,
        )

        ax.set_ylabel("compaction read (GB)", fontsize=12)
        ax.set_xlabel("epoch", fontsize=12)

        ax.set_ylim(bottom=0)

        ax.set_xticks(range(epochs))
        ax.set_xticklabels([f"{epoch}" for epoch in range(1, epochs + 1)], fontsize=12)

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
        )
        plt.show()

    def plot_levels_state(self):
        vanilla_levels_state = [van.LevelsState for van in self._vanilla]
        rqdc_levels_state = [rqdc.LevelsState for rqdc in self._rqdc]

        fig_size = (6, 4)
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
    vanilla_plot_kwargs = {
        "label": "vanilla universal",
        "color": "saddlebrown",
    }
    rqdc_plot_kwargs = {
        "label": "rqdc",
        "color": "steelblue",
    }

    def __init__(self, vanilla: pd.DataFrame, rqdc: pd.DataFrame):
        self._vanilla = vanilla.copy(deep=True)
        self._rqdc = rqdc.copy(deep=True)

    def bytes_written_for_each_range_query(self):
        vanilla_rq_bytes = (
            self._vanilla[
                [
                    str(RQColumn.DATA_USEFUL_BYTES_WRITTEN),
                    str(RQColumn.DATA_UNUSEFUL_BYTES_WRITTEN),
                ]
            ]
            .sum(axis=1)
            .to_list()
        )
        rqdc_rq_bytes = (
            self._rqdc[
                [
                    str(RQColumn.DATA_USEFUL_BYTES_WRITTEN),
                    str(RQColumn.DATA_UNUSEFUL_BYTES_WRITTEN),
                ]
            ]
            .sum(axis=1)
            .to_list()
        )

        if len(vanilla_rq_bytes) != len(rqdc_rq_bytes):
            raise Exception("found different number of range queries")

        fig_size = (20, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        # ax.plot(range(len(vanilla_rq_bytes)), vanilla_rq_bytes)
        ax.bar(range(len(rqdc_rq_bytes)), rqdc_rq_bytes, color="black")

        ax.set_ylabel("total write (MB)", fontsize=12)
        ax.set_xlabel("range query number", fontsize=12)

        ax.set_ylim(bottom=0)

        ax.xaxis.set_major_locator(ticker.FixedLocator(ax.get_xticks()))
        ax.set_xticklabels([f"{int(tick)}" for tick in ax.get_xticks()], fontsize=12)

        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticklabels(
            [f"{int(i/(1000 ** 2))}" if i != 0 else "0" for i in ax.get_yticks()],
            fontsize=12,
        )
        ax.set_title("total write (RQDC range query)", fontsize=12)

        plt.show()

    def bytes_read_for_each_range_query(self):
        vanilla_rq_bytes = (
            self._vanilla[[str(RQColumn.TOTAL_ENTRIES_READ)]]
            .apply(lambda x: x * ENTRY_SIZE)[str(RQColumn.TOTAL_ENTRIES_READ)]
            .to_list()
        )
        rqdc_rq_bytes = (
            self._rqdc[[str(RQColumn.TOTAL_ENTRIES_READ)]]
            .apply(lambda x: x * ENTRY_SIZE)[str(RQColumn.TOTAL_ENTRIES_READ)]
            .to_list()
        )

        if len(vanilla_rq_bytes) != len(rqdc_rq_bytes):
            raise Exception("found different number of range queries")

        fig_size = (20, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        ax.plot(
            range(len(vanilla_rq_bytes)), vanilla_rq_bytes, **self.vanilla_plot_kwargs
        )
        ax.plot(range(len(rqdc_rq_bytes)), rqdc_rq_bytes, **self.rqdc_plot_kwargs)

        ax.set_ylabel("total read (MB)", fontsize=12)
        ax.set_xlabel("range query number", fontsize=12)

        ax.set_ylim(bottom=0)

        ax.xaxis.set_major_locator(ticker.FixedLocator(ax.get_xticks()))
        ax.set_xticklabels([f"{int(tick)}" for tick in ax.get_xticks()], fontsize=12)

        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticklabels(
            [f"{int(i/(1000 ** 2))}" if i != 0 else "0" for i in ax.get_yticks()],
            fontsize=12,
        )
        ax.set_title("total read", fontsize=12)

        fig.legend(
            loc="lower center",
            ncol=2,
            fontsize=12,
            bbox_to_anchor=(0.5, 0.1),
            frameon=False,
        )

        plt.show()

    def latency_for_each_range_query(self):

        plotting_column = str(RQColumn.RQ_TOTAL_TIME)

        vanilla_rq_time = self._vanilla[plotting_column].to_list()
        rqdc_rq_time = self._rqdc[plotting_column].to_list()

        if len(vanilla_rq_time) != len(rqdc_rq_time):
            raise Exception("found different number of range queries")

        fig_size = (20, 4)
        fig, ax = plt.subplots(figsize=fig_size)

        ax.plot(
            range(len(vanilla_rq_time)), vanilla_rq_time, **self.vanilla_plot_kwargs
        )
        ax.plot(range(len(rqdc_rq_time)), rqdc_rq_time, **self.rqdc_plot_kwargs)

        ax.set_ylabel("latency (ms)", fontsize=12)
        ax.set_xlabel("range query number", fontsize=12)

        ax.set_ylim(bottom=0)

        ax.xaxis.set_major_locator(ticker.FixedLocator(ax.get_xticks()))
        ax.set_xticklabels([f"{int(tick)}" for tick in ax.get_xticks()], fontsize=12)

        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticklabels(
            [f"{int(i/(1000 ** 2))}" if i != 0 else "0" for i in ax.get_yticks()],
            fontsize=12,
        )

        fig.legend(
            loc="lower center",
            ncol=2,
            fontsize=12,
            bbox_to_anchor=(0.5, 0.1),
            frameon=False,
        )

        ax.annotate(
            f"avg vanilla: {self._vanilla[plotting_column].mean()/(1000 ** 2):.2f}",
            xy=(5, 200000000),
            fontsize=12,
        )
        ax.annotate(
            f"avg RQDC: {self._rqdc[plotting_column].mean()/(1000 ** 2):.2f}",
            xy=(90, 200000000),
            fontsize=12,
        )

        plt.show()


def plot_total_data_movement(
    _vanilla: List[PlottingStats],
    _rqdc: List[PlottingStats],
    vanilla: pd.DataFrame,
    rqdc: pd.DataFrame,
):

    tmp_vanilla_df = vanilla.copy(deep=True)
    tmp_rqdc_df = rqdc.copy(deep=True)
    tmp_vanilla_df["Row_Group"] = tmp_vanilla_df.index // (NUMEPOCHS - 1)
    tmp_rqdc_df["Row_Group"] = tmp_rqdc_df.index // (NUMEPOCHS - 1)

    tmp_vanilla_range_query_read = (
        tmp_vanilla_df.groupby("Row_Group")[str(RQColumn.TOTAL_ENTRIES_READ)]
        .sum()
        .reset_index()[str(RQColumn.TOTAL_ENTRIES_READ)]
        .to_list()
    )
    tmp_rqdc_range_query_read = (
        tmp_rqdc_df.groupby("Row_Group")[str(RQColumn.TOTAL_ENTRIES_READ)]
        .sum()
        .reset_index()[str(RQColumn.TOTAL_ENTRIES_READ)]
        .to_list()
    )

    if len(tmp_vanilla_range_query_read) != 0:
        tmp_vanilla_range_query_read.insert(0, 0)
        tmp_rqdc_range_query_read.insert(0, 0)

        vanilla_datamovement = [
            van.TotalWriteBytes
            + van.CompactionReadBytes
            + (tmp_vanilla_range_query_read[idx] * ENTRY_SIZE)
            for idx, van in enumerate(_vanilla)
        ]
        rqdc_datamovement = [
            rqdc.TotalWriteBytes
            + rqdc.CompactionReadBytes
            + (tmp_rqdc_range_query_read[idx] * ENTRY_SIZE)
            for idx, rqdc in enumerate(_rqdc)
        ]
    else:
        vanilla_datamovement = [
            van.TotalWriteBytes + van.CompactionReadBytes
            for idx, van in enumerate(_vanilla)
        ]
        rqdc_datamovement = [
            rqdc.TotalWriteBytes + rqdc.CompactionReadBytes
            for idx, rqdc in enumerate(_rqdc)
        ]

    vanilla_bar_kwargs = {
        "label": "vanilla universal",
        "color": "None",
        "hatch": "",
        "edgecolor": "black",
    }
    rqdc_bar_kwargs = {
        "label": "level renaming",
        "color": "None",
        "hatch": "--",
        "edgecolor": "black",
    }

    fig_size = (6, 4)
    bar_width = 0.35
    num_bars_per_group = 2
    epochs = NUMEPOCHS

    index = np.arange(epochs)
    fig, ax = plt.subplots(figsize=fig_size)

    ax.bar(
        index - (bar_width / num_bars_per_group),
        vanilla_datamovement,
        bar_width,
        **vanilla_bar_kwargs,
    )
    ax.bar(
        index + (bar_width / num_bars_per_group),
        rqdc_datamovement,
        bar_width,
        **rqdc_bar_kwargs,
    )

    ax.set_ylabel("total datamovement (GB)", fontsize=12)
    ax.set_xlabel("epoch", fontsize=12)

    ax.set_ylim(bottom=0)

    ax.set_xticks(range(epochs))
    ax.set_xticklabels([f"{epoch}" for epoch in range(1, epochs + 1)], fontsize=12)

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
    )
    plt.show()
