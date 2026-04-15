"""
Phase 1 + 2 — evaluation_harness.py
======================================
Main evaluation orchestrator. Reads dataset.json, runs each of the 100
scripts through one of 4 pipeline modes, and saves structured results.

Usage (locally for pylint/rag modes, or on Kaggle for qwen/hybrid):
    python evaluation_harness.py --mode pylint_only
    python evaluation_harness.py --mode rag_only
    python evaluation_harness.py --mode qwen_only
    python evaluation_harness.py --mode hybrid
    python evaluation_harness.py --mode hybrid --limit 3   # dry-run

For Kaggle: this file + its imports must be uploaded as a dataset input.
See the Kaggle guide notebook (evaluation_kaggle.ipynb) for the full workflow.
"""

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
BASE_DIR    = Path(__file__).parent
DATASET     = BASE_DIR / "dataset.json"
RESULTS_DIR = BASE_DIR / "results"
RESULTS_DIR.mkdir(exist_ok=True)

KB_PATH = BASE_DIR.parent / "knowledge_base.md"   # adjust if needed on Kaggle

# ---------------------------------------------------------------------------
# Pipeline mode definitions — 4 primary modes for the ablation study
# ---------------------------------------------------------------------------
MODES = {
    "pylint_only": {"pylint": True,  "rag": False, "qwen": False},
    "rag_only":    {"pylint": False, "rag": True,  "qwen": False},
    "qwen_only":   {"pylint": False, "rag": False, "qwen": True},
    "hybrid":      {"pylint": True,  "rag": True,  "qwen": True},
}

# ---------------------------------------------------------------------------
# Detection patterns — used to extract structured labels from review text
# ---------------------------------------------------------------------------
DETECTION_PATTERNS = {
    "mutable_default":   r"mutable\s+default|default\s+arg.*=\s*[\[{]|shared\s+across\s+calls",
    "off_by_one":        r"off.by.one|IndexError|index\s+out\s+of\s+range|range.*\+\s*1|<=\s*len",
    "list_mutation":     r"mutat.*list|mutat.*iter|remov.*while.*iter|modify.*during",
    "missing_docstring": r"missing\s+docstring|add\s+a?\s*docstring|no\s+docstring",
    "camelcase":         r"camelcase|CamelCase|snake_case|pep\s*8.*name|naming\s+conven",
    "eval_injection":    r"eval\(\)|arbitrary\s+code\s+execut|code\s+inject|dangerous.*eval",
    "hardcoded_secret":  r"hardcoded?\s*(secret|api.?key|key|token|pass|credential)|use\s+environ",
    "unclosed_file":     r"unclosed\s+file|file.*not\s+closed|missing.*\.close|with\s+open|context\s+manager",
    "missing_super":     r"super\(\).*not\s+called|missing.*super|parent.*__init__.*not",
    "performance_n2":    r"O\(n\^?2\)|O\(n²\)|nested\s+loop.*inefficien|quadratic|use\s+set\(\)",
    "bare_except":       r"bare\s+except|except\s*:|generic\s+exception\s+catch",
    "dry_violation":     r"DRY|code\s+duplic|repeated\s+logic|refactor.*common",
    "shared_class_state":r"class.level\s+attr|class\s+variable.*shared|all\s+instances\s+share",
    "none_comparison":   r"== None|is None.*prefer|val == None|use\s+is\s+None",
    "logical_error":     r"logical\s+(?:error|off.by.one)|skips\s+index\s+0|misses.*last|incorrect.*range",
}

# RAG-only keywords per category (Option A: retrieval quality check)
RAG_SPEC_KEYWORDS = {
    "mutable_default":   ["mutable default", "default argument", "none as default"],
    "off_by_one":        ["off-by-one", "index error", "boundary"],
    "list_mutation":     ["mutating", "iteration", "remove during"],
    "missing_docstring": ["docstring", "pep 257", "documentation"],
    "camelcase":         ["snake_case", "pep 8", "naming convention", "camelcase"],
    "eval_injection":    ["eval", "code injection", "owasp", "arbitrary code"],
    "hardcoded_secret":  ["hardcoded", "environment variable", "owasp", "secret"],
    "unclosed_file":     ["with statement", "context manager", "file close", "resource leak"],
    "missing_super":     ["super()", "parent class", "__init__"],
    "performance_n2":    ["o(n^2)", "nested loop", "set()", "time complexity"],
    "bare_except":       ["bare except", "specific exception", "exception handling"],
    "shared_class_state":["class variable", "instance variable", "shared state"],
}


