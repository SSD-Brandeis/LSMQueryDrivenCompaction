import os
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from brokenaxes import brokenaxes

from plotter.epochstats import EpochStats
# from plotter.plotepochstats import (
#     PlotRangeQueryStats,
#     PlotEpochStats,
#     # plot_total_data_movement,
#     PlotOperationLatencyStats,
# )
from plotter.plotstyles import line_styles_no_marker, point_styles

prop = font_manager.FontProperties(fname="./plotter/LinLibertine_Mah.ttf")
plt.rcParams["font.family"] = prop.get_name()
plt.rcParams["text.usetex"] = True
plt.rcParams["font.size"] = 18

# --------------------------------------------------------------------
#           Global constants
# --------------------------------------------------------------------
tag = "new_2_phase_exp"
OUTPUT_DIR = f"Figures/Fig10"
os.makedirs(OUTPUT_DIR, exist_ok=True)

inserts = 14_680_064
updates = 20_971_520
range_queries = 500
selectivity = 0.1

size_ratio = 6

entry_size = 128
num_page_per_file = 1024
entries_per_page = 32


# -------------------------------------------------------------------
#             Class and function definitions
# -------------------------------------------------------------------
from copy import deepcopy
from typing import List, Dict, Tuple

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker

from plotter.plotstyles import (
    bar_styles,
    line_styles_no_marker_with_abbr,
    line_styles_no_marker,
    point_styles,
    line_styles,
)
from plotter.dataclass import (
    AdditionalStats,
    PlottingStats,
    RQColumn,
)


