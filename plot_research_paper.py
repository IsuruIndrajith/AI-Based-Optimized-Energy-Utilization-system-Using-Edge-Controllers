"""
plot_research_paper.py
======================
Generates 5 publication-quality, IEEE-style research paper figures.

Usage:
    python3 plot_research_paper.py --outdir figures/paper/

Figures produced:
    fig1_cost_comparison.png/pdf       – Baseline vs Optimised cost per appliance
    fig2_lstm_energy_demand.png/pdf    – LSTM predicted hourly energy demand (24 h)
    fig3_schedule_heatmap.png/pdf      – 24-hour appliance schedule heatmap
    fig4_peak_load.png/pdf             – Peak-load comparison (baseline vs agent)
    fig5_performance_summary.png/pdf   – KPI summary bar / radar chart
"""

import argparse
import json
import os
import sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import LinearSegmentedColormap

# ── Paths ────────────────────────────────────────────────────────────────────
BASE = os.path.abspath(os.path.join(os.path.dirname(__file__)))
sys.path.insert(0, os.path.join(BASE, "src"))
from config import (
    APPLIANCES, POWER_KWH,
    LECO_RATE_OFF_PEAK_LKR, LECO_RATE_DAY_LKR, LECO_RATE_PEAK_LKR,
    LECO_DAY_START_HOUR, LECO_DAY_END_HOUR,
    LECO_PEAK_START_HOUR, LECO_PEAK_END_HOUR,
)

# ── IEEE-style global settings ───────────────────────────────────────────────
plt.rcParams.update({
    "font.family":       "DejaVu Serif",
    "font.size":         10,
    "axes.titlesize":    11,
    "axes.labelsize":    10,
    "xtick.labelsize":   9,
    "ytick.labelsize":   9,
    "legend.fontsize":   9,
    "axes.linewidth":    0.8,
    "axes.grid":         True,
    "grid.linestyle":    "--",
    "grid.alpha":        0.4,
    "grid.linewidth":    0.5,
    "figure.dpi":        300,
    "savefig.dpi":       300,
    "savefig.bbox":      "tight",
    "savefig.pad_inches": 0.05,
})

# ── Colour palette (accessible, professional) ────────────────────────────────
C_BASELINE  = "#4472C4"   # blue
C_AGENT     = "#ED7D31"   # orange
C_SAVING    = "#70AD47"   # green
C_PEAK      = "#FF4040"   # red
C_OFFPEAK   = "#5B9BD5"   # light blue
C_DAY       = "#FFC000"   # amber

APPLIANCE_LABELS = {
    "WashingMachine_Power": "Washing\nMachine",
    "Heater_Power":         "Heater",
    "AC_Power":             "Air\nConditioner",
    "VehicleCharger_Power": "EV\nCharger",
    "VacuumCleaner_Power":  "Vacuum\nCleaner",
}

# ── Load pipeline data ────────────────────────────────────────────────────────
def load_data():
    with open(os.path.join(BASE, "appliance_data.json"), "r") as f:
        ad = json.load(f)
    with open(os.path.join(BASE, "output.json"), "r") as f:
        sched = json.load(f)
    return ad, sched

def build_price_map():
    pm = {}
    for h in range(24):
        pm[h] = {"price": LECO_RATE_OFF_PEAK_LKR, "band": "off_peak"}
    for h in range(LECO_DAY_START_HOUR, LECO_DAY_END_HOUR):
        pm[h] = {"price": LECO_RATE_DAY_LKR, "band": "day"}
    for h in range(LECO_PEAK_START_HOUR, LECO_PEAK_END_HOUR):
        pm[h] = {"price": LECO_RATE_PEAK_LKR, "band": "peak"}
    return pm

def cost_from_averages(averages, power_kwh, price_map):
    total = 0.0
    for h, avg_w in enumerate(averages):
        kwh = avg_w / 1000.0
        total += kwh * price_map[h]["price"]
    return total

def cost_from_states(states, power_kwh, price_map):
    return sum(s * power_kwh * price_map[h]["price"]
               for h, s in enumerate(states))