# ===========================================================================
# Component Wrappers
# ===========================================================================

class PylintRunner:
    """Thin wrapper; mirrors UnifiedCodeReviewer._run_pylint()."""

    @staticmethod
    def analyze(code: str) -> str:
        with tempfile.NamedTemporaryFile(
            mode="w+", suffix=".py", delete=False, encoding="utf-8"
        ) as fh:
            fh.write(code)
            fname = fh.name

        try:
            result = subprocess.run(
                ["pylint", fname, "--output-format=json", "--disable=C0301"],
                capture_output=True, text=True, timeout=30
            )
            if not result.stdout.strip():
                return "No issues reported by Pylint."
            errors = json.loads(result.stdout)
            # Cap at 20 messages to prevent context flooding for Tier-3 scripts
            capped = errors[:20]
            lines  = [f"Line {e['line']}: {e['message']} ({e['symbol']})" for e in capped]
            if len(errors) > 20:
                lines.append(f"... and {len(errors) - 20} more messages")
            return "\n".join(lines)
        except (subprocess.TimeoutExpired, json.JSONDecodeError, Exception) as exc:
            return f"Pylint error: {exc}"
        finally:
            if os.path.exists(fname):
                os.remove(fname)


class RAGOnlyReviewer:
    """
    Wraps KnowledgeBase for standalone retrieval without LLM.
    Evaluation (Option A): check whether retrieved text mentions the right keywords.
    """

    def __init__(self, kb_path: str = str(KB_PATH)):
        # Import lazily so pylint-only mode doesn't need LangChain installed
        try:
            from langchain_community.document_loaders import TextLoader
            from langchain_huggingface import HuggingFaceEmbeddings
            from langchain_community.vectorstores import FAISS
            from langchain_community.retrievers import BM25Retriever
            try:
                from langchain_text_splitters import RecursiveCharacterTextSplitter
            except ImportError:
                from langchain.text_splitter import RecursiveCharacterTextSplitter

            loader   = TextLoader(kb_path, encoding="utf-8")
            data     = loader.load()
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=500, chunk_overlap=60,
                separators=["\n## ", "\n### ", "\n- ", "\n", " "]
            )
            splits   = splitter.split_documents(data)
            emb      = HuggingFaceEmbeddings(
                model_name="all-MiniLM-L6-v2",
                model_kwargs={"device": "cpu"}
            )
            self.vectorstore    = FAISS.from_documents(splits, emb)
            self.bm25_retriever = BM25Retriever.from_documents(splits)
            self.bm25_retriever.k = 3
            self._ok = True
            print(f"  ✅ RAG engine ready ({len(splits)} chunks)")
        except Exception as exc:
            print(f"  ⚠️  RAG engine failed to load: {exc}")
            self._ok = False

    def retrieve(self, queries: list[str]) -> str:
        if not self._ok:
            return ""
        results = []
        for q in queries:
            results.extend(self.vectorstore.similarity_search(q, k=2))
            results.extend(self.bm25_retriever.invoke(q))
        unique = {d.page_content: d for d in results}.values()
        return "\n\n".join(f"[Guide]: {d.page_content}" for d in unique)

    def score_rag_labels(
        self, retrieved_text: str, expected_labels: list[dict]
    ) -> list[dict]:
        """
        Option A evaluation: for each expected label, check if the retrieved
        chunks contain relevant specification keywords.
        Returns a list of detected labels (those whose keywords appear).
        """
        lower = retrieved_text.lower()
        detected = []
        for label in expected_labels:
            cat = label["category"]
            keywords = RAG_SPEC_KEYWORDS.get(cat, [label["keyword"].lower()])
            if any(kw in lower for kw in keywords):
                detected.append({
                    "severity": label["severity"],
                    "category": cat,
                    "keyword":  label["keyword"],
                    "source":   "rag_retrieval",
                })
        return detected


