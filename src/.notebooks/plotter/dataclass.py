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
    DATA_USEFUL_BYTES_WRITTEN = ("Data uBytes Written Back",)
    TOTAL_USEFUL_BYTES_WRITTN = ("Total uBytes Written Back",)
    USEFUL_ENTRIES_COUNT_WRITTEN = ("uEntries Count Written Back",)
    TOTAL_ENTRIES_READ = ("Total Entries Read",)
    DATA_UNUSEFUL_BYTES_WRITTEN = ("Data unBytes Written Back",)
    TOTAL_UNUSEFUL_BYTES_WRITTEN = ("Total unBytes Written Back",)
    UNUSEFUL_ENTRIES_COUNT_WRITTEN = ("unEntries Count Written Back",)
    RQ_REFRESH_TIME = ("RQ Refresh Time",)
    RQ_RESET_TIME = ("RQ Reset Time",)
    RQ_TIME = ("Actual RQ Time",)
    CPU_CYCLES = ("CPU Cycles",)

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