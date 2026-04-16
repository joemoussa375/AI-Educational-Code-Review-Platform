# AI-Powered Educational Code Review Platform

![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)
![Python 3.10+](https://img.shields.io/badge/Python-3.10%2B-blue.svg)
![React](https://img.shields.io/badge/React-18-61dafb.svg)

An open-source, edge-deployable Educational Feedback Loop Platform designed to transition automated LLM-based code review from a generic "code solver" to a rigorous "code tutor." Built originally as a university Senior Project.

## 📖 Overview

The rapid expansion of computer engineering curricula has exacerbated the student-to-instructor ratio, creating a bottleneck in delivering timely, personalized programming feedback. While students increasingly rely on Large Language Models (LLMs), generalized tools are optimized for industrial code generation rather than pedagogical instruction, often resulting in hallucinated syntax and the circumvention of academic standards.

This platform introduces a **hybrid architecture** that integrates the heuristic reasoning of **Qwen2.5-Coder-7B** with deterministic static analysis via **Pylint**. To enforce strict pedagogical compliance, it utilizes an offline **Retrieval-Augmented Generation (RAG)** engine grounded in PEP 8 and OWASP 2025 guidelines.

### 🌟 Key Features

- **Hybrid Analysis Pipeline:** Combines deterministic AST pre-filtering (Pylint) with high-level heuristic reasoning (Qwen2.5-Coder), eliminating syntax hallucination.
- **Offline RAG Knowledge Vault:** Actively anchors LLM feedback in official style and security guidelines (PEP 8, SOLID, OWASP) using FAISS semantic chunk retrieval.
- **Edge Deployable:** Utilizes 4-bit Normal Float (NF4) quantization via QLoRA to operate smoothly on consumer-tier hardware (e.g., dual-T4 GPUs, standard laptops) with under 6GB of VRAM.
- **Pedagogical Strictness:** Rubric-aligned structure explicitly differentiates between Critical logical bugs and Stylistic violations, completely avoiding arbitrary "code solving" without explanation.

## 🏗️ Architecture Stack

- **Backend AI Engine:** Python, PyTorch, HuggingFace Transformers, LangChain, FAISS, Pylint
- **Language Model:** Qwen/Qwen2.5-Coder-7B-Instruct (Quantized)
- **Frontend Dashboard:** React, Vanilla CSS

## 📊 Evaluation & Dataset

This architecture was subjected to a controlled ablation study comparing the base open-weights model against the full Hybrid pipeline over a proprietary 100-script Curated Tiered Dataset. 

As documented in the corresponding academic paper, the Hybrid model introduces a "rubric-misalignment" phenomenon: statistically trading off raw precision to generate crucial pedagogical True Positives (e.g., intentionally flagging missing docstrings and bare except clauses that standard solvers ignore).

*(The raw evaluation inputs `Testing_Dataset.txt` are available in the root directory for reproducibility).*

## 🚀 Installation & Setup

If you wish to spin up the local development environment or evaluate the backend API logic:

### 1. Clone the Repository
```bash
git clone https://github.com/joemoussa375/AI-Educational-Code-Review-Platform.git
cd AI-Educational-Code-Review-Platform
```

### 2. Backend Setup
Ensure you have Python 3.10+ installed.
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
```

Start the Flask API Server:
```bash
python api.py
```

### 3. Frontend Setup
In a new terminal window:
```bash
cd frontend
npm install
npm run dev
```

## 📜 Citation

If you utilize this architecture or dataset in your academic research, please link back to this repository and pending publication. 

*Department of Computer Engineering, The British University in Egypt.*
