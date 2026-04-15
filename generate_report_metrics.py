import json
import ast
import os
import matplotlib.pyplot as plt

def extract_code_block(review_text):
    """Extracts the python code block from the markdown review."""
    if "```python" in review_text and "```" in review_text.split("```python")[1]:
        return review_text.split("```python")[1].split("```")[0].strip()
    return None

def main():
    if not os.path.exists('evaluation_results.json'):
        print("❌ evaluation_results.json not found! Run evaluate_model.py first.")
        return

    with open('evaluation_results.json', 'r', encoding='utf-8') as f:
        results = json.load(f)

    print("="*50)
    print(" 📊 ACADEMIC METRICS EVALUATION")
    print("="*50)

    # 1. Code Resolution Rate (Validity via AST parsing - Chen et al., 2021)
    valid_count = 0
    total_with_code = 0
    
    for r in results:
        code = extract_code_block(r['review'])
        if code:
            total_with_code += 1
            try:
                ast.parse(code)
                valid_count += 1
            except SyntaxError:
                pass
                
    resolution_rate = (valid_count / total_with_code) * 100 if total_with_code > 0 else 0
    print(f"✅ Code Resolution Rate (AST Validity): {resolution_rate:.1f}% ({valid_count}/{total_with_code})")

    # 2. Functional Error Detection Rate (Recall - SWRBench, 2025)
    # Tests that contain known logic/security bugs: T1, T2, T4, T7, T8, T9
    bug_tests = [1, 2, 4, 7, 8, 9]
    detected = 0
    
    # Simple heuristic: if the critical issues section is not "No critical issues found."
    for r in results:
        if r['id'] in bug_tests:
            # Check if critical section has substance
            crit = r['review'].split('**2. Style')[0].lower() if '**2. Style' in r['review'] else r['review'].lower()
            if "no critical issues" not in crit and "none exist" not in crit:
                detected += 1
                
    recall_rate = (detected / len(bug_tests)) * 100 if bug_tests else 0
    print(f"🎯 Functional Error Detection Rate (Recall): {recall_rate:.1f}% ({detected}/{len(bug_tests)})")

    # 3. Specification Compliance (SGCR Framework, 2025)
    # T6 specifically tests PEP-8 style formatting based on RAG guidelines
    t6_review = next((r['review'] for r in results if r['id'] == 6), "")
    style_section = t6_review.split('**3. Refactored')[0].lower() if '**3. Refactored' in t6_review else t6_review.lower()
    
    # Did it catch CamelCase or spacing?
    compliance = "camelcase" in style_section or "snake_case" in style_section or "lowercase" in style_section
    compliance_score = 100 if compliance else 0
    print(f"📜 Specification Compliance Rate: {compliance_score}% (Detected PEP-8 naming correctly? {compliance})")

    # 4. Generate Plot
    print("\n📈 Generating graphs for report...")
    metrics = ['AST Validity \n(Code Resolution)', 'Error Recall \n(Functional Detection)', 'Spec Compliance \n(RAG Integration)']
    scores = [resolution_rate, recall_rate, compliance_score]
    colors = ['#2ECC71', '#3498DB', '#9B59B6']

    plt.figure(figsize=(9, 6))
    bars = plt.bar(metrics, scores, color=colors)
    plt.ylim(0, 110)
    plt.ylabel('Percentage Score (%)', fontsize=12)
    plt.title('AI Code Mentor Performance (Qwen2.5-Coder-7B)', fontsize=14, fontweight='bold')

    # Add score labels on top
    for bar in bars:
        yval = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, yval + 2, f'{yval:.1f}%', ha='center', fontsize=12, fontweight='bold')

    # Save to disk
    plt.savefig('report_metrics.png', dpi=300, bbox_inches='tight')
    print("✅ Saved 'report_metrics.png' successfully!")
    print("\n👉 Upload 'evaluate_model.py' to Colab, run it, then run this script to generate your report data!")

if __name__ == "__main__":
    main()
