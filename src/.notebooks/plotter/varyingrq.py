
from copy import deepcopy
from typing import List

import pandas as pd
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
from matplotlib.patches import Patch

from plotter.epochstats import EpochStats
from plotter.dataclass import AdditionalStats, PlottingStats, RQColumn
from matplotlib.ticker import LogLocator, LogFormatter
from plotter.plotstyles import line_styles, bar_styles, box_styles

x_axis_labels1 = {
    "0.000003814697265625": "$2^{5}$",
    "0.00000762939453125": "$2^{6}$",
    "0.0000152587890625": "$2^{7}$",
    "0.000030517578125": "$2^{8}$",
    "0.00006103515625": "$2^{9}$",
    "0.0001220703125": "$2^{10}$",
    "0.000244140625": "$2^{11}$",
    "0.00048828125": "$2^{12}$",
    "0.0009765625": "$2^{13}$",
    "0.001953125": "$2^{14}$",
    "0.00390625": "$2^{15}$",
    "0.0078125": "$2^{16}$",
    "0.015625": "$2^{17}$",
    "0.03125": "$2^{18}$",
    "0.0625": "$2^{19}$",
    "0.125": "$2^{20}$",
    "0.25": "$2^{21}$",
    "0.5": "$2^{22}$",
}

x_axis_labels2 = {
    "0.000003814697265625": "$\\frac{1}{2^{18}}$",
    "0.00000762939453125": "$\\frac{1}{2^{17}}$",
    "0.0000152587890625": "$\\frac{1}{2^{16}}$",
    "0.000030517578125": "$\\frac{1}{2^{15}}$",
    "0.00006103515625": "$\\frac{1}{2^{14}}$",
    "0.0001220703125": "$\\frac{1}{2^{13}}$",
    "0.000244140625": "$\\frac{1}{2^{12}}$",
    "0.00048828125": "$\\frac{1}{2^{11}}$",
    "0.0009765625": "$\\frac{1}{2^{10}}$",
    "0.001953125": "$\\frac{1}{2^{9}}$",
    "0.00390625": "$\\frac{1}{2^{8}}$",
    "0.0078125": "$\\frac{1}{2^{7}}$",
    "0.015625": "$\\frac{1}{2^{6}}$",
    "0.03125": "$\\frac{1}{2^{5}}$",
    "0.0625": "$\\frac{1}{2^{4}}$",
    "0.125": "$\\frac{1}{2^{3}}$",
    "0.25": "$\\frac{1}{2^{2}}$",
    "0.5": "$\\frac{1}{2^{1}}$",
}

rq_perccentage_axises = (
   0.000003814697265625,
    # 0.00000762939453125,
    0.0000152587890625,
    # 0.000030517578125,
   0.00006103515625,
    # 0.0001220703125,
    0.000244140625,
    # 0.00048828125,
   0.0009765625,
    # 0.001953125,
    0.00390625,        # 2^15
    # 0.0078125,
   0.015625,
    # 0.03125,
    # 0.0625,
    # 0.125,
    # 0.25,
    # 0.5,
)

rq_percentages = (
   "0.000003814697265625",
    # "0.00000762939453125",
    "0.0000152587890625",
    # "0.000030517578125",
   "0.00006103515625",
    # "0.0001220703125",
    "0.000244140625",
    # "0.00048828125",
   "0.0009765625",
    # "0.001953125",
    "0.00390625",
    # "0.0078125",
   "0.015625",
    # "0.03125",
    # "0.0625",
    # "0.125",
    # "0.25",
    # "0.5",
)

x_axis_labels = x_axis_labels1
rotation = 0


def human_readable_bytes(bytes_val):
    gb = bytes_val / (1024**3)
    if gb < 10:
        return f"{gb:.1f}"
    else:
        return f"{gb:.0f}"


