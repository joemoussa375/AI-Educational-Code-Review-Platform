"""
Phase 3 — calculate_metrics.py
================================
Reads all raw_results_*.json files from the results/ directory,
computes IEEE-standard metrics (Recall, Precision, F1, AST Validity,
Spec Compliance Rate) per mode and per tier, and writes:
  - results/metrics_summary.csv
  - results/confusion_matrix_by_category.csv

Run LOCALLY after downloading results from Kaggle:
    python testing/calculate_metrics.py
"""

import ast
import json
import math
import os
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR    = Path(__file__).parent
RESULTS_DIR = BASE_DIR / "results"
OUTPUT_DIR  = BASE_DIR / "new_metrics_analysis"
MODES       = ["qwen_only", "hybrid"]


# ---------------------------------------------------------------------------
# Core metric helpers
# ---------------------------------------------------------------------------

def safe_divide(num: float, den: float) -> float:
    return round(num / den, 4) if den > 0 else 0.0


def compute_f1(precision: float, recall: float) -> float:
    if precision + recall == 0:
        return 0.0
    return round(2 * precision * recall / (precision + recall), 4)


def check_ast_validity(review_text: str) -> bool:
    """Return True if the ```python block in the review parses without SyntaxError."""
    if "```python" not in review_text:
        return None   # No code block present — not counted
    parts = review_text.split("```python")
    if len(parts) < 2:
        return None
    block = parts[1].split("```")[0].strip()
    if not block:
        return None
    try:
        ast.parse(block)
        return True
    except SyntaxError:
        return False


# ---------------------------------------------------------------------------
# Load results
# ---------------------------------------------------------------------------

def load_all_results() -> dict[str, list[dict]]:
    """Load raw_results_{mode}.json for each available mode."""
    all_results = {}
    for mode in MODES:
        path = RESULTS_DIR / f"raw_results_{mode}.json"
        if path.exists():
            with open(path, encoding="utf-8") as fh:
                all_results[mode] = json.load(fh)
            print(f"  ✅ Loaded {len(all_results[mode])} results for mode='{mode}'")
        else:
            print(f"  ⚠️  No results file for mode='{mode}' — skipping")
    return all_results


# ---------------------------------------------------------------------------
# Per-script aggregates
# ---------------------------------------------------------------------------

def aggregate_per_script(results: list[dict]) -> pd.DataFrame:
    """Flatten each result into a row-per-script DataFrame."""
    rows = []
    for r in results:
        mr  = r.get("match_result", {})
        ast_v = r.get("ast_validity", {})
        spec  = r.get("spec_compliance", {})

        tp = len(mr.get("TP", []))
        fp = len(mr.get("FP", []))
        fn = len(mr.get("FN", []))

        rows.append({
            "id":               r["id"],
            "tier":             r["tier"],
            "title":            r["title"],
            "mode":             r["mode"],
            "tp":               tp,
            "fp":               fp,
            "fn":               fn,
            "precision":        safe_divide(tp, tp + fp),
            "recall":           safe_divide(tp, tp + fn),
            "f1":               compute_f1(
                                    safe_divide(tp, tp + fp),
                                    safe_divide(tp, tp + fn)
                                ),
            "has_code_block":   ast_v.get("has_code", False),
            "ast_valid":        ast_v.get("is_valid", False) if ast_v.get("has_code") else None,
            "spec_compliant":   spec.get("compliant", 0),
            "spec_total":       spec.get("total", 0),
            "latency_seconds":  r.get("latency_seconds", 0),
        })
    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Metrics summary (grouped by mode × tier)
# ---------------------------------------------------------------------------

def compute_metrics_summary(all_results: dict[str, list[dict]]) -> pd.DataFrame:
    """Produce the main metrics table: one row per (mode, tier) combination, plus an 'All' row."""
    rows = []

    for mode, results in all_results.items():
        df = aggregate_per_script(results)

        for tier in sorted(df["tier"].unique()):
            sub = df[df["tier"] == tier]
            rows.append(_compute_row(mode, tier, sub))

        # "All tiers" aggregate per mode
        rows.append(_compute_row(mode, "All", df))

    summary = pd.DataFrame(rows)
    cols = ["Mode", "Tier", "N", "TP", "FP", "FN",
            "Precision", "Recall", "F1",
            "AST_Validity_%", "Spec_Compliance_%", "Avg_Latency_s"]
    return summary[cols]


def _compute_row(mode: str, tier, df: pd.DataFrame) -> dict:
    tp_total = int(df["tp"].sum())
    fp_total = int(df["fp"].sum())
    fn_total = int(df["fn"].sum())

    precision = safe_divide(tp_total, tp_total + fp_total)
    recall    = safe_divide(tp_total, tp_total + fn_total)
    f1        = compute_f1(precision, recall)

    # AST Validity — only count scripts that produced a code block
    code_df  = df[df["has_code_block"] == True]
    ast_rate = (
        round(code_df["ast_valid"].sum() / len(code_df) * 100, 1)
        if len(code_df) > 0 else float("nan")
    )

    # Spec Compliance
    spec_tot = int(df["spec_total"].sum())
    spec_com = int(df["spec_compliant"].sum())
    spec_rate = round(safe_divide(spec_com, spec_tot) * 100, 1)

    avg_lat   = round(df["latency_seconds"].mean(), 2)

    return {
        "Mode":               mode,
        "Tier":               str(tier),
        "N":                  len(df),
        "TP":                 tp_total,
        "FP":                 fp_total,
        "FN":                 fn_total,
        "Precision":          precision,
        "Recall":             recall,
        "F1":                 f1,
        "AST_Validity_%":     ast_rate,
        "Spec_Compliance_%":  spec_rate,
        "Avg_Latency_s":      avg_lat,
    }


