"""
Phase 4 — generate_plots.py
==============================
Reads the CSV outputs from calculate_metrics.py and error_analysis.py,
and generates 5 publication-quality figures for the IEEE paper.

Outputs (all in results/figures/):
  fig1_ablation_f1.png          — F1 by Mode × Tier (ablation bar chart)
  fig2_tp_fp_fn_distribution.png — TP/FP/FN stacked bars per error category
  fig3_fn_heatmap.png            — False Negative heatmap (Tier × Category)
  fig4_latency_by_tier.png       — Inference latency per script across tiers
  fig5_radar_comparison.png      — Multi-metric radar/spider chart per mode

Run locally after running calculate_metrics.py and error_analysis.py:
    python testing/generate_plots.py
"""

import json
import math
import os
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")   # Non-interactive backend for Kaggle / headless environments
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import pandas as pd
import seaborn as sns

warnings.filterwarnings("ignore")

# ---------------------------------------------------------------------------
BASE_DIR     = Path(__file__).parent
RESULTS_DIR  = BASE_DIR / "results"
OUTPUT_DIR   = BASE_DIR / "new_metrics_analysis"
FIGURES_DIR  = OUTPUT_DIR / "figures"
FIGURES_DIR.mkdir(parents=True, exist_ok=True)

# --- Aesthetics ---
PALETTE = {
    "pylint_only": "#4C72B0",   # blue
    "rag_only":    "#DD8452",   # orange
    "qwen_only":   "#55A868",   # green
    "hybrid":      "#C44E52",   # red
}
LABEL_MODES = {
    "pylint_only": "Pylint Only",
    "rag_only":    "RAG Only",
    "qwen_only":   "Qwen Only",
    "hybrid":      "Hybrid (Full System)",
}
TIER_LABELS = {"1": "Tier 1\n(Novice)", "2": "Tier 2\n(Junior)", "3": "Tier 3\n(Monolithic)", "All": "Overall"}

FONT_FAMILY = "DejaVu Sans"
plt.rcParams.update({
    "font.family":      FONT_FAMILY,
    "axes.titlesize":   13,
    "axes.labelsize":   11,
    "xtick.labelsize":  10,
    "ytick.labelsize":  10,
    "legend.fontsize":  9,
    "figure.dpi":       150,
    "savefig.dpi":      300,
    "savefig.bbox":     "tight",
})


def load_csv(name: str) -> pd.DataFrame | None:
    path = OUTPUT_DIR / name
    if path.exists():
        return pd.read_csv(path)
    print(f"  ⚠️  {name} not found — skipping related plot")
    return None


# ===========================================================================
# Fig 1 — Ablation F1 Score (Mode × Tier) grouped bar chart
# ===========================================================================

def plot_fig1_ablation_f1():
    df = load_csv("metrics_summary.csv")
    if df is None:
        return

    # Exclude 'All' row for the per-tier chart, use it separately for annotation
    tier_df = df[df["Tier"].isin(["1", "2", "3"])].copy()
    modes   = [m for m in ["qwen_only", "hybrid"] if m in tier_df["Mode"].unique()]
    tiers   = ["1", "2", "3"]
    x       = np.arange(len(tiers))
    width   = 0.18

    fig, ax = plt.subplots(figsize=(10, 5))

    for i, mode in enumerate(modes):
        sub    = tier_df[tier_df["Mode"] == mode]
        values = [
            sub[sub["Tier"] == t]["F1"].values[0] if len(sub[sub["Tier"] == t]) > 0 else 0
            for t in tiers
        ]
        offset = (i - len(modes) / 2 + 0.5) * width
        bars   = ax.bar(x + offset, values, width, label=LABEL_MODES.get(mode, mode),
                        color=PALETTE.get(mode, "#888888"), edgecolor="white", linewidth=0.5)
        for bar, val in zip(bars, values):
            if val > 0:
                ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.01,
                        f"{val:.2f}", ha="center", va="bottom", fontsize=8, fontweight="bold")

    ax.set_xticks(x)
    ax.set_xticklabels([TIER_LABELS[t] for t in tiers])
    ax.set_ylim(0, 1.12)
    ax.set_xlabel("Dataset Tier")
    ax.set_ylabel("F1 Score")
    ax.set_title("Ablation Study — F1 Score by Pipeline Mode and Complexity Tier",
                 fontweight="bold", pad=12)
    ax.legend(loc="upper right", framealpha=0.9)
    ax.axhline(0, color="black", linewidth=0.5)
    ax.yaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)

    path = FIGURES_DIR / "fig1_ablation_f1.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"  💾 Fig 1 → {path}")


