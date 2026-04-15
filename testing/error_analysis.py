"""
Phase 4 — error_analysis.py
==============================
Reads all raw_results_*.json files and produces per-label DataFrames for
the paper's Discussion section. Outputs:
  - results/error_detail.csv             — one row per (script × label)
  - results/false_negative_summary.csv   — what the system missed
  - results/false_positive_summary.csv   — what it hallucinated
  - results/tier_breakdown.csv           — per-tier TP/FP/FN rates

Run locally after downloading Kaggle results:
    python testing/error_analysis.py
"""

import json
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
BASE_DIR    = Path(__file__).parent
RESULTS_DIR = BASE_DIR / "results"
MODES       = ["pylint_only", "rag_only", "qwen_only", "hybrid"]

TIER_LABELS = {1: "Tier 1 (Novice)", 2: "Tier 2 (Junior)", 3: "Tier 3 (Monolithic)"}


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------

def load_all_results() -> dict[str, list[dict]]:
    all_results = {}
    for mode in MODES:
        path = RESULTS_DIR / f"raw_results_{mode}.json"
        if path.exists():
            with open(path, encoding="utf-8") as fh:
                all_results[mode] = json.load(fh)
    return all_results


# ---------------------------------------------------------------------------
# Build the per-label "error_detail" DataFrame
# ---------------------------------------------------------------------------

def build_error_detail(all_results: dict[str, list[dict]]) -> pd.DataFrame:
    """
    One row per (script_id, mode, label).
    classification ∈ {TP, FP, FN}
    """
    rows = []

    for mode, results in all_results.items():
        for r in results:
            mr         = r.get("match_result", {})
            script_id  = r["id"]
            tier       = r["tier"]
            title      = r["title"]

            for (sev, cat) in mr.get("TP", []):
                rows.append(_row(script_id, tier, title, mode, sev, cat, "TP", r))

            for (sev, cat) in mr.get("FP", []):
                rows.append(_row(script_id, tier, title, mode, sev, cat, "FP", r))

            for (sev, cat) in mr.get("FN", []):
                rows.append(_row(script_id, tier, title, mode, sev, cat, "FN", r))

    df = pd.DataFrame(rows)
    return df


def _row(script_id, tier, title, mode, severity, category, classification, result) -> dict:
    """Extract a short excerpt of the review near the category keyword (for debugging)."""
    review   = result.get("raw_review", "")
    excerpt  = _find_excerpt(review, category, max_len=120)
    return {
        "script_id":      script_id,
        "tier":           tier,
        "tier_label":     TIER_LABELS.get(tier, f"Tier {tier}"),
        "title":          title[:60],
        "mode":           mode,
        "label_severity": severity,
        "label_category": category,
        "classification": classification,
        "review_excerpt": excerpt,
    }


def _find_excerpt(review: str, category: str, max_len: int = 120) -> str:
    """Find a short snippet of the review relevant to the category keyword."""
    import re
    # Use a simplified word from the category as the search term
    keyword = category.replace("_", " ").replace("n2", "n²")
    match   = re.search(keyword, review, re.IGNORECASE)
    if not match:
        # Try generic fragments of the category name
        for part in category.split("_"):
            match = re.search(part, review, re.IGNORECASE)
            if match:
                break
    if match:
        start   = max(0, match.start() - 20)
        snippet = review[start : start + max_len].replace("\n", " ")
        return snippet.strip()
    return "(not found in review)"


# ---------------------------------------------------------------------------
# Summarise false negatives (what the system missed)
# ---------------------------------------------------------------------------

def build_fn_summary(detail_df: pd.DataFrame) -> pd.DataFrame:
    """
    Per (mode, tier, category): count FNs and list script IDs.
    """
    fn_df = detail_df[detail_df["classification"] == "FN"].copy()
    if fn_df.empty:
        return pd.DataFrame()

    summary = (
        fn_df.groupby(["mode", "tier_label", "label_severity", "label_category"])
        .agg(
            fn_count=("script_id", "count"),
            fn_script_ids=("script_id", lambda x: sorted(x.unique().tolist()))
        )
        .reset_index()
        .sort_values(["mode", "fn_count"], ascending=[True, False])
    )
    return summary


# ---------------------------------------------------------------------------
# Summarise false positives (hallucinations)
# ---------------------------------------------------------------------------

def build_fp_summary(detail_df: pd.DataFrame) -> pd.DataFrame:
    """
    Per (mode, tier, category): count FPs and list script IDs.
    """
    fp_df = detail_df[detail_df["classification"] == "FP"].copy()
    if fp_df.empty:
        return pd.DataFrame()

    summary = (
        fp_df.groupby(["mode", "tier_label", "label_severity", "label_category"])
        .agg(
            fp_count=("script_id", "count"),
            fp_script_ids=("script_id", lambda x: sorted(x.unique().tolist()))
        )
        .reset_index()
        .sort_values(["mode", "fp_count"], ascending=[True, False])
    )
    return summary


# ---------------------------------------------------------------------------
# Per-tier breakdown
# ---------------------------------------------------------------------------