class VaryingRQPlots:
    vanilla_boxplot_kwargs = {
        "label": "RocksDB",
        "showfliers": False,
        "notch": True,
        "patch_artist": True,
        "boxprops": dict(facecolor="grey", edgecolor="black", linewidth=1.5, hatch=""),
        "medianprops": dict(color="black", linewidth=1.5),
        "whiskerprops": dict(color="black", linewidth=1),
        "capprops": dict(color="black", linewidth=1),
    }
    rqdc_boxplot_kwargs = {
        "label": "RangeReduce",
        "showfliers": False,
        "notch": True,
        "patch_artist": True,
        "boxprops": dict(facecolor="tab:red", edgecolor="black", linewidth=1.5, hatch="x"),
        "medianprops": dict(color="black", linewidth=1.5),
        "whiskerprops": dict(color="black", linewidth=1),
        "capprops": dict(color="black", linewidth=1),
    }

    def __init__(
        self,
        vanilla: List[EpochStats],
        succinctkv: List[EpochStats],
        rqdc: List[EpochStats],
        max_lvl_per_epoch: List[List[int]],
        tag,
        inserts,
        entry_size,
        operation_count: List[int],
        epoch_to_plot: int = -1,
    ):
        self.tag = tag
        self.inserts = inserts
        self.entry_size = entry_size
        self.fig_size = (5, 3.8) if self.tag == "overlapping100" else (5, 3.3)

        if len(vanilla) != len(rqdc):
            raise Exception("lengths of vanilla and rqdc stats are not the same")
        self._vanilla: List[PlottingStats] = deepcopy(
            [van.get_plotstats(max_lvl_per_epoch)[epoch_to_plot] for van in vanilla]
        )
        self._succinctkv: List[PlottingStats] = deepcopy(
            [suc.get_plotstats(max_lvl_per_epoch)[epoch_to_plot] for suc in succinctkv]
        )
        self._rqdc: List[PlottingStats] = deepcopy(
            [rqd.get_plotstats(max_lvl_per_epoch)[epoch_to_plot] for rqd in rqdc]
        )
        self._vanilla_rq: List[pd.DataFrame] = [
            van.get_rangequerystats().copy(deep=True) for van in vanilla
        ]
        self._succinctkv_rq: List[pd.DataFrame] = [  
            suc.get_rangequerystats().copy(deep=True) for suc in succinctkv
        ]
        self._rqdc_rq: List[pd.DataFrame] = [
            rqd.get_rangequerystats().copy(deep=True) for rqd in rqdc
        ]
        self._op_count = operation_count

    def plot_throughput(self):
        convert_to_ = 1000**3
        vanilla_throughput = [
            self._op_count[i] / (van.WorkloadExecutionTime / convert_to_)
            for i, van in enumerate(self._vanilla, 0)
        ]
        succinctkv_throughput = [
            self._op_count[i] / (suc.WorkloadExecutionTime / convert_to_)
            for i, suc in enumerate(self._succinctkv)
        ]
        rqdc_throughput = [
            self._op_count[i] / (rqdc.WorkloadExecutionTime / convert_to_)
            for i, rqdc in enumerate(self._rqdc)
        ]

        vanilla_norm = [vanilla_throughput[i] / vanilla_throughput[i] for i in range(len(vanilla_throughput))]
        succinctkv_norm = [succinctkv_throughput[i] / vanilla_throughput[i] for i in range(len(vanilla_throughput))]
        rqdc_norm = [rqdc_throughput[i] / vanilla_throughput[i] for i in range(len(vanilla_throughput))]

        fig, ax = plt.subplots(figsize=self.fig_size)

        ax.set_xscale("log", base=2)
        # if self.tag == "selectivityplots":
        #     ax.set_xticks(rq_perccentage_axises)
        #     ax.set_xticklabels([f"" for per in rq_percentages], rotation=rotation)
        # else:
        ax.set_xlabel("range query count")
        ax.set_xticks(rq_perccentage_axises[::2])
        ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages[::2]], rotation=rotation)

        ax.plot(rq_perccentage_axises, vanilla_norm, **line_styles["RocksDB"])
        ax.plot(rq_perccentage_axises, succinctkv_norm, **line_styles["SuccinctKV"])
        ax.plot(rq_perccentage_axises, rqdc_norm, **line_styles["RangeReduce[lb=T^-1 & re=1]"])
        ax.set_ylabel("norm. throughput")
        ax.set_ylim(bottom=0)

        desired_yticks = [0, 0.5, 1, 1.5]
        desired_norm_yticks = [x for x in desired_yticks]
        ax.set_yticks(desired_norm_yticks)
        ax.set_yticklabels([0] + [f"{x:.1f}" for x in desired_yticks[1:]])

        plt.tight_layout()
        plt.savefig(f'{self.tag}/throughput.pdf', bbox_inches='tight', pad_inches=0.06)

        # legend_fig = plt.figure(figsize=(8, 2))
        # legend_text = (
        #     f"M={round((entry_size * entries_per_page * num_pages_per_file)/(1024*1024))}MB\\hspace{{1cm}}"
        #     f"E={entry_size}B\\hspace{{1cm}}"
        #     f"T={size_ratio}\\hspace{{1cm}}"
        #     f"I={round(inserts/1000000, 1)}M\\hspace{{1cm}}"
        #     f"S+U={round(updates/1000000, 1)}M\\hspace{{1cm}}"
        #     f"s={selectivity}\\hspace{{1cm}}"
        # )
        # if self.tag == "overlapping100":
        #     legend_text = "\\hspace{1cm}every 100 RQs are identical"
        # legend_fig.text(0.5, 0.85, legend_text, ha='center', va='center')
        # legend_fig.savefig(f'{self.tag}/experimental-legend-config.pdf', bbox_inches='tight', pad_inches=0.015)

        handles1, labels1 = ax.get_legend_handles_labels()
        combined_handles = handles1 
        combined_labels = labels1

        legend_fig = plt.figure(figsize=(10, 2))
        legend_fig.legend(combined_handles, combined_labels, loc="center", ncol=4, frameon=False, borderaxespad=0, labelspacing=0, 
                    borderpad=0)
        legend_fig.savefig(f'{self.tag}/experimental.pdf', bbox_inches='tight', pad_inches=0.015)

    # def plot_range_query_latency(self):
    #     vanilla_rq_times = [df[str(RQColumn.RQ_TOTAL_TIME)] for df in self._vanilla_rq]
    #     rqdc_rq_times = [df[str(RQColumn.RQ_TOTAL_TIME)] for df in self._rqdc_rq]

    #     x_positions = np.arange(len(rq_percentages))
    #     vanilla_means = [np.mean(data) for data in vanilla_rq_times]
    #     rqdc_means = [np.mean(data) for data in rqdc_rq_times]

    #     fig, ax = plt.subplots(figsize=self.fig_size)
    #     ax.plot(x_positions, vanilla_means, **line_styles["RocksDB"])
    #     ax.plot(x_positions, rqdc_means, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

    #     ax.set_ylabel("avg. RQ latency (sec)")
    #     ax.set_ylim(bottom=0)
    #     if self.tag == "selectivityplots":
    #         ax.set_xticks(x_positions)
    #         ax.set_xticklabels([f"" for per in rq_percentages], rotation=rotation)
    #     else:
    #         ax.set_xlabel("range query count")
    #         ax.set_xticks(x_positions)
    #         ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages], rotation=rotation)

    #     convert_to_ = 10**9
    #     desired_yticks = [0, 1, 2]
    #     desired_sec_yticks = [x * convert_to_ for x in desired_yticks]
    #     ax.set_yticks(desired_sec_yticks)
    #     ax.set_yticklabels(['0'] + [f"{x}" for x in desired_yticks[1:]])

    #     plt.tight_layout()
    #     plt.savefig(f'{self.tag}/range_query_latency.pdf', bbox_inches='tight', pad_inches=0.06)

    def plot_range_query_box_plot_latency(self):
        convert_to_ = 10**9
        vanilla_rq_times = [df[str(RQColumn.RQ_TOTAL_TIME)] for df in self._vanilla_rq]
        succinct_kv_rq_times = [df[str(RQColumn.RQ_TOTAL_TIME)] for df in self._succinctkv_rq]
        rqdc_rq_times = [df[str(RQColumn.RQ_TOTAL_TIME)] for df in self._rqdc_rq]

        x_positions = np.arange(len(rq_percentages))
        width = 0.22 
        offsets = [-width, 0, +width]

        fig, ax = plt.subplots(figsize=(4.6, 3.8))
        mpl.rcParams["hatch.linewidth"] = 0.5 
        
        ax.boxplot(
            vanilla_rq_times,
            positions=x_positions - 0.25 + offsets[0],
            widths=width,
            whis=(0,95),
            patch_artist=True,
            boxprops=box_styles["RocksDB"],
            medianprops=dict(color="black"),
            showfliers=False
        )

        ax.boxplot(
            succinct_kv_rq_times,
            positions=x_positions + offsets[0],
            widths=width,
            whis=(0,95),
            patch_artist=True,
            boxprops=box_styles["SuccinctKV"],
            medianprops=dict(color="black"),
            showfliers=False
        )

        ax.boxplot(
            rqdc_rq_times,
            positions=x_positions + 0.25 + offsets[0],
            widths=width,
            whis=(0,95),
            patch_artist=True,
            boxprops=box_styles["RangeReduce[lb=T^-1 & re=1]"],
            medianprops=dict(color="black"),
            showfliers=False
        )

        ax.set_ylabel("RQ latency (sec)")
        ax.yaxis.set_label_coords(-0.12, 0.45)
        ax.set_ylim(bottom=0)

        legend_handles = [
            Patch(facecolor=box_styles["RocksDB"]["facecolor"], hatch=box_styles["RocksDB"]["hatch"], edgecolor="none", label="RocksDB"),
            Patch(facecolor=box_styles["SuccinctKV"]["facecolor"], hatch=box_styles["SuccinctKV"]["hatch"], edgecolor="none", label="SuccinctKV"),
            Patch(facecolor=box_styles["RangeReduce[lb=T^-1 & re=1]"]["facecolor"], hatch=box_styles["RangeReduce[lb=T^-1 & re=1]"]["hatch"], edgecolor="none", label="RangeReduce"),
        ]

        ax.legend(handles=legend_handles, ncol=2, loc=(0.005, -0.01), frameon=False, columnspacing=0.2, handletextpad=0.1, handlelength=1.0, handleheight=0.7, fontsize=17.5)

        # if self.tag == "selectivityplots":
        #     ax.set_xticks(x_positions)
        #     ax.set_xticklabels(["" for _ in rq_percentages], rotation=rotation)
        # else:
        ax.set_xlabel("range query count")
        ax.set_xticks(x_positions)
        ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages], rotation=rotation)

        desired_yticks = [0, 0.5, 1, 1.5]
        ax.set_yticks([x * convert_to_ for x in desired_yticks])
        ax.set_yticklabels([str(x) for x in desired_yticks])

        plt.tight_layout()
        plt.savefig(f'{self.tag}/range_query_latency_boxplot.pdf', bbox_inches='tight', pad_inches=0.06)
        plt.close(fig)

    def plot_compaction_debt(self):
        convert_to_ = 1024**3
        vanilla_compaction_debt = [van.CompactionDebt for van in self._vanilla]
        succinctkv_compaction_debt = [suc.CompactionDebt for suc in self._succinctkv]
        rqdc_compaction_debt = [rqd.CompactionDebt for rqd in self._rqdc]

        fig, ax = plt.subplots(figsize=self.fig_size)
        ax.plot(rq_perccentage_axises, vanilla_compaction_debt, **line_styles["RocksDB"])
        ax.plot(rq_perccentage_axises, succinctkv_compaction_debt, **line_styles["SuccinctKV"])
        ax.plot(rq_perccentage_axises, rqdc_compaction_debt, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

        ax.set_ylabel("compaction debt (GB)", labelpad=-1, loc="top")
        # if self.tag != "selectivityplots":
        # ax.yaxis.set_label_coords(-0.1, 0.45)
        ax.set_ylim(bottom=0)
        ax.set_xscale("log", base=2)
        # if self.tag == "selectivityplots":
        #     ax.set_xticks(rq_perccentage_axises[::2])
        #     ax.set_xticklabels([f"" for per in rq_percentages[::2]], rotation=rotation)
        # else:
        ax.set_xlabel("range query count")
        ax.set_xticks(rq_perccentage_axises[::2])
        ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages[::2]], rotation=rotation)

        desired_yticks = [0, 5, 10, 15]
        desired_gb_yticks = [x * convert_to_ for x in desired_yticks]
        ax.set_yticks(desired_gb_yticks)
        ax.set_yticklabels([0] + [f"{x}" for x in desired_yticks[1:]])

        plt.tight_layout()
        plt.savefig(f'{self.tag}/compaction_debt.pdf', bbox_inches='tight', pad_inches=0.06)

    # def plot_wkl_exec_time(self):
    #     convert_to_ = 1000**3
    #     to_hours = 60 * 60
    #     vanilla_wkl_exec_time = [(van.WorkloadExecutionTime / convert_to_) / to_hours for van in self._vanilla]
    #     rqdc_wkl_exec_time = [(rqd.WorkloadExecutionTime / convert_to_) / to_hours for rqd in self._rqdc]

    #     fig, ax = plt.subplots(figsize=self.fig_size)
    #     ax.plot(rq_perccentage_axises, vanilla_wkl_exec_time, **line_styles["RocksDB"])
    #     ax.plot(rq_perccentage_axises, rqdc_wkl_exec_time, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

    #     ax.set_ylabel("execution time (hrs)")
    #     ax.set_ylim(bottom=0)
    #     ax.set_xscale("log", base=2)
    #     if self.tag == "selectivityplots":
    #         ax.set_xticks(rq_perccentage_axises[::2])
    #         ax.set_xticklabels([f"" for per in rq_percentages[::2]], rotation=rotation)
    #     else:
    #         ax.set_xlabel("range query count")
    #         ax.set_xticks(rq_perccentage_axises[::2])
    #         ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages[::2]], rotation=rotation)

    #     plt.tight_layout()
    #     plt.savefig(f'{self.tag}/wkl_execution_time.pdf', bbox_inches='tight', pad_inches=0.06)

    def plot_space_amp(self):
        vanilla_space_amp = [van.DBSize / (self.inserts * (self.entry_size)) for van in self._vanilla]
        succinctkv_space_amp = [suc.DBSize / (self.inserts * (self.entry_size)) for suc in self._succinctkv]
        rqdc_space_amp = [rqd.DBSize / (self.inserts * (self.entry_size)) for rqd in self._rqdc]

        fig, ax = plt.subplots(figsize=self.fig_size)
        ax.plot(rq_perccentage_axises, vanilla_space_amp, **line_styles["RocksDB"])
        ax.plot(rq_perccentage_axises, succinctkv_space_amp, **line_styles["SuccinctKV"])
        ax.plot(rq_perccentage_axises, rqdc_space_amp, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

        ax.set_ylabel("space amplification")
        ax.set_ylim(bottom=0, top=max(vanilla_space_amp) + 0.5)
        ax.set_xscale("log", base=2)
        # if self.tag == "selectivityplots":
        #     ax.set_xticks(rq_perccentage_axises[::2])
        #     ax.set_xticklabels([f"" for per in rq_percentages[::2]], rotation=rotation)
        # else:
        ax.set_xlabel("range query count")
        ax.set_xticks(rq_perccentage_axises[::2])
        ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages[::2]], rotation=rotation)

        desired_yticks = [0, 0.5, 1, 1.5, 2]
        ax.set_yticks(desired_yticks)
        ax.set_yticklabels([0] + [f"{x:.1f}" for x in desired_yticks[1:]])
        plt.tight_layout()
        plt.savefig(f'{self.tag}/space_amplification.pdf', bbox_inches='tight', pad_inches=0.06)

    # def plot_total_bytes_written(self):
    #     convert_to_ = 1024**3
    #     vanilla_writes = [(van.CompactionWrittenBytes + van.RangeReduceWrittenBytes) for van in self._vanilla]
    #     rqdc_writes = [(rqdc.CompactionWrittenBytes + rqdc.RangeReduceWrittenBytes) for rqdc in self._rqdc]

    #     fig, ax = plt.subplots(figsize=self.fig_size)
    #     ax.plot(rq_perccentage_axises, vanilla_writes, **line_styles["RocksDB"])
    #     ax.plot(rq_perccentage_axises, rqdc_writes, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

    #     ax.set_ylabel("total writes (GB)")
    #     ax.set_xscale("log", base=2)
    #     if self.tag == "selectivityplots":
    #         ax.set_xticks(rq_perccentage_axises[::2])
    #         ax.set_xticklabels([f"" for per in rq_percentages[::2]], rotation=rotation)
    #     else:
    #         ax.set_xlabel("range query count")
    #         ax.set_xticks(rq_perccentage_axises[::2])
    #         ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages[::2]], rotation=rotation)
        
    #     desired_yticks = [0, 25, 50, 75]
    #     desired_gb_yticks = [x * convert_to_ for x in desired_yticks]
    #     ax.set_yticks(desired_gb_yticks)
    #     ax.set_yticklabels([0] + [f"{x}" for x in desired_yticks[1:]])

    #     plt.tight_layout()
    #     plt.savefig(f'{self.tag}/total_bytes_written.pdf', bbox_inches='tight', pad_inches=0.06)

    def plot_overall_datamovement(self):
        convert_to_ = 1024**4
        vanilla_rq_read = [df[str(RQColumn.TOTAL_ENTRIES_READ)].sum() * self.entry_size for df in self._vanilla_rq]
        succinctkv_rq_read = [df[str(RQColumn.TOTAL_ENTRIES_READ)].sum() * self.entry_size for df in self._succinctkv_rq]
        rqdc_rq_read = [df[str(RQColumn.TOTAL_ENTRIES_READ)].sum() * self.entry_size for df in self._rqdc_rq]
        
        vanilla_comp_read_write = [(van.CompactionReadBytes + van.CompactionWrittenBytes) for van in self._vanilla]
        succinctkv_comp_read_write = [(suc.CompactionReadBytes + suc.CompactionWrittenBytes) for suc in self._succinctkv]
        rqdc_comp_read_write = [(rqdc.CompactionReadBytes + rqdc.CompactionWrittenBytes) for rqdc in self._rqdc]
        
        rqdc_rq_write = [rqdc.RangeReduceWrittenBytes for rqdc in self._rqdc]

        vanilla_datamov = [(vanilla_rq_read[i] + vanilla_comp_read_write[i]) / convert_to_ for i in range(len(vanilla_rq_read))]
        succinctkv_datamov = [(succinctkv_rq_read[i] + succinctkv_comp_read_write[i]) / convert_to_ for i in range(len(succinctkv_rq_read))]
        rqdc_datamov = [(rqdc_rq_read[i] + rqdc_comp_read_write[i] + rqdc_rq_write[i]) / convert_to_ for i in range(len(rqdc_rq_write))]

        vanilla_norm = [vanilla_datamov[i] / vanilla_datamov[i] for i in range(len(vanilla_datamov))]
        succinctkv_norm = [succinctkv_datamov[i] / vanilla_datamov[i] for i in range(len(vanilla_datamov))]
        rqdc_norm = [rqdc_datamov[i] / vanilla_datamov[i] for i in range(len(vanilla_datamov))]

        fig, ax = plt.subplots(figsize=self.fig_size)
        ax.set_xscale("log", base=2)
        # if self.tag == "selectivityplots":
        #     ax.set_xticks(rq_perccentage_axises[::2])
        #     ax.set_xticklabels([f"" for per in rq_percentages[::2]], rotation=rotation)
        # else:
        ax.set_xlabel("range query count")
        ax.set_xticks(rq_perccentage_axises[::2])
        ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages[::2]], rotation=rotation)

        ax.plot(rq_perccentage_axises, vanilla_norm, **line_styles["RocksDB"])
        ax.plot(rq_perccentage_axises, succinctkv_norm, **line_styles["SuccinctKV"])
        ax.plot(rq_perccentage_axises, rqdc_norm, **line_styles["RangeReduce[lb=T^-1 & re=1]"])
        ax.set_ylabel("norm. data movement", labelpad=-1, loc='top')
        # if self.tag == "overlapping100":
            # ax.yaxis.label.set_position((1.1, 0.45))
        ax.set_ylim(bottom=0)

        desired_yticks = [0, 0.5, 1, 1.5]
        ax.set_yticks(desired_yticks)
        ax.set_yticklabels([0] + [f"{x:.1f}" for x in desired_yticks[1:]])

        plt.tight_layout()
        plt.savefig(f'{self.tag}/overall_data_movement.pdf', bbox_inches='tight', pad_inches=0.06)

    # def plot_total_bytes_read(self):
    #     convert_to_ = 1024**4
    #     vanilla_rq_read = [df[str(RQColumn.TOTAL_ENTRIES_READ)].sum() * self.entry_size for df in self._vanilla_rq]
    #     rqdc_rq_read = [df[str(RQColumn.TOTAL_ENTRIES_READ)].sum() * self.entry_size for df in self._rqdc_rq]
        
    #     vanilla_comp_read = [(van.CompactionReadBytes) for van in self._vanilla]
    #     rqdc_comp_read = [(rqdc.CompactionReadBytes) for rqdc in self._rqdc]

    #     vanilla_datamov = [(vanilla_rq_read[i] + vanilla_comp_read[i]) for i in range(len(vanilla_rq_read))]
    #     rqdc_datamov = [(rqdc_rq_read[i] + rqdc_comp_read[i]) for i in range(len(rqdc_comp_read))]

    #     fig, ax = plt.subplots(figsize=self.fig_size)
    #     ax.plot(rq_perccentage_axises, vanilla_datamov, **line_styles["RocksDB"])
    #     ax.plot(rq_perccentage_axises, rqdc_datamov, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

    #     ax.set_ylabel("total read (TB)")
    #     ax.set_ylim(bottom=0, top=max(vanilla_datamov) + max(vanilla_datamov) * 0.02)
    #     ax.set_xscale("log", base=2)
    #     if self.tag == "selectivityplots":
    #         ax.set_xticks(rq_perccentage_axises[::2])
    #         ax.set_xticklabels([f"" for per in rq_percentages[::2]], rotation=rotation)
    #     else:
    #         ax.set_xlabel("range query count")
    #         ax.set_xticks(rq_perccentage_axises[::2])
    #         ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages[::2]], rotation=rotation)
        
    #     desired_yticks = [0, 5, 10, 15]
    #     desired_tb_yticks = [x * convert_to_ for x in desired_yticks]
    #     ax.set_yticks(desired_tb_yticks)
    #     ax.set_yticklabels([0] + [f"{x}" for x in desired_yticks[1:]])

    #     plt.tight_layout()
    #     plt.savefig(f'{self.tag}/total_bytes_read.pdf', bbox_inches='tight', pad_inches=0.06)

    # def plot_total_bytes_written_in_compactions(self):
    #     convert_to_ = 1024**3
    #     vanilla_writes = [(van.CompactionWrittenBytes) / convert_to_ for van in self._vanilla]
    #     rqdc_writes = [(rqdc.CompactionWrittenBytes) / convert_to_ for rqdc in self._rqdc]

    #     fig, ax = plt.subplots(figsize=self.fig_size)
    #     ax.plot(rq_perccentage_axises, vanilla_writes, **line_styles["RocksDB"])
    #     ax.plot(rq_perccentage_axises, rqdc_writes, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

    #     ax.set_ylabel("writes (GB)")
    #     ax.set_ylim(bottom=0, top=max(vanilla_writes) + 0.5)
    #     ax.set_title("compactions triggered on level saturation")
    #     ax.set_xscale("log", base=2)
    #     if self.tag == "selectivityplots":
    #         ax.set_xticks(rq_perccentage_axises[::2])
    #         ax.set_xticklabels([f"" for per in rq_percentages[::2]], rotation=rotation)
    #     else:
    #         ax.set_xlabel("range query count")
    #         ax.set_xticks(rq_perccentage_axises[::2])
    #         ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages[::2]], rotation=rotation)
            
    #     plt.tight_layout()
    #     plt.savefig(f'{self.tag}/compaction_writes_on_level_saturation.pdf', bbox_inches='tight', pad_inches=0.06)
















