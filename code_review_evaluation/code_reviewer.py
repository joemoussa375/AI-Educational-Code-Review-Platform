"""
AI Code Reviewer - Core Module
Combines RAG (Knowledge Base) + Static Analysis (Pylint) + LLM (Qwen2.5-Coder)
"""

import torch
import json
import re
import os
import subprocess
import tempfile
import textwrap
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

# LangChain Imports
from langchain_community.document_loaders import TextLoader
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_community.retrievers import BM25Retriever
from langchain_core.documents import Document

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter


# ---------------------------------------------------------
# 1. KNOWLEDGE BASE (RAG Engine)
# ---------------------------------------------------------
class KnowledgeBase:
    """
    RAG-based knowledge retrieval from a local offline Knowledge Base.
    Covers PEP 8 style, OWASP Security, and SOLID Design Principles.
    Uses hybrid search: FAISS (semantic) + BM25 (keyword).
    """
    
    def __init__(self, filepath="knowledge_base.md"):
        if not os.path.exists(filepath):
            raise FileNotFoundError(
                f"❌ Knowledge base file '{filepath}' not found! "
                "Please upload it to the /content/ folder on Colab."
            )
        
        print(f"📚 Loading Offline Knowledge Base from: {filepath}")
        loader = TextLoader(filepath, encoding='utf-8')
        data = loader.load()

        # Split on markdown section headers to preserve semantic meaning
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=500,
            chunk_overlap=60,
            separators=["\n## ", "\n### ", "\n- ", "\n", " "]
        )
        splits = text_splitter.split_documents(data)
        
        # CPU Embedding (Saves GPU for the LLM)
        embedding_model = HuggingFaceEmbeddings(
            model_name="all-MiniLM-L6-v2",
            model_kwargs={'device': 'cpu'}
        )

        self.vectorstore = FAISS.from_documents(splits, embedding_model)
        self.bm25_retriever = BM25Retriever.from_documents(splits)
        self.bm25_retriever.k = 3
        
        print(f"✅ Knowledge Base Ready. ({len(splits)} rule chunks indexed)")

    def search(self, queries):
        """
        Hybrid search: combines semantic (FAISS) and keyword (BM25) results.
        """
        results = []
        for q in queries:
            docs_faiss = self.vectorstore.similarity_search(q, k=2)
            docs_bm25 = self.bm25_retriever.invoke(q)
            results.extend(docs_faiss + docs_bm25)
        
        # Deduplicate
        unique_docs = {doc.page_content: doc for doc in results}.values()
        return "\n\n".join([f"[Guide Excerpt]: {doc.page_content}" for doc in unique_docs])


