"""
Phase 1 — prepare_dataset.py
==============================
Reads Testing_Dataset.txt (which contains multiple JSON array blocks),
merges them into a single validated list, unescape Tier-2/3 markdown artefacts,
adds 'tier' and 'expected_labels' fields, and writes a clean dataset.json.

Run locally BEFORE uploading to Kaggle:
    python testing/prepare_dataset.py
"""

import json
import re
import ast
import os
import sys

# ---------------------------------------------------------------------------
# 1. Configuration
# ---------------------------------------------------------------------------
INPUT_FILE  = os.path.join(os.path.dirname(__file__), "..", "Testing_Dataset.txt")
OUTPUT_FILE = os.path.join(os.path.dirname(__file__), "dataset.json")

TIER_RANGES = {1: range(1, 51), 2: range(51, 81), 3: range(81, 101)}

# Severity emoji → label key
SEVERITY_MAP = {
    "🔴": "critical",
    "🟡": "style",
    "🔵": "info",
}

# Map free-text descriptions to canonical category keys
CATEGORY_PATTERNS = [
    ("mutable_default",     r"mutable\s+default\s+arg|default.*=\s*[\[{]"),
    ("off_by_one",          r"off.by.one|IndexError|range.*\+\s*1|range.*len.*\+|<=.*len|index\s+out\s+of"),
    ("list_mutation",       r"mutat.*list|mutat.*while\s+iter|remov.*while.*iter|modify.*iteration"),
    ("missing_docstring",   r"missing\s+docstring|no\s+docstring"),
    ("camelcase",           r"camelcase|CamelCase|snake_case|naming\s+convention|pep\s*8.*name"),
    ("eval_injection",      r"eval\(\)|eval\s+|arbitrary\s+code"),
    ("hardcoded_secret",    r"hardcoded?\s+(secret|api\s+key|key|token|pass|credential)|API_KEY|SECRET|PASSWORD|TOKEN"),
    ("unclosed_file",       r"unclosed\s+file|file.*not.*closed|missing.*close|open\(\).*without"),
    ("missing_super",       r"super\(\)|missing.*super|parent.*init"),
    ("performance_n2",      r"O\(n\^?2\)|O\(n²\)|nested\s+loop.*inefficien|quadratic|n\s*squared"),
    ("bare_except",         r"bare\s+except|except\s*:|generic\s+exception"),
    ("dry_violation",       r"DRY\s+violation|code\s+duplic|repeated\s+logic"),
    ("shared_class_state",  r"shared.*class.*state|class.level\s+attribute|class\s+variable"),
    ("none_comparison",     r"== None|is None.*instead|val == None"),
    ("logical_error",       r"logical\s+(?:off.by.one|error)|skips\s+index|skips\s+first|misses\s+last"),
]


# ---------------------------------------------------------------------------
# 2. Parse the raw .txt file (multiple JSON arrays concatenated)
# ---------------------------------------------------------------------------
def load_raw_blocks(filepath: str) -> list[dict]:
    """Extracts all top-level JSON arrays from the file and merges them."""
    print(f"📂 Reading: {filepath}")
    with open(filepath, "r", encoding="utf-8") as fh:
        raw = fh.read()

    # --- Strategy: split on the ]\n[ boundary that separates the array blocks,
    # then parse each independently. This is more robust than bracket-scanning
    # because the Tier-2/3 blocks contain escaped backslashes inside JSON strings
    # that confuse a character-level depth counter.
    # The file looks like:  [ {...}, {...} ]\r\n[ {...} ]\r\n...

    # 1. Pre-repair the whole file to fix the worst markdown escape artefacts
    repaired_raw = _repair_full_text(raw)

    # 2. Split into individual [..] blocks using a regex on line boundaries
    #    Match from start-of-line '[' to end-of-line ']'
    block_texts = re.split(r'(?<=\])[\r\n]+(?=\[)', repaired_raw.strip())

    entries = []
    for idx, block_str in enumerate(block_texts):
        block_str = block_str.strip()
        if not block_str:
            continue
        try:
            block = json.loads(block_str)
            if isinstance(block, list):
                entries.extend(block)
        except json.JSONDecodeError as exc:
            # Attempt a second repair pass on just this block
            repaired = _repair_json_block(block_str)
            try:
                block = json.loads(repaired)
                entries.extend(block)
                print(f"  ⚠️  Block #{idx+1} required extra repair.")
            except json.JSONDecodeError:
                # Last resort: try ast.literal_eval on each object in the block
                recovered = _recover_objects(block_str)
                if recovered:
                    entries.extend(recovered)
                    print(f"  ⚠️  Block #{idx+1} partially recovered ({len(recovered)} objects).")
                else:
                    print(f"  ❌ Block #{idx+1} could not be parsed: {exc}")

    print(f"  ✅ Extracted {len(entries)} raw entries from {filepath}")
    return entries