class PlotEpochStats:
    bar_width = 0.55
    fig_size = (1.2, 2)
    epoch_fig_size = (3.2, 2.03)

    def __init__(
        self,
        approaches: Dict[str, List[PlottingStats]],
        approach_abr_order=List[str],
        epoch_to_plot: int = -1,
    ):
        self.approaches_: Dict[str, List[PlottingStats]] = deepcopy(approaches)
        self.approach_abr_order = deepcopy(approach_abr_order)
        self.epoch_to_plot = epoch_to_plot

    def plot_total_rq_bytes_written(self):
        convert_to_ = 1024**4
        ylabel = "total RQ write (TB)"
        desired_yticks = [0, 0.5]

        approach_data: Dict[str, List[PlottingStats]] = dict()
        for approach, data in self.approaches_.items():
            approach_data[approach] = [
                stat.RangeReduceWrittenBytes / convert_to_ for stat in data
            ]

        _, ax = plt.subplots(figsize=self.fig_size)
        bar_containers = []

        for approach, data in approach_data.items():
            bars = ax.bar(
                approach,
                data[self.epoch_to_plot],
                width=self.bar_width,
                **bar_styles[approach],
            )
            bar_containers.append(bars)

        ax.set_ylabel(ylabel)
        desired_tb_yticks = [byte for byte in desired_yticks]
        ax.set_yticks(desired_tb_yticks)
        ax.set_yticklabels([f"{byte}" for byte in desired_yticks])
        ax.set_ylim(bottom=0, top=desired_yticks[-1] + 0.4)
        ax.yaxis.set_label_coords(x=-0.26, y=0.42)

        ax.set_xticks(range(len(approach_data)))
        ax.set_xticklabels([per for per in self.approach_abr_order], rotation=90)

        for bars in bar_containers:
            for bar in bars:
                height = bar.get_height()
                if height < 0.5:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        height,
                        f"{height:.2f}",
                        ha="center",
                        va="bottom",
                        fontsize=18,
                        rotation=90,
                    )

        plt.savefig(f"{OUTPUT_DIR}/total-rq-writes.pdf", bbox_inches="tight", pad_inches=0.06)

    def plot_total_bytes_written(self):
        convert_to_ = 1024**3
        ylabel = "total write (GB)"
        desired_yticks = [0, 50, 100]

        approach_data: Dict[str, List[PlottingStats]] = dict()
        for approach, data in self.approaches_.items():
            approach_data[approach] = [
                (stat.CompactionWrittenBytes + stat.RangeReduceWrittenBytes)
                / convert_to_
                for stat in data
            ]

        _, ax = plt.subplots(figsize=self.fig_size)
        bar_containers = []

        for approach, data in approach_data.items():
            bars = ax.bar(
                approach,
                data[self.epoch_to_plot],
                width=self.bar_width,
                **bar_styles[approach],
            )
            bar_containers.append(bars)

        ax.set_ylabel(ylabel, labelpad=-6, loc="top")
        desired_tb_yticks = [byte for byte in desired_yticks]
        ax.set_yticks(desired_tb_yticks)
        ax.set_yticklabels([f"{byte}" for byte in desired_yticks])
        ax.set_ylim(bottom=0, top=(desired_yticks[-1] + 0.05))
        # ax.yaxis.set_label_coords(x=-0.44, y=0.45)

        ax.set_xticks(range(len(approach_data)))
        ax.set_xticklabels([per for per in self.approach_abr_order], rotation=90)

        for bars in bar_containers:
            for bar in bars:
                height = bar.get_height()

                if height < 0.5:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        height,
                        f"{height:.2f}",
                        ha="center",
                        va="bottom",
                        fontsize=18,
                        rotation=90,
                    )

        plt.savefig(f"{OUTPUT_DIR}/total-writes.pdf", bbox_inches="tight", pad_inches=0.06)

    def plot_total_bytes_written_normalized(self):
            convert_to_ = 1024**3
            # Updated label to reflect normalization
            ylabel = "norm. write"
            
            # 1. Calculate raw GB values first
            approach_gb = {}
            for approach, data in self.approaches_.items():
                # Get the data for the specific epoch
                stat = data[self.epoch_to_plot]
                total_bytes = stat.CompactionWrittenBytes + stat.RangeReduceWrittenBytes
                approach_gb[approach] = total_bytes / convert_to_

            # 2. Establish Baseline (RocksDB)
            # Handle case where RocksDB might not be in the dict to avoid KeyError
            rocksdb_val = approach_gb.get("RocksDB", 1.0) 
            if rocksdb_val == 0: rocksdb_val = 1.0 # Prevent division by zero

            # 3. Normalize all values
            normalized_data = {app: val / rocksdb_val for app, val in approach_gb.items()}

            fig, ax = plt.subplots(figsize=self.fig_size)
            x_positions = np.arange(len(self.approach_abr_order))
            
            for i, approach in enumerate(ACTIVE_APPROACHES):
                if approach not in normalized_data: continue
                
                val = normalized_data[approach]
                bar = ax.bar(
                    i,
                    val,
                    width=self.bar_width,
                    **bar_styles[approach],
                )
            ax.set_ylabel(ylabel)
            # Set y-ticks to show 0, 0.5, 1.0, and a bit above
            ax.set_yticks([0, 0.5, 1.0, 1.5])
            ax.set_yticklabels([f"{tick}" for tick in [0, 0.5, 1.0, 1.5]])
            ax.set_ylim(bottom=0) # Adjust top based on your max regression
            
            ax.set_xticks(x_positions)
            ax.set_xticklabels([self.approach_abr_order[i] for i in range(len(self.approach_abr_order))], rotation=90)

            plt.savefig(f"{OUTPUT_DIR}/total-writes-normalized.pdf", bbox_inches="tight", pad_inches=0.06)
            plt.close(fig)

    def plot_compaction_debt_over_epochs(self):
        convert_to_ = 1024**3
        ylabel = "compaction debt (GB)"
        desired_yticks = [0, 5, 10, 15]
        desired_xticks = [0, 5]
        xlabel = "epoch"

        fig, ax = plt.subplots(figsize=self.epoch_fig_size)

        for approach in self.approaches_.keys():
            data = self.approaches_[approach]

            compaction_debt = [stat.CompactionDebt / convert_to_ for stat in data]

            ax.plot(
                range(len(compaction_debt) -1),
                compaction_debt[:-1],
                **line_styles[approach],
            )
            # print(approach)
            # print(compaction_debt)

        ax.set_ylabel(ylabel) #, labelpad=-1, loc="top")
        ax.set_yticks(desired_yticks)
        ax.set_yticklabels([f"{byte}" for byte in desired_yticks])
        ax.set_ylim(bottom=0, top=desired_yticks[-1]+1)
        ax.yaxis.set_label_coords(-0.14, 0.315)

        ax.set_xlabel(xlabel)
        ax.set_xticks(desired_xticks)
        ax.set_xticklabels([str(x + 1) for x in desired_xticks])

        plt.savefig(
            f"{OUTPUT_DIR}/compaction-debt-over-epochs.pdf",
            bbox_inches="tight",
            pad_inches=0.06,
        )
        plt.close(fig)

    def plot_compaction_debt_normalized(self):
            convert_to_ = 1024**3
            ylabel = "norm. compaction debt"
            
            # 1. Calculate raw GB values
            approach_gb = {}
            for approach, data in self.approaches_.items():
                stat = data[self.epoch_to_plot]
                approach_gb[approach] = stat.CompactionDebt / convert_to_

            # 2. Establish Baseline (RocksDB)
            rocksdb_val = approach_gb.get("RocksDB", 1.0) 
            if rocksdb_val == 0: rocksdb_val = 1.0 # Prevent division by zero

            # 3. Normalize values relative to RocksDB
            normalized_data = {app: val / rocksdb_val for app, val in approach_gb.items()}

            fig, ax = plt.subplots(figsize=self.fig_size)
            x_positions = np.arange(len(self.approach_abr_order))
            
            # Use ACTIVE_APPROACHES for consistent ordering
            for i, approach in enumerate(ACTIVE_APPROACHES):
                if approach not in normalized_data: continue
                
                val = normalized_data[approach]
                bar = ax.bar(
                    i,
                    val,
                    width=self.bar_width,
                    **bar_styles[approach],
                )

            ax.set_ylabel(ylabel)
            # Ticks for 0, 0.5, 1.0, and 1.5 to show regressions if they exist
            ax.set_yticks([0, 0.5, 1.0, 1.5])
            ax.set_yticklabels([f"{tick}" for tick in [0, 0.5, 1, 1.5]])
            ax.set_ylim(bottom=0, top=1.6) 

            ax.set_xticks(x_positions)
            ax.set_xticklabels(self.approach_abr_order, rotation=90)
            
            # Position y-label to avoid overlap with ticks
            ax.yaxis.set_label_coords(x=-0.48, y=0.34)

            plt.savefig(f"{OUTPUT_DIR}/compaction-debt-normalized.pdf", bbox_inches="tight", pad_inches=0.06)
            plt.close(fig)

    def plot_compaction_debt(self):
        convert_to_ = 1024**3
        ylabel = "compaction debt (GB)"
        desired_yticks = [0, 5, 10, 15]
        adjust_ytop_by = 0.001

        approach_data: Dict[str, List[PlottingStats]] = dict()
        for approach, data in self.approaches_.items():
            approach_data[approach] = [
                stat.CompactionDebt / convert_to_ for stat in data
            ]

        _, ax = plt.subplots(figsize=self.fig_size)
        bar_containers = []

        for approach, data in approach_data.items():
            bars = ax.bar(
                approach,
                data[self.epoch_to_plot],
                width=self.bar_width,
                **bar_styles[approach],
            )
            bar_containers.append(bars)

            # print(approach)
            # print(data[self.epoch_to_plot])

        ax.set_ylabel(ylabel)
        ax.set_yticks(desired_yticks)
        ax.set_yticklabels([f"{byte}" for byte in desired_yticks])
        ax.set_ylim(bottom=0, top=desired_yticks[-1] + adjust_ytop_by)
        ax.yaxis.set_label_coords(-0.34, 0.34)

        ax.set_xticks(range(len(approach_data)))
        ax.set_xticklabels([per for per in self.approach_abr_order], rotation=90)

        for bars in bar_containers:
            for bar in bars:
                height = bar.get_height()

                if height < 0.5:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        height,
                        f"{height:.1f}",
                        ha="center",
                        va="bottom",
                        fontsize=18,
                        rotation=90,
                    )

        plt.savefig(f"{OUTPUT_DIR}/compaction-debt.pdf", bbox_inches="tight", pad_inches=0.06)

        handles, labels = ax.get_legend_handles_labels()
        legend_fig = plt.figure(figsize=(8, 2))
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

        legend_fig.savefig(
            f"{OUTPUT_DIR}/bounded-metric-legend.pdf", bbox_inches="tight", pad_inches=0.015
        )


    def plot_space_amp_over_epochs(self):
        desired_yticks = [0, 0.5, 1, 1.5]
        adjust_ytop_by = 0
        xlabel = "epoch"
        desired_xticks = [0, 5]

        fig, ax = plt.subplots(figsize=self.epoch_fig_size)

        for approach in self.approaches_.keys():
            data = self.approaches_[approach]

            space_amp = [stat.DBSize / (inserts * entry_size) for stat in data]

            ax.plot(
                range(len(space_amp) - 1),
                space_amp[:-1],
                **line_styles[approach],
            )

            # print(approach)
            # print(space_amp)

        ax.set_ylabel("space amplification", labelpad=-0.8, loc="top")
        ax.set_yticks(desired_yticks)
        ax.set_yticklabels([f"{tick}" for tick in desired_yticks])
        ax.set_ylim(bottom=0, top=desired_yticks[-1] + adjust_ytop_by)
        # ax.yaxis.set_label_coords(-0.46, 0.34)

        ax.set_xlabel(xlabel)
        ax.set_xticks(desired_xticks)
        ax.set_xticklabels([str(x + 1) for x in desired_xticks])
        plt.savefig(
            f"{OUTPUT_DIR}/space-amp-over-epochs.pdf",
            bbox_inches="tight",
            pad_inches=0.06,
        )
        plt.close(fig)

    def plot_space_amplification(self):
        desired_yticks = [0, 0.5, 1, 1.5, 2]
        adjust_ytop_by = 0

        approach_data: Dict[str, List[PlottingStats]] = dict()
        for approach, data in self.approaches_.items():
            approach_data[approach] = [
                data[self.epoch_to_plot].DBSize / (inserts * (entry_size + 10))
            ]

        _, ax = plt.subplots(figsize=self.fig_size)

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
        ax.set_yticks(desired_yticks)
        ax.set_yticklabels([f"{tick}" for tick in desired_yticks])
        ax.set_ylim(bottom=0, top=desired_yticks[-1] + adjust_ytop_by)
        ax.yaxis.set_label_coords(-0.46, 0.34)

        ax.set_xticks(range(len(approach_data)))
        ax.set_xticklabels([per for per in self.approach_abr_order], rotation=90)

        for bars in bar_containers:
            for bar in bars:
                height = bar.get_height()

                if height < 1:
                    ax.text(
                        bar.get_x() + bar.get_width() / 2,
                        height,
                        f"{height:.2f}",
                        ha="center",
                        va="bottom",
                        fontsize=18,
                        rotation=90,
                    )

        plt.savefig(
            f"{OUTPUT_DIR}/space-amplification.pdf", bbox_inches="tight", pad_inches=0.06
        )

    def plot_insert_throughput_for_phases(self, phases: List[Tuple[int]] = [(1, -1)]):
        """phases: List[Tuple(phase, num_inserts_in_that_phase)]"""
        convert_to_ = 10**9
        ylabel = "throughput (s)"
        desired_yticks = [0, 0.5, 1]

        phase_idxs = {tup[0]: tup[1] for tup in phases}

        throughput: Dict[str, List[int]] = dict()
        for approach, data in self.approaches_.items():
            throughput[approach] = list()
            for phase, time in enumerate(data, 1):
                # print(approach, "---", time.insertsExecutionTime)
                if phase in phase_idxs.keys():
                    throughput[approach].append(
                        phase_idxs[phase] / time.insertsExecutionTime / convert_to_
                    )

        fig, ax = plt.subplots(figsize=self.fig_size)

        normalized_througput: Dict[str, List[int]] = dict()
        for approach, data in throughput.items():
            normalized_througput[approach] = list()
            for idx in range(len(data)):
                normalized_througput[approach].append(
                    data[idx] / throughput["RocksDB"][idx]
                )

        # print(throughput)
        # print(normalized_througput)

        for approach, data in normalized_througput.items():
            ax.plot(
                range(len(data)),
                data,
                alpha=0.8,
                **line_styles_no_marker_with_abbr[approach],
            )

        ax.set_ylabel(ylabel)
        # ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        # ax.set_yticks(desired_yticks)
        # ax.set_yticklabels([str(sec) for sec in desired_yticks])
        ax.set_ylim(bottom=0)

        # ax.set_xlabel("range query number")
        # ax.xaxis.set_major_locator(ticker.FixedLocator(ax.get_xticks()))
        # ax.set_xticks(desired_xticks)
        # ax.set_xticklabels([str(x) for x in desired_xticks])

        plt.savefig(
            f"{OUTPUT_DIR}/inserts-throughput.pdf", bbox_inches="tight", pad_inches=0.04
        )
        plt.close(fig)

    def plot_workload_exec_time(self):
        convert_to_ = 1000**3
        to_hours = 1 / (60 * 60)
        ylabel = "execution time (hr)"
        desired_yticks = [0, 2, 4]
        adjust_ytop_by = 0.3

        approach_data: Dict[str, List[PlottingStats]] = dict()
        for approach, data in self.approaches_.items():
            approach_data[approach] = [
                (stat.WorkloadExecutionTime / convert_to_) * to_hours
                for stat in [data[self.epoch_to_plot]]
            ]

        _, ax = plt.subplots(figsize=self.fig_size)
        for approach, data in approach_data.items():
            ax.bar(
                approach,
                data,
                width=self.bar_width,
                **bar_styles[approach],
            )

        ax.set_ylabel(ylabel)
        ax.yaxis.set_label_coords(-0.3, 0.34)
        ax.set_yticks(desired_yticks)
        ax.set_yticklabels([f"{tick}" for tick in desired_yticks])
        ax.set_ylim(bottom=0, top=desired_yticks[-1] + adjust_ytop_by)

        ax.set_xticks([])
        ax.set_xticks(range(len(approach_data)))
        ax.set_xticklabels([per for per in self.approach_abr_order], rotation=90)

        plt.savefig(
            f"{OUTPUT_DIR}/wkl-execution-time.pdf", bbox_inches="tight", pad_inches=0.06
        )


