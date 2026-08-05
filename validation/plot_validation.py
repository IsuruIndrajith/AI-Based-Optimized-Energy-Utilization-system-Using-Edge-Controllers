"""
plot_validation.py - Research-Quality Validation Visualizations
===============================================================
Reads validation_report.json (produced by validate_policies.py) plus the
real pipeline outputs (appliance_data.json, output.json,
output_explanations.json) and generates publication-ready figures for a
research paper.

Figures produced (saved as high-DPI PNG + PDF):
  1. validation_summary_donut.png   - Policy pass/fail donut by category
  2. cost_savings_bar.png           - Per-appliance baseline vs agent cost
  3. cost_waterfall.png             - Waterfall chart of savings per appliance
  4. lstm_accuracy_bar.png          - LSTM required vs scheduled hours
  5. tou_heatmap.png                - 24-h appliance schedule heatmap (agent vs baseline)
  6. peak_load_comparison.png       - Hourly aggregate load comparison
  7. savings_gauge.png              - Gauge chart showing overall savings %
  8. combined_dashboard.png         - All panels in one figure

Usage:
    python plot_validation.py
    python plot_validation.py --outdir figures/
"""

import json, os, argparse, math, re
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec
import numpy as np

BASE = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(BASE, ".."))

def _get_path(fname):
    p = os.path.join(BASE, fname)
    return p if os.path.exists(p) else os.path.join(PROJECT_ROOT, fname)

REPORT_PATH   = _get_path("validation_report.json")
APP_DATA_PATH = _get_path("appliance_data.json")
OUTPUT_PATH   = _get_path("output.json")
EXPL_PATH     = _get_path("output_explanations.json")

LECO_RATE_OFF_PEAK = 33.0
LECO_RATE_DAY      = 47.0
LECO_RATE_PEAK     = 106.0
LECO_DAY_START = 5; LECO_DAY_END = 18
LECO_PEAK_START = 18; LECO_PEAK_END = 22

APPLIANCES = ["WashingMachine_Power","Heater_Power","AC_Power",
              "VehicleCharger_Power","VacuumCleaner_Power"]
POWER_KWH  = {"WashingMachine_Power":0.6,"Heater_Power":2.0,
               "AC_Power":1.2,"VehicleCharger_Power":2.2,"VacuumCleaner_Power":1.1}
SHORT_LABELS = {"WashingMachine_Power":"Washing\nMachine","Heater_Power":"Heater",
                "AC_Power":"AC","VehicleCharger_Power":"EV\nCharger",
                "VacuumCleaner_Power":"Vacuum\nCleaner"}

C_BASE="#4A90D9"; C_AGENT="#27AE60"; C_SAVE="#F39C12"
C_PEAK="#E74C3C"; C_DAY="#F1C40F";  C_OFF="#2ECC71"
C_FAIL="#E74C3C"; C_PASS="#2ECC71"; C_BG="#F8F9FA"; C_GRID="#DEE2E6"
FONT_TITLE={"fontsize":14,"fontweight":"bold","color":"#1A1A2E"}
FONT_LABEL={"fontsize":11,"color":"#343A40"}
DPI=300

def build_price_map():
    pm = {h: LECO_RATE_OFF_PEAK for h in range(24)}
    for h in range(LECO_DAY_START, LECO_DAY_END):   pm[h] = LECO_RATE_DAY
    for h in range(LECO_PEAK_START, LECO_PEAK_END): pm[h] = LECO_RATE_PEAK
    return pm

def cost_for_states(states, power_kwh, pm):
    return sum(s*power_kwh*pm[h] for h,s in enumerate(states) if s==1)

def cost_for_averages(averages, pm):
    return sum((avg / 1000.0) * pm[h] for h, avg in enumerate(averages))

def get_nominal_baseline_states(app_data):
    nominal = {}
    for a in APPLIANCES:
        averages = app_data[a].get("averages", [0.0]*24)
        power_rating = POWER_KWH.get(a, 1.0)
        req_h = int(round(sum(averages) / (power_rating * 1000.0)))
        req_h = max(0, min(24, req_h))
        orig_states = [0]*24
        if req_h > 0:
            top_indices = np.argsort(averages)[-req_h:]
            for idx in top_indices:
                orig_states[idx] = 1
        nominal[a] = orig_states
    return nominal