# ===========================================================================
# Fig 2 — TP / FP / FN distribution per error category (Hybrid only)
# ===========================================================================

def plot_fig2_tp_fp_fn_distribution():
    df = load_csv("confusion_matrix_by_category.csv")
    if df is None:
        return

    hybrid = df[df["Mode"] == "hybrid"].copy()
    if hybrid.empty:
        print("  ⚠️  No hybrid data in confusion_matrix_by_category.csv")
        return

    hybrid = hybrid.sort_values("TP", ascending=False).head(15)  # top 15 categories
    cats   = hybrid["Category"].tolist()
    y      = np.arange(len(cats))

    fig, ax = plt.subplots(figsize=(10, 7))
    ax.barh(y, hybrid["TP"],  color="#2ECC71", label="True Positive",  height=0.6)
    ax.barh(y, hybrid["FN"],  left=hybrid["TP"], color="#E74C3C", label="False Negative", height=0.6)
    ax.barh(y, hybrid["FP"],  left=hybrid["TP"] + hybrid["FN"], color="#F39C12", label="False Positive", height=0.6)

    ax.set_yticks(y)
    ax.set_yticklabels([c.replace("_", " ").title() for c in cats])
    ax.invert_yaxis()
    ax.set_xlabel("Label Count")
    ax.set_title("TP / FP / FN Distribution per Error Category\n(Hybrid System — Full 100-Script Benchmark)",
                 fontweight="bold", pad=10)
    ax.legend(loc="lower right", framealpha=0.9)
    ax.xaxis.grid(True, linestyle="--", alpha=0.35)
    ax.set_axisbelow(True)

    path = FIGURES_DIR / "fig2_tp_fp_fn_distribution.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"  💾 Fig 2 → {path}")


# ===========================================================================
# Fig 3 — FN Heatmap (Tier × Category, Hybrid)
# ===========================================================================

def plot_fig3_fn_heatmap():
    df = load_csv("fn_heatmap_hybrid.csv")
    if df is None:
        return

    df = df.set_index("tier") if "tier" in df.columns else df
    df.index = [TIER_LABELS.get(str(i), f"Tier {i}") for i in df.index]
    df.columns = [c.replace("_", "\n") for c in df.columns]

    fig, ax = plt.subplots(figsize=(max(10, len(df.columns) * 1.1), 4))
    sns.heatmap(
        df, annot=True, fmt="d", cmap="Reds",
        linewidths=0.5, linecolor="white",
        cbar_kws={"label": "FN Count"},
        ax=ax
    )
    ax.set_title("False Negative Rate Heatmap — Hybrid System (by Tier × Error Category)",
                 fontweight="bold", pad=10)
    ax.set_xlabel("Error Category")
    ax.set_ylabel("Dataset Tier")
    ax.tick_params(axis="x", rotation=45)

    path = FIGURES_DIR / "fig3_fn_heatmap.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"  💾 Fig 3 → {path}")


# ===========================================================================
# Fig 4 — Inference Latency per script across tiers (Line chart)
# ===========================================================================