class PlotRangeQueryStats:
    fig_size_for_bar = (2, 3)
    width_for_bar = 0.55
    # fig_size = (1.7, 0.75)
    fig_size = (3.2, 2)

    def __init__(
        self, approaches: Dict[str, pd.DataFrame], approaches_order: List[str]
    ):
        self.approaches_: Dict[str, pd.DataFrame] = deepcopy(approaches)
        self.approaches_order = deepcopy(approaches_order)

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

    def plot_did_rq_run(self, approach_abbr: List[str]):
        convert_to = 1
        ylabel = "optimization trigger count"

        approach_data = dict()
        for appraoch, data in self.approaches_.items():
            approach_data[appraoch] = data[str(RQColumn.DID_RUN_RR)].sum() / convert_to

        _, ax = plt.subplots(figsize=self.fig_size_for_bar)

        for approach, data in approach_data.items():
            ax.bar(approach, data, width=self.width_for_bar, **bar_styles[approach])

        ax.set_ylabel(ylabel)
        ax.yaxis.set_label_coords(-0.42, 0.4)

        ax.set_xticks(range(len(approach_data)))
        ax.set_xticklabels([per for per in approach_abbr], rotation=90)

        plt.savefig(
            f"{OUTPUT_DIR}/did-optimization-trigger.pdf", bbox_inches="tight", pad_inches=0.06
        )

    def bytes_read_for_each_range_query_rolling_broken_axes(self, window=200):
            convert_to_ = 1024**2
            ylabel = "bytes read (MB)"
            # Note: desired_mb_ticks is no longer used directly as we manually set ticks per axis
            desired_xticks = [1, range_queries/2, range_queries]

            fig = plt.figure(figsize=self.fig_size)
            
            # Initialize brokenaxes
            bax = brokenaxes(
                ylims=((0, 2), (100, 150)), 
                hspace=0.15, 
                height_ratios=[6, 1],
                despine=False,
                fig=fig
            )

            for approach in self.approaches_order:
                data = (
                    self.approaches_[approach][str(RQColumn.TOTAL_ENTRIES_READ)].astype(float)
                    * entry_size / convert_to_
                )

                s = pd.Series(data)
                mean = s.rolling(window, min_periods=1).mean()
                q05 = s.rolling(window, min_periods=1).quantile(0.05)
                q95 = s.rolling(window, min_periods=1).quantile(0.95)

                style = line_styles_no_marker[approach]
                style["linewidth"] = 1

                # Plot on bax directly
                bax.plot(mean.values, **style)

                # fill_between works on bax
                bax.fill_between(
                    range(len(mean)),
                    q05.values, # Use .values to avoid index alignment issues
                    q95.values,
                    color=line_styles_no_marker[approach]["color"],
                    alpha=0.25,
                    linewidth=0,
                )

            # FIX: Placing text in brokenaxes
            # Using the first axes (bax.axs[0]) to position text relative to the plot
            bax.axs[0].text(
                0.15, 0.95, # Top-left coordinates
                f"rolling window: {window} pts\nline: mean; band: p5–p95",
                transform=bax.axs[0].transAxes, # Use local axis coordinates
                fontsize=17,
                verticalalignment='top'
            )

            # Set specific Y-ticks for each segment
            bax.axs[0].set_yticks([90, 120, 150]) 
            bax.axs[1].set_yticks([0])            

            # Global Labels
            bax.set_ylabel(ylabel, labelpad=40) 
            bax.set_xlabel("range query number")
            
            # Set X-ticks
            bax.set_xticks(desired_xticks)

            plt.savefig(
                f"{OUTPUT_DIR}/range-query-bytes-read-rolling-borken-axes.pdf",
                bbox_inches="tight",
                pad_inches=0.04,
            )
            plt.close(fig)

    def bytes_read_for_each_range_query_rolling(self, window=200):
        convert_to_ = 1024**2
        ylabel = "bytes read (MB)"
        desired_mb_ticks = [0, 100, 200, 300] # [1e0, 1e2, 1e4]
        adjust_ytop_by = 0
        desired_xticks = [1, range_queries//2, range_queries]

        fig, ax = plt.subplots(figsize=self.fig_size)

        for approach in self.approaches_order:
            data = (
                self.approaches_[approach][str(RQColumn.TOTAL_ENTRIES_READ)].astype(
                    float
                )
                * entry_size
                / convert_to_
            )

            s = pd.Series(data)

            # print(approach)
            # print(s.mean())

            mean = s.rolling(window, min_periods=1).mean()
            q05 = s.rolling(window, min_periods=1).quantile(0.05)
            q95 = s.rolling(window, min_periods=1).quantile(0.95)

            style = line_styles_no_marker[approach]
            style["linewidth"] = 1

            ax.plot(
                mean.values,
                **style,
            )

            ax.fill_between(
                range(len(mean)),
                q05,
                q95,
                color=line_styles_no_marker[approach]["color"],
                alpha=0.25,
                linewidth=0,
                edgecolor="none",
            )

        ax.text(
            0.02,
            0.56,
            f"rolling window: {window} pts\nline: mean\nband: p5–p95",
            transform=ax.transAxes,
            fontsize=17,
        )

        ax.set_ylabel(ylabel, labelpad=-0.5, loc='top')
        # ax.set_yscale("log")
        ax.set_yticks(desired_mb_ticks)
        # ax.set_yticklabels([str(mb) for mb in desired_mb_ticks])
        # ax.yaxis.set_label_coords(-0.14, 0.45)
        ax.set_ylim(bottom=desired_mb_ticks[0], top=desired_mb_ticks[-1])

        ax.set_xlabel("range query number")
        ax.set_xticks(desired_xticks)
        ax.set_xticklabels([str(tick) for tick in desired_xticks])
        # ax.set_xlim(left=-200)

        plt.savefig(
            f"{OUTPUT_DIR}/range-query-bytes-read-rolling.pdf",
            bbox_inches="tight",
            pad_inches=0.04,
        )
        plt.close(fig)

    def bytes_read_for_each_range_query_line_normalized(self, window=500):
            convert_to_ = 1024**2
            ylabel = "norm. bytes read"
            desired_xticks = [1, range_queries/2, range_queries]

            # 1. Get RocksDB baseline data (element-wise)
            # Using .replace(0, np.nan) prevents 'inf' values if RocksDB reads 0 bytes
            baseline_data = (
                self.approaches_['RocksDB'][str(RQColumn.TOTAL_ENTRIES_READ)].astype(float)
                * entry_size / convert_to_
            ).replace(0, np.nan)

            fig, ax = plt.subplots(figsize=self.fig_size)
            
            for approach in self.approaches_order:
                # 2. Calculate raw data
                raw_data = (
                    self.approaches_[approach][str(RQColumn.TOTAL_ENTRIES_READ)].astype(float)
                    * entry_size / convert_to_
                )
                
                # 3. Normalize Point-by-Point
                normalized_s = raw_data / baseline_data
                
                # 4. Apply Smoothing (Rolling mean)
                # Use window=1 if you want the absolute raw point-by-point line
                s = pd.Series(normalized_s)
                plot_data = s.rolling(window, min_periods=1).mean()

                # 5. Plot as Line
                style = line_styles_no_marker[approach].copy()
                style['linewidth'] = 1.2
                
                ax.plot(
                    range(len(plot_data)),
                    plot_data.values,
                    **style,
                )

            # 6. Add a horizontal line at 1.0 to show the RocksDB baseline
            ax.axhline(1.0, color='black', linestyle='--', linewidth=1, alpha=0.7)

            # Styling
            ax.set_ylim(0, 1.5) # Focus on 0x to 1.5x range
            ax.set_yticks([0, 0.5, 1, 1.5])
            
            ax.set_ylabel(ylabel, labelpad=-0.5, loc='top') 
            ax.set_xlabel("range query number")
            ax.set_xticks(desired_xticks)

            plt.savefig(
                f"{OUTPUT_DIR}/range-query-bytes-read-line-normalized.pdf", 
                bbox_inches="tight"
            )
            plt.close(fig)

    def bytes_read_for_each_range_query_scatter_normalized(self):
            convert_to_ = 1024**2
            ylabel = "norm. bytes read"
            desired_xticks = [1, range_queries/2, range_queries]

            # 1. Get RocksDB baseline data (element-wise)
            # We assume the index and order of queries are identical across approaches
            baseline_data = (
                self.approaches_['RocksDB'][str(RQColumn.TOTAL_ENTRIES_READ)].astype(float)
                * entry_size / convert_to_
            )

            fig, bax = plt.subplots(figsize=self.fig_size)
            
            # ylims: Bottom segment focuses on improvements (0 to 1.2x)
            # Top segment catches significant regressions (2.0x to 5.0x)
            # bax = brokenaxes(
            #     ylims=((0, 1.2), (2.0, 5.0)), 
            #     hspace=0.15, 
            #     height_ratios=[1, 4], # Make the bottom part (0-1.2) larger
            #     despine=False,
            #     fig=fig
            # )

            for approach in self.approaches_order:
                # 2. Calculate raw data and divide by baseline
                raw_data = (
                    self.approaches_[approach][str(RQColumn.TOTAL_ENTRIES_READ)].astype(float)
                    * entry_size / convert_to_
                )
                
                # Avoid division by zero if RocksDB has 0-byte reads
                normalized_s = raw_data / baseline_data.replace(0, np.nan)
                
                bax.scatter(
                    range(len(normalized_s)),
                    normalized_s.values,
                    s=10,
                    **point_styles[approach],
                )

            # 3. Add a horizontal line at 1.0 to show the RocksDB baseline
            # for ax in bax.axs:
            bax.axhline(1.0, color='black', linestyle='--', linewidth=1, alpha=0.7)

            # Set specific ticks
            bax.set_yticks([0, 0.5, 1, 1.5])
            bax.set_yticklabels(["0", "0.5", "1", "1.5"])

            bax.set_ylabel(ylabel, labelpad=-0.2, loc="top")
            bax.set_xlabel("range query number")
            bax.set_xticks(desired_xticks)

            plt.savefig(f"{OUTPUT_DIR}/range-query-bytes-read-scatter-normalized.pdf", bbox_inches="tight")
            plt.close(fig)

    def bytes_read_for_each_range_query_scatter(self):
        convert_to_ = 1024**3
        ylabel = "bytes read (GB)"
        desired_xticks = [1, range_queries/2, range_queries]

        fig, bax = plt.subplots(figsize=self.fig_size)
        
        # # FIX 1: Add height_ratios to make the top part (data) larger than the bottom (break)
        # # FIX 2: Use despine=False if you want the right/top borders to stay
        # bax = brokenaxes(
        #     ylims=((0, 2), (90, 150)), 
        #     hspace=0.15, 
        #     height_ratios=[5, 1], # Top is 3x taller than bottom
        #     despine=False,
        #     fig=fig
        # )

        for approach in self.approaches_order:
            data = (
                self.approaches_[approach][str(RQColumn.TOTAL_ENTRIES_READ)].astype(float)
                * entry_size / convert_to_
            )
            
            bax.scatter(
                range(len(data)),
                data.values,
                s=10,
                **point_styles[approach],
            )

        # # FIX 3: Set specific y-ticks for each segment to avoid auto-labeling overlap
        # bax.axs[0].set_yticks([90, 150]) # Top segment ticks
        # bax.axs[1].set_yticks([0])            # Bottom segment ticks

        bax.set_ylabel(ylabel) #, labelpad=40) 
        bax.set_xlabel("range query number")
        bax.set_ylim(bottom=0)
        bax.set_yticks([0, 0.1, 0.2])
        bax.set_yticklabels(["0", "0.1", "o.2"])

        # FIX 4: Ensure x-axis doesn't overlap
        bax.set_xticks(desired_xticks)

        plt.savefig(f"{OUTPUT_DIR}/range-query-bytes-read-scatter.pdf", bbox_inches="tight")
        plt.close(fig)

    # def bytes_read_for_each_range_query_scatter(self):
    #     convert_to_ = 1024**2
    #     ylabel = "bytes read (MB)"
    #     desired_mb_ticks = [0, 75, 150] # [1e0, 1e2, 1e4, 1e6]
    #     adjust_ytop_by = 0
    #     desired_xticks = [1, range_queries/2, range_queries]

    #     fig, ax = plt.subplots(figsize=self.fig_size)

    #     for approach in self.approaches_order:
    #         data = (
    #             self.approaches_[approach][str(RQColumn.TOTAL_ENTRIES_READ)].astype(
    #                 float
    #             )
    #             * entry_size
    #             / convert_to_
    #         )

    #         s = pd.Series(data)
    #         # print(approach)
    #         # print(s[0])
    #         # print(s[1:1000].mean())
    #         # print(s[1000: ].mean())

    #         style = line_styles_no_marker[approach]
    #         style["linewidth"] = 1

    #         ax.scatter(
    #             range(len(s)),
    #             s.values,
    #             s=10,
    #             **point_styles[approach],
    #         )

    #     ax.set_ylabel(ylabel)
    #     # ax.set_yscale("log")
    #     ax.set_yticks(desired_mb_ticks)
    #     # ax.set_yticklabels([str(mb) for mb in desired_mb_ticks])
    #     ax.yaxis.set_label_coords(-0.14, 0.45)
    #     ax.set_ylim(bottom=desired_mb_ticks[0], top=desired_mb_ticks[-1])

    #     ax.set_xlabel("range query number")
    #     ax.set_xticks(desired_xticks)
    #     ax.set_xticklabels([str(tick) for tick in desired_xticks])
    #     # ax.set_xlim(left=-200)

    #     plt.savefig(
    #         f"{OUTPUT_DIR}/range-query-bytes-read-scatter.pdf",
    #         bbox_inches="tight",
    #         pad_inches=0.04,
    #     )
    #     plt.close(fig)

    def bytes_read_cdf(self):
        convert_to_ = 1024**3
        xlabel = ""  # "read GBs"
        desired_yticks = [0, 0.5, 1]
        desired_xticks = [0, 0.2]

        fig, ax = plt.subplots(figsize=self.fig_size)

        for approach in self.approaches_order:
            data = (
                self.approaches_[approach][str(RQColumn.TOTAL_ENTRIES_READ)].astype(
                    float
                )
                * entry_size
            ) / convert_to_

            sorted_data = np.sort(data)
            y = np.arange(1, len(sorted_data) + 1) / len(sorted_data)

            ax.plot(
                sorted_data,
                y,
                **line_styles_no_marker_with_abbr[approach],
            )

        ax.set_ylabel("")  # "cdf"
        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticks(desired_yticks)
        ax.set_yticklabels(["" for tick in desired_yticks])  # str(tick)
        ax.set_ylim(0, 1)

        ax.set_xlabel(xlabel)  # , fontsize=18.7
        ax.xaxis.set_major_locator(ticker.FixedLocator(ax.get_xticks()))
        ax.set_xticks(desired_xticks)
        ax.set_xticklabels(["" for tick in desired_xticks])  # str(tick)
        ax.set_xlim(left=0, right=desired_xticks[-1] + 0.03)

        plt.savefig(
            f"{OUTPUT_DIR}/range-query-bytes-read-cdf.pdf",
            bbox_inches="tight",
            pad_inches=0.04,
        )
        plt.close(fig)

    def bytes_read_for_each_range_query(self, range_query_pattern=""):
        convert_to_ = 1024**2
        ylabel = "bytes read (MB)"
        desired_mb_ticks = [0, 50, 100, 150]
        # desired_xticks = [0, 2250, 4500, 6750, 9000]

        approach_data = dict()
        for approach, data in self.approaches_.items():
            approach_data[approach] = (
                data[[str(RQColumn.TOTAL_ENTRIES_READ)]]
                .apply(lambda x: (x * entry_size) / convert_to_)[
                    str(RQColumn.TOTAL_ENTRIES_READ)
                ]
                .to_list()
            )

        _, ax = plt.subplots(figsize=self.fig_size)

        for approach in self.approaches_order:
            data = approach_data[approach]
            ax.plot(
                range(len(data)),
                data,
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

        ax.set_ylabel(ylabel)
        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticks(desired_mb_ticks)
        ax.set_yticklabels([str(mb) for mb in desired_mb_ticks])

        ax.set_ylim(0, desired_mb_ticks[-1] + 25)
        # ax.yaxis.set_label_coords(-0.1, 0.42)

        ax.set_xlabel("range query number")
        # ax.set_xticks(desired_xticks)
        # ax.set_xticklabels([str(x) for x in desired_xticks])

        plt.savefig(
            f"{OUTPUT_DIR}/range-query-bytes-read.pdf", bbox_inches="tight", pad_inches=0.06
        )

    def normalized_latency_line(self, window=500):
            ylabel = "norm. latency"
            desired_xticks = [1, range_queries/2, range_queries]

            # 1. Get RocksDB baseline data (Point-to-Point)
            # Using .replace(0, np.nan) prevents 'inf' values from division by zero
            rocksdb_raw = self.approaches_['RocksDB'][str(RQColumn.RQ_TOTAL_TIME)].astype(float).replace(0, np.nan)

            fig, ax = plt.subplots(figsize=self.fig_size)
            
            for approach in self.approaches_order:
                raw_latency = self.approaches_[approach][str(RQColumn.RQ_TOTAL_TIME)].astype(float)
                
                # 2. Normalize: Point-to-Point normalization
                # Each query in 'approach' is divided by the same query number in RocksDB
                normalized_data = raw_latency / rocksdb_raw 

                # 3. Apply Rolling Window 
                # This smooths the line so you can see the trend relative to the baseline
                s = pd.Series(normalized_data)
                rolling_mean = s.rolling(window, min_periods=1).mean()
                
                # 4. Plotting
                style = line_styles_no_marker[approach].copy()
                style['linewidth'] = 1.2 
                
                ax.plot(
                    range(len(rolling_mean)),
                    rolling_mean.values,
                    **style,
                )

            # 5. Baseline reference (RocksDB normalized by itself is always 1.0)
            ax.axhline(1.0, color='black', linestyle='--', linewidth=1, alpha=0.7)

            # Styling
            ax.set_ylim(0, 2.5) # Focus on 0x to 2.5x performance range
            ax.set_ylabel(ylabel)
            ax.set_xlabel("range query number")
            ax.set_xticks(desired_xticks)

            plt.savefig(
                f"{OUTPUT_DIR}/range-query-latency-normalized-line-ptp.pdf",
                bbox_inches="tight",
                pad_inches=0.04,
            )
            plt.close(fig)

    def normalized_latency_scatter(self):
            ylabel = "norm. latency"
            desired_xticks = [1, range_queries/2, range_queries]

            # 1. Get RocksDB baseline data (element-wise)
            # Ensure RocksDB exists in your approaches
            baseline_latency = self.approaches_['RocksDB'][str(RQColumn.RQ_TOTAL_TIME)].astype(float)

            fig, bax = plt.subplots(figsize=self.fig_size)
            
            # ylims: Bottom segment shows the main comparison (0 to 1.5x)
            # Top segment catches outliers (e.g., 5x to 10x slower)
            # bax = brokenaxes(
            #     ylims=((0, 1.5), (5, 10)), 
            #     hspace=0.15, 
            #     height_ratios=[1, 4], # Bottom part is larger to see the 0-1 range clearly
            #     despine=False,
            #     fig=fig
            # )

            for approach in self.approaches_order:
                # 2. Normalize: Current RQ / RocksDB RQ
                raw_latency = self.approaches_[approach][str(RQColumn.RQ_TOTAL_TIME)].astype(float)
                normalized_data = raw_latency / baseline_latency

                bax.scatter(
                    range(len(normalized_data)),
                    normalized_data.values,
                    s=10,
                    **point_styles[approach],
                )

            # 3. Add a horizontal line at 1.0 to clearly show the RocksDB baseline
            # for ax in bax.axs:
            bax.axhline(1.0, color='black', linestyle='--', linewidth=1, alpha=0.7)

            # Set specific Y-ticks
            # bax.set_yticks([5, 10])       # Top segment (Outliers)
            bax.set_yticks([0, 1, 2, 3]) # Bottom segment (The meat of the data)

            bax.set_ylabel(ylabel, labelpad=-0.5)
            bax.set_xlabel("range query number")
            bax.set_xticks(desired_xticks)

            plt.savefig(
                f"{OUTPUT_DIR}/range-query-latency-normalized.pdf",
                bbox_inches="tight",
                pad_inches=0.04,
            )
            plt.close(fig)

    def latency_for_each_range_query_rolling(self, window=200):
            convert_to_ = 10**9
            ylabel = "latency (s)"
            desired_yticks = [0, 1, 2, 3]
            desired_xticks = [1, range_queries/2, range_queries]

            fig, bax = plt.subplots(figsize=self.fig_size)
            
            for approach in self.approaches_order:
                data = (
                    self.approaches_[approach][str(RQColumn.RQ_TOTAL_TIME)].astype(float)
                    / convert_to_
                )

                s = pd.Series(data)

                # print(approach)
                # print(s.mean())

                mean = s.rolling(window, min_periods=1).mean()
                q05 = s.rolling(window, min_periods=1).quantile(0.05)
                q95 = s.rolling(window, min_periods=1).quantile(0.95)

                style = line_styles_no_marker[approach]
                style["linewidth"] = 1

                # Plot on brokenaxes
                bax.plot(mean.values, **style)

                bax.fill_between(
                    range(len(mean)),
                    q05.values,
                    q95.values,
                    color=line_styles_no_marker[approach]["color"],
                    alpha=0.25,
                    linewidth=0,
                )

            # Positioning text in the top segment (axs[0])
            # Moved slightly higher (0.85) to avoid overlapping the data lines
            bax.text(
                0.02, 0.97, 
                f"rolling window: {window} pts\nline: mean\nband: p5–p95",
                transform=bax.transAxes,
                fontsize=16,
                verticalalignment='top'
            )

            # Set specific Y-ticks to ensure clarity
            bax.set_yticks(desired_yticks)

            # Global Labels
            bax.set_ylabel(ylabel, labelpad=-0.5) 
            bax.set_xlabel("range query number")
            
            # Set X-ticks
            bax.set_xticks(desired_xticks)

            plt.savefig(
                f"{OUTPUT_DIR}/range-query-latency-rolling.pdf",
                bbox_inches="tight",
                pad_inches=0.04,
            )
            plt.close(fig)

    def latency_for_each_range_query_rolling_broken_axes(self, window=200):
            convert_to_ = 10**9
            ylabel = "latency (s)"
            desired_xticks = [1, range_queries/2, range_queries]

            fig = plt.figure(figsize=self.fig_size)
            
            # Initialize brokenaxes
            # Adjusted ylims: bottom sliver for 0, top segment for actual latency spread
            bax = brokenaxes(
                ylims=((0, 0.05), (0.65, 2.0)), 
                hspace=0.15, 
                height_ratios=[5, 1],
                despine=False,
                fig=fig
            )

            for approach in self.approaches_order:
                data = (
                    self.approaches_[approach][str(RQColumn.RQ_TOTAL_TIME)].astype(float)
                    / convert_to_
                )

                s = pd.Series(data)
                mean = s.rolling(window, min_periods=1).mean()
                q05 = s.rolling(window, min_periods=1).quantile(0.05)
                q95 = s.rolling(window, min_periods=1).quantile(0.95)

                style = line_styles_no_marker[approach]
                style["linewidth"] = 1

                # Plot on brokenaxes
                bax.plot(mean.values, **style)

                bax.fill_between(
                    range(len(mean)),
                    q05.values,
                    q95.values,
                    color=line_styles_no_marker[approach]["color"],
                    alpha=0.25,
                    linewidth=0,
                )

            # Positioning text in the top segment (axs[0])
            # Moved slightly higher (0.85) to avoid overlapping the data lines
            bax.axs[0].text(
                0.12, 0.97, 
                f"rolling window: {window} pts\nline: mean; band: p5–p95",
                transform=bax.axs[0].transAxes,
                fontsize=17,
                verticalalignment='top'
            )

            # Set specific Y-ticks to ensure clarity
            bax.axs[0].set_yticks([0.75, 1.25, 2.0]) 
            bax.axs[1].set_yticks([0])            

            # Global Labels
            bax.set_ylabel(ylabel, labelpad=14) 
            bax.set_xlabel("range query number")
            
            # Set X-ticks
            bax.set_xticks(desired_xticks)

            plt.savefig(
                f"{OUTPUT_DIR}/range-query-latency-rolling.pdf",
                bbox_inches="tight",
                pad_inches=0.04,
            )
            plt.close(fig)

    def latency_for_each_range_query_scatter(self):
            convert_to_ = 10**9
            ylabel = "latency (s)"
            # Note: We'll split the log scale into two relevant windows
            desired_xticks = [1, range_queries/2, range_queries]

            fig, bax = plt.subplots(figsize=self.fig_size)
            
            # # Initialize brokenaxes with log-friendly ranges
            # # Segment 1: 1e0 to 1e2 | Segment 2: 1e4 to 1e8
            # bax = brokenaxes(
            #     ylims=((0, 0.05), (0.5, 2.0)), 
            #     hspace=0.15, 
            #     height_ratios=[4, 1],
            #     despine=False,
            #     fig=fig
            # )

            for approach in self.approaches_order:
                data = (
                    self.approaches_[approach][str(RQColumn.RQ_TOTAL_TIME)].astype(float)
                    / convert_to_
                )
                s = pd.Series(data)

                bax.scatter(
                    range(len(s)),
                    s.values,
                    s=10,
                    **point_styles[approach],
                )

            # # Set manual log ticks to maintain the look of your previous plots
            # bax.axs[0].set_yticks([0.75, 1.25, 2.0]) 
            # bax.axs[1].set_yticks([0])
            bax.set_yticks([0, 1, 2, 3])

            bax.set_ylabel(ylabel)
            bax.set_xlabel("range query number")
            
            bax.set_xticks(desired_xticks)

            plt.savefig(
                f"{OUTPUT_DIR}/range-query-latency-scatter.pdf",
                bbox_inches="tight",
                pad_inches=0.04,
            )
            plt.close(fig)

    def latency_cdf(self):
        convert_to_ = 10**9
        desired_yticks = [0, 0.5, 1]
        desired_xticks = [0, 2]

        fig, ax = plt.subplots(figsize=self.fig_size)

        for approach in self.approaches_order:
            data = (
                self.approaches_[approach][str(RQColumn.RQ_TOTAL_TIME)].astype(float)
                / convert_to_
            )

            sorted_data = np.sort(data)
            y = np.arange(1, len(sorted_data) + 1) / len(sorted_data)

            ax.plot(
                sorted_data,
                y,
                **line_styles_no_marker_with_abbr[approach],
            )

        ax.set_ylabel("cdf")
        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticks(desired_yticks)
        ax.set_yticklabels([str(tick) for tick in desired_yticks])
        ax.set_ylim(0, 1)

        ax.set_xlabel("")  # "latency (s)"
        ax.xaxis.set_major_locator(ticker.FixedLocator(ax.get_xticks()))
        ax.set_xticks(desired_xticks)
        ax.set_xticklabels(["" for tick in desired_xticks])  # str(tick)
        ax.set_xlim(left=0, right=desired_xticks[-1] + 0.5)

        plt.savefig(
            f"{OUTPUT_DIR}/range-query-latency-cdf.pdf",
            bbox_inches="tight",
            pad_inches=0.04,
        )
        plt.close(fig)

    def latency_for_each_range_query(self, range_query_pattern=""):
        convert_to_ = 10**9
        ylabel = "latency (s)"  # use this if micro, µ
        desired_yticks = [0, 1, 2]
        # desired_xticks = [0, 2250, 4500, 6750, 9000]

        approach_data = dict()
        for approach, data in self.approaches_.items():
            approach_data[approach] = (
                data[str(RQColumn.RQ_TOTAL_TIME)]
                .apply(lambda x: x / convert_to_)
                .to_list()
            )

        fig, ax = plt.subplots(figsize=self.fig_size)

        for approach in self.approaches_order:
            data = approach_data[approach]
            ax.plot(
                range(len(data)),
                data,
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
            # print("avg ", approach, sum(data)/len(data))

        ax.set_ylabel(ylabel)
        ax.yaxis.set_major_locator(ticker.FixedLocator(ax.get_yticks()))
        ax.set_yticks(desired_yticks)
        ax.set_yticklabels([str(sec) for sec in desired_yticks])
        ax.set_ylim(bottom=0)

        ax.set_xlabel("range query number")
        ax.xaxis.set_major_locator(ticker.FixedLocator(ax.get_xticks()))
        # ax.set_xticks(desired_xticks)
        # ax.set_xticklabels([str(x) for x in desired_xticks])

        plt.savefig(
            f"{OUTPUT_DIR}/range-query-latency.pdf", bbox_inches="tight", pad_inches=0.04
        )
        plt.close(fig)

        legend_fig = plt.figure(figsize=(8, 2))

        # Add your custom text above the legend
        # legend_text = r"E=128\hspace{1cm}I=8388608\hspace{1cm}U=8388608\hspace{1cm}S=900\hspace{1cm}T=6\hspace{1cm}B=32\hspace{1cm}P=1024"
        legend_text = (
            f"M={round((entry_size*entries_per_page*num_page_per_file)/(1024*1024))}MB\\hspace{{1cm}}"
            f"E={entry_size}B\\hspace{{1cm}}"
            f"T={size_ratio}\\hspace{{1cm}}"
            f"I={round(inserts/1000000, 1)}M\\hspace{{1cm}}"
            f"U={round(updates/1000000, 1)}M\\hspace{{1cm}}"
            f"S={round(range_queries/1000)}K\\hspace{{1cm}}"
            f"s={SELECTIVITY}\\hspace{{1cm}}"
            # f"B={entries_per_page}\\hspace{{1cm}}"
            # f"P={num_page_per_file}"
        )
        legend_fig.text(0.5, 0.85, legend_text, ha="center", va="center")

        legend_fig.savefig(
            f"{OUTPUT_DIR}/bounded-legend-config.pdf", bbox_inches="tight", pad_inches=0.015
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
            f"{OUTPUT_DIR}/bounded-legend.pdf", bbox_inches="tight", pad_inches=0.015
        )
        plt.close(legend_fig)


def plot_total_data_movement(
    approaches_plotting_stats: Dict[str, List[PlottingStats]],
    approaches_rq_stats: Dict[str, pd.DataFrame],
    approach_abr_order: List[str],
    epoch_to_plot: int = -1,
):
    bar_width = 0.55
    convert_to_ = 1024**4
    ylabel = "data movement (TB)"
    desired_yticks = [0, 0.1, 0.2, 0.3]
    adjust_ytop_by = 0
    fig_size = (1.2, 2.03)

    plotting_stats = deepcopy(approaches_plotting_stats)
    rq_stats = deepcopy(approaches_rq_stats)

    approach_data: Dict[str, int] = dict()
    for approach, data in rq_stats.items():
        approach_data[approach] = (
            data[str(RQColumn.TOTAL_ENTRIES_READ)].sum() * entry_size
        )

    for approach, data in plotting_stats.items():
        approach_data[approach] += (
            data[epoch_to_plot].CompactionReadBytes
            + data[epoch_to_plot].CompactionWrittenBytes
            + data[epoch_to_plot].RangeReduceWrittenBytes
        )
        approach_data[approach] = approach_data[approach] / convert_to_

    _, ax = plt.subplots(figsize=fig_size)
    bar_containers = []

    for approach, data in approach_data.items():
        bars = ax.bar(
            approach,
            data,
            width=bar_width,
            **bar_styles[approach],
        )
        bar_containers.append(bars)

        # print(approach, f"{data:.2f} GB")

    ax.set_ylabel(ylabel)
    ax.set_yticks(desired_yticks)
    ax.set_yticklabels([str(tb) for tb in desired_yticks])
    ax.set_ylim(bottom=0, top=desired_yticks[-1] + adjust_ytop_by)
    ax.yaxis.set_label_coords(-0.42, 0.34)

    ax.set_xticks(range(len(approach_data)))
    ax.set_xticklabels([per for per in approach_abr_order], rotation=90)

    for bars in bar_containers:
        for bar in bars:
            height = bar.get_height()

            if height < 0.05:
                ax.text(
                    bar.get_x() + bar.get_width() / 2,
                    height,
                    f"{height:.2f}",
                    ha="center",
                    va="bottom",
                    fontsize=18,
                    rotation=90,
                )

    plt.savefig(
        f"{OUTPUT_DIR}/overall-data-movement.pdf", bbox_inches="tight", pad_inches=0.06
    )

def plot_data_movement_over_epoch(
    approaches_plotting_stats: Dict[str, List[PlottingStats]],
    approaches_rq_stats: Dict[str, pd.DataFrame],
    approach_order: List[str], # Use the full names as keys for dicts
):
    convert_to_ = 1024**4
    ylabel = "data movement (TB)"
    xlabel = "epoch"
    desired_xticks = [0, 5]
    # Adjust y-ticks based on your expected data volume
    desired_yticks = [0, 0.1, 0.2] 

    # Map your JSON workload counts to RQ dataframe slices
    # These indices must be cumulative
    rq_epoch_map = {
        2: (0, 1),           # Group 2: 1 querys
        3: (1, 1001),        # Group 3: 1000 queries
        4: (1001, 1201),     # Group 4: 200 queries
        9: (1201, 1401)      # Group 9: 200 queries
    }

    fig, ax = plt.subplots(figsize=(3.2, 2)) # Adjusting size for time-series

    for approach in approach_order:
        stats_list = approaches_plotting_stats[ABBR_TO_NAME[approach]]
        rq_df = approaches_rq_stats[ABBR_TO_NAME[approach]]
        
        movement_per_epoch = []
        
        # Iterate through every epoch available in the stats
        for epoch_idx in range(len(stats_list)):
            # 1. Sum RQ bytes if this epoch has range queries
            rq_bytes = 0
            if epoch_idx in rq_epoch_map:
                start, end = rq_epoch_map[epoch_idx]
                rq_bytes = rq_df.iloc[start:end][str(RQColumn.TOTAL_ENTRIES_READ)].sum() * entry_size
            
            # 2. Add internal movement (Compaction + RangeReduce)
            internal_bytes = (
                stats_list[epoch_idx].CompactionReadBytes + 
                stats_list[epoch_idx].CompactionWrittenBytes + 
                stats_list[epoch_idx].RangeReduceWrittenBytes
            )
            
            total_gb = (rq_bytes + internal_bytes) / convert_to_
            movement_per_epoch.append(total_gb)

        # Plot as a line
        ax.plot(
            range(len(movement_per_epoch) - 1),
            movement_per_epoch[:-1],
            **line_styles[ABBR_TO_NAME[approach]],
        )
        print(approach)
        print(movement_per_epoch)

    # Formatting
    ax.set_ylabel(ylabel)
    ax.set_yticks(desired_yticks)
    ax.set_yticklabels([str(y) for y in desired_yticks])
    ax.set_ylim(bottom=0, top=desired_yticks[-1])
    ax.yaxis.set_label_coords(-0.18, 0.34)

    ax.set_xlabel(xlabel)
    ax.set_xticks(desired_xticks)
    ax.set_xticklabels([str(x + 1) for x in desired_xticks])

    plt.savefig(
        f"{OUTPUT_DIR}/data-movement-over-epochs.pdf",
        bbox_inches="tight",
        pad_inches=0.06,
    )
    plt.close(fig)


class PlotOperationLatencyStats:
    fig_size = (4, 2.5)

    def __init__(
        self,
        op_latency_stats: Dict[str, List[Tuple[str, float]]],
        approaches_order: List[str],
    ):
        self.op_latency_stats = deepcopy(op_latency_stats)
        self.approaches_order = deepcopy(approaches_order)

    # -------------------------------
    # Internal helpers
    # -------------------------------

    def _collect_latencies(
        self,
        approach,
        operations=None,
        convert_to=1e3,
    ):
        """
        Returns:
            x: sequential indices
            y: latencies in µs
        """
        data = self.op_latency_stats[approach]

        latencies = []

        for op, latency_ns in data:
            if operations is None or op in operations:
                latencies.append(latency_ns / convert_to)

        return latencies

    # -------------------------------
    # Scatter plot
    # -------------------------------

    def plot_scatter(self, operations=None, tag="all"):
        ylabel = r"latency ($\mu$s)"
        xlabel = f"{tag}"

        fig, ax = plt.subplots(figsize=self.fig_size)

        for approach in self.approaches_order:
            latencies = self._collect_latencies(approach, operations)

            style = point_styles[approach].copy()

            # print(approach)
            # print(sum(latencies[0:5000])/5000)
            # print(sum(latencies[5000:10000])/5000)
            # print(sum(latencies[10000:])/(len(latencies)-10000))

            ax.scatter(
                range(len(latencies)),
                latencies,
                s=10,
                **style,
            )

        ax.set_yscale("log")
        ax.set_ylim(bottom=1e0, top=1e4)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)

        plt.savefig(
            f"{OUTPUT_DIR}/op-latency-scatter-{tag}.pdf",
            bbox_inches="tight",
            pad_inches=0.04,
        )
        plt.close(fig)

    # -------------------------------
    # Normal line plot
    # -------------------------------

    def plot_line(self, operations=None, tag="all"):
        ylabel = r"latency ($\mu$s)"
        xlabel = f"{tag}"

        fig, ax = plt.subplots(figsize=self.fig_size)

        for approach in self.approaches_order:
            latencies = self._collect_latencies(approach, operations)

            ax.plot(
                range(len(latencies)),
                latencies,
                **line_styles_no_marker[approach],
            )

        ax.set_yscale("log")
        ax.set_ylim(bottom=1e0, top=1e4)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)

        plt.savefig(
            f"{OUTPUT_DIR}/op-latency-line-{tag}.pdf",
            bbox_inches="tight",
            pad_inches=0.04,
        )
        plt.close(fig)

    # -------------------------------
    # Rolling window plot
    # -------------------------------

    def plot_rolling(
        self,
        operations=None,
        window=200,
        statistic="mean",
        tag="all",
    ):
        ylabel = r"latency ($\mu$s)"
        xlabel = f"{tag}"

        fig, ax = plt.subplots(figsize=self.fig_size)

        for approach in self.approaches_order:
            latencies = self._collect_latencies(approach, operations)

            s = pd.Series(latencies)

            q05 = s.rolling(window, min_periods=1).quantile(0.05)
            q95 = s.rolling(window, min_periods=1).quantile(0.95)

            if statistic == "mean":
                rolled = s.rolling(window, min_periods=1).mean()
            else:
                rolled = s.rolling(window, min_periods=1).mean()

            x = range(len(rolled))
            ax.plot(
                x,
                rolled.values,
                **line_styles_no_marker[approach],
            )

            ax.fill_between(
                x,
                q05,
                q95,
                color=line_styles_no_marker[approach]["color"],
                alpha=0.25,
                linewidth=0,
                edgecolor="none",
            )
        ax.text(
            0.02,
            0.65,
            f"rolling window: {window} pts\nline: mean\nband: p5–p95",
            transform=ax.transAxes,
            fontsize=17,
        )

        ax.set_yscale("log")
        ax.set_ylim(bottom=1e0, top=1e4)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)

        plt.savefig(
            f"{OUTPUT_DIR}/op-latency-rolling-{statistic}-{tag}.pdf",
            bbox_inches="tight",
            pad_inches=0.04,
        )
        plt.close(fig)