def hourly_load(schedules):
    hl = [0.0]*24
    for app in APPLIANCES:
        for h,s in enumerate(schedules.get(app,[0]*24)):
            hl[h] += s*POWER_KWH[app]
    return hl

def load_data():
    with open(REPORT_PATH)   as f: report     = json.load(f)
    with open(APP_DATA_PATH) as f: app_data   = json.load(f)
    with open(OUTPUT_PATH)   as f: agent_sched= json.load(f)
    with open(EXPL_PATH)     as f: expl       = json.load(f)
    return report, app_data, agent_sched, expl

def styled_ax(ax, title="", xlabel="", ylabel=""):
    ax.set_facecolor(C_BG)
    ax.grid(axis="y",color=C_GRID,linewidth=0.6,linestyle="--",zorder=0)
    ax.spines[["top","right"]].set_visible(False)
    ax.spines[["left","bottom"]].set_color("#ADB5BD")
    ax.tick_params(colors="#495057",labelsize=9)
    if title:   ax.set_title(title,**FONT_TITLE,pad=10)
    if xlabel:  ax.set_xlabel(xlabel,**FONT_LABEL,labelpad=6)
    if ylabel:  ax.set_ylabel(ylabel,**FONT_LABEL,labelpad=6)
    return ax

def save_fig(fig, outdir, name):
    for ext in ("png","pdf"):
        p = os.path.join(outdir,f"{name}.{ext}")
        fig.savefig(p,dpi=DPI,bbox_inches="tight",facecolor=fig.get_facecolor())
        print(f"  Saved -> {p}")

# --- Figure 1: Validation Summary Donut ---
def fig_donut(report, outdir):
    by_cat = report["summary"]["by_category"]
    cats = list(by_cat.keys())
    cat_labels = {"capacity":"Capacity\nConstraints","format":"Format\nChecks",
                  "llm_preference":"LLM\nPreference","lstm_accuracy":"LSTM\nAccuracy",
                  "cost_optimality":"Cost\nOptimality","savings_threshold":"Savings\nThreshold",
                  "weather_comfort":"Weather\nComfort"}
    labels  = [cat_labels.get(c,c) for c in cats]
    totals  = [by_cat[c]["total"]  for c in cats]
    passed  = [by_cat[c]["passed"] for c in cats]
    failed  = [t-p for t,p in zip(totals,passed)]
    palette = ["#3498DB","#9B59B6","#1ABC9C","#F39C12","#E67E22","#27AE60","#E74C3C"]

    fig,(ax1,ax2) = plt.subplots(1,2,figsize=(13,6),facecolor="white")
    fig.suptitle("Validation Policy Results Summary",fontsize=16,fontweight="bold",color="#1A1A2E")
    ax1.set_facecolor("white")
    wedges,texts,autotexts = ax1.pie(totals,labels=labels,colors=palette,autopct="%1.0f%%",
        startangle=140,wedgeprops=dict(width=0.52,edgecolor="white",linewidth=2),
        pctdistance=0.78,labeldistance=1.12)
    for t in texts:    t.set_fontsize(8); t.set_color("#343A40")
    for at in autotexts: at.set_fontsize(8); at.set_color("white"); at.set_fontweight("bold")
    tp=report["summary"]["passed"]; tt=report["summary"]["total_policies"]
    ax1.text(0,0,f"{tp}/{tt}",ha="center",va="center",fontsize=18,fontweight="bold",color="#1A1A2E")
    ax1.text(0,-0.22,"Policies\nPassed",ha="center",va="center",fontsize=9,color="#6C757D")
    ax1.set_title("Policy Distribution by Category",fontsize=12,fontweight="bold",pad=12,color="#1A1A2E")

    ax2.set_facecolor(C_BG); ax2.spines[["top","right"]].set_visible(False)
    ax2.spines[["left","bottom"]].set_color("#ADB5BD")
    xi = np.arange(len(cats)); ax2.bar(xi,passed,color=C_PASS,label="Passed",zorder=3,width=0.55)
    ax2.bar(xi,failed,bottom=passed,color=C_FAIL,label="Failed",zorder=3,width=0.55)
    for i,(p,t) in enumerate(zip(passed,totals)):
        ax2.text(i,p/2,str(p),ha="center",va="center",fontsize=9,fontweight="bold",color="white",zorder=4)
    ax2.set_xticks(xi); ax2.set_xticklabels(labels,fontsize=8,color="#495057")
    ax2.set_ylabel("Number of Policies",**FONT_LABEL)
    ax2.set_title("Pass / Fail by Category",fontsize=12,fontweight="bold",pad=12,color="#1A1A2E")
    ax2.legend(fontsize=9,framealpha=0.6)
    ax2.grid(axis="y",color=C_GRID,linewidth=0.6,linestyle="--",zorder=0)
    pr = report["summary"]["pass_rate_percentage"]
    fig.text(0.5,-0.02,f"Overall Pass Rate: {pr:.1f}%  |  Total Policies: {tt}",
             ha="center",fontsize=10,color="#495057",style="italic")
    plt.tight_layout(); save_fig(fig,outdir,"validation_summary_donut"); plt.close(fig)