class QwenReviewer:
    """
    Wraps UnifiedCodeReviewer from code_reviewer.py.
    Can run in 'qwen_only' mode (no Pylint context, no RAG context)
    or as part of the full hybrid pipeline.
    """

    def __init__(self, mode_config: dict, rag_engine=None):
        self.use_pylint = mode_config["pylint"]
        self.use_rag    = mode_config["rag"]
        self.rag_engine = rag_engine
        self._reviewer  = None

    def _ensure_loaded(self):
        if self._reviewer is not None:
            return
        # Add parent dir to path so we can import code_reviewer
        sys.path.insert(0, str(BASE_DIR.parent))
        from code_reviewer import UnifiedCodeReviewer
        self._reviewer = UnifiedCodeReviewer()

    def review(self, code: str) -> str:
        self._ensure_loaded()

        if self.use_pylint and self.use_rag:
            # Full hybrid — delegate entirely to the existing .review() method
            return self._reviewer.review(code)

        # Custom prompt for qwen_only (no external context)
        linter_section = ""
        rag_section    = ""

        if self.use_pylint:
            linter_section = (
                f"STATIC ANALYSIS REPORT:\n{self._reviewer._run_pylint(code)}\n\n"
            )
        if self.use_rag and self.rag_engine:
            queries    = self._reviewer._generate_search_plan(code)
            rag_result = self.rag_engine.retrieve(queries)
            rag_section = f"STYLE GUIDE:\n{rag_result}\n\n"

        # Build a lean prompt for qwen_only mode
        system_msg = f"""You are a Python code reviewer.{linter_section}{rag_section}
KNOWN BUG PATTERNS — flag these if you see them:
- Using eval() is a CRITICAL security vulnerability.
- Removing items from a list while iterating is a CRITICAL bug.
- open() without a 'with' statement leaves the file unclosed.
- Hardcoded API keys or secrets in source code is a CRITICAL security vulnerability.
- Bare 'except:' without specifying an exception type hides all errors.
- Nested O(n²) loops can often be replaced with sets for better performance.

RULES:
- Only report issues that ACTUALLY exist in the code.
- Use this exact format:

**1. Critical Issues:**
List bugs and security issues. If none, write "No critical issues found."

**2. Style Analysis:**
List naming/formatting issues based on PEP 8. If clean, say so.

**3. Refactored Solution:**
```python
(corrected code here)
```"""

        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user",   "content": f"Review this code:\n\n{code}"},
        ]
        return self._reviewer._ask_llm(messages, max_tokens=1024)


# ===========================================================================
# Label Extraction & Matching
# ===========================================================================

def extract_detected_labels(review_text: str) -> list[dict]:
    """
    Scan the review string for each pattern in DETECTION_PATTERNS.
    Returns a list of detected label dicts.
    """
    lower    = review_text.lower()
    detected = []
    for category, pattern in DETECTION_PATTERNS.items():
        if re.search(pattern, lower, re.IGNORECASE):
            # Determine severity heuristic from the section heading context
            severity = _infer_severity(lower, pattern)
            detected.append({"severity": severity, "category": category})
    return detected


def _infer_severity(text_lower: str, pattern: str) -> str:
    """Guess severity by looking at what section the match appears in."""
    match = re.search(pattern, text_lower, re.IGNORECASE)
    if not match:
        return "info"
    pos = match.start()
    # Look backwards ~200 chars for a section header
    context = text_lower[max(0, pos - 200): pos]
    if "critical" in context:
        return "critical"
    if "style" in context:
        return "style"
    if "info" in context:
        return "info"
    return "critical"   # most errors in the dataset are critical


def compare_labels(expected_labels: list[dict], detected_labels: list[dict]) -> dict:
    """
    Compare expected vs detected using (severity, category) as the key.
    Returns: {TP: list, FP: list, FN: list}
    """
    exp_set = {(l["severity"], l["category"]) for l in expected_labels}
    det_set = {(l["severity"], l["category"]) for l in detected_labels}

    tp = list(exp_set & det_set)
    fp = list(det_set - exp_set)
    fn = list(exp_set - det_set)

    return {"TP": tp, "FP": fp, "FN": fn}