def plot_total_data_movement_normalized(
    approaches_plotting_stats: Dict[str, List[PlottingStats]],
    approaches_rq_stats: Dict[str, pd.DataFrame],
    approach_abr_order: List[str],
    epoch_to_plot: int = -1,
):
    bar_width = 0.55
    ylabel = "norm. data movement"
    fig_size = (1.2, 2.5) # Keeping your compact figure size

    # 1. Calculate raw GB for all
    approach_gb = {}
    for approach, data in approaches_rq_stats.items():
        # Query reads
        query_bytes = data[str(RQColumn.TOTAL_ENTRIES_READ)].sum() * entry_size
        # Background I/O
        bg_stats = approaches_plotting_stats[approach][epoch_to_plot]
        bg_bytes = (bg_stats.CompactionReadBytes + 
                    bg_stats.CompactionWrittenBytes + 
                    bg_stats.RangeReduceWrittenBytes)
        
        approach_gb[approach] = (query_bytes + bg_bytes) / (1024**3)

    # 2. Baseline (RocksDB)
    rocksdb_val = approach_gb.get("RocksDB", 1.0)
    if rocksdb_val == 0: rocksdb_val = 1.0
    
    # 3. Normalize
    normalized_data = {app: val / rocksdb_val for app, val in approach_gb.items()}

    fig, ax = plt.subplots(figsize=fig_size)
    
    for i, approach in enumerate(ACTIVE_APPROACHES):
        if approach not in normalized_data: continue
        val = normalized_data[approach]
        
        ax.bar(i, val, width=bar_width, **bar_styles[approach])
        
        if val < 0.1: # Annotate tiny bars
            ax.text(i, val + 0.01, f"{val:.2f}", ha="center", va="bottom", fontsize=14, rotation=90)

    ax.set_ylabel(ylabel)
    ax.set_ylim(0, 1.4) 
    ax.set_yticks([0, 0.5, 1.0])
    ax.set_yticklabels([str(tick) for tick in [0, 0.5, 1]])
    
    ax.set_xticks(range(len(approach_abr_order)))
    ax.set_xticklabels(approach_abr_order, rotation=90)
    ax.yaxis.set_label_coords(-0.4, 0.38)

    plt.savefig(f"{OUTPUT_DIR}/overall-data-movement-normalized.pdf", bbox_inches="tight")