# --- Figure 2: Cost Savings Bar ---
def fig_cost_savings(app_data, agent_sched, expl, outdir):
    pm = build_price_map()
    b_costs=[]; a_costs=[]; save_pct=[]
    for app in APPLIANCES:
        bc=cost_for_averages(app_data[app]["averages"],pm)
        ac=cost_for_states(agent_sched.get(app,[0]*24),POWER_KWH[app],pm)
        b_costs.append(bc); a_costs.append(ac)
        save_pct.append((bc-ac)/bc*100 if bc>0 else 0)
    x=np.arange(len(APPLIANCES)); w=0.34
    fig,ax=plt.subplots(figsize=(11,6),facecolor="white")
    styled_ax(ax,title="Per-Appliance Energy Cost: Baseline vs. Optimised Agent (LKR)",
              xlabel="Appliance",ylabel="Cost (LKR)")
    ax.bar(x-w/2,b_costs,width=w,color=C_BASE,label="Baseline (LSTM-predicted)",zorder=3,edgecolor="white")
    ax.bar(x+w/2,a_costs,width=w,color=C_AGENT,label="Optimised Agent (MILP)",zorder=3,edgecolor="white")
    for i,(bc,ac,sp) in enumerate(zip(b_costs,a_costs,save_pct)):
        ax.text(i-w/2,bc+8,f"Rs{bc:.0f}",ha="center",va="bottom",fontsize=8,fontweight="bold")
        ax.text(i+w/2,ac+8,f"Rs{ac:.0f}\n(-{sp:.0f}%)",ha="center",va="bottom",fontsize=7.5,color="#1A6B3A",fontweight="bold")
    ax.set_xticks(x); ax.set_xticklabels([SHORT_LABELS[a] for a in APPLIANCES],fontsize=10)
    ax.legend(fontsize=10,framealpha=0.7,loc="upper right")
    tb=sum(b_costs); ta=sum(a_costs); tsp=(tb-ta)/tb*100
    ax.text(0.98,0.97,f"Total Baseline: Rs{tb:.0f}\nTotal Agent:   Rs{ta:.0f}\nTotal Saving:  Rs{tb-ta:.0f}  ({tsp:.1f}%)",
            transform=ax.transAxes,ha="right",va="top",fontsize=9.5,color="#1A1A2E",
            bbox=dict(boxstyle="round,pad=0.5",facecolor="white",edgecolor=C_GRID,alpha=0.9))
    plt.tight_layout(); save_fig(fig,outdir,"cost_savings_bar"); plt.close(fig)