# from copy import deepcopy
# from typing import List

# import pandas as pd
# import numpy as np
# import matplotlib as mpl
# import matplotlib.pyplot as plt
# import matplotlib.ticker as ticker
# from matplotlib.patches import Patch

# from plotter import *
# from plotter.epochstats import EpochStats
# from plotter.dataclass import AdditionalStats, PlottingStats, RQColumn
# from matplotlib.ticker import LogLocator, LogFormatter
# from plotter.plotstyles import line_styles, bar_styles, box_styles

# x_axis_labels1 = {
#     "0.000003814697265625": "$2^{5}$",
#     "0.00000762939453125": "$2^{6}$",
#     "0.0000152587890625": "$2^{7}$",
#     "0.000030517578125": "$2^{8}$",
#     "0.00006103515625": "$2^{9}$",
#     "0.0001220703125": "$2^{10}$",
#     "0.000244140625": "$2^{11}$",
#     "0.00048828125": "$2^{12}$",
#     "0.0009765625": "$2^{13}$",
#     "0.001953125": "$2^{14}$",
#     "0.00390625": "$2^{15}$",
#     "0.0078125": "$2^{16}$",
#     "0.015625": "$2^{17}$",
#     "0.03125": "$2^{18}$",
#     "0.0625": "$2^{19}$",
#     "0.125": "$2^{20}$",
#     "0.25": "$2^{21}$",
#     "0.5": "$2^{22}$",
# }