# -------------------------------------------------------------------
# Experiment configuration
# -------------------------------------------------------------------

PROJECT_DIR = Path.cwd().parent.parent

epoch_to_plot = -1
ROLLING_WINDOW = 20

# --- Which approaches to include in *this* experiment ---
ACTIVE_APPROACHES = [
    "RocksDB",
    "SuccinctKV",
    "RangeReduce[lb=T^-1 & re=1]",
]
APPROACH_ABBR = [
    "RDB",
    "SKV",
    "RR",
]

ABBR_TO_NAME = {
    "RDB": "RocksDB",
    "SKV": "SuccinctKV",
    "RR": "RangeReduce[lb=T^-1 & re=1]",
}

ALL_APPROACHES = {
    "RocksDB": "RocksDB",
    "RangeReduce[lb=T^-1 & re=1]": "RangeReduce[lb=T^-1ANDre=1]",
    "SuccinctKV": "SuccinctKV",
    # "RangeReduce[lb=0]": "RangeReduce[lb=0]",
    # "RangeReduce[lb=T^-1]": "RangeReduce[lb=T^-1]",
}

EXPDIRNAME = f"{PROJECT_DIR}/logs/experiments-{tag}-T{size_ratio}"

filesize = entry_size * entries_per_page * num_page_per_file

