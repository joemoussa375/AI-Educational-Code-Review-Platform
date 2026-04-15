import requests
import json
import time
import os

def extract_tests(filepath):
    """Parses test_codes.py into individual structured test cases using a robust state machine."""
    print("🔍 Reading test_codes.py...")
    if not os.path.exists(filepath):
        print(f"❌ Error: {filepath} not found.")
        return []
        
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    tests = []
    current_test = {"title": "Unknown", "expected": "", "code": []}
    in_test = False
    
    for line in content.splitlines():
        if line.startswith('# TEST'):
            # Save the previous test if we are already in one
            if in_test and current_test["code"]:
                tests.append({
                    "title": current_test["title"],
                    "expected": current_test["expected"],
                    "code": '\n'.join(current_test["code"]).strip()
                })
                
            in_test = True
            current_test = {"title": line.replace('# ', '').strip(), "expected": "", "code": []}
        elif line.startswith('# Expected:') and in_test:
            current_test["expected"] = line.replace('# Expected:', '').strip()
        elif not line.startswith('#') and in_test:
            # Add line to code (skip leading blank lines, keep internal ones)
            if line.strip() or current_test["code"]:
                current_test["code"].append(line)
                
    # Save the very last test
    if in_test and current_test["code"]:
        tests.append({
            "title": current_test["title"],
            "expected": current_test["expected"],
            "code": '\n'.join(current_test["code"]).strip()
        })
                
    if not tests:
        print("❌ Error: Could not parse any tests! Make sure test_codes.py starts test cases with '# TEST'.")
    else:
        print(f"✅ Successfully found {len(tests)} tests.")
        
    return tests

def run_evaluation():
    tests = extract_tests('test_codes.py')
    if not tests:
        return
        
    print(f"🚀 Found {len(tests)} test cases. Starting automated evaluation...")
    results = []
    
    for i, test in enumerate(tests):
        print(f"\n[{i+1}/{len(tests)}] Running {test['title']}...")
        print(f"    Expected: {test['expected']}")
        
        start_time = time.time()
        
        try:
            # Ping the local Flask API
            response = requests.post(
                "http://localhost:5000/api/review", 
                json={"code": test["code"]},
                timeout=300
            )
            data = response.json()
            if "error" in data:
                review = f"API Error: {data['error']}"
            else:
                review = data.get("review", "Missing review data")
        except Exception as e:
            review = f"Request Failed: {e}"
            
        elapsed = time.time() - start_time
        
        results.append({
            "id": i + 1,
            "title": test["title"],
            "expected": test["expected"],
            "code": test["code"],
            "review": review,
            "time_seconds": round(elapsed, 2)
        })
        print(f"    ✅ Completed in {elapsed:.1f}s")
        
    # Save results
    with open('evaluation_results.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, indent=4)
        
    print("\n🎉 Evaluation complete!")
    print("💾 Saved all results to evaluation_results.json")
    print("   Download this file from Colab to generate your report graphs.")

if __name__ == "__main__":
    # Ensure Colab allows local API calls
    # Simply run: python evaluate_model.py
    run_evaluation()