# ---------------------------------------------------------------------------
# Per-category confusion matrix
# ---------------------------------------------------------------------------

def compute_category_confusion(all_results: dict[str, list[dict]]) -> pd.DataFrame:
    """
    For each (mode, category) pair, aggregate TP/FP/FN counts.
    Useful for identifying which error types the system handles best/worst.
    """
    rows = []

    for mode, results in all_results.items():
        # Collect all (severity, category) pairs seen across expected + detected
        cat_data: dict[str, dict] = {}

        for r in results:
            mr = r.get("match_result", {})
            for sev, cat in mr.get("TP", []):
                key = f"{sev}:{cat}"
                cat_data.setdefault(key, {"tp": 0, "fp": 0, "fn": 0})
                cat_data[key]["tp"] += 1
            for sev, cat in mr.get("FP", []):
                key = f"{sev}:{cat}"
                cat_data.setdefault(key, {"tp": 0, "fp": 0, "fn": 0})
                cat_data[key]["fp"] += 1
            for sev, cat in mr.get("FN", []):
                key = f"{sev}:{cat}"
                cat_data.setdefault(key, {"tp": 0, "fp": 0, "fn": 0})
                cat_data[key]["fn"] += 1

        for key, counts in sorted(cat_data.items()):
            sev, cat = key.split(":", 1)
            tp = counts["tp"]
            fp = counts["fp"]
            fn = counts["fn"]
            prec   = safe_divide(tp, tp + fp)
            recall = safe_divide(tp, tp + fn)
            f1     = compute_f1(prec, recall)
            rows.append({
                "Mode":      mode,
                "Severity":  sev,
                "Category":  cat,
                "TP":        tp,
                "FP":        fp,
                "FN":        fn,
                "Precision": prec,
                "Recall":    recall,
                "F1":        f1,
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# Console display helpers
# ---------------------------------------------------------------------------

def get_summary_table_str(df: pd.DataFrame) -> str:
    """Format the summary table as a string."""
    out = "\n" + "=" * 90 + "\n"
    out += "  📊 IEEE METRICS SUMMARY\n"
    out += "=" * 90 + "\n"
    try:
        from tabulate import tabulate
        out += tabulate(df, headers="keys", tablefmt="github", showindex=False, floatfmt=".3f") + "\n"
    except ImportError:
        out += df.to_string(index=False) + "\n"
    return out

def print_summary_table(df: pd.DataFrame):
    """Pretty print the summary table in the console."""
    print(get_summary_table_str(df))


def get_ablation_pivot_str(df: pd.DataFrame) -> str:
    """Format the F1 ablation table as a string."""
    out = "\n" + "=" * 60 + "\n"
    out += "  🔬 ABLATION F1 PIVOT (Mode × Tier)\n"
    out += "=" * 60 + "\n"
    pivot = df.pivot_table(index="Mode", columns="Tier", values="F1", aggfunc="mean")
    # Move 'All' to the last column
    if "All" in pivot.columns:
        cols = [c for c in pivot.columns if c != "All"] + ["All"]
        pivot = pivot[cols]
    
    # Reindex to ensure order matches MODES
    valid_modes = [m for m in MODES if m in pivot.index]
    pivot = pivot.reindex(valid_modes)
    
    try:
        from tabulate import tabulate
        out += tabulate(pivot, headers="keys", tablefmt="github", floatfmt=".3f") + "\n"
    except ImportError:
        out += pivot.to_string() + "\n"
    return out

def print_ablation_pivot(df: pd.DataFrame):
    """Print a compact F1 ablation table (Mode × Tier)."""
    print(get_ablation_pivot_str(df))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    RESULTS_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)

    print("📂 Loading result files...")
    all_results = load_all_results()

    if not all_results:
        print("❌ No result files found. Run evaluation_harness.py first.")
        return

    print("\n⚙️  Computing metrics summary...")
    summary_df = compute_metrics_summary(all_results)

    print("\n⚙️  Computing per-category confusion matrix...")
    confusion_df = compute_category_confusion(all_results)

    # ---- Save to CSV ----
    summary_path   = OUTPUT_DIR / "metrics_summary.csv"
    confusion_path = OUTPUT_DIR / "confusion_matrix_by_category.csv"

    summary_df.to_csv(summary_path, index=False)
    confusion_df.to_csv(confusion_path, index=False)

    print(f"\n💾 Saved → {summary_path}")
    print(f"💾 Saved → {confusion_path}")

    # ---- Console output ----
    summary_str = get_summary_table_str(summary_df)
    ablation_str = get_ablation_pivot_str(summary_df)
    
    print(summary_str)
    print(ablation_str)
    
    # ---- Save to TXT ----
    txt_path = OUTPUT_DIR / "metrics_summary_report.txt"
    with open(txt_path, "w", encoding="utf-8") as f:
        f.write(summary_str)
        f.write("\n")
        f.write(ablation_str)
        f.write("\n")
    print(f"💾 Saved textual report → {txt_path}")

    # ---- Quick sanity print per mode ----
    for mode, results in all_results.items():
        df = aggregate_per_script(results)
        total_tp = df["tp"].sum()
        total_fn = df["fn"].sum()
        total_fp = df["fp"].sum()
        overall_recall = safe_divide(total_tp, total_tp + total_fn)
        print(f"  {mode:15s} — Overall Recall: {overall_recall:.3f} | TP={total_tp} FN={total_fn} FP={total_fp}")

    print("\n✅ Metrics calculation complete.\n")


if __name__ == "__main__":
    main()