# x_axis_labels2 = {
#     "0.000003814697265625": "$\\frac{1}{2^{18}}$",
#     "0.00000762939453125": "$\\frac{1}{2^{17}}$",
#     "0.0000152587890625": "$\\frac{1}{2^{16}}$",
#     "0.000030517578125": "$\\frac{1}{2^{15}}$",
#     "0.00006103515625": "$\\frac{1}{2^{14}}$",
#     "0.0001220703125": "$\\frac{1}{2^{13}}$",
#     "0.000244140625": "$\\frac{1}{2^{12}}$",
#     "0.00048828125": "$\\frac{1}{2^{11}}$",
#     "0.0009765625": "$\\frac{1}{2^{10}}$",
#     "0.001953125": "$\\frac{1}{2^{9}}$",
#     "0.00390625": "$\\frac{1}{2^{8}}$",
#     "0.0078125": "$\\frac{1}{2^{7}}$",
#     "0.015625": "$\\frac{1}{2^{6}}$",
#     "0.03125": "$\\frac{1}{2^{5}}$",
#     "0.0625": "$\\frac{1}{2^{4}}$",
#     "0.125": "$\\frac{1}{2^{3}}$",
#     "0.25": "$\\frac{1}{2^{2}}$",
#     "0.5": "$\\frac{1}{2^{1}}$",
# }

# x_axis_labels = x_axis_labels1
# rotation = 0


# def human_readable_bytes(bytes_val):
#     gb = bytes_val / (1024**3)
#     if gb < 10:
#         return f"{gb:.1f}"
#     else:
#         return f"{gb:.0f}"


# class VaryingRQPlots:
#     vanilla_boxplot_kwargs = {
#         "label": "RocksDB",
#         "showfliers": False,
#         "notch": True,
#         "patch_artist": True,
#         "boxprops": dict(facecolor="grey", edgecolor="black", linewidth=1.5, hatch=""),
#         "medianprops": dict(color="black", linewidth=1.5),
#         "whiskerprops": dict(color="black", linewidth=1),
#         "capprops": dict(color="black", linewidth=1),
#     }
#     rqdc_boxplot_kwargs = {
#         "label": "RangeReduce",
#         "showfliers": False,
#         "notch": True,
#         "patch_artist": True,
#         "boxprops": dict(facecolor="tab:red", edgecolor="black", linewidth=1.5, hatch="x"),
#         "medianprops": dict(color="black", linewidth=1.5),
#         "whiskerprops": dict(color="black", linewidth=1),
#         "capprops": dict(color="black", linewidth=1),
#     }
#     bm_boxplot_kwargs = {
#         "label": "BoundedMerge",
#         "showfliers": False,
#         "notch": True,
#         "patch_artist": True,
#         "boxprops": dict(facecolor="tab:green", edgecolor="black", linewidth=1.5, hatch="--"),
#         "medianprops": dict(color="black", linewidth=1.5),
#         "whiskerprops": dict(color="black", linewidth=1),
#         "capprops": dict(color="black", linewidth=1),
#     }

#     fig_size = (5, 3.8) if self.tag == "overlapping100" else (5, 3.3)

#     def __init__(
#         self,
#         vanilla: List[EpochStats],
#         succinctkv: List[EpochStats],
#         rqdc: List[EpochStats],
#         bm: List[EpochStats],
#         max_lvl_per_epoch: List[List[int]],
#         operation_count: int = 0,
#         epoch_to_plot: int = -1,
#     ):

#         if len(vanilla) != len(rqdc):
#             raise Exception("lengths of vanilla and rqdc stats are not the same")
#         self._vanilla: List[PlottingStats] = deepcopy(
#             [van.get_plotstats(max_lvl_per_epoch[i])[epoch_to_plot] for i, van in enumerate(vanilla, 0)]
#         )
#         self._succinctkv: List[PlottingStats] = deepcopy(
#             [suc.get_plotstats(max_lvl_per_epoch[i])[epoch_to_plot] for i, suc in enumerate(succinctkv, 0)]
#         )
#         self._rqdc: List[PlottingStats] = deepcopy(
#             [rqd.get_plotstats(max_lvl_per_epoch[i])[epoch_to_plot] for i, rqd in enumerate(rqdc, 0)]
#         )
#         self._bm: List[PlottingStats] = deepcopy(
#             [b.get_plotstats(max_lvl_per_epoch[i])[epoch_to_plot] for i, b in enumerate(bm, 0)]
#         )
#         self._vanilla_rq: List[pd.DataFrame] = [
#             van.get_rangequerystats().copy(deep=True) for van in vanilla
#         ]
#         self._succinctkv_rq: List[pd.DataFrame] = [  
#             suc.get_rangequerystats().copy(deep=True) for suc in succinctkv
#         ]
#         self._rqdc_rq: List[pd.DataFrame] = [
#             rqd.get_rangequerystats().copy(deep=True) for rqd in rqdc
#         ]
#         self._bm_rq: List[pd.DataFrame] = [
#             b.get_rangequerystats().copy(deep=True) for b in bm
#         ]
#         self._op_count = operation_count

#     def plot_throughput(self):
#         convert_to_ = 1000**3
#         print([van.WorkloadExecutionTime for van in self._vanilla])
#         vanilla_throughput = [
#             self._op_count / (van.WorkloadExecutionTime / convert_to_)
#             for van in self._vanilla
#         ]
#         succinctkv_throughput = [
#             self._op_count / (suc.WorkloadExecutionTime / convert_to_)
#             for suc in self._succinctkv
#         ]
#         rqdc_throughput = [
#             self._op_count / (rqdc.WorkloadExecutionTime / convert_to_)
#             for rqdc in self._rqdc
#         ]
#         bm_throughput = [
#             self._op_count / (bm.WorkloadExecutionTime / convert_to_)
#             for bm in self._bm
#         ]

#         vanilla_norm = [vanilla_throughput[i] / vanilla_throughput[i] for i in range(len(vanilla_throughput))]
#         succinctkv_norm = [succinctkv_throughput[i] / vanilla_throughput[i] for i in range(len(vanilla_throughput))]
#         rqdc_norm = [rqdc_throughput[i] / vanilla_throughput[i] for i in range(len(vanilla_throughput))]
#         bm_norm = [bm_throughput[i] / vanilla_throughput[i] for i in range(len(vanilla_throughput))]

#         print(self.tag)
#         print(vanilla_norm)
#         print(succinctkv_norm)
#         print(bm_norm)
#         print(rqdc_norm)

#         fig, ax = plt.subplots(figsize=self.fig_size)