def _repair_full_text(text: str) -> str:
    """
    Whole-file pre-processing pass. Fixes the aggressive double-escaping
    that affects Tier 2/3 blocks generated inside an escaped markdown context.
    """
    # \\\\n  (4 backslashes + n in the raw file) → \\n (a real JSON newline escape)
    text = text.replace('\\\\n', '\\n')
    # \\\\t  → \\t
    text = text.replace('\\\\t', '\\t')
    # \\\\r  → \\r
    text = text.replace('\\\\r', '\\r')
    # Escaped underscores:  \\_ → _
    text = text.replace('\\_', '_')
    # Escaped exclamation:  \\! → !
    text = text.replace('\\!', '!')
    # **__init__**  and similar bold-tagged dunder names → __init__
    text = re.sub(r'\*\*(\w+)\*\*', r'__\1__', text)
    # Google search URL wrappers injected by the dataset generator:
    # https://www.google.com/search?q=https://... → https://...
    text = re.sub(r'https://www\.google\.com/search\?q=', '', text)
    return text


def _repair_json_block(text: str) -> str:
    """Secondary repair for individual blocks — same transforms as the full-text pass."""
    return _repair_full_text(text)


def _recover_objects(block_str: str) -> list[dict]:
    """
    Last-resort recovery: extract individual JSON objects {…} from a broken array.
    Uses a simple brace-depth scanner that is more forgiving than json.loads.
    """
    objects = []
    depth = 0
    start = None
    for i, ch in enumerate(block_str):
        if ch == '{' and depth == 0:
            depth = 1
            start = i
        elif ch == '{':
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start is not None:
                obj_str = block_str[start: i + 1]
                try:
                    obj = json.loads(obj_str)
                    if isinstance(obj, dict) and 'id' in obj:
                        objects.append(obj)
                except json.JSONDecodeError:
                    pass
                start = None
    return objects


# ---------------------------------------------------------------------------
# 3. Unescape code strings for individual entries
# ---------------------------------------------------------------------------
def unescape_code(raw_code: str) -> str:
    """
    Some code strings inside the JSON still have left-over escape artefacts.
    We normalise them here so Pylint and ast.parse() work correctly.
    """
    # Replace literal four-backslash-n with real newline escape
    code = raw_code.replace("\\\\n", "\\n")
    # Restore __dunder__ names mangled to **dunder**
    code = re.sub(r'\*\*(\w+)\*\*', r'__\1__', code)
    # Un-escape underscores
    code = code.replace("\\_", "_")
    # Fix \! → !
    code = code.replace("\\!", "!")
    # Fix stray markdown link artefacts like https://www.google.com/search?q=https://...
    # (leave URLs that look normal alone)
    code = re.sub(r'https://www\.google\.com/search\?q=', '', code)
    return code


# ---------------------------------------------------------------------------
# 4. Assign tier
# ---------------------------------------------------------------------------
def get_tier(script_id: int) -> int:
    for tier, rng in TIER_RANGES.items():
        if script_id in rng:
            return tier
    return 0   # unknown — should not happen


# ---------------------------------------------------------------------------
# 5. Parse expected string → structured labels
# ---------------------------------------------------------------------------
def classify_category(text: str) -> str:
    """Return the first matching canonical category key for a description fragment."""
    lower = text.lower()
    for category, pattern in CATEGORY_PATTERNS:
        if re.search(pattern, lower, re.IGNORECASE):
            return category
    return "other"


def extract_keyword(text: str) -> str:
    """Pull out the most informative keyword fragment from a label description."""
    # Try to grab text inside quotes or single-quotes
    quoted = re.findall(r"['\"]([^'\"]+)['\"]", text)
    if quoted:
        return quoted[0]
    # Fall back to the full text (trimmed)
    return text.strip()[:80]