def check_ast_validity(review_text: str) -> dict:
    """Extract ```python block from review and ast.parse() it."""
    if "```python" not in review_text:
        return {"has_code": False, "is_valid": False}
    parts = review_text.split("```python")
    if len(parts) < 2:
        return {"has_code": False, "is_valid": False}
    code_block = parts[1].split("```")[0].strip()
    if not code_block:
        return {"has_code": False, "is_valid": False}
    try:
        ast.parse(code_block)
        return {"has_code": True, "is_valid": True}
    except SyntaxError as exc:
        return {"has_code": True, "is_valid": False, "syntax_error": str(exc)}


def check_spec_compliance(review_text: str, expected_labels: list[dict]) -> dict:
    """Check if the review correctly cites the relevant spec/rule for each label."""
    SPEC_MAP = {
        "hardcoded_secret":  ["owasp", "environment variable", "os.getenv", "secrets"],
        "eval_injection":    ["owasp", "security", "arbitrary code", "injection"],
        "unclosed_file":     ["with open", "context manager", "resource", "close()"],
        "camelcase":         ["pep 8", "pep8", "snake_case", "naming convention"],
        "missing_docstring": ["pep 257", "docstring", "documentation"],
        "performance_n2":    ["o(n", "set()", "time complexity", "inefficient"],
        "missing_super":     ["super()", "parent class", "inherit"],
        "list_mutation":     ["list comprehension", "copy", "iterate over a copy"],
        "mutable_default":   ["none as default", "mutable default"],
    }
    lower = review_text.lower()
    compliant = total = 0
    details = []
    for label in expected_labels:
        cat = label["category"]
        if cat in SPEC_MAP:
            total += 1
            if any(kw in lower for kw in SPEC_MAP[cat]):
                compliant += 1
                details.append({"category": cat, "compliant": True})
            else:
                details.append({"category": cat, "compliant": False})
    return {"compliant": compliant, "total": total, "details": details}


# ===========================================================================
# Main Harness
# ===========================================================================

