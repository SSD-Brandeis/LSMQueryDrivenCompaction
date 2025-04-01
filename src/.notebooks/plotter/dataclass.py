from typing import List, NamedTuple, TypedDict
from collections import namedtuple
from enum import Enum

import pandas as pd


PlottingStats = namedtuple(
    "PlottingStats",
    [
        "CompactionDebt",
        "WriteAmpDebt",
        "WriteAmpDebtFull",
        "WriteAmpDebtPartial",
        # "AvgEntriesPerFile",
        "FilesCount",
        "DBSize",
        # "ValidEntriesCount",
        # "InvalidEntriesCount",
        "CompactionWrittenBytes",
        "CompactionReadBytes",
        "RangeReduceWrittenBytes",
        "LevelsState",
        "WorkloadExecutionTime",
    ],
)

AdditionalStats = namedtuple(
    "AdditionalStats", ["min", "max", "mean", "std", "p90th", "p95th", "p98th", "p99th"]
)


class SelectivityVsMetric(NamedTuple):
    Vanilla: PlottingStats
    RangeReduce: PlottingStats
    # VanillaSameRQ: PlottingStats
    # RangeReduceSameRQ: PlottingStats
    # VanillaOverlappingRQ: PlottingStats
    # RangeReduceOverlappingRQ: PlottingStats


class SelectivityVsRangeQueryMetric(NamedTuple):
    Vanilla: pd.DataFrame
    RangeReduce: pd.DataFrame
    # VanillaSameRQ: pd.DataFrame
    # RangeReduceSameRQ: pd.DataFrame
    # VanillaOverlappingRQ: pd.DataFrame
    # RangeReduceOverlappingRQ: pd.DataFrame


class RQColumn(Enum):
    RQ_NUMBER = ("RQ Number",)
    RQ_TOTAL_TIME = ("RQ Total Time",)
    # DATA_USEFUL_BYTES_WRITTEN = ("Data uBytes Written Back",)
    # TOTAL_USEFUL_BYTES_WRITTN = ("Total uBytes Written Back",)
    # USEFUL_ENTRIES_COUNT_WRITTEN = ("uEntries Count Written Back",)
    TOTAL_ENTRIES_READ = ("Total Entries Read",)
    # DATA_UNUSEFUL_BYTES_WRITTEN = ("Data unBytes Written Back",)
    # TOTAL_UNUSEFUL_BYTES_WRITTEN = ("Total unBytes Written Back",)
    # UNUSEFUL_ENTRIES_COUNT_WRITTEN = ("unEntries Count Written Back",)
    TOTAL_ENTRIES_RETURNED = ("Total Entries Returned",)
    RQ_REFRESH_TIME = ("RQ Refresh Time",)
    RQ_RESET_TIME = ("RQ Reset Time",)
    RQ_TIME = ("Actual RQ Time",)
    DID_RUN_RR = ("Did Run RR",)
    # CPU_CYCLES = ("CPU Cycles",)

    def __str__(self):
        return "%s" % self.value

class HeatMapStat(TypedDict):
    lb: float
    ub: float
    plottingStats: List[PlottingStats]
    rqStats: pd.DataFrame

AdditionalStats = namedtuple(
    'AdditionalStats',
    [
        'min',
        'max',
        'mean',
        'std',
        'p90th',
        'p95th',
        'p98th',
        'p99th'
    ]
)

class Approach(Enum):
    ROCKSDB = ("RocksDB",)
    ROCKSDB_TUNED = ("RocksDBTuned",)
    RANGE_REDUCE_LB_0_AND_SMLCK_0 = ("RangeReduce[lb=0 & smlck=0]",)
    RANGE_REDUCE_LB_0 = ("RangeReduce[lb=0]",)
    RANGE_REDUCE_LB_T_MINUS_1 = ("RangeReduce[lb=T^-1]",)
    RANGE_REDUCE_LB_T_MINUS_1_AND_RE_1 = ("RangeReduce[lb=T^-1 & re=1]",)

    def __str__(self):
        return "%s" % self.value


class Metric(Enum):
    TOTAL_WRITES = ("tot. writes (GB)",)
    SPACE_AMP = ("s. amp.",)
    COMPACTION_DEBT = ("comp. debt. (MB)",)
    AVG_RQ_LATENCY = ("RQ lat. (avg ms)",)
    OVERALL_DATA_MOVEMENT = ("overall data mov. (GB)",)
    WL_EXECUTION_TIME = ("w/l exec. time (sec)",)
    RR_TRIGGERED_COUNT = ("# RR trig",)
    AVG_FILE_SIZE = ("avg. fsize",)
    TOTAL_FILES_COUNT = ("tot. fcount",)
    # AVG_RQ_READ_AMP = ("Average RQ Read Amplification",)
    AVG_BYTES_READ_RQ = ("avg. bytes read RQ (MB)",)
    AVG_BYTES_WRITTENT_BY_RR = ("avg. bytes written RR (MB)",)
    TOTAL_COMP_READ_NOT_FOR_RR = ("tot. comp. read (Not RR) (GB)",)
    TAIL_RQ_LATENCY_98 = ("tail RQ lat. 98",)
    TAIL_RQ_LATENCY_100 = ("tail RQ lat. 100",)

    def __str__(self):
        return "%s" % self.value

TABLE_DATA = {
    str(Approach.ROCKSDB): {},
    str(Approach.ROCKSDB_TUNED): {},
    str(Approach.RANGE_REDUCE_LB_0_AND_SMLCK_0): {},
    str(Approach.RANGE_REDUCE_LB_0): {},
    str(Approach.RANGE_REDUCE_LB_T_MINUS_1): {},
    str(Approach.RANGE_REDUCE_LB_T_MINUS_1_AND_RE_1): {},
}

heatmap_value = dict()