# --- Figure 3: Waterfall ---
def fig_waterfall(app_data, agent_sched, outdir):
    pm = build_price_map()
    b_costs=[cost_for_averages(app_data[a]["averages"],pm) for a in APPLIANCES]
    a_costs=[cost_for_states(agent_sched.get(a,[0]*24),POWER_KWH[a],pm) for a in APPLIANCES]
    savings=[b-a for b,a in zip(b_costs,a_costs)]
    labels=["Baseline\nTotal"]+[SHORT_LABELS[a] for a in APPLIANCES]+["Agent\nTotal"]
    running=sum(b_costs)
    bottoms,heights,colours=[0],[running],["#3498DB"]
    for sv in savings:
        bottoms.append(running-sv); heights.append(sv); colours.append(C_SAVE); running-=sv
    bottoms.append(0); heights.append(running); colours.append(C_AGENT)
    fig,ax=plt.subplots(figsize=(12,6),facecolor="white")
    styled_ax(ax,title="Cost Savings Waterfall (LSTM Baseline to MILP Agent, LKR)",ylabel="Cumulative Cost (LKR)")
    bars=ax.bar(range(len(labels)),heights,bottom=bottoms,color=colours,zorder=3,width=0.6,edgecolor="white",linewidth=1.0)
    for i,(bar,h,b) in enumerate(zip(bars,heights,bottoms)):
        ypos=b+h/2
        lbl=f"Rs{h:.0f}" if i==0 or i==len(labels)-1 else f"-Rs{h:.0f}"
        ax.text(bar.get_x()+bar.get_width()/2,ypos,lbl,ha="center",va="center",
                fontsize=8.5,fontweight="bold",color="white" if h>80 else "#343A40")
    for i in range(len(labels)-1):
        y=heights[0] if i==0 else bottoms[i]
        ax.plot([i+0.3,i+0.7],[y,y],color="#ADB5BD",linewidth=0.8,linestyle="--")
    ax.set_xticks(range(len(labels))); ax.set_xticklabels(labels,fontsize=9)
    legend_patches=[mpatches.Patch(color="#3498DB",label="Baseline Total"),
                    mpatches.Patch(color=C_SAVE,label="Per-Appliance Saving"),
                    mpatches.Patch(color=C_AGENT,label="Optimised Total")]
    ax.legend(handles=legend_patches,fontsize=9,framealpha=0.7)
    plt.tight_layout(); save_fig(fig,outdir,"cost_waterfall"); plt.close(fig)

# --- Figure 4: LSTM Accuracy ---
def fig_lstm_accuracy(app_data, agent_sched, outdir):
    required=[int(round(sum(app_data[a]["averages"]) / (POWER_KWH[a]*1000.0))) for a in APPLIANCES]
    required=[max(0, min(24, r)) for r in required]
    scheduled=[int(sum(agent_sched.get(a,[0]*24))) for a in APPLIANCES]
    match_pct=[100*(1-abs(r-s)/r) if r>0 else (100 if s==0 else 0) for r,s in zip(required,scheduled)]
    labels=[SHORT_LABELS[a] for a in APPLIANCES]; x=np.arange(len(APPLIANCES)); w=0.34
    fig,(ax1,ax2)=plt.subplots(1,2,figsize=(13,5.5),facecolor="white")
    styled_ax(ax1,title="LSTM-Predicted vs Agent-Scheduled Runtime",xlabel="Appliance",ylabel="Hours (h)")
    ax1.bar(x-w/2,required,width=w,color=C_BASE,label="LSTM Required",zorder=3,edgecolor="white")
    ax1.bar(x+w/2,scheduled,width=w,color=C_AGENT,label="Agent Scheduled",zorder=3,edgecolor="white")
    for i,(r,s) in enumerate(zip(required,scheduled)):
        ax1.text(i-w/2,r+0.1,str(r),ha="center",va="bottom",fontsize=9,fontweight="bold")
        ax1.text(i+w/2,s+0.1,str(s),ha="center",va="bottom",fontsize=9,fontweight="bold",color="#1A6B3A")
    ax1.set_xticks(x); ax1.set_xticklabels(labels,fontsize=9); ax1.legend(fontsize=9,framealpha=0.7)
    styled_ax(ax2,title="LSTM to Agent Schedule Match Accuracy (%)",xlabel="Match Accuracy (%)")
    bar_colours=[C_PASS if m>=80 else C_FAIL for m in match_pct]
    hbars=ax2.barh(labels,match_pct,color=bar_colours,zorder=3,height=0.5,edgecolor="white")
    ax2.axvline(80,color="#E74C3C",linewidth=1.2,linestyle="--",label="80% threshold")
    for bar,m in zip(hbars,match_pct):
        ax2.text(min(m+1.5,96),bar.get_y()+bar.get_height()/2,f"{m:.1f}%",va="center",fontsize=9,fontweight="bold")
    ax2.set_xlim(0,108); ax2.legend(fontsize=9)
    ax2.grid(axis="x",color=C_GRID,linewidth=0.6,linestyle="--",zorder=0)
    ax2.spines[["top","right"]].set_visible(False)
    avg=sum(match_pct)/len(match_pct)
    fig.text(0.5,-0.02,f"Average Schedule Match Accuracy: {avg:.1f}%",ha="center",fontsize=10,style="italic",color="#495057")
    plt.tight_layout(); save_fig(fig,outdir,"lstm_accuracy_bar"); plt.close(fig)