def plot_fig4_latency():
    # Load raw results for each mode that includes LLM inference
    modes_to_plot = []
    all_data = {}

    for mode in ["qwen_only", "hybrid"]:
        path = RESULTS_DIR / f"raw_results_{mode}.json"
        if path.exists():
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            all_data[mode] = sorted(data, key=lambda r: r["id"])
            modes_to_plot.append(mode)

    if not all_data:
        print("  ⚠️  No raw results found for latency plot")
        return

    fig, ax = plt.subplots(figsize=(12, 5))

    for mode in modes_to_plot:
        results  = all_data[mode]
        ids      = [r["id"] for r in results]
        latencies = [r.get("latency_seconds", 0) for r in results]
        ax.plot(ids, latencies, label=LABEL_MODES.get(mode, mode),
                color=PALETTE.get(mode), linewidth=1.4, alpha=0.85)

    # Tier boundary vertical lines
    for boundary, label in [(50.5, "T1→T2"), (80.5, "T2→T3")]:
        ax.axvline(boundary, color="gray", linestyle="--", linewidth=0.8, alpha=0.6)
        ax.text(boundary + 0.5, ax.get_ylim()[1] * 0.95, label, fontsize=8, color="gray")

    ax.set_xlabel("Script ID")
    ax.set_ylabel("Latency (seconds)")
    ax.set_title("Inference Latency per Script Across Complexity Tiers",
                 fontweight="bold", pad=10)
    ax.legend(loc="upper left", framealpha=0.9)
    ax.yaxis.grid(True, linestyle="--", alpha=0.4)
    ax.set_axisbelow(True)

    path = FIGURES_DIR / "fig4_latency_by_tier.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"  💾 Fig 4 → {path}")


# ===========================================================================
# Fig 5 — Multi-metric Radar Chart (one polygon per mode)
# ===========================================================================

def plot_fig5_radar():
    df = load_csv("metrics_summary.csv")
    if df is None:
        return

    # Filter to overall ('All') rows only
    overall = df[df["Tier"] == "All"].copy()
    if overall.empty:
        print("  ⚠️  No 'All' tier rows in metrics_summary.csv")
        return

    METRICS  = ["Recall", "Precision", "F1", "AST_Validity_%", "Spec_Compliance_%"]
    LABELS   = ["Recall", "Precision", "F1 Score", "AST Validity (%)", "Spec Compliance (%)"]
    N        = len(METRICS)
    angles   = [n / float(N) * 2 * math.pi for n in range(N)]
    angles  += angles[:1]   # close the loop

    fig, ax = plt.subplots(figsize=(7, 7), subplot_kw=dict(polar=True))
    ax.set_theta_offset(math.pi / 2)
    ax.set_theta_direction(-1)

    # Draw one polygon per mode
    modes = [m for m in ["qwen_only", "hybrid"]
             if m in overall["Mode"].values]

    for mode in modes:
        row = overall[overall["Mode"] == mode].iloc[0]
        values = []
        for m in METRICS:
            val = row.get(m, 0)
            # Normalise AST and Spec (they're in %) to [0, 1] for the chart scale
            if "_%" in m:
                val = val / 100.0
            values.append(float(val) if not pd.isna(val) else 0.0)
        values += values[:1]

        color = PALETTE.get(mode, "#888888")
        ax.plot(angles, values, "o-", linewidth=2, color=color, label=LABEL_MODES.get(mode, mode))
        ax.fill(angles, values, alpha=0.08, color=color)

    # Category labels
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(LABELS, size=10)
    ax.set_ylim(0, 1)
    ax.set_yticks([0.25, 0.5, 0.75, 1.0])
    ax.set_yticklabels(["0.25", "0.50", "0.75", "1.00"], size=8, color="grey")

    ax.set_title("Multi-Metric Radar: Pipeline Mode Comparison\n(Overall — 100 Scripts)",
                 fontweight="bold", pad=20)
    ax.legend(loc="upper right", bbox_to_anchor=(1.35, 1.1), framealpha=0.9)

    path = FIGURES_DIR / "fig5_radar_comparison.png"
    fig.savefig(path)
    plt.close(fig)
    print(f"  💾 Fig 5 → {path}")


# ===========================================================================
# Main
# ===========================================================================

def main():
    print("📊 Generating IEEE publication figures...\n")

    plot_fig1_ablation_f1()
    plot_fig2_tp_fp_fn_distribution()
    plot_fig3_fn_heatmap()
    plot_fig4_latency()
    plot_fig5_radar()

    print(f"\n✅ All figures saved to {FIGURES_DIR}\n")


if __name__ == "__main__":
    main()
