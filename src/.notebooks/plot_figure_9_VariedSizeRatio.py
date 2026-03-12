import os
import re
from typing import List
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib
import matplotlib.patches as mpatches
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

from plotter import *
from plotter.epochstats import EpochStats
from plotter.dataclass import AdditionalStats, PlottingStats, RQColumn
from plotter.utils import vanilla_dirname, rqdc_dirname
from plotter.plotstyles import line_styles_with_abbr, bar_styles
# from plotter.paperplots import PaperPlots

PROJECT_DIR = Path.cwd().parent.parent

prop = font_manager.FontProperties(fname="./plotter/LinLibertine_Mah.ttf")
plt.rcParams['font.family'] = prop.get_name()
plt.rcParams['text.usetex'] = True
plt.rcParams['font.weight'] = 'bold'
plt.rcParams['font.size'] = 22

TAG = "diff_size_ratio"

rocksdb_stats = dict()
succinct_kv_stats = dict()
bounded_merge_stats = dict()
rangereduce_stats = dict()
rocksdb_rq_stats = dict()
succinct_kv_rq_stats = dict()
bounded_merge_rq_stats = dict()
rangereduce_rq_stats = dict()

if TAG == "overlapdiffsizeratio":
    fig_size = (5, 3.8)
else:
    fig_size = (5, 3)

size_ratios = [2, 4, 6, 8, 10]
bar_width = 0.25
_op_count = INSERTS + UPDATES + RANGE_QUERIES

for size_ratio in size_ratios:
    EXPDIRNAME = f"{PROJECT_DIR}/.vstats_old/experiments-{TAG}-U{UPDATES}-E{ENTRY_SIZE}-B{ENTRIES_PER_PAGE}-S{RANGE_QUERIES}-Y{SELECTIVITY}-T{size_ratio}"
    rocksdb_path = os.path.join(EXPDIRNAME, "RocksDB")
    succinct_kv_path = os.path.join(EXPDIRNAME, "RangeReduce[lb=0]")
    boudned_merge_path = os.path.join(EXPDIRNAME, "RangeReduce[lb=T^-1]")
    rangereduce_path = os.path.join(EXPDIRNAME, "RangeReduce[lb=T^-1ANDre=1]")

    filesize = ENTRY_SIZE * ENTRIES_PER_PAGE * NUM_PAGE_PER_FILE

    rocksdb = EpochStats(rocksdb_path, NUMEPOCHS, filesize)
    succtint_kv = EpochStats(succinct_kv_path, 10, filesize)
    boudned_merge = EpochStats(boudned_merge_path, NUMEPOCHS, filesize)
    rangereduce = EpochStats(rangereduce_path, NUMEPOCHS, filesize)

    rocksdb_stats[size_ratio] = rocksdb.get_plotstats()[-1:] # only last epoch
    succinct_kv_stats[size_ratio] = succtint_kv.get_plotstats()[-1:]
    bounded_merge_stats[size_ratio] = boudned_merge.get_plotstats()[-1:]
    rangereduce_stats[size_ratio] = rangereduce.get_plotstats()[-1:]

    rocksdb_rq_stats[size_ratio] = rocksdb.get_rangequerystats()
    succinct_kv_rq_stats[size_ratio] = succtint_kv.get_rangequerystats()
    bounded_merge_rq_stats[size_ratio] = boudned_merge.get_rangequerystats()
    rangereduce_rq_stats[size_ratio] = rangereduce.get_rangequerystats()