def save(fig, path_base, fmt_list=("png", "pdf")):
    for fmt in fmt_list:
        fig.savefig(f"{path_base}.{fmt}")
    print(f"  Saved -> {path_base}.png / .pdf")

# =============================================================================
# FIG 1 -- Cost Comparison (Baseline vs Optimised)
# =============================================================================
def fig1_cost_comparison(ad, sched, price_map, outdir):
    labels   = [APPLIANCE_LABELS[a] for a in APPLIANCES]
    baseline = []
    agent    = []

    for a in APPLIANCES:
        b = cost_from_averages(ad[a]["averages"], POWER_KWH[a], price_map)
        o = cost_from_states(sched[a], POWER_KWH[a], price_map)
        baseline.append(b)
        agent.append(o)

    x = np.arange(len(APPLIANCES))
    w = 0.33
    fig, ax = plt.subplots(figsize=(7.0, 3.8))

    bars_b = ax.bar(x - w/2, baseline, w, label="Baseline (LSTM Predicted)",
                    color=C_BASELINE, edgecolor="white", linewidth=0.6, zorder=3)
    bars_a = ax.bar(x + w/2, agent,    w, label="Optimised (MILP Agent)",
                    color=C_AGENT,    edgecolor="white", linewidth=0.6, zorder=3)

    for i, (b, a_val) in enumerate(zip(baseline, agent)):
        pct = (b - a_val) / b * 100
        ax.annotate(f"{pct:.0f}%",
                    xy=(x[i] + w/2, a_val),
                    xytext=(0, 4), textcoords="offset points",
                    ha="center", fontsize=7.5, color=C_SAVING, fontweight="bold")

    tot_base  = sum(baseline)
    tot_agent = sum(agent)
    tot_pct   = (tot_base - tot_agent) / tot_base * 100
    ax.text(0.99, 0.97,
            f"Total savings: {tot_pct:.1f}%\n({tot_base:.0f} -> {tot_agent:.0f} LKR/day)",
            transform=ax.transAxes, ha="right", va="top",
            fontsize=8.5, color="#222222",
            bbox=dict(boxstyle="round,pad=0.35", fc="white", ec="#AAAAAA", lw=0.7))

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=9)
    ax.set_ylabel("Daily Energy Cost (LKR)")
    ax.set_title("Fig. 1 -- Appliance-Level Cost Comparison: LSTM Baseline vs. MILP-Optimised Schedule", pad=8)
    ax.legend(loc="upper right", framealpha=0.9)
    ax.set_ylim(0, max(baseline) * 1.28)
    ax.yaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)
    fig.tight_layout()
    save(fig, os.path.join(outdir, "fig1_cost_comparison"))
    plt.close(fig)


# =============================================================================
# FIG 2 -- LSTM Hourly Energy Demand (24 h)
# =============================================================================
def fig2_lstm_demand(ad, price_map, outdir):
    hours = np.arange(24)

    fig, ax = plt.subplots(figsize=(7.0, 3.5))

    # TOU band background shading
    for h in range(24):
        band   = price_map[h]["band"]
        colour = {"off_peak": "#EBF5FB", "day": "#FEF9E7", "peak": "#FDEDEC"}[band]
        ax.axvspan(h - 0.5, h + 0.5, color=colour, alpha=0.7, linewidth=0)

    line_styles = ["-", "--", "-.", ":", (0,(3,1,1,1))]
    markers     = ["o", "s", "^", "D", "v"]
    colours     = ["#2E75B6", "#C55A11", "#538135", "#7030A0", "#C00000"]

    for i, a in enumerate(APPLIANCES):
        vals = np.array(ad[a]["averages"]) / 1000.0
        ax.plot(hours, vals,
                linestyle=line_styles[i], marker=markers[i],
                color=colours[i], markersize=4, linewidth=1.4,
                label=APPLIANCE_LABELS[a].replace("\n", " "), zorder=5)

    leg_patches = [
        mpatches.Patch(facecolor="#EBF5FB", edgecolor="#ADB5BD", label="Off-Peak"),
        mpatches.Patch(facecolor="#FEF9E7", edgecolor="#ADB5BD", label="Day"),
        mpatches.Patch(facecolor="#FDEDEC", edgecolor="#ADB5BD", label="Peak"),
    ]
    leg1 = ax.legend(handles=leg_patches, loc="upper left", fontsize=7.5,
                     title="TOU Band", title_fontsize=8, framealpha=0.92)
    ax.add_artist(leg1)
    ax.legend(loc="upper center", fontsize=7.5, ncol=3, framealpha=0.92)

    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("Predicted Energy Demand (kWh)")
    ax.set_title("Fig. 2 -- LSTM-Predicted Hourly Energy Demand per Appliance (24 h)", pad=8)
    ax.set_xticks(hours)
    ax.set_xticklabels([f"{h:02d}:00" for h in hours], rotation=45, fontsize=7.5)
    ax.set_xlim(-0.5, 23.5)
    ax.yaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)
    fig.tight_layout()
    save(fig, os.path.join(outdir, "fig2_lstm_demand"))
    plt.close(fig)