def parse_expected(expected_str: str) -> list[dict]:
    """
    Convert e.g.:
      "🔴 Critical: Mutable default argument 'MyList=[]', 🟡 Style: CamelCase, 🔵 Info: Missing docstring"
    into:
      [
        {"severity": "critical", "category": "mutable_default",   "keyword": "MyList=[]"},
        {"severity": "style",    "category": "camelcase",         "keyword": "CamelCase"},
        {"severity": "info",     "category": "missing_docstring", "keyword": "Missing docstring"},
      ]
    """
    # Split on comma + whitespace + emoji (the standard delimiter in your dataset)
    segments = re.split(r',\s*(?=🔴|🟡|🔵)', expected_str.strip())
    labels = []
    for seg in segments:
        seg = seg.strip()
        if not seg:
            continue
        severity = "info"  # default
        for emoji, sev in SEVERITY_MAP.items():
            if seg.startswith(emoji):
                severity = sev
                break
        # Strip the leading "🔴 Critical: " or "🟡 Style: " prefix
        cleaned = re.sub(r'^[🔴🟡🔵]\s+\w+:\s*', '', seg).strip()
        category = classify_category(cleaned)
        keyword  = extract_keyword(cleaned)
        labels.append({
            "severity": severity,
            "category": category,
            "keyword":  keyword,
        })
    return labels


# ---------------------------------------------------------------------------
# 6. Validate & enrich each entry
# ---------------------------------------------------------------------------
def validate_entry(entry: dict, idx: int) -> dict | None:
    """Returns enriched entry or None if entry is unrecoverable."""
    required = {"id", "title", "expected", "code"}
    missing  = required - entry.keys()
    if missing:
        print(f"  ⚠️  Entry #{idx} missing fields: {missing} — skipping")
        return None

    # Unescape code
    entry["code"] = unescape_code(entry["code"])

    # Assign tier
    entry["tier"] = get_tier(int(entry["id"]))

    # Parse expected into structured labels
    entry["expected_labels"] = parse_expected(entry["expected"])

    # Quick sanity check: can Python parse the code?
    try:
        ast.parse(entry["code"])
        entry["code_ast_valid"] = True
    except SyntaxError:
        entry["code_ast_valid"] = False  # still include it — Pylint may still run

    return entry


# ---------------------------------------------------------------------------
# 7. Main
# ---------------------------------------------------------------------------
def main():
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)

    raw_entries = load_raw_blocks(INPUT_FILE)

    if not raw_entries:
        print("❌ No entries found. Check the path to Testing_Dataset.txt")
        sys.exit(1)

    # Sort by id so the dataset is ordered 1-100
    raw_entries.sort(key=lambda e: int(e.get("id", 0)))

    # Remove duplicates (keep first occurrence)
    seen_ids = set()
    deduped  = []
    for entry in raw_entries:
        eid = int(entry.get("id", -1))
        if eid not in seen_ids:
            seen_ids.add(eid)
            deduped.append(entry)
        else:
            print(f"  ⚠️  Duplicate id={eid} found — keeping first occurrence")

    print(f"\n🔧 Validating and enriching {len(deduped)} entries...")
    clean_entries = []
    for i, entry in enumerate(deduped):
        enriched = validate_entry(entry, i + 1)
        if enriched:
            clean_entries.append(enriched)

    # Verify coverage
    all_ids = {e["id"] for e in clean_entries}
    expected_ids = set(range(1, 101))
    missing_ids  = expected_ids - all_ids
    if missing_ids:
        print(f"\n⚠️  WARNING: Missing script IDs: {sorted(missing_ids)}")
    else:
        print(f"\n✅ All 100 script IDs present.")

    # Tier summary
    by_tier = {1: 0, 2: 0, 3: 0}
    for e in clean_entries:
        by_tier[e["tier"]] = by_tier.get(e["tier"], 0) + 1
    print(f"   Tier 1: {by_tier[1]} scripts | Tier 2: {by_tier[2]} scripts | Tier 3: {by_tier[3]} scripts")

    # AST validity summary
    valid   = sum(1 for e in clean_entries if e.get("code_ast_valid"))
    invalid = len(clean_entries) - valid
    print(f"   Code AST valid: {valid}/{len(clean_entries)} ({invalid} have syntax errors — expected for some Tier-3 scripts)")

    # Write output
    with open(OUTPUT_FILE, "w", encoding="utf-8") as fh:
        json.dump(clean_entries, fh, indent=2, ensure_ascii=False)

    print(f"\n💾 Saved clean dataset → {OUTPUT_FILE}")
    print("   You can now upload this file to Kaggle and proceed with the harness.\n")


if __name__ == "__main__":
    main()