def plot_compaction_only():
    convert_to_ = 1024**4
    fig, ax = plt.subplots(figsize=(fig_size[0], fig_size[1]))

    rocksdb_comp_read = []
    rocksdb_comp_write = []
    succinct_kv_comp_read = []
    succinct_kv_comp_write = []
    bounded_merge_comp_read = []
    bounded_merge_comp_write = []
    rangereduce_comp_read = []
    rangereduce_comp_write = []

    for size_ratio in size_ratios:
        # RocksDB
        rocksdb_comp_read.append(sum(v.CompactionReadBytes for v in rocksdb_stats[size_ratio]))
        rocksdb_comp_write.append(sum(v.CompactionWrittenBytes for v in rocksdb_stats[size_ratio]))
        r_total = rocksdb_comp_read[-1] + rocksdb_comp_write[-1]

        # SuccinctKV
        succinct_kv_comp_read.append(sum(s.CompactionReadBytes for s in succinct_kv_stats[size_ratio]))
        succinct_kv_comp_write.append(sum(s.CompactionWrittenBytes for s in succinct_kv_stats[size_ratio]))
        skv_total = succinct_kv_comp_read[-1] + succinct_kv_comp_write[-1]

        # BoundedMerge
        bounded_merge_comp_read.append(sum(b.CompactionReadBytes for b in bounded_merge_stats[size_ratio]))
        bounded_merge_comp_write.append(sum(b.CompactionWrittenBytes for b in bounded_merge_stats[size_ratio]))
        b_total = bounded_merge_comp_read[-1] + bounded_merge_comp_write[-1]

        # RQDC
        rangereduce_comp_read.append(sum(r.CompactionReadBytes for r in rangereduce_stats[size_ratio]))
        rangereduce_comp_write.append(sum(r.CompactionWrittenBytes for r in rangereduce_stats[size_ratio]))
        rr_total = rangereduce_comp_read[-1] + rangereduce_comp_write[-1]

        skv_improvement = ((r_total - skv_total) / r_total) * 100 if r_total != 0 else 0
        bm_improvement = ((r_total - b_total) / r_total) * 100 if r_total != 0 else 0
        rr_improvement = ((r_total - rr_total) / r_total) * 100 if r_total != 0 else 0

        print(f"{str(size_ratio):<12}{r_total/convert_to_:.2f}    {skv_total/convert_to_:.2f}{skv_improvement:>10.2f}%    {b_total/convert_to_:.2f}{bm_improvement:>10.2f}%    {rr_total/convert_to_:.2f}{rr_improvement:>10.2f}%")

    x_vals = list(range(len(size_ratios)))
    bar_width = 0.2

    # RocksDB
    ax.bar(
        [x - 1.5 * bar_width for x in x_vals], rocksdb_comp_read, width=bar_width,
        color='None', edgecolor='tab:blue', linewidth=0.5, hatch="\\\\\\", label="read"
    )
    ax.bar(
        [x - 1.5 * bar_width for x in x_vals], rocksdb_comp_write, width=bar_width,
        bottom=rocksdb_comp_read, color='None', edgecolor='tab:red', linewidth=0.5, hatch="///", label="write"
    )

    # SuccinctKV
    ax.bar(
        [x - 0.5 * bar_width for x in x_vals], succinct_kv_comp_read, width=bar_width,
        color='None', edgecolor='tab:blue', linewidth=0.5, hatch="\\\\\\"
    )
    ax.bar(
        [x - 0.5 * bar_width for x in x_vals], succinct_kv_comp_write, width=bar_width,
        bottom=succinct_kv_comp_read, color='None', edgecolor='tab:red', linewidth=0.5, hatch="///"
    )

    # BoundedMerge
    ax.bar(
        [x + 0.5 * bar_width for x in x_vals], bounded_merge_comp_read, width=bar_width,
        color='None', edgecolor='tab:blue', linewidth=0.5, hatch="\\\\\\"
    )
    ax.bar(
        [x + 0.5 * bar_width for x in x_vals], bounded_merge_comp_write, width=bar_width,
        bottom=bounded_merge_comp_read, color='None', edgecolor='tab:red', linewidth=0.5, hatch="///"
    )

    # RangeReduce
    ax.bar(
        [x + 1.5 * bar_width for x in x_vals], rangereduce_comp_read, width=bar_width,
        color='None', edgecolor='tab:blue', linewidth=0.5, hatch="\\\\\\"
    )
    ax.bar(
        [x + 1.5 * bar_width for x in x_vals], rangereduce_comp_write, width=bar_width,
        bottom=rangereduce_comp_read, color='None', edgecolor='tab:red', linewidth=0.5, hatch="///"
    )


    # Annotate tops of bars
    for i, x in enumerate(x_vals):
        # RocksDB
        total_rdb = rocksdb_comp_read[i] + rocksdb_comp_write[i]
        ax.text(x - 1.4 * bar_width, total_rdb * 1.015, "RDB", 
                ha='center', va='bottom', fontsize=11.5, rotation=90)

        # SuccinctKV
        total_skv = succinct_kv_comp_read[i] + succinct_kv_comp_write[i]
        ax.text(x - 0.4 * bar_width, total_skv * 1.015, "SKV", 
                ha='center', va='bottom', fontsize=12, rotation=90)

        # BoundedMerge
        total_bm = bounded_merge_comp_read[i] + bounded_merge_comp_write[i]
        ax.text(x + 0.6 * bar_width, total_bm * 1.015, "BM", 
                ha='center', va='bottom', fontsize=12, rotation=90)

        # RangeReduce
        total_rr = rangereduce_comp_read[i] + rangereduce_comp_write[i]
        ax.text(x + 1.6 * bar_width, total_rr * 1.015, "RR", 
                ha='center', va='bottom', fontsize=12, rotation=90)

    desired_yticks = [0, 0.05, 0.1, 0.15]
    desired_tb_yticks = [x * convert_to_ for x in desired_yticks]
    ax.set_yticks(desired_tb_yticks)
    ax.set_yticklabels([0] + [f"{x:.2f}" for x in desired_yticks[1:]])

    if TAG == "diffsizeratio":
        fig.legend(
            loc="upper center",
            ncol=2,
            bbox_to_anchor=(0.6, 0.92),
            frameon=False,
            columnspacing=0.5,
        )
        ax.set_xticks(x_vals)
        ax.set_xticklabels(['', '', '', '', ''])
    else:
        ax.set_xlabel("size ratio")
        ax.set_xticks(x_vals)
        ax.set_xticklabels(['2', '4', '6', '8', '10'])

    ax.tick_params(axis='y')
    ax.set_ylabel("comp. work (TB)")
    ax.set_ylim(bottom=0)

    plt.tight_layout()
    plt.savefig(f'{TAG}-compaction_data_movement.pdf', bbox_inches='tight', pad_inches=0.06)
    # plt.show()

