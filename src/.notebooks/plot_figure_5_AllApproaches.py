import os
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager

from plotter import *
from plotter.epochstats import EpochStats
from plotter.plotepochstats import (
    PlotEpochStats,
    PlotRangeQueryStats,
    plot_total_data_movement,
)

# -------------------------------------------------------------------
# Matplotlib configuration
# -------------------------------------------------------------------

matplotlib.use("Agg")

FONT_PROP = font_manager.FontProperties(fname="./plotter/LinLibertine_Mah.ttf")
plt.rcParams.update(
    {
        "font.family": FONT_PROP.get_name(),
        "text.usetex": True,
        "font.weight": "bold",
        "font.size": 20,
    }
)

# -------------------------------------------------------------------
# Experiment configuration
# -------------------------------------------------------------------

PROJECT_DIR = Path.cwd().parent.parent
TAG = "mergeonscan"

EXPERIMENT_DIR = (
    f"{PROJECT_DIR}/.vstats_old/experiments-{TAG}"
    f"-U{UPDATES}-E{ENTRY_SIZE}"
    f"-B{ENTRIES_PER_PAGE}-P{NUM_PAGE_PER_FILE}"
    f"-S{RANGE_QUERIES}-Y{SELECTIVITY}-T{SIZE_RATIO}"
)

# -------------------------------------------------------------------
# Database directories
# -------------------------------------------------------------------

DB_DIRS = {
    "RocksDB": os.path.join(EXPERIMENT_DIR, "RocksDB"),
    "SuccinctKV": os.path.join(EXPERIMENT_DIR, "SuccinctKV"),
    "RangeReduce[lb=0 & smlck=0]": os.path.join(
        EXPERIMENT_DIR, "RangeReduce[lb=0ANDsmlck=0]"
    ),
    "RangeReduce[lb=0]": os.path.join(EXPERIMENT_DIR, "RangeReduce[lb=0]"),
    "RangeReduce[lb=T^-1]": os.path.join(EXPERIMENT_DIR, "RangeReduce[lb=T^-1]"),
    # "RangeReduce[lb=T^-1 & re=1]": os.path.join(
    #     EXPERIMENT_DIR, "RangeReduce[lb=T^-1ANDre=1]"
    # ),
}

APPROACH_ABBREVIATIONS = ["RDB", "SKV", "MoS", "FSMoS", "BM"] #, "RR"]
EPOCH_TO_PLOT = -1

# -------------------------------------------------------------------
# Load epoch statistics
# -------------------------------------------------------------------

FILE_SIZE = ENTRY_SIZE * ENTRIES_PER_PAGE * NUM_PAGE_PER_FILE

epoch_stats = {
    name: EpochStats(path, FILE_SIZE)
    for name, path in DB_DIRS.items()
}

# -------------------------------------------------------------------
# Compute maximum levels per epoch (shared y-axis scaling)
# -------------------------------------------------------------------

max_levels_by_db = [
    stats.get_max_levels() for stats in epoch_stats.values()
]

max_epoch_length = max(len(levels) for levels in max_levels_by_db)
max_levels_per_epoch = [0] * max_epoch_length

for levels in max_levels_by_db:
    for idx, level in enumerate(levels):
        max_levels_per_epoch[idx] = max(max_levels_per_epoch[idx], level)

# -------------------------------------------------------------------
# Range query plots
# -------------------------------------------------------------------

rq_plotter = PlotRangeQueryStats(
    {
        name: stats.get_rangequerystats()
        for name, stats in epoch_stats.items()
    },
    approaches_order=[
        "RocksDB",
        "SuccinctKV",
        "RangeReduce[lb=0]",
        "RangeReduce[lb=0 & smlck=0]",
        "RangeReduce[lb=T^-1]",
        # "RangeReduce[lb=T^-1 & re=1]",
    ],
)

rq_plotter.bytes_read_for_each_range_query()
rq_plotter.bytes_read_for_each_range_query_rolling(window=200)
rq_plotter.bytes_read_cdf()

rq_plotter.latency_for_each_range_query()
rq_plotter.latency_for_each_range_query_rolling(window=200)
rq_plotter.latency_cdf()

rq_plotter.plot_did_rq_run(APPROACH_ABBREVIATIONS)

# -------------------------------------------------------------------
# Epoch-level metric plots
# -------------------------------------------------------------------

epoch_plotter = PlotEpochStats(
    {
        name: stats.get_plotstats(max_levels_per_epoch)
        for name, stats in epoch_stats.items()
    },
    approach_abr_order=APPROACH_ABBREVIATIONS,
    epoch_to_plot=EPOCH_TO_PLOT,
)

epoch_plotter.plot_total_bytes_written()
epoch_plotter.plot_total_rq_bytes_written()
epoch_plotter.plot_compaction_debt()
epoch_plotter.plot_space_amplification()

# -------------------------------------------------------------------
# Total data movement (writes + reads)
# -------------------------------------------------------------------