epoch_stats = {}
max_lvl_mtx = []

for name, dirname in ALL_APPROACHES.items():
    dirpath = os.path.join(EXPDIRNAME, dirname)
    stats = EpochStats(dirpath, filesize)
    epoch_stats[name] = stats
    max_lvl_mtx.append(stats.get_max_levels())

max_length_epoch = max(len(col) for col in max_lvl_mtx)
max_lvl_per_epoch = [0] * max_length_epoch

for col in max_lvl_mtx:
    for idx, lvl in enumerate(col):
        max_lvl_per_epoch[idx] = max(max_lvl_per_epoch[idx], lvl)

rq_stats = {name: epoch_stats[name].get_rangequerystats() for name in ACTIVE_APPROACHES}


# # -------------------------------------------------------------------
# # Plot Range Query Stats
# # -------------------------------------------------------------------

plot_rq = PlotRangeQueryStats(
    rq_stats,
    approaches_order=ACTIVE_APPROACHES,
)

# # plot_rq.bytes_read_for_each_range_query()
plot_rq.bytes_read_for_each_range_query_scatter_normalized()
# plot_rq.bytes_read_for_each_range_query_line_normalized(window=ROLLING_WINDOW)
# # plot_rq.bytes_read_for_each_range_query_rolling_broken_axes(window=ROLLING_WINDOW)
# plot_rq.bytes_read_for_each_range_query_rolling(window=ROLLING_WINDOW)
# plot_rq.bytes_read_for_each_range_query_scatter()

