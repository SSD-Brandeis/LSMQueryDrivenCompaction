from typing import NamedTuple
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
        "AvgEntriesPerFile",
        "FilesCount",
        "DBSize",
        "ValidEntriesCount",
        "InvalidEntriesCount",
        "TotalWriteBytes",
        "CompactionReadBytes",
        "LevelsState",
    ],
)


class SelectivityVsMetric(NamedTuple):
    Vanilla: PlottingStats
    RangeReduce: PlottingStats
    RangeReduceSameRQ: PlottingStats
    RangeReduceOverlappingRQ: PlottingStats


class SelectivityVsRangeQueryMetric(NamedTuple):
    Vanilla: pd.DataFrame
    RangeReduce: pd.DataFrame
    RangeReduceSameRQ: pd.DataFrame
    RangeReduceOverlappingRQ: pd.DataFrame


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

    def __str__(self):
        return "%s" % self.value
