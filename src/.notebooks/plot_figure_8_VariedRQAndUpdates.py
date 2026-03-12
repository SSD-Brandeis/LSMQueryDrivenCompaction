import os
import re
from typing import List
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager
from mpl_toolkits.axes_grid1.inset_locator import inset_axes

from plotter.epochstats import EpochStats
from plotter.plotepochstats import PlotRangeQueryStats
from plotter.plotselectivities import PlotSelectivities, PlotSelectivitiesRangeQuery
from plotter.dataclass import SelectivityVsMetric, SelectivityVsRangeQueryMetric
from plotter.varyingrq import VaryingRQPlots, rq_percentages
from plotter.utils import vanilla_dirname, rqdc_dirname
# from plotter.paperplots import PaperPlots

PROJECT_DIR = Path.cwd().parent.parent

prop = font_manager.FontProperties(fname="./plotter/LinLibertine_Mah.ttf")
plt.rcParams['font.family'] = prop.get_name()
plt.rcParams['text.usetex'] = True
plt.rcParams['font.weight'] = 'bold'
plt.rcParams['font.size'] = 20

tag = "selectivityplots"
# tag = "overlapping100"
inserts = 8_388_608

entry_size = 128
entries_per_page = 32
num_pages_per_file = 1024
selectivity = 0.1
size_ratio = 6

vanilla_stats: List[EpochStats] = list()
succinctkv_stats: List[EpochStats] = list()
rangeReduce_stats: List[EpochStats] = list()
bm_stats: List[EpochStats] = list()
epoch_to_plot = -1
max_lvls = list()
op_count = list()

for range_query_percent in rq_percentages:

    range_queries = int(float(range_query_percent) * inserts)
    updates = inserts - range_queries
    op_count.append(inserts + updates + range_queries)
    # print(range_queries)
    # print(updates)
    # deletes = updates

    EXPDIRNAME = f"{PROJECT_DIR}/.vstats_old/experiments-{tag}-U{updates}-E{entry_size}-B{entries_per_page}-S{range_queries}-Y{selectivity}-T{size_ratio}"
    vandirpath = os.path.join(EXPDIRNAME, "RocksDB")
    succinctkvdirpath = os.path.join(EXPDIRNAME, "RangeReduce[lb=0]")
    rqdcdirpath = os.path.join(EXPDIRNAME, f"RangeReduce[lb=T^-1ANDre=1]")
    # bmdirpath = os.path.join(EXPDIRNAME, "RangeReduce[lb=T^-1]")

    filesize = entry_size * entries_per_page * num_pages_per_file
    max_lvl_mtx = []

    van = EpochStats(vandirpath, filesize)
    max_lvl_mtx.append(van.get_max_levels())
    suc = EpochStats(succinctkvdirpath, filesize)
    max_lvl_mtx.append(suc.get_max_levels())
    rqdc = EpochStats(rqdcdirpath, filesize)
    max_lvl_mtx.append(rqdc.get_max_levels())
    # bm = EpochStats(bmdirpath, filesize)
    # max_lvl_mtx.append(bm.get_max_levels())

    vanilla_stats.append(van)
    succinctkv_stats.append(suc)
    rangeReduce_stats.append(rqdc)
    # bm_stats.append(bm)

    max_length_epoch = max([len(num_epochs) for num_epochs in max_lvl_mtx])
    max_lvl_per_epoch = [0] * max_length_epoch

    for col in max_lvl_mtx:
        for idx, row in enumerate(col):
            max_lvl_per_epoch[idx] = max(max_lvl_per_epoch[idx], row)
    
    max_lvls.append(max_lvl_per_epoch)


pprplots = VaryingRQPlots(vanilla_stats, succinctkv_stats, rangeReduce_stats, max_lvl_per_epoch, tag, inserts, entry_size, op_count, -1)

pprplots.plot_range_query_box_plot_latency()
pprplots.plot_throughput()
# pprplots.plot_range_query_latency()
# pprplots.plot_range_query_box_plot_latency()
pprplots.plot_compaction_debt()
# pprplots.plot_wkl_exec_time()
pprplots.plot_space_amp()
# pprplots.plot_total_bytes_written()
# pprplots.plot_total_bytes_read()
pprplots.plot_overall_datamovement()
# pprplots.plot_total_bytes_written_in_compactions()