def build_tier_breakdown(detail_df: pd.DataFrame) -> pd.DataFrame:
    """
    Per (mode, tier): TP/FP/FN counts and rates.
    """
    rows = []
    for mode in detail_df["mode"].unique():
        for tier in sorted(detail_df["tier"].unique()):
            sub = detail_df[(detail_df["mode"] == mode) & (detail_df["tier"] == tier)]
            tp  = len(sub[sub["classification"] == "TP"])
            fp  = len(sub[sub["classification"] == "FP"])
            fn  = len(sub[sub["classification"] == "FN"])
            prec   = round(tp / (tp + fp), 4) if (tp + fp) > 0 else 0.0
            recall = round(tp / (tp + fn), 4) if (tp + fn) > 0 else 0.0
            f1     = round(2 * prec * recall / (prec + recall), 4) if (prec + recall) > 0 else 0.0
            rows.append({
                "Mode":      mode,
                "Tier":      tier,
                "Tier_Label": TIER_LABELS.get(tier, f"Tier {tier}"),
                "TP":        tp,
                "FP":        fp,
                "FN":        fn,
                "Precision": prec,
                "Recall":    recall,
                "F1":        f1,
            })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# FN Heatmap pivot (Tier × Category) — for Fig3 in generate_plots.py
# ---------------------------------------------------------------------------

def build_fn_heatmap_pivot(detail_df: pd.DataFrame, mode: str = "hybrid") -> pd.DataFrame:
    """
    Pivot: rows = tiers (1-3), columns = error categories, values = FN count.
    Used to identify which categories are hardest for the full hybrid system.
    """
    fn_df = detail_df[
        (detail_df["classification"] == "FN") &
        (detail_df["mode"] == mode)
    ].copy()
    if fn_df.empty:
        return pd.DataFrame()

    pivot = fn_df.pivot_table(
        index="tier",
        columns="label_category",
        values="script_id",
        aggfunc="count",
    ).fillna(0).astype(int)
    return pivot


# ---------------------------------------------------------------------------
# Console summary
# ---------------------------------------------------------------------------

def print_top_failures(detailed_df: pd.DataFrame, mode: str = "hybrid", top_n: int = 10):
    """Print the most common false negatives for a given mode."""
    fn = detailed_df[
        (detailed_df["classification"] == "FN") & (detailed_df["mode"] == mode)
    ]
    print(f"\n  Top {top_n} Missed Categories (mode={mode}):")
    counts = fn["label_category"].value_counts().head(top_n)
    for cat, cnt in counts.items():
        bar = "█" * int(cnt / max(counts) * 20)
        print(f"    {cat:28s}  {bar}  ({cnt})")


def print_top_hallucinations(detailed_df: pd.DataFrame, mode: str = "hybrid", top_n: int = 10):
    """Print the most common false positives for a given mode."""
    fp = detailed_df[
        (detailed_df["classification"] == "FP") & (detailed_df["mode"] == mode)
    ]
    print(f"\n  Top {top_n} Hallucinated Categories (mode={mode}):")
    counts = fp["label_category"].value_counts().head(top_n)
    for cat, cnt in counts.items():
        bar = "█" * int(cnt / max(counts) * 20) if len(counts) else ""
        print(f"    {cat:28s}  {bar}  ({cnt})")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    RESULTS_DIR.mkdir(exist_ok=True)

    print("📂 Loading result files...")
    all_results = load_all_results()

    if not all_results:
        print("❌ No result files found. Run evaluation_harness.py first.")
        return

    print(f"  Loaded modes: {list(all_results.keys())}")

    print("\n⚙️  Building error detail dataframe...")
    detail_df = build_error_detail(all_results)

    print("⚙️  Building FN summary...")
    fn_summary = build_fn_summary(detail_df)

    print("⚙️  Building FP summary...")
    fp_summary = build_fp_summary(detail_df)

    print("⚙️  Building tier breakdown...")
    tier_df = build_tier_breakdown(detail_df)

    # ---- Save CSVs ----
    detail_path  = RESULTS_DIR / "error_detail.csv"
    fn_path      = RESULTS_DIR / "false_negative_summary.csv"
    fp_path      = RESULTS_DIR / "false_positive_summary.csv"
    tier_path    = RESULTS_DIR / "tier_breakdown.csv"

    detail_df.to_csv(detail_path, index=False)
    fn_summary.to_csv(fn_path,    index=False)
    fp_summary.to_csv(fp_path,    index=False)
    tier_df.to_csv(tier_path,     index=False)

    print(f"\n💾 Saved → {detail_path}")
    print(f"💾 Saved → {fn_path}")
    print(f"💾 Saved → {fp_path}")
    print(f"💾 Saved → {tier_path}")

    # ---- FN Heatmap pivot for hybrid ----
    fn_heatmap = build_fn_heatmap_pivot(detail_df, mode="hybrid")
    if not fn_heatmap.empty:
        heatmap_path = RESULTS_DIR / "fn_heatmap_hybrid.csv"
        fn_heatmap.to_csv(heatmap_path)
        print(f"💾 Saved → {heatmap_path}")

    # ---- Console insights ----
    if "hybrid" in all_results:
        print("\n" + "=" * 60)
        print("  📋 QUALITATIVE ANALYSIS INSIGHTS (Hybrid Mode)")
        print("=" * 60)
        print_top_failures(detail_df, mode="hybrid")
        print_top_hallucinations(detail_df, mode="hybrid")

    print("\n  Tier Breakdown (Hybrid Mode):")
    hybrid_tier = tier_df[tier_df["Mode"] == "hybrid"] if "hybrid" in all_results else pd.DataFrame()
    if not hybrid_tier.empty:
        print(hybrid_tier[["Tier_Label", "TP", "FP", "FN", "Recall", "Precision", "F1"]].to_string(index=False))

    print("\n✅ Error analysis complete.\n")


if __name__ == "__main__":
    main()
