"""
plot_figure_6.py — standalone slide/paper plotter for figure 6
(RangeReduceRatio heatmap).

Fully self-contained: no dependency on the shared plotter/ package.  All
constants, log parsing, metric extraction, and plotting live in this single
file, so it can be copied and run on its own.  Only the final summary heatmap
is produced — the eight workload metrics, normalized by RocksDB, across the
RangeReduceRatio (lb = 1/(eps*T)) sweep.
"""

import os
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager
import pandas as pd

# ===================================================================
# Libertine paper format
# ===================================================================

FONT_PROP = font_manager.FontProperties(fname="./plotter/LinLibertine_Mah.ttf")
plt.rcParams.update(
    {
        "font.family": FONT_PROP.get_name(),
        "text.usetex": True,
        "font.weight": "bold",
        "font.size": 22,
    }
)

# ===================================================================
# Workload / experiment constants
# ===================================================================

INSERTS          = 8388608
UPDATES          = 8388608
RANGE_QUERIES    = 9000
SELECTIVITY      = 0.1
SIZE_RATIO       = 6
ENTRY_SIZE       = 128
ENTRIES_PER_PAGE = 32
NUM_PAGE_PER_FILE = 1024
EPSILON_VALUES   = (1, 2, 4, 8, 0.5, 0.25, 0.125)

# Range-query CSV column names (post-strip).
RQ_TOTAL_TIME      = "RQ Total Time"
TOTAL_ENTRIES_READ = "Total Entries Read"

# ===================================================================
# Paths
# ===================================================================

PROJECT_DIR = Path.cwd().parent.parent
TAG         = "rangereduceratio"

OUTPUT_DIR = f"Figures/Fig6"
os.makedirs(OUTPUT_DIR, exist_ok=True)

FILE_SIZE = ENTRY_SIZE * ENTRIES_PER_PAGE * NUM_PAGE_PER_FILE

EXP_DIR = (
    f"{PROJECT_DIR}/logs/experiments-{TAG}"
    f"-U{UPDATES}-E{ENTRY_SIZE}-B{ENTRIES_PER_PAGE}-P{NUM_PAGE_PER_FILE}"
    f"-S{RANGE_QUERIES}-Y{SELECTIVITY}-T{SIZE_RATIO}"
)

# ===================================================================
# Approaches — RocksDB baseline + one RangeReduce run per epsilon.
# Each row: (column label, directory name, lower bound lb).
# ===================================================================

APPROACHES: List[Tuple[str, str, float]] = [("RocksDB", "RocksDB", 0.0)]
for _eps in EPSILON_VALUES:
    _lb    = 1 / (SIZE_RATIO * _eps)
    _label = f"$\\frac{{1}}{{{'' if _eps == 1 else _eps}T}}$"
    APPROACHES.append((_label, f"RangeReduce[lb=T^-1]{_eps}", _lb))

# ===================================================================
# Log parsing (minimal, faithful port of plotter.epochstats)
# ===================================================================

LOG_FILENAME = "workload.log"
RQ_FILENAME  = "range_queries.csv"


def _read_epochs(filepath: str) -> List[List[str]]:
    epochs: List[List[str]] = []
    current: List[str] = []

    with open(filepath) as f:
        for line in f:
            line = line.rstrip()
            if line.startswith("====================="):
                if current:
                    epochs.append(current)
                    current = []
                continue
            if line.startswith("===========END HERE========="):
                break
            current.append(line)

    # Merge trailing workload times into the last epoch.
    for i, line in enumerate(current):
        if line.startswith("Workload Execution Time"):
            epochs[-1].extend(current[i:])
            break

    return epochs[1:]


def _parse_levels(epoch_stats: List[str]) -> Dict:
    cfd: Dict = {"Levels": []}
    for line in epoch_stats:
        if line.startswith("Column Family Name"):
            kv = line.split(",")
            cfd["Size"]        = int(kv[1].split(":")[1].strip().strip(",").strip(" bytes"))
            cfd["Files Count"] = int(kv[2].split(":")[1].strip().strip(","))
        elif line.startswith("Level:"):
            kv = line.split(",")
            cfd["Levels"].append(
                {
                    "Level":           int(kv[0].split(":")[1].strip().strip(",")),
                    "LevelFilesCount": int(kv[1].split(":")[1].strip().strip(",")),
                    "LevelSize":       int(kv[2].split(":")[1].strip().strip(",").strip(" bytes")),
                }
            )
    return cfd