plot_total_data_movement(
    {
        name: stats.get_plotstats(max_levels_per_epoch)
        for name, stats in epoch_stats.items()
    },
    {
        name: stats.get_rangequerystats()
        for name, stats in epoch_stats.items()
    },
    approach_abr_order=APPROACH_ABBREVIATIONS,
    epoch_to_plot=EPOCH_TO_PLOT,
)































































# import os
# from pathlib import Path
# from tabulate import tabulate

# import matplotlib

# matplotlib.use("Agg")
# import matplotlib.pyplot as plt
# import matplotlib.font_manager as font_manager
# from mpl_toolkits.axes_grid1.inset_locator import inset_axes

# from plotter import *
# from plotter.epochstats import EpochStats
# from plotter.plotepochstats import (
#     PlotRangeQueryStats,
#     PlotEpochStats,
#     plot_total_data_movement,
# )
# from plotter.plotselectivities import PlotSelectivities, PlotSelectivitiesRangeQuery
# from plotter.utils import vanilla_dirname, rqdc_dirname
# from plotter.dataclass import TABLE_DATA, Metric

# PROJECT_DIR = Path.cwd().parent.parent

# prop = font_manager.FontProperties(fname="./plotter/LinLibertine_Mah.ttf")
# plt.rcParams["font.family"] = prop.get_name()
# plt.rcParams["text.usetex"] = True
# plt.rcParams["font.weight"] = "bold"
# plt.rcParams["font.size"] = 24

# TAG = "ycsbee"

# random_rq_stats = dict()
# random_rq_stats_for_rq = dict()

# lb = 1 / SIZE_RATIO
# EXPDIRNAME = f"{PROJECT_DIR}/.vstats_old/experiments-{TAG}-U{UPDATES}-E{ENTRY_SIZE}-B{ENTRIES_PER_PAGE}-P{NUM_PAGE_PER_FILE}-S{RANGE_QUERIES}-Y{SELECTIVITY}-T{SIZE_RATIO}"  #  -P{NUM_PAGE_PER_FILE}

# rocksdb_dirpath = os.path.join(EXPDIRNAME, "RocksDB")
# # rocksdb_tuned_dirpath = os.path.join(EXPDIRNAME, "RocksDBTuned")
# rr_lb0_smlck0_dirpath = os.path.join(EXPDIRNAME, "RangeReduce[lb=0ANDsmlck=0]")
# rr_lb0_dirpath = os.path.join(EXPDIRNAME, "RangeReduce[lb=0]")
# succinctkv_dirpath = os.path.join(EXPDIRNAME, "SuccinctKV")
# rr_lb_1_by_T_dirpath = os.path.join(EXPDIRNAME, "RangeReduce[lb=T^-1]")
# rr_lb_1_by_T_and_re_1_dirpath = os.path.join(EXPDIRNAME, "RangeReduce[lb=T^-1ANDre=1]")

# filesize = ENTRY_SIZE * ENTRIES_PER_PAGE * NUM_PAGE_PER_FILE
# max_lvl_mtx = []

# rocksdb = EpochStats(rocksdb_dirpath, filesize)
# max_lvl_mtx.append(rocksdb.get_max_levels())
# # rocksdb_tuned = EpochStats(rocksdb_tuned_dirpath, filesize)
# # max_lvl_mtx.append(rocksdb_tuned.get_max_levels())
# rr_lb_0_smlck_0 = EpochStats(rr_lb0_smlck0_dirpath, filesize)
# max_lvl_mtx.append(rr_lb_0_smlck_0.get_max_levels())
# rr_lb_0 = EpochStats(rr_lb0_dirpath, filesize)
# max_lvl_mtx.append(rr_lb_0.get_max_levels())
# succinctkv = EpochStats(succinctkv_dirpath, filesize)
# max_lvl_mtx.append(succinctkv.get_max_levels())
# rr_lb_1_by_T = EpochStats(rr_lb_1_by_T_dirpath, filesize)
# max_lvl_mtx.append(rr_lb_1_by_T.get_max_levels())
# rr_lb_1_by_T_and_re_1 = EpochStats(rr_lb_1_by_T_and_re_1_dirpath, filesize)
# max_lvl_mtx.append(rr_lb_1_by_T_and_re_1.get_max_levels())

# max_length_epoch = max([len(num_epochs) for num_epochs in max_lvl_mtx])
# max_lvl_per_epoch = [0] * max_length_epoch

# for col in max_lvl_mtx:
#     for idx, row in enumerate(col):
#         max_lvl_per_epoch[idx] = max(max_lvl_per_epoch[idx], row)

# epoch_to_plot = -1
# approach_abbr = ["RDB", "SKV", "RR"] # "FSMoS"] # "SKV", "MoS", , "BM"