# =============================================================================
# FIG 3 -- 24-Hour Appliance Schedule Heatmap
# =============================================================================
def fig3_schedule_heatmap(sched, price_map, outdir):
    hours  = np.arange(24)
    n_apps = len(APPLIANCES)

    grid = np.zeros((n_apps, 24))
    for i, a in enumerate(APPLIANCES):
        grid[i, :] = sched[a]

    tou_row = np.array([
        {"off_peak": 0, "day": 1, "peak": 2}[price_map[h]["band"]]
        for h in hours
    ], dtype=float)

    fig, axes = plt.subplots(2, 1, figsize=(7.0, 4.2),
                             gridspec_kw={"height_ratios": [4, 0.6], "hspace": 0.12})

    ax = axes[0]
    cmap_sched = LinearSegmentedColormap.from_list("sched", ["#F8F9FA", "#2E75B6"], N=2)
    ax.imshow(grid, cmap=cmap_sched, vmin=0, vmax=1, aspect="auto", interpolation="nearest")

    for x in np.arange(-0.5, 24, 1):
        ax.axvline(x, color="white", linewidth=0.6)
    for y in np.arange(-0.5, n_apps, 1):
        ax.axhline(y, color="white", linewidth=0.6)

    for i in range(n_apps):
        for h in range(24):
            val = int(grid[i, h])
            txt = "ON" if val else ""
            ax.text(h, i, txt, ha="center", va="center",
                    fontsize=6.5, color="white" if val else "#AAAAAA", fontweight="bold")

    ax.set_yticks(range(n_apps))
    ax.set_yticklabels([APPLIANCE_LABELS[a].replace("\n", " ") for a in APPLIANCES], fontsize=9)
    ax.set_xticks([])
    ax.set_title("Fig. 3 -- Optimised 24-Hour Appliance ON/OFF Schedule", pad=8)

    off_patch = mpatches.Patch(facecolor="#F8F9FA", edgecolor="#ADB5BD", label="OFF")
    on_patch  = mpatches.Patch(facecolor="#2E75B6", label="ON")
    ax.legend(handles=[on_patch, off_patch], loc="upper right", fontsize=8, framealpha=0.9)

    ax2 = axes[1]
    tou_cmap = LinearSegmentedColormap.from_list("tou", ["#D6EAF8", "#FDEBD0", "#FADBD8"], N=3)
    ax2.imshow(tou_row[np.newaxis, :], cmap=tou_cmap, vmin=0, vmax=2,
               aspect="auto", interpolation="nearest")
    for h in range(24):
        band   = price_map[h]["band"]
        label  = {"off_peak": "OP", "day": "D", "peak": "PK"}[band]
        colour = {"off_peak": "#1A5276", "day": "#7D6608", "peak": "#922B21"}[band]
        ax2.text(h, 0, label, ha="center", va="center",
                 fontsize=6.5, color=colour, fontweight="bold")
    ax2.set_yticks([0])
    ax2.set_yticklabels(["TOU\nBand"], fontsize=8)
    ax2.set_xticks(range(24))
    ax2.set_xticklabels([f"{h:02d}" for h in range(24)], fontsize=7.5)
    ax2.set_xlabel("Hour of Day")

    fig.tight_layout()
    save(fig, os.path.join(outdir, "fig3_schedule_heatmap"))
    plt.close(fig)