def _sum_lines(epoch_stats: List[str], prefix: str) -> int:
    return sum(
        int(line.split(":")[1]) for line in epoch_stats if line.startswith(prefix)
    )


def _workload_execution_time(epoch_stats: List[str]) -> float:
    for line in epoch_stats:
        if line.startswith("Workload Execution Time"):
            return float(line.split(": ")[1])
    return 0.0


def _max_nonempty_levels(cfd: Dict) -> int:
    sorted_cfd = sorted(cfd["Levels"], key=lambda x: x["Level"])
    while sorted_cfd and sorted_cfd[-1]["LevelSize"] == 0:
        sorted_cfd.pop()
    return len(sorted_cfd)


def _compaction_debt(levels: List[Dict], L: int) -> int:
    sum_of_bytes  = 0
    last_lvl_index = L - 1
    for lvl, data in enumerate(levels):
        if lvl == last_lvl_index:
            break
        sum_of_bytes += data.get("LevelSize", 0) * SIZE_RATIO * (last_lvl_index - lvl + 1)
    return sum_of_bytes + levels[L - 1].get("LevelSize", 0)


class LogStats:
    """Last-epoch workload metrics for a single experiment directory."""

    def __init__(self, logdir: str):
        self.epochs = _read_epochs(os.path.join(logdir, LOG_FILENAME))
        self.cfds   = [_parse_levels(e) for e in self.epochs]
        self.max_levels = [_max_nonempty_levels(cfd) for cfd in self.cfds]

        rq = pd.read_csv(os.path.join(logdir, RQ_FILENAME))
        rq = rq.map(lambda x: x.strip() if isinstance(x, str) else x)
        rq.columns = rq.columns.str.strip()
        self.rq = rq

    def last_epoch_stats(self, max_lvls_per_epoch: List[int]) -> Dict:
        epoch = len(self.epochs) - 1
        L     = max_lvls_per_epoch[epoch]
        cfd   = self.cfds[epoch]
        es    = self.epochs[epoch]

        sorted_cfd = sorted(cfd["Levels"], key=lambda x: x["Level"])
        n = len(sorted_cfd) - 1
        while sorted_cfd:
            if sorted_cfd[n]["LevelSize"] == 0 and n >= L:
                sorted_cfd.pop()
                n -= 1
            else:
                break

        return {
            "CompactionDebt":          _compaction_debt(sorted_cfd, L),
            "DBSize":                  cfd["Size"],
            "CompactionWrittenBytes":  _sum_lines(es, "rocksdb.compact.write.bytes"),
            "CompactionReadBytes":     _sum_lines(es, "rocksdb.compact.read.bytes"),
            "RangeReduceWrittenBytes": _sum_lines(es, "rocksdb.rangereduce.write.bytes"),
            "WorkloadExecutionTime":   _workload_execution_time(es),
        }

# ===================================================================
# Metrics — (row label, value extractor).  Order = heatmap row order.
# ===================================================================

def _rq_entries_read(rq: pd.DataFrame) -> pd.Series:
    return rq[TOTAL_ENTRIES_READ].astype(float)


METRICS = [
    ("space amplification",
     lambda p, rq: p["DBSize"] / (INSERTS * ENTRY_SIZE)),
    ("compaction debt",
     lambda p, rq: p["CompactionDebt"] / (1024 ** 2)),
    ("compaction reads",
     lambda p, rq: p["CompactionReadBytes"] / (1024 ** 2)),
    ("avg. bytes read in RQ",
     lambda p, rq: _rq_entries_read(rq).mean() * ENTRY_SIZE / (1024 ** 2)),
    ("total writes",
     lambda p, rq: (p["RangeReduceWrittenBytes"] + p["CompactionWrittenBytes"]) / (1024 ** 2)),
    ("total data movement",
     lambda p, rq: (
         p["CompactionWrittenBytes"] + p["CompactionReadBytes"] + p["RangeReduceWrittenBytes"]
         + _rq_entries_read(rq).sum() * ENTRY_SIZE
     ) / (1024 ** 3)),
    ("avg. RQ latency",
     lambda p, rq: rq[RQ_TOTAL_TIME].astype(float).mean() / (1000 ** 3)),
    ("total execution time",
     lambda p, rq: p["WorkloadExecutionTime"] / (1000 ** 3)),
]

