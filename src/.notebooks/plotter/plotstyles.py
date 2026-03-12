# ==========================
# COMMON BASE STYLE SETTINGS
# ==========================
common_bar_style = {
    "color": "None",
    "linewidth": 0.2,
}

common_line_style = {
    "markersize": 12,
    "markerfacecolor": "none",
    "linewidth": 2,
}

# ==========================
# INDIVIDUAL POINT STYLES
# ==========================
point_styles = {
    "RocksDB": {
        "label": "RocksDB",
        "color": "grey",
        # "marker": "^",
        # "facecolors": "none",
        "alpha": 0.9,
    },
    "RangeReduce[lb=0 & smlck=0]": {
        "label": "Merge-on-Scan",
        "color": "#9C27B0",
        # "marker": "v",
        # "facecolors": "none",
        "alpha": 0.75,
    },
    "RangeReduce[lb=0]": {
        "label": "File-Size-Aware-Merge-on-Scan",
        "color": "tab:orange",
        # "marker": "+",
        # "facecolors": "none",
        "alpha": 0.75,
    },
    "SuccinctKV": {
        "label": "SuccinctKV",
        "color": "#0077FF",
        # "marker": "s",
        # "facecolors": "none",
        "alpha": 0.5,
    },
    "RangeReduce[lb=T^-1]": {
        "label": "Bounded-Merge",
        "color": "#00C853",
        # "marker": "x",
        # "facecolors": "none",
        "alpha": 0.5,
    },
    "RangeReduce[lb=T^-1 & re=1]": {
        "label": "RangeReduce",
        "color": "#FF1744",
        # "marker": "o",
        # "facecolors": "none",
        "alpha": 0.5,
    },
}

# ==========================
# INDIVIDUAL BAR STYLES
# ==========================
bar_styles = {
    "RocksDB": {
        **common_bar_style,
        "label": "RocksDB",
        "edgecolor": "grey",
        "hatch": "",
        "color": "grey",
    },
    "RangeReduce[lb=0 & smlck=0]": {
        **common_bar_style,
        "label": "Merge-on-Scan",
        "edgecolor": "#9C27B0",
        "hatch": "//",
    },
    "RangeReduce[lb=0]": {
        **common_bar_style,
        "label": "File-Size-Aware-Merge-on-Scan",
        "edgecolor": "tab:orange",
        "hatch": "\\\\",
    },
    "SuccinctKV": {
        **common_bar_style,
        "label": "SuccinctKV",
        "edgecolor": "#0077FF",
        "hatch": "\\\\\\\\",
    },
    "RangeReduce[lb=T^-1]": {
        **common_bar_style,
        "label": "Bounded-Merge",
        "edgecolor": "#00C853",
        "hatch": "--",
    },
    "RangeReduce[lb=T^-1 & re=1]": {
        **common_bar_style,
        "label": "RangeReduce",
        "edgecolor": "#FF1744",
        "hatch": "x",
    },
}

# ==========================
# INDIVIDUAL LINE STYLES
# ==========================
line_styles = {
    "RocksDB": {
        **common_line_style,
        "label": "RocksDB",
        "color": "grey",
        "linestyle": "-",
        "marker": "^",
    },
    "RangeReduce[lb=0 & smlck=0]": {
        **common_line_style,
        "label": "Merge-on-Scan",
        "color": "#9C27B0",
        "linestyle": "--",
        "marker": "v",
    },
    "RangeReduce[lb=0]": {
        **common_line_style,
        "label": "File-Size-Aware-Merge-on-Scan",
        "color": "tab:orange",
        "linestyle": (0, (3, 1, 1, 1, 1, 1)),
        "marker": "+",
    },
    "SuccinctKV": {
        **common_line_style,
        "label": "SuccinctKV",
        "color": "#0077FF",
        "linestyle": "-.",
        "marker": "s",
    },
    "RangeReduce[lb=T^-1]": {
        **common_line_style,
        "label": "Bounded-Merge",
        "color": "#00C853",
        "linestyle": ":",
        "marker": "x",
    },
    "RangeReduce[lb=T^-1 & re=1]": {
        **common_line_style,
        "label": "RangeReduce",
        "color": "#FF1744",
        "linestyle": (0, (5, 2)),
        "marker": "o",
    },
}

box_styles = {
    "RocksDB": {
        "linewidth": 0.05,
        "label": "RocksDB",
        "facecolor": "grey",
        "hatch": "",
        "edgecolor": "none",
    },
    "SuccinctKV": {
        "linewidth": 0.05,
        "label": "SuccinctKV",
        "facecolor": "#0077FF",
        "hatch": "\\\\\\\\",
        "edgecolor": "none",
    },
    "RangeReduce[lb=T^-1]": {
        "linewidth": 0.05,
        "label": "Bounded-Merge",
        "facecolor": "#00C853",
        "hatch": "////",
        "edgecolor": "none",
    },
    "RangeReduce[lb=T^-1 & re=1]": {
        "linewidth": 0.05,
        "label": "RangeReduce",
        "facecolor": "#FF1744",
        "hatch": "xx",
        "edgecolor": "none",
    },
}


line_styles_no_marker = {k: {**v, "marker": None} for k, v in line_styles.items()}

point_styles_with_abbr = {
    k: {**v, "label": v["label"].split()[0] + f" ({abbr})"}
    for (k, v), abbr in zip(
        point_styles.items(), ["RDB", "MoS", "FSMoS", "SKV", "BM", "RR"]
    )
}


line_styles_no_marker_with_abbr = {
    k: {**v, "label": v["label"].split()[0] + f" ({abbr})", "marker": None}
    for (k, v), abbr in zip(
        line_styles.items(), ["RDB", "MoS", "FSMoS", "SKV", "BM", "RR"]
    )
}

line_styles_with_abbr = {
    k: {**v, "label": v["label"].split()[0] + f" ({abbr})"}
    for (k, v), abbr in zip(
        line_styles.items(), ["RDB", "MoS", "FSMoS", "SKV", "BM", "RR"]
    )
}