# --- Figure 5: TOU Heatmap ---
def fig_heatmap(app_data, agent_sched, outdir):
    baseline_sc = get_nominal_baseline_states(app_data)
    hours=np.arange(24)
    baseline_mat=np.array([baseline_sc[a] for a in APPLIANCES],dtype=float)
    agent_mat=np.array([agent_sched.get(a,[0]*24) for a in APPLIANCES],dtype=float)
    fig,axes=plt.subplots(2,1,figsize=(14,6),facecolor="white",gridspec_kw={"hspace":0.45})
    for ax,mat,title,cmap in zip(axes,[baseline_mat,agent_mat],
        ["LSTM Baseline Schedule (24-Hour ON/OFF)","Optimised Agent Schedule (24-Hour ON/OFF)"],
        ["Blues","Greens"]):
        ax.imshow(mat,aspect="auto",cmap=cmap,vmin=0,vmax=1,interpolation="nearest")
        ax.set_yticks(range(len(APPLIANCES))); ax.set_yticklabels([SHORT_LABELS[a] for a in APPLIANCES],fontsize=9)
        ax.set_xticks(hours)
        ax.set_xticklabels([f"{h:02d}:00" for h in hours],fontsize=7,rotation=45,ha="right")
        ax.set_title(title,**FONT_TITLE,pad=8); ax.tick_params(colors="#495057")
        for h in hours:
            if LECO_PEAK_START<=h<LECO_PEAK_END: ax.axvspan(h-0.5,h+0.5,color=C_PEAK,alpha=0.10,zorder=0)
            elif LECO_DAY_START<=h<LECO_DAY_END: ax.axvspan(h-0.5,h+0.5,color=C_DAY,alpha=0.06,zorder=0)
    legend_patches=[mpatches.Patch(color=C_OFF,alpha=0.5,label="Off-Peak"),
                    mpatches.Patch(color=C_DAY,alpha=0.5,label="Day band (05-18h)"),
                    mpatches.Patch(color=C_PEAK,alpha=0.5,label="Peak band (18-22h)"),
                    mpatches.Patch(color="#27AE60",label="ON"),
                    mpatches.Patch(color="#F8F9FA",label="OFF",edgecolor="#ADB5BD")]
    fig.legend(handles=legend_patches,loc="lower center",ncol=5,fontsize=8.5,framealpha=0.7,bbox_to_anchor=(0.5,-0.05))
    save_fig(fig,outdir,"tou_heatmap"); plt.close(fig)

# --- Figure 6: Peak Load ---
def fig_peak_load(app_data, agent_sched, outdir):
    baseline_sc = get_nominal_baseline_states(app_data)
    hours=np.arange(24); b_load=hourly_load(baseline_sc); a_load=hourly_load(agent_sched)
    fig,ax=plt.subplots(figsize=(13,5.5),facecolor="white")
    styled_ax(ax,title="Hourly Aggregate Load Profile: Baseline vs. Optimised Agent",xlabel="Hour of Day",ylabel="Total Load (kW)")
    ax.axvspan(-0.5,LECO_DAY_START-0.5,color=C_OFF,alpha=0.07,label="Off-Peak")
    ax.axvspan(LECO_DAY_START-0.5,LECO_DAY_END-0.5,color=C_DAY,alpha=0.10,label="Day")
    ax.axvspan(LECO_DAY_END-0.5,LECO_PEAK_END-0.5,color=C_PEAK,alpha=0.10,label="Peak")
    ax.axvspan(LECO_PEAK_END-0.5,23.5,color=C_OFF,alpha=0.07)
    ax.fill_between(hours,b_load,alpha=0.18,color=C_BASE); ax.fill_between(hours,a_load,alpha=0.18,color=C_AGENT)
    ax.plot(hours,b_load,"o-",color=C_BASE,linewidth=2.0,markersize=5,label=f"Baseline (peak={max(b_load):.2f} kW)",zorder=3)
    ax.plot(hours,a_load,"s-",color=C_AGENT,linewidth=2.0,markersize=5,label=f"Agent (peak={max(a_load):.2f} kW)",zorder=3)
    ax.set_xticks(hours); ax.set_xticklabels([f"{h:02d}h" for h in hours],fontsize=8,rotation=45)
    ax.set_xlim(-0.5,23.5); ax.legend(fontsize=9.5,framealpha=0.7,loc="upper left")
    plt.tight_layout(); save_fig(fig,outdir,"peak_load_comparison"); plt.close(fig)