class EvaluationHarness:

    def __init__(self, mode: str = "hybrid", dataset_path: str = str(DATASET)):
        assert mode in MODES, f"Unknown mode '{mode}'. Choose from: {list(MODES)}"
        self.mode    = mode
        self.config  = MODES[mode]
        self.dataset = self._load_dataset(dataset_path)

        # Lazy-load components
        self.pylint_runner = PylintRunner() if self.config["pylint"] else None

        self.rag_engine = None
        if self.config["rag"]:
            self.rag_engine = RAGOnlyReviewer()

        self.qwen_reviewer = None
        if self.config["qwen"]:
            self.qwen_reviewer = QwenReviewer(self.config, rag_engine=self.rag_engine)

    def _load_dataset(self, path: str) -> list[dict]:
        if not os.path.exists(path):
            print(f"❌ dataset.json not found at {path}")
            print("   Run prepare_dataset.py first.")
            sys.exit(1)
        with open(path, encoding="utf-8") as fh:
            data = json.load(fh)
        print(f"📦 Loaded {len(data)} scripts from {path}")
        return data

    def run(self, limit: int = None, start_after_id: int = 0) -> list[dict]:
        """
        Evaluate all scripts (or a subset).
        start_after_id: resume from a specific ID (crash recovery).
        """
        checkpoint_path = RESULTS_DIR / f"checkpoint_{self.mode}.json"
        results = self._load_checkpoint(checkpoint_path)
        done_ids = {r["id"] for r in results}

        scripts = self.dataset
        if start_after_id:
            scripts = [s for s in scripts if s["id"] > start_after_id]
        if limit:
            scripts = scripts[:limit]

        total = len(scripts)
        print(f"\n{'='*65}")
        print(f"  MODE: {self.mode.upper()} | Scripts to evaluate: {total}")
        print(f"{'='*65}\n")

        for i, entry in enumerate(scripts, 1):
            if entry["id"] in done_ids:
                print(f"  [SKIP] #{entry['id']} already done")
                continue

            print(f"  [{i}/{total}] ID={entry['id']} | Tier {entry['tier']} | {entry['title'][:55]}...")
            result = self._evaluate_single(entry)
            results.append(result)

            # Save checkpoint after each script
            self._save_checkpoint(results, checkpoint_path)

            # Brief progress summary
            tp_count = len(result["match_result"]["TP"])
            fn_count = len(result["match_result"]["FN"])
            fp_count = len(result["match_result"]["FP"])
            print(f"    ✅ Done in {result['latency_seconds']:.1f}s | TP={tp_count} FN={fn_count} FP={fp_count}")

        # Save final results
        final_path = RESULTS_DIR / f"raw_results_{self.mode}.json"
        with open(final_path, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2, ensure_ascii=False)
        print(f"\n💾 Saved final results → {final_path}")
        return results

    def _evaluate_single(self, entry: dict) -> dict:
        code       = entry["code"]
        t0         = time.time()
        outputs    = {}
        raw_review = ""

        # --- PYLINT ONLY ---
        if self.config["pylint"] and not self.config["qwen"] and not self.config["rag"]:
            pylint_out  = self.pylint_runner.analyze(code)
            outputs["pylint"] = pylint_out
            raw_review  = pylint_out
            detected    = extract_detected_labels(raw_review)

        # --- RAG ONLY (Option A: retrieval quality) ---
        elif self.config["rag"] and not self.config["qwen"] and not self.config["pylint"]:
            queries     = _extract_queries_from_code(code)
            retrieved   = self.rag_engine.retrieve(queries)
            raw_review  = retrieved
            # Option A: directly score based on keyword presence in retrieved chunks
            detected    = self.rag_engine.score_rag_labels(retrieved, entry["expected_labels"])

        # --- QWEN ONLY or HYBRID (both go through QwenReviewer) ---
        else:
            raw_review = self.qwen_reviewer.review(code)
            detected   = extract_detected_labels(raw_review)

        elapsed       = round(time.time() - t0, 2)
        match_result  = compare_labels(entry["expected_labels"], detected)
        ast_validity  = check_ast_validity(raw_review)
        spec_result   = check_spec_compliance(raw_review, entry["expected_labels"])

        return {
            "id":               entry["id"],
            "tier":             entry["tier"],
            "title":            entry["title"],
            "mode":             self.mode,
            "expected":         entry["expected"],
            "expected_labels":  entry["expected_labels"],
            "detected_labels":  detected,
            "match_result":     match_result,
            "ast_validity":     ast_validity,
            "spec_compliance":  spec_result,
            "raw_review":       raw_review,
            "latency_seconds":  elapsed,
        }

    @staticmethod
    def _load_checkpoint(path: Path) -> list[dict]:
        if path.exists():
            with open(path, encoding="utf-8") as fh:
                data = json.load(fh)
            print(f"  📥 Resuming from checkpoint: {len(data)} results loaded")
            return data
        return []

    @staticmethod
    def _save_checkpoint(results: list[dict], path: Path):
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(results, fh, indent=2, ensure_ascii=False)


def _extract_queries_from_code(code: str) -> list[str]:
    """Simple heuristic to derive 3 RAG search queries without needing the LLM."""
    queries = ["Python naming conventions PEP 8"]
    if "eval(" in code:
        queries.append("eval() security vulnerability OWASP")
    if "open(" in code:
        queries.append("file handling resource management context manager")
    if "def " in code:
        queries.append("function documentation docstring")
    if "API_KEY" in code or "SECRET" in code or "PASSWORD" in code or "TOKEN" in code:
        queries.append("hardcoded credentials OWASP security")
    if ".remove(" in code or "for " in code:
        queries.append("list mutation during iteration Python bug")
    return queries[:3]


# ===========================================================================
# CLI entry point
# ===========================================================================

def parse_args():
    parser = argparse.ArgumentParser(description="AI Code Review Evaluation Harness")
    parser.add_argument(
        "--mode",
        choices=list(MODES),
        default="hybrid",
        help="Pipeline mode to evaluate"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit to first N scripts (for dry-runs)"
    )
    parser.add_argument(
        "--start-after",
        type=int,
        default=0,
        help="Resume evaluation after this script ID"
    )
    parser.add_argument(
        "--dataset",
        default=str(DATASET),
        help="Path to dataset.json"
    )
    return parser.parse_args()


if __name__ == "__main__":
    args    = parse_args()
    harness = EvaluationHarness(mode=args.mode, dataset_path=args.dataset)
    harness.run(limit=args.limit, start_after_id=args.start_after)