#         # ax.plot(rq_perccentage_axises, vanilla_throughput, **line_styles["RocksDB"])
#         # ax.plot(rq_perccentage_axises, rqdc_throughput, **line_styles["RangeReduce[lb=T^-1 & re=1]"])
#         # ax.plot(rq_perccentage_axises, bm_throughput, **line_styles["RangeReduce[lb=T^-1]"])

#         # ax.set_ylabel("throughput (ops/sec)")
#         # # ax.set_xlabel("range query count")
#         # ax.set_yscale("log")
#         # ax.set_ylim(bottom=1e-0, top=1e4)
#         ax.set_xscale("log", base=2)
#         if self.tag == "selectivityplots":
#             ax.set_xticks(rq_perccentage_axises)
#             ax.set_xticklabels([f"" for per in rq_percentages], rotation=rotation)
#         else:
#             ax.set_xlabel("range query count")
#             ax.set_xticks(rq_perccentage_axises[::2])
#             ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages[::2]], rotation=rotation)

#         # ax = ax.twinx()
#         ax.plot(rq_perccentage_axises, vanilla_norm, **line_styles["RocksDB"])
#         ax.plot(rq_perccentage_axises, succinctkv_norm, **line_styles["SuccinctKV"])
#         ax.plot(rq_perccentage_axises, bm_norm, **line_styles["RangeReduce[lb=T^-1]"])
#         ax.plot(rq_perccentage_axises, rqdc_norm, **line_styles["RangeReduce[lb=T^-1 & re=1]"])
#         ax.set_ylabel("norm. throughput")
#         ax.set_ylim(bottom=0)

#         desired_yticks = [0, 0.5, 1, 1.5]
#         desired_norm_yticks = [x for x in desired_yticks]
#         ax.set_yticks(desired_norm_yticks)
#         ax.set_yticklabels([0] + [f"{x:.1f}" for x in desired_yticks[1:]])

#         plt.tight_layout()
#         plt.savefig(f'{self.tag}/throughput.pdf', bbox_inches='tight', pad_inches=0.06)

#         # Create a new figure solely for the legend
#         legend_fig = plt.figure(figsize=(8, 2))

#         # Add your custom text above the legend
#         # legend_text = r"E=128\hspace{1cm}I=8388608\hspace{1cm}U=8388608\hspace{1cm}S=900\hspace{1cm}T=6\hspace{1cm}B=32\hspace{1cm}P=1024"
#         legend_text = (
#             f"M={round((ENTRY_SIZE*ENTRIES_PER_PAGE*NUM_PAGE_PER_FILE)/(1024*1024))}MB\\hspace{{1cm}}"
#             f"E={ENTRY_SIZE}B\\hspace{{1cm}}"
#             f"T={SIZE_RATIO}\\hspace{{1cm}}"
#             f"I={round(INSERTS/1000000, 1)}M\\hspace{{1cm}}"
#             f"S+U={round(UPDATES/1000000, 1)}M\\hspace{{1cm}}"
#             # f"S={round(RANGE_QUERIES/1000)}K\\hspace{{1cm}}"
#             f"s={SELECTIVITY}\\hspace{{1cm}}"
#             # f"B={ENTRIES_PER_PAGE}\\hspace{{1cm}}"
#             # f"P={NUM_PAGE_PER_FILE}"
#         )
#         if self.tag == "overlapping100":
#             legend_text = "\\hspace{1cm}every 100 RQs are identical"
#         legend_fig.text(0.5, 0.85, legend_text, ha='center', va='center')
#         legend_fig.savefig(f'{self.tag}/experimental-legend-config.pdf', bbox_inches='tight', pad_inches=0.015)

#         # Get legend handles and labels from both axes
#         handles1, labels1 = ax.get_legend_handles_labels()     # Absolute throughput lines
#         # handles2, labels2 = ax2.get_legend_handles_labels()     # Normalized lines (unfilled markers)

#         # labels2 = [f"{label} (normalized)" for label in labels2]

#         # Combine them
#         combined_handles = handles1 #+ handles2
#         combined_labels = labels1 #+ labels2

#         # Create a new figure solely for the combined legend
#         legend_fig = plt.figure(figsize=(10, 2))

#         # Add combined legend (2 rows or 2 columns depending on your preference)
#         legend_fig.legend(combined_handles, combined_labels, loc="center", ncol=5, frameon=False, borderaxespad=0, labelspacing=0, 
#                     borderpad=0)
#         # Save the legend figure separately; bbox_inches='tight' helps crop extra whitespace.
#         legend_fig.savefig(f'{self.tag}/experimental.pdf', bbox_inches='tight', pad_inches=0.015)
#         # plt.show()

#     def plot_range_query_latency(self):
#         convert_to_ = 10**9
#         vanilla_rq_times = [df[str(RQColumn.RQ_TOTAL_TIME)] for df in self._vanilla_rq]
#         rqdc_rq_times = [df[str(RQColumn.RQ_TOTAL_TIME)] for df in self._rqdc_rq]
#         bm_rq_times = [df[str(RQColumn.RQ_TOTAL_TIME)] for df in self._bm_rq]

#         x_positions = np.arange(len(rq_percentages))

#         # Compute average latencies (in seconds)
#         vanilla_means = [np.mean(data) for data in vanilla_rq_times]
#         rqdc_means = [np.mean(data) for data in rqdc_rq_times]
#         bm_means = [np.mean(data) for data in bm_rq_times]

#         fig, ax = plt.subplots(figsize=self.fig_size)

#         # Plot average latencies as simple lines
#         ax.plot(x_positions, vanilla_means, **line_styles["RocksDB"])
#         ax.plot(x_positions, bm_means, **line_styles["RangeReduce[lb=T^-1]"])
#         ax.plot(x_positions, rqdc_means, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

#         # Set axis labels and ticks
#         ax.set_ylabel("avg. RQ latency (sec)")
#         # ax.set_xlabel("range query count")
#         ax.set_ylim(bottom=0)
#         if self.tag == "selectivityplots":
#             ax.set_xticks(x_positions)
#             ax.set_xticklabels([f"" for per in rq_percentages], rotation=rotation)
#         else:
#             ax.set_xlabel("range query count")
#             ax.set_xticks(x_positions)
#             ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages], rotation=rotation)

#         # ax.set_xticks(x_positions)
#         # ax.set_xticklabels([x_axis_labels[i] for i in rq_percentages], rotation=rotation)
#         desired_yticks = [0, 1, 2]
#         desired_sec_yticks = [x * convert_to_ for x in desired_yticks]
#         ax.set_yticks(desired_sec_yticks)
#         ax.set_yticklabels(['0'] + [f"{x}" for x in desired_yticks[1:]])

#         # ax.legend(loc='upper left', frameon=False)
#         plt.tight_layout()
#         plt.savefig(f'{self.tag}/range_query_latency.pdf', bbox_inches='tight', pad_inches=0.06)
#         plt.show()

#     def plot_range_query_box_plot_latency(self):
#         convert_to_ = 10**9

#         vanilla_rq_times = [df[str(RQColumn.RQ_TOTAL_TIME)] for df in self._vanilla_rq]
#         succinct_kv_rq_times = [df[str(RQColumn.RQ_TOTAL_TIME)] for df in self._succinctkv_rq]
#         # bm_rq_times = [df[str(RQColumn.RQ_TOTAL_TIME)] for df in self._bm_rq]
#         rqdc_rq_times = [df[str(RQColumn.RQ_TOTAL_TIME)] for df in self._rqdc_rq]

#         x_positions = np.arange(len(rq_percentages))
#         width = 0.22  # slightly smaller since we now have 4 boxes
#         offsets = [-width, 0, +width]

#         fig, ax = plt.subplots(figsize=(4.6, 3.8))
#         mpl.rcParams["hatch.linewidth"] = 0.5 
#         # RocksDB
#         ax.boxplot(
#             vanilla_rq_times,
#             positions=x_positions - 0.25 + offsets[0],
#             widths=width,
#             whis=(0,95),
#             patch_artist=True,
#             boxprops=box_styles["RocksDB"],
#             medianprops=dict(color="black"),
#             showfliers=False
#         )

#         # SuccinctKV
#         ax.boxplot(
#             succinct_kv_rq_times,
#             positions=x_positions + offsets[0],
#             widths=width,
#              whis=(0,95),
#             patch_artist=True,
#             boxprops=box_styles["SuccinctKV"],
#             medianprops=dict(color="black"),
#             showfliers=False
#         )

#         # # RangeReduce (lb = T^-1)
#         # ax.boxplot(
#         #     bm_rq_times,
#         #     positions=x_positions + 0.5 * (width),
#         #     widths=width,
#         #      whis=(0,95),
#         #     patch_artist=True,
#         #     boxprops=box_styles["RangeReduce[lb=T^-1]"],
#         #     medianprops=dict(color="black"),
#         #     showfliers=False
#         # )

#         # RangeReduce (lb = T^-1, re = 1)
#         ax.boxplot(
#             rqdc_rq_times,
#             positions=x_positions + 0.25 + offsets[0],
#             widths=width,
#              whis=(0,95),
#             patch_artist=True,
#             boxprops=box_styles["RangeReduce[lb=T^-1 & re=1]"],
#             medianprops=dict(color="black"),
#             showfliers=False
#         )