# # # plot_rq.latency_for_each_range_query()
plot_rq.normalized_latency_scatter()
# plot_rq.normalized_latency_line(window=ROLLING_WINDOW)
# # plot_rq.latency_for_each_range_query_rolling_broken_axes(window=ROLLING_WINDOW)
# plot_rq.latency_for_each_range_query_rolling(window=ROLLING_WINDOW)
# plot_rq.latency_for_each_range_query_scatter()

# # # plot_rq.bytes_read_cdf()
# # # plot_rq.latency_cdf()


epoch_plot_stats = {
    name: epoch_stats[name].get_plotstats(max_lvl_per_epoch)
    for name in ACTIVE_APPROACHES
}

# op_latency_stats = {
#     name: epoch_stats[name].get_op_latency() for name in ACTIVE_APPROACHES
# }

# plot_op = PlotOperationLatencyStats(
#     op_latency_stats=op_latency_stats,
#     approaches_order=ACTIVE_APPROACHES,
# )

# plot_op.plot_scatter()
# plot_op.plot_scatter(operations=["Q"], tag="point query")
# plot_op.plot_scatter(operations=["I", "U"], tag="insert + update")

# plot_op.plot_line(operations=["I", "U"], tag="insert + update")

# plot_op.plot_rolling(
#     operations=["I", "U"],
#     window=100,
#     statistic="mean",
#     tag="insert + update",
# )

