import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scratch.execute_evaluation import build_report

def main():
    raw_results_path = Path("scratch/evaluation_gemma_raw_results.json")
    if not raw_results_path.exists():
        print("Raw results not found at scratch/evaluation_gemma_raw_results.json")
        return
        
    with open(raw_results_path, "r", encoding="utf-8") as f:
        results = json.load(f)
        
    # Load manual evaluations
    manual_evals_path = Path("scratch/extracted_manual_evals.json")
    if manual_evals_path.exists():
        with open(manual_evals_path, "r", encoding="utf-8") as f:
            manual_evals = json.load(f)
    else:
        manual_evals = {}
        
    print(f"Loaded {len(results)} results and {len(manual_evals)} manual evals. Rebuilding report...")
    build_report(results, manual_evals)
    print("Report rebuilt successfully!")

if __name__ == "__main__":
    main()