ROW_LABELS = [name for name, _ in METRICS]

# ===================================================================
# Data loading — last-epoch stats per approach, shared max-level scaling.
# ===================================================================

loaded: Dict[str, LogStats] = {}
for label, dirname, _ in APPROACHES:
    loaded[label] = LogStats(os.path.join(EXP_DIR, dirname))

max_epoch_len      = max(len(s.max_levels) for s in loaded.values())
max_lvls_per_epoch = [0] * max_epoch_len
for s in loaded.values():
    for i, lvl in enumerate(s.max_levels):
        max_lvls_per_epoch[i] = max(max_lvls_per_epoch[i], lvl)

ps: Dict[str, Dict]         = {}
rq: Dict[str, pd.DataFrame] = {}
lb_of: Dict[str, float]     = {}
for label, dirname, lb in APPROACHES:
    ps[label]    = loaded[label].last_epoch_stats(max_lvls_per_epoch)
    rq[label]    = loaded[label].rq
    lb_of[label] = lb

# ===================================================================
# Build the normalized DataFrame (rows = metrics, cols = RangeReduceRatio).
# ===================================================================

records = {
    label: {name: fn(ps[label], rq[label]) for name, fn in METRICS}
    for label, _, _ in APPROACHES
}

df = pd.DataFrame(records).reindex(ROW_LABELS)

df_norm = df.div(df["RocksDB"], axis=0).drop(columns=["RocksDB"])

# Columns ordered by ascending lower bound (matches the original sweep order).
ordered_cols = sorted(
    [label for label, _, _ in APPROACHES if label != "RocksDB"],
    key=lambda l: lb_of[l],
)
df_norm = df_norm[ordered_cols]

# ===================================================================
# Plot — final RangeReduceRatio heatmap (seaborn-free).
# ===================================================================

fig, ax = plt.subplots(figsize=(10, 4))
data = df_norm.to_numpy(dtype=float)
im = ax.imshow(data, cmap="viridis", vmin=0, vmax=2.5, aspect="auto")

ax.set_xticks(range(df_norm.shape[1]))
ax.set_xticklabels(df_norm.columns)
ax.set_yticks(range(df_norm.shape[0]))
ax.set_yticklabels(df_norm.index)
ax.set_xlabel("RangeReduceRatio")

# Annotate each cell; flip text color for dark backgrounds.
for r in range(data.shape[0]):
    for c in range(data.shape[1]):
        val = data[r, c]
        ax.text(
            c, r, f"{val:.2f}", ha="center", va="center", fontsize=16,
            color="white" if val < 1.25 else "black",
        )

ax.text(
    -0.25, -0.05, "$normalized\\ by$\n$RocksDB$", transform=ax.transAxes,
    fontsize=20, ha="center", va="top", color="gray",
)

cbar = fig.colorbar(im, ax=ax)
cbar.set_ticks([0, 2.5])
cbar.set_ticklabels(["0", "2.5"])

plt.tight_layout()
plt.savefig(
    os.path.join(OUTPUT_DIR, "RangeReduceRatio.pdf"),
    bbox_inches="tight", pad_inches=0.02,
)
plt.close(fig)

# ===================================================================
# Separate config legend figure.
# ===================================================================

legend_fig  = plt.figure(figsize=(8, 2))
legend_text = (
    f"M={round((ENTRY_SIZE * ENTRIES_PER_PAGE * NUM_PAGE_PER_FILE) / (1024 * 1024))}MB\\hspace{{1cm}}"
    f"E={ENTRY_SIZE}B\\hspace{{1cm}}"
    f"T={SIZE_RATIO}\\hspace{{1cm}}"
    f"I={round(INSERTS / 1000000, 1)}M\\hspace{{1cm}}"
    f"U={round(UPDATES / 1000000, 1)}M\\hspace{{1cm}}"
    f"S={round(RANGE_QUERIES / 1000)}K\\hspace{{1cm}}"
    f"s={SELECTIVITY}"
)
legend_fig.text(0.5, 0.85, legend_text, ha="center", va="center")
legend_fig.savefig(
    os.path.join(OUTPUT_DIR, "rangereduceratio-legend-config.pdf"),
    bbox_inches="tight", pad_inches=0.015,
)
plt.close(legend_fig)