def plot_range_query_only():
    convert_to_ = 1024**4
    fig, ax = plt.subplots(figsize=(fig_size[0], fig_size[1]))

    rocksdb_range_query_read = []
    succinct_kv_range_query_read = []
    succinct_kv_range_query_write = []
    bounded_merge_range_query_read = []
    bounded_merge_range_query_write = []
    rangereduce_range_query_read = []
    rangereduce_range_query_write = []

    ideal_val = INSERTS * ENTRY_SIZE * SELECTIVITY * RANGE_QUERIES

    for size_ratio in size_ratios:
        # RocksDB
        rocksdb_range_query_read.append(
            rocksdb_rq_stats[size_ratio][str(RQColumn.TOTAL_ENTRIES_READ)].sum() * ENTRY_SIZE
        )

        # SuccinctKV
        succinct_kv_range_query_read.append(
            succinct_kv_rq_stats[size_ratio][str(RQColumn.TOTAL_ENTRIES_READ)].sum() * ENTRY_SIZE
        )
        succinct_kv_range_query_write.append(
            sum(s.RangeReduceWrittenBytes for s in succinct_kv_stats[size_ratio])
        )

        # BoundedMerge
        bounded_merge_range_query_read.append(
            bounded_merge_rq_stats[size_ratio][str(RQColumn.TOTAL_ENTRIES_READ)].sum() * ENTRY_SIZE
        )
        bounded_merge_range_query_write.append(
            sum(b.RangeReduceWrittenBytes for b in bounded_merge_stats[size_ratio])
        )

        # RQDC
        rangereduce_range_query_read.append(
            rangereduce_rq_stats[size_ratio][str(RQColumn.TOTAL_ENTRIES_READ)].sum() * ENTRY_SIZE
        )
        rangereduce_range_query_write.append(
            sum(r.RangeReduceWrittenBytes for r in rangereduce_stats[size_ratio])
        )

    x_vals = list(range(len(size_ratios)))
    bar_width = 0.2

    # RocksDB
    ax.bar(
        [x - 1.5 * bar_width for x in x_vals], rocksdb_range_query_read, width=bar_width,
        color='None', edgecolor='tab:blue', linewidth=0.3, hatch="\\\\\\"
    )

    # SuccinctKV
    ax.bar(
        [x - 0.5 * bar_width for x in x_vals], succinct_kv_range_query_read, width=bar_width,
        color='None', edgecolor='tab:blue', linewidth=0.3, hatch="\\\\\\"
    )
    ax.bar(
        [x - 0.5 * bar_width for x in x_vals], succinct_kv_range_query_write, width=bar_width,
        bottom=succinct_kv_range_query_read, color='None', edgecolor='tab:red', linewidth=0.3, hatch="///"
    )

    # BoundedMerge
    ax.bar(
        [x + 0.5 * bar_width for x in x_vals], bounded_merge_range_query_read, width=bar_width,
        color='None', edgecolor='tab:blue', linewidth=0.3, hatch="\\\\\\"
    )
    ax.bar(
        [x + 0.5 * bar_width for x in x_vals], bounded_merge_range_query_write, width=bar_width,
        bottom=bounded_merge_range_query_read, color='None', edgecolor='tab:red', linewidth=0.3, hatch="///"
    )

    # RangeReduce
    ax.bar(
        [x + 1.5 * bar_width for x in x_vals], rangereduce_range_query_read, width=bar_width,
        color='None', edgecolor='tab:blue', linewidth=0.3, hatch="\\\\\\"
    )
    ax.bar(
        [x + 1.5 * bar_width for x in x_vals], rangereduce_range_query_write, width=bar_width,
        bottom=rangereduce_range_query_read, color='None', edgecolor='tab:red', linewidth=0.3, hatch="///"
    )

    ax.axhline(y=ideal_val, color='black', linestyle='-.', linewidth=1)
    # ax.text(len(x_vals) - 0.3, ideal_val * 1.01, 'Ideal', color='black', ha='right', va='bottom')

    # Annotate tops of bars
    for i, x in enumerate(x_vals):
        # RocksDB
        total_rdb = rocksdb_range_query_read[i]
        ax.text(x - 1.5 * bar_width, total_rdb * 1.01, "RDB",
                ha='center', va='bottom', fontsize=12, rotation=90)

        # SuccinctKV
        total_skv = succinct_kv_range_query_read[i] + succinct_kv_range_query_write[i]
        ax.text(x - 0.4 * bar_width, total_skv * 1.01, "SKV",
                ha='center', va='bottom', fontsize=12, rotation=90)

        # BoundedMerge
        total_bm = bounded_merge_range_query_read[i] + bounded_merge_range_query_write[i]
        ax.text(x + 0.55 * bar_width, total_bm * 1.01, "BM",
                ha='center', va='bottom', fontsize=12, rotation=90)

        # RangeReduce
        total_rr = rangereduce_range_query_read[i] + rangereduce_range_query_write[i]
        ax.text(x + 1.55 * bar_width, total_rr * 1.01, "RR",
                ha='center', va='bottom', fontsize=12, rotation=90)


    desired_yticks = [0, 0.5, 1, 1.5]
    desired_tb_yticks = [x * convert_to_ for x in desired_yticks]
    ax.set_yticks(desired_tb_yticks)
    ax.set_yticklabels([0] + [f"{x:.1f}" for x in desired_yticks[1:]])

    if TAG == "diffsizeratio":
        ax.set_xticks(x_vals)
        ax.set_xticklabels(['', '', '', '', ''])
    else:
        ax.set_xlabel("size ratio")
        ax.set_xticks(x_vals)
        ax.set_xticklabels(['2', '4', '6', '8', '10'])

    ax.set_ylabel("RQ work (TB)")
    ax.set_ylim(bottom=0)

    plt.tight_layout()
    plt.savefig(f'{TAG}-rangequery_data_movement.pdf', bbox_inches='tight', pad_inches=0.06)
    # plt.show()