# =============================================================================
# FIG 4 -- Peak Load Comparison
# =============================================================================
def fig4_peak_load(sched, outdir):
    hours = np.arange(24)

    baseline_load = np.zeros(24)
    agent_load    = np.zeros(24)

    for a in APPLIANCES:
        baseline_load += np.ones(24) * POWER_KWH[a]
        agent_load    += np.array(sched[a]) * POWER_KWH[a]

    fig, ax = plt.subplots(figsize=(7.0, 3.5))

    ax.fill_between(hours, baseline_load, alpha=0.18, color=C_BASELINE, zorder=2)
    ax.fill_between(hours, agent_load,    alpha=0.22, color=C_AGENT,    zorder=3)
    ax.plot(hours, baseline_load, color=C_BASELINE, linewidth=1.8, marker="o",
            markersize=4, label="Baseline Load", zorder=4)
    ax.plot(hours, agent_load,    color=C_AGENT,    linewidth=1.8, marker="s",
            markersize=4, label="Optimised Load",  zorder=5, linestyle="--")

    for h in range(LECO_PEAK_START_HOUR, LECO_PEAK_END_HOUR):
        ax.axvspan(h - 0.5, h + 0.5, alpha=0.10, color=C_PEAK, zorder=1)
    ax.axvspan(LECO_PEAK_START_HOUR - 0.5, LECO_PEAK_END_HOUR - 0.5, alpha=0, color=C_PEAK,
               label=f"Peak Band ({LECO_PEAK_START_HOUR}:00-{LECO_PEAK_END_HOUR}:00)")

    peak_b    = baseline_load.max()
    peak_a    = agent_load.max()
    reduction = (peak_b - peak_a) / peak_b * 100

    ax.axhline(peak_b, color=C_BASELINE, linestyle=":", linewidth=1.0, alpha=0.7)
    ax.axhline(peak_a, color=C_AGENT,    linestyle=":", linewidth=1.0, alpha=0.7)
    ax.text(23.3, peak_b + 0.05, f"{peak_b:.1f} kW", va="bottom", ha="right",
            fontsize=8, color=C_BASELINE)
    ax.text(23.3, peak_a - 0.12, f"{peak_a:.1f} kW", va="top", ha="right",
            fontsize=8, color=C_AGENT)

    ax.text(0.02, 0.97, f"Peak reduction: {reduction:.1f}%",
            transform=ax.transAxes, ha="left", va="top",
            fontsize=9, color=C_SAVING, fontweight="bold",
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#AAAAAA", lw=0.6))

    ax.set_xlabel("Hour of Day")
    ax.set_ylabel("Total Load (kW)")
    ax.set_title("Fig. 4 -- 24-Hour Load Profile: Baseline vs. Optimised Agent", pad=8)
    ax.set_xticks(hours)
    ax.set_xticklabels([f"{h:02d}:00" for h in hours], rotation=45, fontsize=7.5)
    ax.set_xlim(-0.5, 23.5)
    ax.legend(loc="upper left", fontsize=8.5, framealpha=0.9)
    ax.yaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)
    fig.tight_layout()
    save(fig, os.path.join(outdir, "fig4_peak_load"))
    plt.close(fig)