#         # Axis labels
#         ax.set_ylabel("RQ latency (sec)")
#         ax.yaxis.set_label_coords(-0.12, 0.45)
#         ax.set_ylim(bottom=0)

#         legend_handles = [
#             Patch(
#                 facecolor=box_styles["RocksDB"]["facecolor"],
#                 hatch=box_styles["RocksDB"]["hatch"],
#                 edgecolor="none",
#                 label="RocksDB",
#             ),
#             Patch(
#                 facecolor=box_styles["SuccinctKV"]["facecolor"],
#                 hatch=box_styles["SuccinctKV"]["hatch"],
#                 edgecolor="none",
#                 label="SuccinctKV",
#             ),
#             # Patch(
#             #     facecolor=box_styles["RangeReduce[lb=T^-1]"]["facecolor"],
#             #     hatch=box_styles["RangeReduce[lb=T^-1]"]["hatch"],
#             #     edgecolor="black",
#             #     label="Bounded-Merge",
#             # ),
#             Patch(
#                 facecolor=box_styles["RangeReduce[lb=T^-1 & re=1]"]["facecolor"],
#                 hatch=box_styles["RangeReduce[lb=T^-1 & re=1]"]["hatch"],
#                 edgecolor="none",
#                 label="RangeReduce",
#             ),
#         ]

#         ax.legend(
#             handles=legend_handles,
#             ncol=2,
#             loc=(0.005, -0.01), frameon=False,
#             columnspacing=0.2, handletextpad=0.1, handlelength=1.0, handleheight=0.7,
#             fontsize=17.5
#         )

#         if self.tag == "selectivityplots":
#             ax.set_xticks(x_positions)
#             ax.set_xticklabels(["" for _ in rq_percentages], rotation=rotation)
#         else:
#             ax.set_xlabel("range query count")
#             ax.set_xticks(x_positions)
#             ax.set_xticklabels(
#                 [f"{x_axis_labels[per]}" for per in rq_percentages],
#                 rotation=rotation
#             )

#         # Y-axis ticks
#         desired_yticks = [0, 0.5, 1, 1.5]
#         ax.set_yticks([x * convert_to_ for x in desired_yticks])
#         ax.set_yticklabels([str(x) for x in desired_yticks])

#         plt.tight_layout()
#         plt.savefig(f'{self.tag}/range_query_latency_boxplot.pdf',
#                     bbox_inches='tight', pad_inches=0.06)
#         plt.close(fig)

#     # def plot_range_query_latency(self):
#     #     convert_to_ = 10**9
#     #     vanilla_rq_times = [
#     #         df[str(RQColumn.RQ_TOTAL_TIME)] for df in self._vanilla_rq
#     #     ]
#     #     rqdc_rq_times = [
#     #         df[str(RQColumn.RQ_TOTAL_TIME)] for df in self._rqdc_rq
#     #     ]
#     #     bm_rq_times = [
#     #         df[str(RQColumn.RQ_TOTAL_TIME)] for df in self._bm_rq
#     #     ]

#     #     n = len(vanilla_rq_times)
#     #     x_positions = np.arange(n)
#     #     offset = 0.2
#     #     width = 0.15

#     #     fig, ax = plt.subplots(figsize=self.fig_size)

#     #     # Boxplots
#     #     ax.boxplot(
#     #         vanilla_rq_times,
#     #         positions=x_positions - offset,
#     #         widths=width,
#     #         whis=[0, 99],
#     #         **self.vanilla_boxplot_kwargs,
#     #     )

#     #     ax.boxplot(
#     #         bm_rq_times,
#     #         positions=x_positions,
#     #         widths=width,
#     #         whis=[0, 99],
#     #         **self.bm_boxplot_kwargs,
#     #     )
#     #     ax.boxplot(
#     #         rqdc_rq_times,
#     #         positions=x_positions + offset,
#     #         widths=width,
#     #         whis=[0, 99],
#     #         **self.rqdc_boxplot_kwargs,
#     #     )

#     #     # Calculate means for each box plot
#     #     vanilla_means = [np.mean(data) for data in vanilla_rq_times]
#     #     rqdc_means = [np.mean(data) for data in rqdc_rq_times]
#     #     bm_means = [np.mean(data) for data in bm_rq_times]

#     #     ax.plot(x_positions - offset, vanilla_means, **line_styles["RocksDB"])
#     #     ax.plot(x_positions, bm_means, **line_styles["RangeReduce[lb=T^-1]"])
#     #     ax.plot(x_positions + offset, rqdc_means, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

#     #     desired_yticks = [0, 1, 2]
#     #     desired_sec_yticks = [x * convert_to_ for x in desired_yticks]
#     #     ax.set_yticks(desired_sec_yticks)
#     #     ax.set_yticklabels([0] + [f"{x}" for x in desired_yticks[1:]])

#     #     # Set labels and legend
#     #     ax.set_xticks(x_positions)
#     #     ax.set_xticklabels([f"{x_axis_labels[i]}" for i in rq_percentages], rotation=rotation)

#     #     ax.tick_params(axis='y')
#     #     ax.set_ylabel("RQ latency (sec)")
#     #     ax.set_xlabel("range query count")
#     #     ax.set_ylim(bottom=0)
#     #     ax.text(
#     #         0.5, 0.08,  # Adjust based on your plot layout
#     #         "shows 0 to 99th percentile",
#     #         transform=ax.transAxes,
#     #         fontsize=12,
#     #         ha="center",
#     #         va="center",
#     #         bbox=dict(edgecolor="none", facecolor="white", alpha=0.8)
#     #     )
#     #     # ax.legend(loc="lower center", bbox_to_anchor=(0.5, 0.09), frameon=False, ncol=2)

#     #     plt.tight_layout()
#     #     plt.savefig(f'{self.tag}/range_query_latency.pdf', bbox_inches='tight', pad_inches=0.06)
#     #     plt.show()

#     def plot_compaction_debt(self):
#         convert_to_ = 1024**3
#         vanilla_compaction_debt = [
#             van.CompactionDebt for van in self._vanilla
#         ]
#         succinctkv_compaction_debt = [
#             suc.CompactionDebt for suc in self._succinctkv
#         ]
#         rqdc_compaction_debt = [rqd.CompactionDebt for rqd in self._rqdc]
#         bm_compaction_debt = [b.CompactionDebt for b in self._bm]

#         print([human_readable_bytes(x) for x in vanilla_compaction_debt])
#         print([human_readable_bytes(x) for x in succinctkv_compaction_debt])
#         print([human_readable_bytes(x) for x in bm_compaction_debt])
#         print([human_readable_bytes(x) for x in rqdc_compaction_debt])

#         fig, ax = plt.subplots(figsize=self.fig_size)
#         ax.plot(rq_perccentage_axises, vanilla_compaction_debt, **line_styles["RocksDB"])
#         ax.plot(rq_perccentage_axises, succinctkv_compaction_debt, **line_styles["SuccinctKV"])
#         ax.plot(rq_perccentage_axises, rqdc_compaction_debt, **line_styles["RangeReduce[lb=T^-1 & re=1]"])
#         ax.plot(rq_perccentage_axises, bm_compaction_debt, **line_styles["RangeReduce[lb=T^-1]"])

#         ax.set_ylabel("compaction debt (GB)")
#         if self.tag != "selectivityplots":
#             ax.yaxis.set_label_coords(-0.1, 0.45)
#         # ax.set_xlabel("range query count")
#         ax.set_ylim(bottom=0)
#         ax.tick_params(axis='y')
#         ax.set_xscale("log", base=2)
#         if self.tag == "selectivityplots":
#             ax.set_xticks(rq_perccentage_axises[::2])
#             ax.set_xticklabels([f"" for per in rq_percentages[::2]], rotation=rotation)
#         else:
#             ax.set_xlabel("range query count")
#             ax.set_xticks(rq_perccentage_axises[::2])
#             ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages[::2]], rotation=rotation)

#         desired_yticks = [0, 5, 10, 15]
#         desired_gb_yticks = [x * convert_to_ for x in desired_yticks]
#         ax.set_yticks(desired_gb_yticks)
#         ax.set_yticklabels([0] + [f"{x}" for x in desired_yticks[1:]])

#         # ax.set_xticks(rq_perccentage_axises)
#         # ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages], rotation=rotation)
#         plt.tight_layout()
#         plt.savefig(f'{self.tag}/compaction_debt.pdf', bbox_inches='tight', pad_inches=0.06)
#         # plt.show()

#     def plot_wkl_exec_time(self):
#         convert_to_ = 1000**3
#         to_hours = 60 * 60
#         vanilla_wkl_exec_time = [
#             (van.WorkloadExecutionTime / convert_to_) / to_hours
#             for van in self._vanilla
#         ]
#         rqdc_wkl_exec_time = [
#             (rqd.WorkloadExecutionTime / convert_to_) / to_hours for rqd in self._rqdc
#         ]
#         bm_wkl_exec_time = [
#             (b.WorkloadExecutionTime / convert_to_) / to_hours for b in self._bm
#         ]