def plot_space_amplification():
    fig, ax = plt.subplots(figsize=(fig_size[0] - 0.16, fig_size[1]))

    vanilla_y = []
    succinct_y = []
    bm_y = []
    rqdc_y = []

    for size_ratio in size_ratios:
        vanilla_y.append(rocksdb_stats[size_ratio][0].DBSize / (INSERTS * ENTRY_SIZE))
        succinct_y.append(succinct_kv_stats[size_ratio][0].DBSize / (INSERTS * ENTRY_SIZE))
        bm_y.append(bounded_merge_stats[size_ratio][0].DBSize / (INSERTS * ENTRY_SIZE))
        rqdc_y.append(rangereduce_stats[size_ratio][0].DBSize / (INSERTS * ENTRY_SIZE))

    x_vals = list(range(len(size_ratios)))
    ax.plot(x_vals, vanilla_y, **line_styles_with_abbr["RocksDB"])
    ax.plot(x_vals, succinct_y, **line_styles_with_abbr["SuccinctKV"])
    ax.plot(x_vals, bm_y, **line_styles_with_abbr["RangeReduce[lb=T^-1]"])
    ax.plot(x_vals, rqdc_y, **line_styles_with_abbr["RangeReduce[lb=T^-1 & re=1]"])

    ax.set_ylabel("space amplification")
    # ax.set_xlabel("size ratio")
    ax.set_ylim(bottom=0, top=2)
    ax.tick_params(axis='y')

    desired_yticks = [0, 0.5, 1, 1.5, 2]
    ax.set_yticks(desired_yticks)
    ax.set_yticklabels([0] + [f"{x:.1f}" for x in desired_yticks[1:]])
    if TAG == "diffsizeratio":
        ax.set_xticks(x_vals)
        ax.set_xticklabels(['', '', '', '', ''])
    else:
        ax.set_xlabel("size ratio")
        ax.set_xticks(x_vals)
        ax.set_xticklabels(['2', '4', '6', '8', '10'])
    # ax.set_xticks(x_vals)
    # ax.set_xticklabels(['2', '4', '6', '8', '10'])

    plt.tight_layout()
    plt.savefig(f'{TAG}-size-ratio-space_amplification.pdf', bbox_inches='tight', pad_inches=0.06)
    # plt.show()