# plot_op.plot_rolling(
#     operations=["Q"],
#     window=100,
#     statistic="mean",
#     tag="point query",
# )

# -------------------------------------------------------------------
# Plot Epoch Metrics
# -------------------------------------------------------------------

metric_exp = PlotEpochStats(
    epoch_plot_stats,
    approach_abr_order=APPROACH_ABBR,
    epoch_to_plot=epoch_to_plot,
)

# metric_exp.plot_total_bytes_written()
# metric_exp.plot_total_bytes_written_normalized()
# metric_exp.plot_compaction_debt()
# metric_exp.plot_compaction_debt_normalized()
metric_exp.plot_compaction_debt_over_epochs()
metric_exp.plot_space_amp_over_epochs()
# metric_exp.plot_space_amplification()
# metric_exp.plot_workload_exec_time()

plot_data_movement_over_epoch(
    epoch_plot_stats,
    rq_stats,
    approach_order=APPROACH_ABBR,
    # epoch_to_plot=epoch_to_plot,
)
# plot_total_data_movement(
#     epoch_plot_stats,
#     rq_stats,
#     approach_abr_order=APPROACH_ABBR,
#     epoch_to_plot=epoch_to_plot,
# )
# plot_total_data_movement_normalized(
#     epoch_plot_stats,
#     rq_stats,
#     approach_abr_order=APPROACH_ABBR,
#     epoch_to_plot=epoch_to_plot,
# )

plt.close("all")
print("✅ All figures generated and saved successfully.")