# --- Figure 7: Savings Gauge ---
def fig_gauge(report, outdir):
    savings_pct=0.0
    for pol in report["policies"]:
        if pol["id"]=="POL_080":
            m=re.search(r"(\d+\.\d+)%",pol["reason"])
            if m: savings_pct=float(m.group(1))
    fig,ax=plt.subplots(figsize=(7,5),facecolor="white",subplot_kw={"aspect":"equal"})
    ax.set_facecolor("white"); ax.axis("off")
    from matplotlib.patches import Wedge
    centre=(0.5,0.28); r_outer=0.38; r_inner=0.24
    zone_colours=["#E74C3C","#E67E22","#F1C40F","#2ECC71","#27AE60"]
    zone_ranges=[(0,20),(20,40),(40,60),(60,80),(80,100)]
    for (lo,hi),col in zip(zone_ranges,zone_colours):
        w=Wedge(centre,r_outer,180-hi*1.8,180-lo*1.8,width=r_outer-r_inner,
                facecolor=col,edgecolor="white",linewidth=1.5,transform=ax.transAxes)
        ax.add_patch(w)
    needle_angle=math.radians(180-savings_pct*1.8); nl=r_inner-0.02
    nx=centre[0]+nl*math.cos(needle_angle); ny=centre[1]+nl*math.sin(needle_angle)
    ax.annotate("",xy=(nx,ny),xytext=centre,xycoords="axes fraction",textcoords="axes fraction",
                arrowprops=dict(arrowstyle="-|>",color="#1A1A2E",lw=2.5,mutation_scale=14))
    circle=plt.Circle(centre,0.022,color="#1A1A2E",transform=ax.transAxes,zorder=5)
    ax.add_patch(circle)
    ax.text(0.5,0.42,f"{savings_pct:.1f}%",transform=ax.transAxes,ha="center",va="center",
            fontsize=28,fontweight="bold",color="#1A1A2E")
    ax.text(0.5,0.32,"Cost Savings",transform=ax.transAxes,ha="center",va="center",fontsize=12,color="#6C757D")
    for (lo,hi),col in zip(zone_ranges,zone_colours):
        mid_angle=math.radians(180-(lo+hi)/2*1.8)
        rx=centre[0]+(r_outer+0.04)*math.cos(mid_angle); ry=centre[1]+(r_outer+0.04)*math.sin(mid_angle)
        ax.text(rx,ry,f"{lo}-{hi}%",transform=ax.transAxes,ha="center",va="center",fontsize=7,color=col,fontweight="bold")
    ax.set_title("Overall Energy Cost Savings Achieved",fontsize=13,fontweight="bold",color="#1A1A2E",pad=10,y=0.98)
    status="PASS - Research Threshold Exceeded (>=20%)" if savings_pct>=20 else "FAIL"
    ax.text(0.5,0.04,status,transform=ax.transAxes,ha="center",fontsize=11,
            color=C_PASS if savings_pct>=20 else C_FAIL,fontweight="bold")
    save_fig(fig,outdir,"savings_gauge"); plt.close(fig)