# plot_exp = PlotRangeQueryStats(
#     {
#         "RocksDB": rocksdb.get_rangequerystats(),
#         # "RocksDBTuned": rocksdb_tuned.get_rangequerystats(),
#         "SuccinctKV": succinctkv.get_rangequerystats(),
#         "RangeReduce[lb=0 & smlck=0]": rr_lb_0_smlck_0.get_rangequerystats(),
#         "RangeReduce[lb=0]": rr_lb_0.get_rangequerystats(),
#         "RangeReduce[lb=T^-1]": rr_lb_1_by_T.get_rangequerystats(),
#         "RangeReduce[lb=T^-1 & re=1]": rr_lb_1_by_T_and_re_1.get_rangequerystats(),
#     },
#     approaches_order=[
#         "RocksDB",
#         "SuccinctKV",
#         "RangeReduce[lb=0]",
#         "RangeReduce[lb=0 & smlck=0]",
#         "RangeReduce[lb=T^-1]",
#         "RangeReduce[lb=T^-1 & re=1]",
#     ],
# )
# plot_exp.bytes_read_for_each_range_query()
# plot_exp.bytes_read_for_each_range_query_rolling(window=10)
# plot_exp.bytes_read_cdf()
# plot_exp.latency_for_each_range_query()
# plot_exp.latency_for_each_range_query_rolling(window=10)
# plot_exp.latency_cdf()
# plot_exp.plot_did_rq_run(approach_abbr)

# metric_exp = PlotEpochStats(
#     {
#         "RocksDB": rocksdb.get_plotstats(max_lvl_per_epoch),
#         # "RocksDBTuned": rocksdb_tuned.get_plotstats(max_lvl_per_epoch),
#         "SuccinctKV": succinctkv.get_plotstats(max_lvl_per_epoch),
#         "RangeReduce[lb=0 & smlck=0]": rr_lb_0_smlck_0.get_plotstats(max_lvl_per_epoch),
#         "RangeReduce[lb=0]": rr_lb_0.get_plotstats(max_lvl_per_epoch),
#         "RangeReduce[lb=T^-1]": rr_lb_1_by_T.get_plotstats(max_lvl_per_epoch),
#         "RangeReduce[lb=T^-1 & re=1]": rr_lb_1_by_T_and_re_1.get_plotstats(max_lvl_per_epoch),
#     },
#     approach_abr_order=approach_abbr,
#     epoch_to_plot=epoch_to_plot,
# )
# metric_exp.plot_total_bytes_written()
# metric_exp.plot_total_rq_bytes_written()
# # metric_exp.plot_database_size()
# metric_exp.plot_compaction_debt()
# metric_exp.plot_space_amplification()
# # metric_exp.plot_insert_throughput_for_phases([(1, 3355443), (3, 3355443), (5, 838860)])
# # metric_exp.plot_compaction_read()
# # metric_exp.plot_workload_exec_time()
# plot_total_data_movement(
#     {
#         "RocksDB": rocksdb.get_plotstats(max_lvl_per_epoch),
#         # "RocksDBTuned": rocksdb_tuned.get_plotstats(max_lvl_per_epoch),
#         "SuccinctKV": succinctkv.get_plotstats(max_lvl_per_epoch),
#         "RangeReduce[lb=0 & smlck=0]": rr_lb_0_smlck_0.get_plotstats(max_lvl_per_epoch),
#         "RangeReduce[lb=0]": rr_lb_0.get_plotstats(max_lvl_per_epoch),
#         "RangeReduce[lb=T^-1]": rr_lb_1_by_T.get_plotstats(max_lvl_per_epoch),
#         "RangeReduce[lb=T^-1 & re=1]": rr_lb_1_by_T_and_re_1.get_plotstats(max_lvl_per_epoch),
#     },
#     {
#         "RocksDB": rocksdb.get_rangequerystats(),
#         # "RocksDBTuned": rocksdb_tuned.get_rangequerystats(),
#         "SuccinctKV": succinctkv.get_rangequerystats(),
#         "RangeReduce[lb=0 & smlck=0]": rr_lb_0_smlck_0.get_rangequerystats(),
#         "RangeReduce[lb=0]": rr_lb_0.get_rangequerystats(),
#         "RangeReduce[lb=T^-1]": rr_lb_1_by_T.get_rangequerystats(),
#         "RangeReduce[lb=T^-1 & re=1]": rr_lb_1_by_T_and_re_1.get_rangequerystats(),
#     },
#     approach_abr_order=approach_abbr,
#     epoch_to_plot=epoch_to_plot,
# )

# # rows = []
# # ordered_columns = ["Method"] + [metric.value[0] for metric in Metric]

# # for method, metrics in TABLE_DATA.items():
# #     row = {"Method": method}
# #     row.update(metrics)
# #     rows.append(row)

# # ordered_rows = []
# # for row in rows:
# #     ordered_row = {col: row.get(col, "") for col in ordered_columns}
# #     ordered_rows.append(ordered_row)

# # markdown_table = tabulate(ordered_rows, headers="keys", tablefmt="github")
# # print(markdown_table)