# =============================================================================
# FIG 5 -- System KPI Summary
# =============================================================================
def fig5_kpi_summary(ad, sched, price_map, outdir):
    baselines = [cost_from_averages(ad[a]["averages"], POWER_KWH[a], price_map) for a in APPLIANCES]
    agents    = [cost_from_states(sched[a], POWER_KWH[a], price_map) for a in APPLIANCES]
    savings   = [(b - o) / b * 100 for b, o in zip(baselines, agents)]

    required_h = []
    sched_h    = []
    for a in APPLIANCES:
        avgs      = ad[a]["averages"]
        total_kwh = sum(v / 1000 for v in avgs)
        rh        = max(1, round(total_kwh / POWER_KWH[a]))
        required_h.append(rh)
        sched_h.append(sum(sched[a]))

    accuracy = [min(100, s / r * 100) for r, s in zip(required_h, sched_h)]
    labels   = [APPLIANCE_LABELS[a].replace("\n", " ") for a in APPLIANCES]

    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.6))

    # Left -- Cost savings %
    ax = axes[0]
    y  = np.arange(len(APPLIANCES))
    bars = ax.barh(y, savings, color=C_SAVING, edgecolor="white",
                   linewidth=0.5, height=0.55, zorder=3)
    for bar, val in zip(bars, savings):
        ax.text(val + 0.4, bar.get_y() + bar.get_height() / 2,
                f"{val:.1f}%", va="center", fontsize=8.5, fontweight="bold", color="#1a5c1a")
    ax.set_yticks(y)
    ax.set_yticklabels(labels, fontsize=9)
    ax.set_xlabel("Cost Savings (%)")
    ax.set_title("(a) Per-Appliance\nCost Savings", pad=6)
    ax.set_xlim(0, max(savings) * 1.30)
    ax.axvline(20, color="red", linestyle="--", linewidth=0.8, alpha=0.7, label="20% threshold")
    ax.legend(fontsize=7.5, loc="lower right")
    ax.xaxis.grid(True, zorder=0)
    ax.set_axisbelow(True)

    # Right -- LSTM accuracy %
    ax2 = axes[1]
    bar_colors = [C_AGENT if acc >= 70 else C_PEAK for acc in accuracy]
    bars2 = ax2.barh(y, accuracy, color=bar_colors, edgecolor="white",
                     linewidth=0.5, height=0.55, zorder=3)
    for bar, val in zip(bars2, accuracy):
        ax2.text(val + 0.4, bar.get_y() + bar.get_height() / 2,
                 f"{val:.0f}%", va="center", fontsize=8.5, fontweight="bold", color="#1a3c6a")
    ax2.set_yticks(y)
    ax2.set_yticklabels([], fontsize=9)
    ax2.set_xlabel("LSTM Runtime Coverage (%)")
    ax2.set_title("(b) LSTM Prediction\nAccuracy", pad=6)
    ax2.set_xlim(0, 120)
    ax2.axvline(70, color="red", linestyle="--", linewidth=0.8, alpha=0.7, label="70% threshold")
    ax2.legend(fontsize=7.5, loc="lower right")
    ax2.xaxis.grid(True, zorder=0)
    ax2.set_axisbelow(True)

    fig.suptitle("Fig. 5 -- System KPI Summary: Cost Savings & LSTM Accuracy", y=1.01, fontsize=10)
    fig.tight_layout()
    save(fig, os.path.join(outdir, "fig5_kpi_summary"))
    plt.close(fig)


# =============================================================================
# MAIN
# =============================================================================
def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--outdir", default="figures/paper/")
    args = parser.parse_args()

    outdir = os.path.abspath(args.outdir)
    os.makedirs(outdir, exist_ok=True)

    print(f"\n[plot_research_paper.py] Saving to: {outdir}\n")
    ad, sched = load_data()
    pm = build_price_map()

    print("[1/5] Fig 1 -- Cost Comparison...")
    fig1_cost_comparison(ad, sched, pm, outdir)

    print("[2/5] Fig 2 -- LSTM Hourly Demand...")
    fig2_lstm_demand(ad, pm, outdir)

    print("[3/5] Fig 3 -- Schedule Heatmap...")
    fig3_schedule_heatmap(sched, pm, outdir)

    print("[4/5] Fig 4 -- Peak Load Profile...")
    fig4_peak_load(sched, outdir)

    print("[5/5] Fig 5 -- KPI Summary...")
    fig5_kpi_summary(ad, sched, pm, outdir)

    print(f"\nDone. All 5 figures saved to: {outdir}\n")


if __name__ == "__main__":
    main()