#         fig, ax = plt.subplots(figsize=self.fig_size)
#         ax.plot(rq_perccentage_axises, vanilla_wkl_exec_time, **line_styles["RocksDB"])
#         ax.plot(rq_perccentage_axises, rqdc_wkl_exec_time, **line_styles["RangeReduce[lb=T^-1 & re=1]"])
#         ax.plot(rq_perccentage_axises, bm_wkl_exec_time, **line_styles["RangeReduce[lb=T^-1]"])

#         ax.set_ylabel("execution time (hrs)")
#         # ax.set_xlabel("range query count")
#         ax.set_ylim(bottom=0)
#         ax.tick_params(axis='y')
#         ax.set_xscale("log", base=2)
#         # ax.set_xticks(rq_perccentage_axises)
#         # ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages], rotation=rotation)
#         if self.tag == "selectivityplots":
#             ax.set_xticks(rq_perccentage_axises[::2])
#             ax.set_xticklabels([f"" for per in rq_percentages[::2]], rotation=rotation)
#         else:
#             ax.set_xlabel("range query count")
#             ax.set_xticks(rq_perccentage_axises[::2])
#             ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages[::2]], rotation=rotation)

#         plt.tight_layout()
#         plt.savefig(f'{self.tag}/wkl_execution_time.pdf', bbox_inches='tight', pad_inches=0.06)
#         plt.show()

#     def plot_space_amp(self):
#         vanilla_space_amp = [
#             van.DBSize / (INSERTS * (ENTRY_SIZE))
#             for van in self._vanilla
#         ]
#         succinctkv_space_amp = [
#             suc.DBSize / (INSERTS * (ENTRY_SIZE))
#             for suc in self._succinctkv
#         ]
#         rqdc_space_amp = [
#             rqd.DBSize / (INSERTS * (ENTRY_SIZE))
#             for rqd in self._rqdc
#         ]
#         bm_space_amp = [
#             b.DBSize / (INSERTS * (ENTRY_SIZE))
#             for b in self._bm
#         ]

#         print(vanilla_space_amp)
#         print(succinctkv_space_amp)
#         print(bm_space_amp)
#         print(rqdc_space_amp)

#         fig, ax = plt.subplots(figsize=self.fig_size)
#         ax.plot(rq_perccentage_axises, vanilla_space_amp, **line_styles["RocksDB"])
#         ax.plot(rq_perccentage_axises, succinctkv_space_amp, **line_styles["SuccinctKV"])
#         ax.plot(rq_perccentage_axises, rqdc_space_amp, **line_styles["RangeReduce[lb=T^-1 & re=1]"])
#         ax.plot(rq_perccentage_axises, bm_space_amp, **line_styles["RangeReduce[lb=T^-1]"])

#         ax.set_ylabel("space amplification")
#         # ax.set_xlabel("range query count")
#         ax.set_ylim(bottom=0, top=max(vanilla_space_amp) + 0.5)
#         ax.tick_params(axis='y')
#         ax.set_xscale("log", base=2)
#         if self.tag == "selectivityplots":
#             ax.set_xticks(rq_perccentage_axises[::2])
#             ax.set_xticklabels([f"" for per in rq_percentages[::2]], rotation=rotation)
#         else:
#             ax.set_xlabel("range query count")
#             ax.set_xticks(rq_perccentage_axises[::2])
#             ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages[::2]], rotation=rotation)

#         desired_yticks = [0, 0.5, 1, 1.5, 2]
#         ax.set_yticks(desired_yticks)
#         ax.set_yticklabels([0] + [f"{x:.1f}" for x in desired_yticks[1:]])
#         # ax.set_xticks(rq_perccentage_axises)
#         # ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages], rotation=rotation)
#         plt.tight_layout()
#         plt.savefig(f'{self.tag}/space_amplification.pdf', bbox_inches='tight', pad_inches=0.06)
#         # plt.show()

#     # def plot_space_amp(self):
#     #     vanilla_space_amp = [
#     #         van.DBSize / (INSERTS * (ENTRY_SIZE))
#     #         for van in self._vanilla
#     #     ]
#     #     rqdc_space_amp = [
#     #         rqd.DBSize / (INSERTS * (ENTRY_SIZE))
#     #         for rqd in self._rqdc
#     #     ]

#     #     x_points = range(len(rq_percentages))
#     #     fig, ax = plt.subplots(figsize=self.fig_size)
#     #     ax.plot(rq_perccentage_axises, vanilla_space_amp, **line_styles["RocksDB"])
#     #     ax.plot(rq_perccentage_axises, rqdc_space_amp, **line_styles["RangeReduce[lb=T^-1 & re=1]"])

#     #     ax.set_ylabel("space amp")
#     #     ax.set_xlabel("range query count")
#     #     ax.set_ylim(bottom=0, top=max(vanilla_space_amp) + 0.5)

#     #     ax.set_xticks(rq_percentages)
#     #     ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages], rotation=rotation)
#     #     ax.tick_params(axis='y')

#     #     fig.legend(
#     #         loc="lower center",
#     #         ncol=2,
#     #         frameon=False,
#     #         bbox_to_anchor=(0.5, 0.1),
#     #     )
#     #     plt.show()

#     def plot_total_bytes_written(self):
#         convert_to_ = 1024**3
#         vanilla_writes = [
#             (van.CompactionWrittenBytes + van.RangeReduceWrittenBytes)
#             for van in self._vanilla
#         ]
#         rqdc_writes = [
#             (rqdc.CompactionWrittenBytes + rqdc.RangeReduceWrittenBytes)
#             for rqdc in self._rqdc
#         ]
#         bm_writes = [
#             (b.CompactionWrittenBytes + b.RangeReduceWrittenBytes)
#             for b in self._bm
#         ]

#         fig, ax = plt.subplots(figsize=self.fig_size)
#         ax.plot(rq_perccentage_axises, vanilla_writes, **line_styles["RocksDB"])
#         ax.plot(rq_perccentage_axises, rqdc_writes, **line_styles["RangeReduce[lb=T^-1 & re=1]"])
#         ax.plot(rq_perccentage_axises, bm_writes, **line_styles["RangeReduce[lb=T^-1]"])

#         ax.set_ylabel("total writes (GB)")
#         # ax.set_xlabel("range query count")
#         # ax.set_ylim(bottom=0, top=max(vanilla_writes) + 0.5)
#         ax.tick_params(axis='y')
#         ax.set_xscale("log", base=2)
#         if self.tag == "selectivityplots":
#             ax.set_xticks(rq_perccentage_axises[::2])
#             ax.set_xticklabels([f"" for per in rq_percentages[::2]], rotation=rotation)
#         else:
#             ax.set_xlabel("range query count")
#             ax.set_xticks(rq_perccentage_axises[::2])
#             ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages[::2]], rotation=rotation)
#         desired_yticks = [0, 25, 50, 75]
#         desired_gb_yticks = [x * convert_to_ for x in desired_yticks]
#         ax.set_yticks(desired_gb_yticks)
#         ax.set_yticklabels([0] + [f"{x}" for x in desired_yticks[1:]])

#         # ax.set_xticks(rq_perccentage_axises)
#         # ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages], rotation=rotation)
#         plt.tight_layout()
#         plt.savefig(f'{self.tag}/total_bytes_written.pdf', bbox_inches='tight', pad_inches=0.06)
#         plt.show()

#     def plot_overall_datamovement(self):
#         convert_to_ = 1024**4
#         vanilla_rq_read = [
#             df[str(RQColumn.TOTAL_ENTRIES_READ)].sum() * ENTRY_SIZE
#             for df in self._vanilla_rq
#         ]
#         succinctkv_rq_read = [
#             df[str(RQColumn.TOTAL_ENTRIES_READ)].sum() * ENTRY_SIZE
#             for df in self._succinctkv_rq
#         ]
#         rqdc_rq_read = [
#             df[str(RQColumn.TOTAL_ENTRIES_READ)].sum() * ENTRY_SIZE
#             for df in self._rqdc_rq
#         ]
#         bm_rq_read = [
#             df[str(RQColumn.TOTAL_ENTRIES_READ)].sum() * ENTRY_SIZE
#             for df in self._bm_rq
#         ]
#         vanilla_comp_read_write = [
#             (van.CompactionReadBytes + van.CompactionWrittenBytes)
#             for van in self._vanilla
#         ]
#         succinctkv_comp_read_write = [
#             (suc.CompactionReadBytes + suc.CompactionWrittenBytes)
#             for suc in self._succinctkv
#         ]
#         rqdc_comp_read_write = [
#             (rqdc.CompactionReadBytes + rqdc.CompactionWrittenBytes)
#             for rqdc in self._rqdc
#         ]
#         bm_comp_read_write = [
#             (b.CompactionReadBytes + b.CompactionWrittenBytes)
#             for b in self._bm
#         ]
#         rqdc_rq_write = [rqdc.RangeReduceWrittenBytes for rqdc in self._rqdc]
#         bm_rq_write = [b.RangeReduceWrittenBytes for b in self._bm]