# ---------------------------------------------------------
# 2. THE UNIFIED REVIEWER (RAG + Pylint + LLM)
# ---------------------------------------------------------
class UnifiedCodeReviewer:
    """
    Main code review engine combining:
    - Static Analysis (Pylint)
    - RAG-based style guide lookup
    - LLM-powered deep analysis
    """
    
    def __init__(self, model_id="Qwen/Qwen2.5-Coder-7B-Instruct", hf_token=None):
        # 1. Initialize RAG
        self.kb = KnowledgeBase()
        
        print(f"🤖 Loading Brain: {model_id}...")
        
        # 2. Handle authentication
        if hf_token:
            from huggingface_hub import login
            login(token=hf_token)
        else:
            # Try to get token from environment or Kaggle
            hf_token = os.getenv("HF_TOKEN")
            if hf_token:
                from huggingface_hub import login
                login(token=hf_token)
            else:
                try:
                    from kaggle_secrets import UserSecretsClient
                    hf_token = UserSecretsClient().get_secret("HF_TOKEN")
                    from huggingface_hub import login
                    login(token=hf_token)
                except Exception:
                    print("⚠️ No HF_TOKEN found. Model may fail to load if not cached.")
        
        # 3. Initialize Model (GPU with 4-bit quantization)
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
        )

        self.tokenizer = AutoTokenizer.from_pretrained(model_id)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            quantization_config=bnb_config,
            device_map="auto",
            low_cpu_mem_usage=True,
            torch_dtype=torch.float16
        )
        print("✅ System Online.")

    def _ask_llm(self, messages, max_tokens=200):
        """Generate response from the LLM using ChatML messages."""
        prompt = self.tokenizer.apply_chat_template(
            messages, tokenize=False, add_generation_prompt=True
        )
        inputs = self.tokenizer(prompt, return_tensors="pt").to("cuda")
        outputs = self.model.generate(
            **inputs, 
            max_new_tokens=max_tokens,
            temperature=0.2,
            repetition_penalty=1.2,
            top_p=0.9,
            do_sample=True
        )
        # Decode and extract only the assistant's response
        full_output = self.tokenizer.decode(outputs[0], skip_special_tokens=False)
        # Split on the last assistant marker to get only the new response
        if "<|im_start|>assistant" in full_output:
            response = full_output.split("<|im_start|>assistant")[-1]
            response = response.replace("<|im_end|>", "").strip()
        else:
            response = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
            response = response[len(prompt):].strip()
        return response

    def _run_pylint(self, code_snippet):
        """Run static analysis on the code using Pylint."""
        with tempfile.NamedTemporaryFile(mode='w+', suffix='.py', delete=False) as f:
            f.write(code_snippet)
            fname = f.name
            
        try:
            result = subprocess.run(
                ["pylint", fname, "--output-format=json"], 
                capture_output=True, text=True
            )
            
            if not result.stdout.strip(): 
                return "No Syntax Errors Found."
            
            try:
                errors = json.loads(result.stdout)
                # Limit to top 15 errors to prevent context flooding
                if len(errors) > 15:
                    report = [f"Line {e['line']}: {e['message']} ({e['symbol']})" for e in errors[:15]]
                    report.append("... (and more)")
                else:
                    report = [f"Line {e['line']}: {e['message']} ({e['symbol']})" for e in errors]
                return "\n".join(report)
            except json.JSONDecodeError: 
                return "Pylint ran but output was not parseable."
        except Exception as e:
            return f"Pylint Failed to Run: {e}"
        finally:
            if os.path.exists(fname): 
                os.remove(fname)

    def _generate_search_plan(self, code_snippet):
        """Analyze code to decide what style topics to search for (returns JSON)."""
        messages = [
            {"role": "system", "content": "You are a Python Style Analyst. Identify 3 SPECIFIC Python style topics relevant to the code. You MUST output ONLY valid JSON. Nothing else. No explanation. Schema: {\"queries\": [\"string\", \"string\", \"string\"]} Example: {\"queries\": [\"function naming conventions\", \"import placement\", \"list comprehensions\"]}"},
            {"role": "user", "content": f"Code:\n{code_snippet}"}
        ]
        
        raw_response = self._ask_llm(messages, max_tokens=150)
        
        try:
            json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
            if json_match:
                data = json.loads(json_match.group(0))
                queries = data.get("queries", [])
                # Validate: ensure we got a list of strings
                if isinstance(queries, list) and len(queries) > 0:
                    return queries[:3]
            return ["Python naming conventions", "code structure", "error handling"]
        except (json.JSONDecodeError, AttributeError):
            return ["Python naming conventions", "code structure", "error handling"]

    def review(self, code_snippet):
        """
        Main entry point: performs comprehensive code review.
        Returns formatted feedback string.
        """
        print("1. 🧠 Analyzing Code Logic...")
        linter_report = self._run_pylint(code_snippet)
        
        print("2. 🔍 Retrieving Style Rules...")
        search_terms = self._generate_search_plan(code_snippet)
        rag_rules = self.kb.search(search_terms)
        
        print("3. 📝 Generating Final Report...")
        system_msg = f"""You are a Python code reviewer. Review the student's code using the reports below.

STATIC ANALYSIS REPORT:
{linter_report}

STYLE GUIDE:
{rag_rules}

KNOWN BUG PATTERNS — flag these if you see them:
- Using eval() is a CRITICAL security vulnerability.
- Removing items from a list while iterating over it is a CRITICAL bug. Fix with list comprehension.
- Using open() without "with" statement means the file may never be closed.
- Bare "except:" without specifying an exception type hides all errors.
- Nested loops for searching can be replaced with sets for better performance.
- Hardcoded API keys, passwords, tokens, or secrets (e.g. "sk_live_", "ghp_", "password=") in source code is a CRITICAL security vulnerability. Always use environment variables.

RULES:
- Only report issues that ACTUALLY exist in the code. Do not make up problems.
- If the code is already correct and clean, say "No issues found" and return it unchanged.
- The refactored code MUST fix all bugs you identified. Do NOT return buggy code.
- Wrap refactored code in ```python and ``` markers.
- FORMATTING: Never add leading spaces or indentation before your top-level helper functions or main function in the code block. The `def` keyword must touch the left edge completely.

Use this exact format:

**1. Critical Issues:**
List bugs and security issues. If none exist, write "No critical issues found."

**2. Style Analysis:**
List naming or formatting issues based on PEP 8. If code is clean, say so.

**3. Refactored Solution:**
```python
(corrected code here)
```"""
        
        messages = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": f"Review this code:\n\n{code_snippet}"}
        ]
        
        raw = self._ask_llm(messages, max_tokens=1024)
        return self._clean_code_blocks(raw)

    def _clean_code_blocks(self, text):
        """Strip leading whitespace/indentation inside ```python code blocks."""
        def dedent_block(match):
            code = match.group(1)
            return "```python\n" + textwrap.dedent(code).lstrip("\n") + "```"
        return re.sub(r"```python\n(.*?)```", dedent_block, text, flags=re.DOTALL)

    @staticmethod
    def extract_severity(review_text):
        """
        Parse the AI's review output to count critical vs. style issues.
        Used by the API to auto-grade submissions.
        
        Returns: { "critical_count": int, "style_count": int }
        """
        critical_count = 0
        style_count = 0
        
        # Split into sections
        sections = re.split(r'\*\*\d+\.\s*', review_text)
        
        for section in sections:
            lower = section.lower()
            
            # Count critical issues (in the Critical Issues section)
            if 'critical' in lower or 'issue' in lower or 'bug' in lower:
                if 'no critical issues' in lower or 'no issues found' in lower:
                    continue
                # Count bullet points / numbered items as individual issues
                bullets = re.findall(r'(?:^|\n)\s*[-•*]\s+', section)
                numbered = re.findall(r'(?:^|\n)\s*\d+[\.\)]\s+', section)
                count = len(bullets) + len(numbered)
                # At minimum 1 if the section has content beyond the header
                content = re.sub(r'[^a-zA-Z]', '', section)
                if count == 0 and len(content) > 20:
                    count = 1
                critical_count += count
            
            # Count style issues (in the Style Analysis section)
            elif 'style' in lower or 'pep' in lower or 'naming' in lower:
                if 'no style' in lower or 'code is clean' in lower or 'follows pep' in lower:
                    continue
                bullets = re.findall(r'(?:^|\n)\s*[-•*]\s+', section)
                numbered = re.findall(r'(?:^|\n)\s*\d+[\.\)]\s+', section)
                count = len(bullets) + len(numbered)
                content = re.sub(r'[^a-zA-Z]', '', section)
                if count == 0 and len(content) > 20:
                    count = 1
                style_count += count
        
        return {
            "critical_count": critical_count,
            "style_count": style_count
        }
