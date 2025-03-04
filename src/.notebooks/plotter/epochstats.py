from typing import Dict, List
import os

import pandas as pd

from .dataclass import PlottingStats


class EpochStats:
    logfilename = "workload.log"
    rangequery_stats_filename = "range_queries.csv"

    def _compaction_debt(self, levels: Dict[str, List]) -> int:
        r"""
        assuming the levels is sorted by level 0, 1, ... L_n
        $ \text{CD} = \sum_{i=1}^{L_{n-1}} \text{Bytes} \left( L_i \right)$
        """
        sum_of_bytes = 0
        last_lvl_index = len(levels) - 1  # 0 indexed levels

        for lvl, data in enumerate(levels):
            if lvl == last_lvl_index or levels[lvl + 1]["LevelSize"] == 0:
                break
            sum_of_bytes += data["LevelSize"]

        return sum_of_bytes

    def _writeamp_debt(self, levels: Dict[str, List]) -> int:
        r"""
        assuming the levels is sorted by level 0, 1, ... L_n
        $ \text{WA} = \sum_{i=1}^{L_{n-1}} \text{Bytes} \left( L_i \right) \times (L_{n} - i) $
        """
        sum_of_bytes = 0
        last_lvl_index = len(levels) - 1  # 0 indexed levels
        last_non_empty_level_index = last_lvl_index

        for data in levels[::-1]:
            if data["LevelSize"] != 0:
                break
            last_non_empty_level_index -= 1

        for lvl, data in enumerate(levels):
            if lvl == last_non_empty_level_index:
                break
            sum_of_bytes += data["LevelSize"] * (last_non_empty_level_index - lvl)

        return sum_of_bytes

    def _writeampfull_debt(self, levels: Dict[str, List]) -> int:
        r"""
        assuming the levels is sorted by level 0, 1, ... L_n
        $ \text{WA\textsuperscript{L1}} = \text{Bytes}\left( L_1 \right) \times (L_{n} - 1)$\\
        $ \text{WA\textsuperscript{full}} = \text{WA\textsuperscript{L1}} + \sum_{i=2}^{L_{n}} \text{Bytes} \left( L_i \right) \times (L_{n} - i + 1) $
        """
        sum_of_bytes = 0
        last_lvl_index = len(levels) - 1  # 0 indexed levels
        last_non_empty_level_index = last_lvl_index

        for data in levels[::-1]:
            if data["LevelSize"] != 0:
                break
            last_non_empty_level_index -= 1

        for lvl, data in enumerate(levels):
            if lvl > last_non_empty_level_index:
                break
            if lvl == 0:
                sum_of_bytes += data["LevelSize"] * last_non_empty_level_index
            else:
                sum_of_bytes += data["LevelSize"] * (
                    last_non_empty_level_index - lvl + 1
                )

        return sum_of_bytes

    def _writeamppartial_debt(self, levels: Dict[str, List], filesize: int) -> int:
        r"""
        assuming the levels is sorted by level 0, 1, ... L_n
        $ \text{File Size (FS)} = (P \times B)$
        $ \text{WA\textsuperscript{partial}} = WA^{partial} + (\sum_{i=2}^{L_{n}} \text{Bytes} \left( L_{i-1} \right)) - FS \times (L_{n} - 1)$
        """
        sum_of_bytes = 0
        last_lvl_index = len(levels) - 1  # 0 indexed levels
        last_non_empty_level_index = last_lvl_index

        for data in levels[::-1]:
            if data["LevelSize"] != 0:
                break
            last_non_empty_level_index -= 1

        for lvl, data in enumerate(levels):
            if lvl > last_non_empty_level_index:
                break
            if lvl == 0:
                continue
            sum_of_bytes += levels[lvl - 1]["LevelSize"]

        return self._writeampfull_debt(levels) + (
            sum_of_bytes - (filesize * last_non_empty_level_index)
        )

    def _compaction_written_bytes(self, epoch_stats: List[str]):
        write_bytes = 0

        for line in epoch_stats:
            if line.startswith("rocksdb.compact.write.bytes"):
                write_bytes += int(line.split(":")[1])

        return write_bytes

    def _compaction_read_bytes(self, epoch_stats: List[str]):
        read_bytes = 0

        for line in epoch_stats:
            if line.startswith("rocksdb.compact.read.bytes"):
                read_bytes += int(line.split(":")[1])

        return read_bytes

    def _rangereduce_written_bytes(self, epoch_stats: List[str]):
        write_bytes = 0

        for line in epoch_stats:
            if line.startswith("rocksdb.rangereduce.write.bytes"):
                write_bytes += int(line.split(":")[1])

        return write_bytes

    def _workload_execution_time(self, epoch_stats: List[str]):
        execution_time = 0

        for line in epoch_stats:
            if line.startswith("Workload Execution Time"):
                execution_time = int(line.split(": ")[1])
                break
        return execution_time

    def _read_one_epoch(self, string_to_check=["===========", "===========", "===========END HERE========="], i=0):
        with open(self.filepath, "r") as file:
            epoch_data = list()
            grabbing_data = False

            for line in file:
                line = line.strip()
                if line.startswith(string_to_check[i]):
                    if grabbing_data:
                        i += 1
                        yield epoch_data
                        epoch_data = list()
                        grabbing_data = False
                elif grabbing_data:
                    epoch_data.append(line)
                else:
                    grabbing_data = True
                    epoch_data.append(line)

    # def _parse_one_epoch_v2(self, epoch_stats: List[str]) -> Dict[str, List]:
    #     columnfamilydata = {"Levels": list()}
    #     i = 0

    #     while i < len(epoch_stats):
    #         currentline = epoch_stats[i]

    #         if currentline.startswith("Column Family Name"):
    #             key_val = currentline.split(",")
    #             columnfamilydata["Column Family Name"] = (
    #                 key_val[0].split(":")[1].strip().strip(",")
    #             )
    #             columnfamilydata["Size"] = int(
    #                 key_val[1].split(":")[1].strip().strip(",").strip(" bytes")
    #             )
    #             columnfamilydata["Files Count"] = int(
    #                 key_val[2].split(":")[1].strip().strip(",")
    #             )
    #         if currentline.startswith("Level:"):
    #             key_val = currentline.split(",")
    #             level = int(key_val[0].split(":")[1].strip().strip(","))
    #             level_files_count = int(key_val[1].split(":")[1].strip().strip(","))
    #             level_size = int(
    #                 key_val[2].split(":")[1].strip().strip(",").strip(" bytes")
    #             )

    #             columnfamilydata["Levels"].append(
    #                 {
    #                     "Level": level,
    #                     "LevelFilesCount": level_files_count,
    #                     "LevelSize": level_size,
    #                 }
    #             )
    #         i += 1

    #     return columnfamilydata

    # def _parse_one_epoch(self, epoch_stats: List[str]) -> Dict[str, List]:
    #     columnfamilydata = {"Levels": list()}
    #     sst_files = {}
    #     i = 0

    #     while i < len(epoch_stats):
    #         currentline = epoch_stats[i]
    #         # Check if the line contains column family data
    #         if currentline.startswith("Column Family Name"):
    #             key_val = currentline.split(",")
    #             columnfamilydata["Column Family Name"] = (
    #                 key_val[0].split(":")[1].strip().strip(",")
    #             )
    #             columnfamilydata["Size"] = int(
    #                 key_val[1].split(":")[1].strip().strip(",").strip(" bytes")
    #             )
    #             columnfamilydata["Files Count"] = int(
    #                 key_val[2].split(":")[1].strip().strip(",")
    #             )
    #             columnfamilydata["Entries Count"] = int(
    #                 key_val[3].split(":")[1].strip().strip(",")
    #             )
    #             columnfamilydata["Invalid Entries Count"] = int(
    #                 key_val[4].split(":")[1].strip().strip(",")
    #             )
    #         if "Level:" in currentline:
    #             key_val = currentline.strip().split(",")
    #             level = int(key_val[0].split(":")[1].strip().strip(","))
    #             level_size = int(
    #                 key_val[1].split(":")[1].strip().strip(",").strip(" bytes")
    #             )
    #             level_files_count = int(key_val[2].split(":")[1].strip().strip(","))

    #             key_val_sst_files = epoch_stats[i + 1].split("],")[:-1]
    #             sst_files = []

    #             for sst_file_string in key_val_sst_files:
    #                 # Extract SST file details
    #                 file_number = int(
    #                     sst_file_string.split(":")[0].split("[#")[1].strip()
    #                 )
    #                 file_details = sst_file_string.split(":")[1].strip().split()
    #                 file_size = int(file_details[0].strip())
    #                 smallest_key = file_details[1].strip(",").strip("(")
    #                 largest_key = file_details[2].strip(")")
    #                 entries_count = int(file_details[3].strip("]"))

    #                 sst_files.append(
    #                     {
    #                         "FNo": file_number,
    #                         "FileSize": file_size,
    #                         "SmallesKey": smallest_key,
    #                         "LargestKey": largest_key,
    #                         "EntriesCount": entries_count,
    #                     }
    #                 )

    #             # if len(sst_files) > 0:
    #             columnfamilydata["Levels"].append(
    #                 {
    #                     "Level": level,
    #                     "LevelSize": level_size,
    #                     "LevelFilesCount": level_files_count,
    #                     "SSTFiles": sst_files,
    #                 }
    #             )
    #             #
    #             i += 1
    #         i += 1
    #     return columnfamilydata

    def _parse_one_epoch(self, epoch_stats: List[str]) -> Dict[str, List]:
        columnfamilydata = {"Levels": list()}
        sst_files = {}
        i = 0
        fallback_used = False  # Flag to determine if fallback is used

        while i < len(epoch_stats):
            currentline = epoch_stats[i]

            try:
                # Primary parsing logic (_parse_one_epoch_v2)
                if currentline.startswith("Column Family Name"):
                    key_val = currentline.split(",")
                    columnfamilydata["Column Family Name"] = (
                        key_val[0].split(":")[1].strip().strip(",")
                    )
                    columnfamilydata["Size"] = int(
                        key_val[1].split(":")[1].strip().strip(",").strip(" bytes")
                    )
                    columnfamilydata["Files Count"] = int(
                        key_val[2].split(":")[1].strip().strip(",")
                    )
                if currentline.startswith("Level:"):
                    key_val = currentline.split(",")
                    level = int(key_val[0].split(":")[1].strip().strip(","))
                    level_files_count = int(key_val[1].split(":")[1].strip().strip(","))
                    level_size = int(
                        key_val[2].split(":")[1].strip().strip(",").strip(" bytes")
                    )

                    columnfamilydata["Levels"].append(
                        {
                            "Level": level,
                            "LevelFilesCount": level_files_count,
                            "LevelSize": level_size,
                        }
                    )
                i += 1

            except (IndexError, ValueError, KeyError):
                # Fallback parsing logic (_parse_one_epoch)
                fallback_used = True
                if currentline.startswith("Column Family Name"):
                    key_val = currentline.split(",")
                    columnfamilydata["Column Family Name"] = (
                        key_val[0].split(":")[1].strip().strip(",")
                    )
                    columnfamilydata["Size"] = int(
                        key_val[1].split(":")[1].strip().strip(",").strip(" bytes")
                    )
                    columnfamilydata["Files Count"] = int(
                        key_val[2].split(":")[1].strip().strip(",")
                    )
                    columnfamilydata["Entries Count"] = int(
                        key_val[3].split(":")[1].strip().strip(",")
                    )
                    columnfamilydata["Invalid Entries Count"] = int(
                        key_val[4].split(":")[1].strip().strip(",")
                    )
                if "Level:" in currentline:
                    key_val = currentline.strip().split(",")
                    level = int(key_val[0].split(":")[1].strip().strip(","))
                    level_size = int(
                        key_val[1].split(":")[1].strip().strip(",").strip(" bytes")
                    )
                    level_files_count = int(key_val[2].split(":")[1].strip().strip(","))

                    key_val_sst_files = epoch_stats[i + 1].split("],")[:-1]
                    sst_files = []

                    for sst_file_string in key_val_sst_files:
                        # Extract SST file details
                        file_number = int(
                            sst_file_string.split(":")[0].split("[#")[1].strip()
                        )
                        file_details = sst_file_string.split(":")[1].strip().split()
                        file_size = int(file_details[0].strip())
                        smallest_key = file_details[1].strip(",").strip("(")
                        largest_key = file_details[2].strip(")")
                        entries_count = int(file_details[3].strip("]"))

                        sst_files.append(
                            {
                                "FNo": file_number,
                                "FileSize": file_size,
                                "SmallesKey": smallest_key,
                                "LargestKey": largest_key,
                                "EntriesCount": entries_count,
                            }
                        )

                    columnfamilydata["Levels"].append(
                        {
                            "Level": level,
                            "LevelSize": level_size,
                            "LevelFilesCount": level_files_count,
                            "SSTFiles": sst_files,
                        }
                    )
                    i += 1
                i += 1

        if fallback_used:
            print("Fallback logic was applied during parsing.")
        return columnfamilydata


    def _parse_logfile(self):
        epoch = self.NUMEPOCHS
        filereader = self._read_one_epoch()
        next(filereader)
        next(filereader)  # Inserts are completed

        try:
            while epoch > 0:
                one_epoch_stats_lines = next(filereader)
                columnfamilydata = self._parse_one_epoch(one_epoch_stats_lines)

                self._epoch_stats.append(columnfamilydata)
                sorted_cfd = sorted(
                    columnfamilydata["Levels"], key=lambda x: x["Level"]
                )

                n = len(sorted_cfd)-1
                while len(sorted_cfd) > 0:
                    if sorted_cfd[n]["LevelSize"] == 0:
                        sorted_cfd.pop(-1)
                    else:
                        break
                    n-=1

                compaction_write_bytes = self._compaction_written_bytes(one_epoch_stats_lines)
                compaction_read = self._compaction_read_bytes(one_epoch_stats_lines)
                rangereduce_write_bytes = self._rangereduce_written_bytes(one_epoch_stats_lines)
                wrkld_exec_time = self._workload_execution_time(one_epoch_stats_lines)

                self._plotting_stats.append(
                    PlottingStats(
                        **{
                            "CompactionDebt": self._compaction_debt(sorted_cfd),
                            "WriteAmpDebt": self._writeamp_debt(sorted_cfd),
                            "WriteAmpDebtFull": self._writeampfull_debt(sorted_cfd),
                            "WriteAmpDebtPartial": self._writeamppartial_debt(
                                sorted_cfd, self.FILESIZE
                            ),
                            # "AvgEntriesPerFile": columnfamilydata["Entries Count"]
                            # / columnfamilydata["Files Count"],
                            "FilesCount": columnfamilydata["Files Count"],
                            "DBSize": columnfamilydata["Size"],
                            # "ValidEntriesCount": columnfamilydata["Entries Count"],
                            # "InvalidEntriesCount": columnfamilydata[
                            #     "Invalid Entries Count"
                            # ],
                            "CompactionWrittenBytes": compaction_write_bytes,
                            "CompactionReadBytes": compaction_read,
                            "RangeReduceWrittenBytes": rangereduce_write_bytes,
                            "LevelsState": [
                                lvl["LevelFilesCount"] for lvl in sorted_cfd
                            ],
                            "WorkloadExecutionTime": wrkld_exec_time,
                        }
                    )
                )
                epoch -= 1
        except Exception as e:
            raise Exception(
                f"failed to parse epoch {self.NUMEPOCHS - epoch} from log file: {self.filepath}"
            )

    def _pull_rqstats(self):
        self._rangequery_stats = pd.read_csv(self.rqfilepath)
        self._rangequery_stats = self._rangequery_stats.applymap(
            lambda x: x.strip(" ") if isinstance(x, str) else x
        )
        self._rangequery_stats.columns = self._rangequery_stats.columns.str.strip()

    def __init__(self, logdirpath: str, numepoch: int, filesize: int):
        self._epoch_stats = list()
        self._plotting_stats: List[PlottingStats] = list()
        self.NUMEPOCHS = numepoch
        self.FILESIZE = filesize

        logfilepath = os.path.join(logdirpath, self.logfilename)

        if not os.path.exists(logdirpath) or not os.path.exists(logfilepath):
            if not os.path.exists(logdirpath):
                raise FileNotFoundError(f"log directory: {logdirpath} not found")
            raise FileNotFoundError(f"log file {logfilepath} not found")

        self.filepath = logfilepath
        self._parse_logfile()

        rqfilepath = os.path.join(logdirpath, self.rangequery_stats_filename)

        if not os.path.exists(rqfilepath):
            raise FileNotFoundError(f"range query log file {rqfilepath} not found")

        self.rqfilepath = rqfilepath
        self._pull_rqstats()

    def get_plotstats(self) -> List[PlottingStats]:
        return self._plotting_stats

    def get_rangequerystats(self) -> pd.DataFrame:
        return self._rangequery_stats