def plot_range_query_latency():
    convert_to_ = 10**9
    fig, ax = plt.subplots(figsize=(fig_size[0] - 0.16, fig_size[1]))

    vanilla_y, succinct_y, bm_y, rqdc_y = [], [], [], []

    for size_ratio in size_ratios:
        vanilla_rq_time = rocksdb_rq_stats[size_ratio][str(RQColumn.RQ_TOTAL_TIME)]
        succinct_rq_time = succinct_kv_rq_stats[size_ratio][str(RQColumn.RQ_TOTAL_TIME)]
        bounded_rq_time = bounded_merge_rq_stats[size_ratio][str(RQColumn.RQ_TOTAL_TIME)]
        rqdc_rq_time = rangereduce_rq_stats[size_ratio][str(RQColumn.RQ_TOTAL_TIME)]

        # # find the % improvement between vanilla and bounded and vanilla and rqdc and print them
        # print(f"size ratio: {size_ratio}")
        # print(f"vanilla: {vanilla_rq_time.mean() / convert_to_}")
        # print(f"succinct: {succinct_rq_time.mean() / convert_to_}")
        # print(f"bounded: {bounded_rq_time.mean() / convert_to_}")
        # print(f"rqdc: {rqdc_rq_time.mean() / convert_to_}")
        # print(f"succinct improvement: {((vanilla_rq_time.mean() - succinct_rq_time.mean()) / vanilla_rq_time.mean()) * 100}%")
        # print(f"bounded improvement: {((vanilla_rq_time.mean() - bounded_rq_time.mean()) / vanilla_rq_time.mean()) * 100}%")
        # print(f"rqdc improvement: {((vanilla_rq_time.mean() - rqdc_rq_time.mean()) / vanilla_rq_time.mean()) * 100}%")

        vanilla_y.append(vanilla_rq_time.mean())
        succinct_y.append(succinct_rq_time.mean())
        bm_y.append(bounded_rq_time.mean())
        rqdc_y.append(rqdc_rq_time.mean())

    x_vals = list(range(len(size_ratios)))
    ax.plot(x_vals, vanilla_y, **line_styles_with_abbr["RocksDB"])
    ax.plot(x_vals, succinct_y, **line_styles_with_abbr["SuccinctKV"])
    ax.plot(x_vals, bm_y, **line_styles_with_abbr["RangeReduce[lb=T^-1]"])
    ax.plot(x_vals, rqdc_y, **line_styles_with_abbr["RangeReduce[lb=T^-1 & re=1]"])

    desired_yticks = [0, 0.5, 1.0, 1.5]
    desired_sec_yticks = [x * convert_to_ for x in desired_yticks]
    ax.set_yticks(desired_sec_yticks)
    ax.set_yticklabels([0] + [f"{x}" for x in desired_yticks[1:]])

    # ax.set_xticks(x_vals)
    # ax.set_xticklabels(['2', '4', '6', '8', '10'])
    ax.set_ylabel("avg. RQ latency (sec)")
    # ax.set_xlabel("size ratio")
    ax.set_ylim(bottom=0)
    ax.tick_params(axis='y')
    if TAG == "diffsizeratio":
        fig.legend(
            loc="upper center",
            ncol=1,
            fontsize=20,
            bbox_to_anchor=(0.57, 0.6),
            frameon=False,
            columnspacing=0.1,
            handletextpad=0.2,
            handlelength=1,
            handleheight=1,
            labelspacing=0.1,
        )
        ax.set_xticks(x_vals)
        ax.set_xticklabels(['', '', '', '', ''])
    else:
        ax.set_xlabel("size ratio")
        ax.set_xticks(x_vals)
        ax.set_xticklabels(['2', '4', '6', '8', '10'])

    plt.tight_layout()
    plt.savefig(f'{TAG}-size-ratio-range_query_latency.pdf', bbox_inches='tight', pad_inches=0.06)
    # plt.show()


plot_compaction_only()
plot_range_query_only()
plot_space_amplification()
plot_range_query_latency()