# --- Figure 8: Combined Dashboard ---
def fig_dashboard(report, app_data, agent_sched, outdir):
    pm=build_price_map()
    baseline_sc = get_nominal_baseline_states(app_data)
    hours=np.arange(24)
    b_costs=[cost_for_averages(app_data[a]["averages"],pm) for a in APPLIANCES]
    a_costs=[cost_for_states(agent_sched.get(a,[0]*24),POWER_KWH[a],pm) for a in APPLIANCES]
    save_pct=[(b-a)/b*100 if b>0 else 0 for b,a in zip(b_costs,a_costs)]
    required=[int(round(sum(app_data[a]["averages"]) / (POWER_KWH[a]*1000.0))) for a in APPLIANCES]
    required=[max(0, min(24, r)) for r in required]
    scheduled=[int(sum(agent_sched.get(a,[0]*24))) for a in APPLIANCES]
    match_pct=[100*(1-abs(r-s)/r) if r>0 else (100 if s==0 else 0) for r,s in zip(required,scheduled)]
    b_load=hourly_load(baseline_sc); a_load=hourly_load(agent_sched)
    by_cat=report["summary"]["by_category"]; cats=list(by_cat.keys())
    cat_labels={"capacity":"Capacity","format":"Format","llm_preference":"LLM Pref",
                "lstm_accuracy":"LSTM Acc","cost_optimality":"Cost Opt",
                "savings_threshold":"Savings","weather_comfort":"Weather"}
    passed_vals=[by_cat[c]["passed"] for c in cats]; total_vals=[by_cat[c]["total"] for c in cats]
    short_labels=[SHORT_LABELS[a] for a in APPLIANCES]; x=np.arange(len(APPLIANCES)); w=0.35

    fig=plt.figure(figsize=(20,14),facecolor="white")
    fig.suptitle("AI-Based Optimised Energy Utilisation - Validation Dashboard",
                 fontsize=18,fontweight="bold",color="#1A1A2E",y=0.98)
    gs=gridspec.GridSpec(3,3,figure=fig,hspace=0.52,wspace=0.38)

    ax_a=fig.add_subplot(gs[0,:2])
    styled_ax(ax_a,title="(a) Per-Appliance Cost: Baseline vs Agent (LKR)",ylabel="Cost (LKR)")
    ax_a.bar(x-w/2,b_costs,width=w,color=C_BASE,label="Baseline",zorder=3,edgecolor="white")
    ax_a.bar(x+w/2,a_costs,width=w,color=C_AGENT,label="Agent",zorder=3,edgecolor="white")
    for i,(bc,ac,sp) in enumerate(zip(b_costs,a_costs,save_pct)):
        ax_a.text(i-w/2,bc+5,f"Rs{bc:.0f}",ha="center",fontsize=7.5,fontweight="bold")
        ax_a.text(i+w/2,ac+5,f"Rs{ac:.0f}\n(-{sp:.0f}%)",ha="center",fontsize=7,color="#1A6B3A",fontweight="bold")
    ax_a.set_xticks(x); ax_a.set_xticklabels(short_labels,fontsize=9); ax_a.legend(fontsize=9)

    ax_b=fig.add_subplot(gs[0,2]); ax_b.set_facecolor("white")
    palette=["#3498DB","#9B59B6","#1ABC9C","#F39C12","#E67E22","#27AE60","#E74C3C"]
    wedges,_,autotexts=ax_b.pie(total_vals,colors=palette,autopct="%1.0f%%",startangle=140,
        wedgeprops=dict(width=0.50,edgecolor="white",linewidth=1.5),pctdistance=0.78)
    for at in autotexts: at.set_fontsize(7); at.set_color("white"); at.set_fontweight("bold")
    tp=report["summary"]["passed"]; tt=report["summary"]["total_policies"]
    ax_b.text(0,0,f"{tp}/{tt}",ha="center",va="center",fontsize=14,fontweight="bold",color="#1A1A2E")
    ax_b.text(0,-0.25,"Pass / Total",ha="center",va="center",fontsize=8,color="#6C757D")
    ax_b.set_title("(b) Policy Pass Rate",fontsize=11,fontweight="bold",color="#1A1A2E",pad=8)

    ax_c=fig.add_subplot(gs[1,0])
    styled_ax(ax_c,title="(c) LSTM Accuracy: Match %",xlabel="Match (%)")
    bar_colours=[C_PASS if m>=80 else C_FAIL for m in match_pct]
    hbars=ax_c.barh(short_labels,match_pct,color=bar_colours,height=0.5,zorder=3,edgecolor="white")
    ax_c.axvline(80,color=C_FAIL,linewidth=1.2,linestyle="--")
    for bar,m in zip(hbars,match_pct):
        ax_c.text(min(m+2,96),bar.get_y()+bar.get_height()/2,f"{m:.0f}%",va="center",fontsize=8,fontweight="bold")
    ax_c.set_xlim(0,108); ax_c.grid(axis="x",color=C_GRID,linewidth=0.6,linestyle="--")
    ax_c.spines[["top","right"]].set_visible(False)

    ax_d=fig.add_subplot(gs[1,1:])
    styled_ax(ax_d,title="(d) Hourly Load Profile (kW)",xlabel="Hour",ylabel="Load (kW)")
    ax_d.axvspan(-0.5,LECO_DAY_START-0.5,color=C_OFF,alpha=0.07)
    ax_d.axvspan(LECO_DAY_START-0.5,LECO_DAY_END-0.5,color=C_DAY,alpha=0.10)
    ax_d.axvspan(LECO_DAY_END-0.5,LECO_PEAK_END-0.5,color=C_PEAK,alpha=0.10)
    ax_d.axvspan(LECO_PEAK_END-0.5,23.5,color=C_OFF,alpha=0.07)
    ax_d.fill_between(hours,b_load,alpha=0.15,color=C_BASE); ax_d.fill_between(hours,a_load,alpha=0.15,color=C_AGENT)
    ax_d.plot(hours,b_load,"o-",color=C_BASE,lw=1.8,ms=4,label=f"Baseline (peak={max(b_load):.2f} kW)")
    ax_d.plot(hours,a_load,"s-",color=C_AGENT,lw=1.8,ms=4,label=f"Agent (peak={max(a_load):.2f} kW)")
    ax_d.set_xticks(hours); ax_d.set_xticklabels([f"{h:02d}" for h in hours],fontsize=7)
    ax_d.set_xlim(-0.5,23.5); ax_d.legend(fontsize=8,framealpha=0.7)

    ax_e=fig.add_subplot(gs[2,:2])
    agent_mat=np.array([agent_sched.get(a,[0]*24) for a in APPLIANCES],dtype=float)
    ax_e.imshow(agent_mat,aspect="auto",cmap="Greens",vmin=0,vmax=1)
    ax_e.set_yticks(range(len(APPLIANCES))); ax_e.set_yticklabels(short_labels,fontsize=9)
    ax_e.set_xticks(hours); ax_e.set_xticklabels([f"{h:02d}" for h in hours],fontsize=7,rotation=45,ha="right")
    ax_e.set_title("(e) Agent 24-Hour Schedule Heatmap",**FONT_TITLE,pad=8); ax_e.tick_params(colors="#495057")
    for h in hours:
        if LECO_PEAK_START<=h<LECO_PEAK_END: ax_e.axvspan(h-0.5,h+0.5,color=C_PEAK,alpha=0.18,zorder=2)

    ax_f=fig.add_subplot(gs[2,2])
    styled_ax(ax_f,title="(f) Policies by Category",ylabel="# Policies")
    xi=np.arange(len(cats)); failed_vals=[t-p for t,p in zip(total_vals,passed_vals)]
    ax_f.bar(xi,passed_vals,color=C_PASS,label="Passed",zorder=3,width=0.55)
    ax_f.bar(xi,failed_vals,bottom=passed_vals,color=C_FAIL,label="Failed",zorder=3,width=0.55)
    ax_f.set_xticks(xi); ax_f.set_xticklabels([cat_labels.get(c,c) for c in cats],fontsize=6.5,rotation=30,ha="right")
    ax_f.legend(fontsize=8,framealpha=0.7)

    for ext in ("png","pdf"):
        p=os.path.join(outdir,f"combined_dashboard.{ext}")
        plt.savefig(p,dpi=DPI,bbox_inches="tight",facecolor="white")
        print(f"  Saved -> {p}")
    plt.close(fig)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--outdir",default=os.path.join(BASE,"figures"))
    args=parser.parse_args()
    os.makedirs(args.outdir,exist_ok=True)
    print(f"\n[plot_validation.py] Output: {args.outdir}\n")
    print("[1/8] Loading data...")
    report,app_data,agent_sched,expl=load_data()
    print("[2/8] Donut summary..."); fig_donut(report,args.outdir)
    print("[3/8] Cost savings bar..."); fig_cost_savings(app_data,agent_sched,expl,args.outdir)
    print("[4/8] Waterfall..."); fig_waterfall(app_data,agent_sched,args.outdir)
    print("[5/8] LSTM accuracy..."); fig_lstm_accuracy(app_data,agent_sched,args.outdir)
    print("[6/8] TOU heatmap..."); fig_heatmap(app_data,agent_sched,args.outdir)
    print("[7/8] Peak load..."); fig_peak_load(app_data,agent_sched,args.outdir)
    print("[8/8] Gauge + dashboard...")
    fig_gauge(report,args.outdir); fig_dashboard(report,app_data,agent_sched,args.outdir)
    print(f"\nAll figures saved to: {args.outdir}")

if __name__=="__main__":
    main()
