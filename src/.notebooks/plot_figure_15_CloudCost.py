import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.font_manager as font_manager
from plotter.plotstyles import line_styles, line_styles_no_marker, bar_styles
import numpy as np
from matplotlib.patches import Patch

prop = font_manager.FontProperties(fname="./plotter/LinLibertine_Mah.ttf")
plt.rcParams["font.family"] = prop.get_name()
plt.rcParams["text.usetex"] = True
plt.rcParams["font.size"] = 20

# Rates & Parameters (10 TB Dataset)
cloud_configs = {
    'AWS':   {'p_inst': 1.008, 'p_gb': 0.011 / 100},
    'GCP':   {'p_inst': 1.048, 'p_gb': 0.023 / 100},
    'Azure': {'p_inst': 1.008, 'p_gb': 0.027 / 128}
}

metrics = {
    'RocksDB': {'sa': 1.40, 'dm': 1.0},
    'SuccinctKV': {'sa': 1.15, 'dm': 0.9},
    'RangeReduce[lb=T^-1 & re=1]': {'sa': 1.05, 'dm': 0.85}
}

# Mapping colors to approaches
colors = {
    'RocksDB': '#7f8c8d',      # Gray
    'SuccinctKV': '#3498db',   # Blue
    'RangeReduce[lb=T^-1 & re=1]': '#e74c3c' # Red
}

time_years = [0.5, 1, 2, 4]
time_months = ["6", "12", "24", "48"]
approaches = ['RocksDB', 'SuccinctKV', 'RangeReduce[lb=T^-1 & re=1]']

fig, axes = plt.subplots(1, 3, figsize=(8, 2), sharey=True)

bar_width = 0.25
offsets = [-bar_width, 0, bar_width] # Offset for the 3 bars in each group

for i, (cloud, c) in enumerate(cloud_configs.items()):
    ax = axes[i]
    x = np.arange(len(time_years)) # 4 positions for the 4 time points
    
    for j, app in enumerate(approaches):
        m = metrics[app]
        color = colors[app]
        
        # Calculate costs for all time points
        stor_costs = [10000 * m['sa'] * c['p_gb'] * 8760 * t for t in time_years]
        comp_costs = [c['p_inst'] * m['dm'] * 8760 * t for t in time_years]
        
        # Position each of the 3 bars relative to the month center
        pos = x + offsets[j]

        if "hatch" in bar_styles[app]:
            del bar_styles[app]["hatch"]
        bar_styles[app]["color"] = "None"
        
        # Plot Storage component (Solid)
        ax.bar(pos, stor_costs, bar_width, **bar_styles[app], hatch="\\\\")
        # Plot Compute component (Hatched) stacked on top
        ax.bar(pos, comp_costs, bar_width, bottom=stor_costs, **bar_styles[app], hatch="////")

    # ax.set_title(cloud)
    ax.set_xticks(x)
    ax.set_xticklabels(time_months)
    ax.set_xlabel("month", fontsize=16)
    ax.tick_params(axis='x', labelsize=16)
    
    # Scale Y labels to 10^4 dollars
    ax.set_yticks([0, 50000, 100000, 150000])
    ax.set_yticklabels(["0", "5", "10", "15"])
    ax.tick_params(axis='y', labelsize=16)
    
    if i == 0:
        ax.set_ylabel(r"cost (\$)", fontsize=16)

pattern_legend_elements = [
    Patch(facecolor='none', edgecolor='black', hatch='\\\\', label='storage'),
    Patch(facecolor='none', edgecolor='black', hatch='////', label='compute')
]
# plt.tight_layout()
plt.savefig("cloudcost_grouped_stacked_bars.pdf", bbox_inches="tight", pad_inches=0.06)