#         vanilla_datamov = [
#             (vanilla_rq_read[i] + vanilla_comp_read_write[i]) / convert_to_
#             for i in range(len(vanilla_rq_read))
#         ]
#         succinctkv_datamov = [
#             (succinctkv_rq_read[i] + succinctkv_comp_read_write[i]) / convert_to_
#             for i in range(len(succinctkv_rq_read))
#         ]
#         rqdc_datamov = [
#             (rqdc_rq_read[i] + rqdc_comp_read_write[i] + rqdc_rq_write[i]) / convert_to_
#             for i in range(len(rqdc_rq_write))
#         ]
#         bm_datamov = [
#             (bm_rq_read[i] + bm_comp_read_write[i] + bm_rq_write[i]) / convert_to_
#             for i in range(len(bm_rq_write))
#         ]

#         vanilla_norm = [vanilla_datamov[i] / vanilla_datamov[i] for i in range(len(vanilla_datamov))]
#         succinctkv_norm = [succinctkv_datamov[i] / vanilla_datamov[i] for i in range(len(vanilla_datamov))]
#         rqdc_norm = [rqdc_datamov[i] / vanilla_datamov[i] for i in range(len(vanilla_datamov))]
#         bm_norm = [bm_datamov[i] / vanilla_datamov[i] for i in range(len(vanilla_datamov))]

#         print(self.tag)
#         print(vanilla_norm)
#         print(succinctkv_norm)
#         print(bm_norm)
#         print(rqdc_norm)

#         x_points = range(len(rq_percentages))
#         fig, ax = plt.subplots(figsize=self.fig_size)
#         # ax.plot(rq_perccentage_axises, vanilla_datamov, **line_styles["RocksDB"])
#         # ax.plot(rq_perccentage_axises, rqdc_datamov, **line_styles["RangeReduce[lb=T^-1 & re=1]"])
#         # ax.plot(rq_perccentage_axises, bm_datamov, **line_styles["RangeReduce[lb=T^-1]"])

#         # ax.set_ylabel("data movement (TB)")
#         # # ax.set_xlabel("range query count")
#         # ax.set_ylim(bottom=0, top=max(vanilla_datamov) + max(vanilla_datamov) * 0.02)
#         # # ax.set_yscale('log')
#         # ax.tick_params(axis='y')
#         ax.set_xscale("log", base=2)
#         # ax.set_xticks(rq_perccentage_axises)
#         # ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages], rotation=rotation)
#         if self.tag == "selectivityplots":
#             ax.set_xticks(rq_perccentage_axises[::2])
#             ax.set_xticklabels([f"" for per in rq_percentages[::2]], rotation=rotation)
#         else:
#             ax.set_xlabel("range query count")
#             ax.set_xticks(rq_perccentage_axises[::2])
#             ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages[::2]], rotation=rotation)

#         # ax = ax.twinx()
#         ax.plot(rq_perccentage_axises, vanilla_norm, **line_styles["RocksDB"])
#         ax.plot(rq_perccentage_axises, succinctkv_norm, **line_styles["SuccinctKV"])
#         ax.plot(rq_perccentage_axises, rqdc_norm, **line_styles["RangeReduce[lb=T^-1 & re=1]"])
#         ax.plot(rq_perccentage_axises, bm_norm, **line_styles["RangeReduce[lb=T^-1]"])
#         ax.set_ylabel("norm. data movement")
#         if self.tag == "overlapping100":
#             ax.yaxis.label.set_position((1.1, 0.45))
#         ax.set_ylim(bottom=0)

#         desired_yticks = [0, 0.5, 1, 1.5]
#         desired_norm_yticks = [x for x in desired_yticks]
#         ax.set_yticks(desired_norm_yticks)
#         ax.set_yticklabels([0] + [f"{x:.1f}" for x in desired_yticks[1:]])
#         # ax2.legend(loc='upper left', bbox_to_anchor=(0.1, 0.9), frameon=False)

#         plt.tight_layout()
#         plt.savefig(f'{self.tag}/overall_data_movement.pdf', bbox_inches='tight', pad_inches=0.06)
#         # plt.show()

#     def plot_total_bytes_read(self):
#         convert_to_ = 1024**4
#         vanilla_rq_read = [
#             df[str(RQColumn.TOTAL_ENTRIES_READ)].sum() * ENTRY_SIZE
#             for df in self._vanilla_rq
#         ]
#         rqdc_rq_read = [
#             df[str(RQColumn.TOTAL_ENTRIES_READ)].sum() * ENTRY_SIZE
#             for df in self._rqdc_rq
#         ]
#         bm_rq_read = [
#             df[str(RQColumn.TOTAL_ENTRIES_READ)].sum() * ENTRY_SIZE
#             for df in self._bm_rq
#         ]
#         vanilla_comp_read = [(van.CompactionReadBytes) for van in self._vanilla]
#         rqdc_comp_read = [(rqdc.CompactionReadBytes) for rqdc in self._rqdc]
#         bm_comp_read = [(b.CompactionReadBytes) for b in self._bm]
#         # rqdc_rq_write = [rqdc.RangeReduceWrittenBytes for rqdc in self._rqdc]

#         vanilla_datamov = [
#             (vanilla_rq_read[i] + vanilla_comp_read[i])
#             for i in range(len(vanilla_rq_read))
#         ]
#         rqdc_datamov = [
#             (rqdc_rq_read[i] + rqdc_comp_read[i])
#             for i in range(len(rqdc_comp_read))
#         ]
#         bm_datamov = [
#             (bm_rq_read[i] + bm_comp_read[i])
#             for i in range(len(bm_comp_read))
#         ]

#         fig, ax = plt.subplots(figsize=self.fig_size)
#         ax.plot(rq_perccentage_axises, vanilla_datamov, **line_styles["RocksDB"])
#         ax.plot(rq_perccentage_axises, rqdc_datamov, **line_styles["RangeReduce[lb=T^-1 & re=1]"])
#         ax.plot(rq_perccentage_axises, bm_datamov, **line_styles["RangeReduce[lb=T^-1]"])

#         ax.set_ylabel("total read (TB)")
#         # ax.set_xlabel("range query count")
#         ax.set_ylim(bottom=0, top=max(vanilla_datamov) + max(vanilla_datamov) * 0.02)
#         # ax.set_yscale('log')
#         ax.tick_params(axis='y')
#         ax.set_xscale("log", base=2)
#         if self.tag == "selectivityplots":
#             ax.set_xticks(rq_perccentage_axises[::2])
#             ax.set_xticklabels([f"" for per in rq_percentages[::2]], rotation=rotation)
#         else:
#             ax.set_xlabel("range query count")
#             ax.set_xticks(rq_perccentage_axises[::2])
#             ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages[::2]], rotation=rotation)
#         desired_yticks = [0, 5, 10, 15]
#         desired_tb_yticks = [x * convert_to_ for x in desired_yticks]
#         ax.set_yticks(desired_tb_yticks)
#         ax.set_yticklabels([0] + [f"{x}" for x in desired_yticks[1:]])

#         # ax.set_xticks(rq_perccentage_axises)
#         # ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages], rotation=rotation)
#         plt.tight_layout()
#         plt.savefig(f'{self.tag}/total_bytes_read.pdf', bbox_inches='tight', pad_inches=0.06)
#         plt.show()

#     def plot_total_bytes_written_in_compactions(self):
#         convert_to_ = 1024**3
#         vanilla_writes = [
#             (van.CompactionWrittenBytes) / convert_to_ for van in self._vanilla
#         ]
#         rqdc_writes = [
#             (rqdc.CompactionWrittenBytes) / convert_to_ for rqdc in self._rqdc
#         ]
#         bm_writes = [
#             (b.CompactionWrittenBytes) / convert_to_ for b in self._bm
#         ]

#         x_points = range(len(rq_percentages))
#         fig, ax = plt.subplots(figsize=self.fig_size)
#         ax.plot(rq_perccentage_axises, vanilla_writes, **line_styles["RocksDB"])
#         ax.plot(rq_perccentage_axises, rqdc_writes, **line_styles["RangeReduce[lb=T^-1 & re=1]"])
#         ax.plot(rq_perccentage_axises, bm_writes, **line_styles["RangeReduce[lb=T^-1]"])

#         ax.set_ylabel("writes (GB)")
#         # ax.set_xlabel("range query count")
#         ax.set_ylim(bottom=0, top=max(vanilla_writes) + 0.5)
#         ax.set_title("compactions triggered on level saturation")
#         ax.tick_params(axis='y')
#         ax.set_xscale("log", base=2)
#         if self.tag == "selectivityplots":
#             ax.set_xticks(rq_perccentage_axises[::2])
#             ax.set_xticklabels([f"" for per in rq_percentages[::2]], rotation=rotation)
#         else:
#             ax.set_xlabel("range query count")
#             ax.set_xticks(rq_perccentage_axises[::2])
#             ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages[::2]], rotation=rotation)
#         # ax.set_xticks(rq_perccentage_axises)
#         # ax.set_xticklabels([f"{x_axis_labels[per]}" for per in rq_percentages], rotation=rotation)
#         plt.tight_layout()
#         plt.savefig(f'{self.tag}/compaction_writes_on_level_saturation.pdf', bbox_inches='tight', pad_inches=0.06)
#         plt.show()