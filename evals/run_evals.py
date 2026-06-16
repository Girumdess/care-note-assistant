"""Run the eval suite: PHI-leakage rate + documentation quality, with cost tracking."""
import json
import time
from datetime import datetime
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor, as_completed

from care_assistant.pipeline import process_note
from care_assistant import config
from evals.dataset import CASES
from evals.metrics import phi_leaks, judge_quality


def run_case(case: dict) -> dict:
    result = process_note(case["note"], case.get("client"))
    leaked = phi_leaks(result["redacted"], case.get("phi_items", []))
    quality = judge_quality(case["note"], result["redacted"])
    return {
        "id": case["id"], "category": case.get("category", ""),
        "client": case.get("client"), "input": case["note"],
        "phi_items": case.get("phi_items", []), "phi_leaked": leaked,
        "phi_caught": result["phi_count"], "quality": quality,
        "final": result["redacted"], "generated": result["generated"],
    }


def main(max_workers: int = 5):
    config.reset_usage()
    t0 = time.time()
    results = []
    with ThreadPoolExecutor(max_workers=max_workers) as ex:
        futs = {ex.submit(run_case, c): c for c in CASES}
        for f in as_completed(futs):
            try:
                results.append(f.result())
            except Exception as e:
                results.append({"id": futs[f]["id"], "error": str(e)[:200]})
    results.sort(key=lambda r: r["id"])

    ok = [r for r in results if "error" not in r]
    total_phi = sum(len(r["phi_items"]) for r in ok)
    leaked_phi = sum(len(r["phi_leaked"]) for r in ok)
    cases_with_phi = [r for r in ok if r["phi_items"]]
    cases_leaking = [r for r in cases_with_phi if r["phi_leaked"]]
    quals = [r["quality"]["overall"] for r in ok if r.get("quality")]
    usage = config.get_usage()

    summary = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "n_cases": len(results),
        "phi_items_total": total_phi,
        "phi_items_leaked": leaked_phi,
        "phi_leakage_rate_pct": round(100 * leaked_phi / total_phi, 1) if total_phi else 0.0,
        "phi_cases_total": len(cases_with_phi),
        "phi_cases_clean": len(cases_with_phi) - len(cases_leaking),
        "avg_quality_overall": round(sum(quals) / len(quals), 2) if quals else 0,
        "runtime_sec": round(time.time() - t0, 1),
        "usage": usage,
    }

    Path("reports").mkdir(exist_ok=True)
    with open("reports/eval_results.json", "w") as f:
        json.dump({"summary": summary, "results": results}, f, indent=2)

    print("=" * 62)
    print("CARE-NOTE ASSISTANT  —  EVALUATION REPORT")
    print("=" * 62)
    print(f"Cases evaluated:        {summary['n_cases']}")
    print(f"PHI items in test set:  {summary['phi_items_total']}")
    print(f"PHI items leaked:       {summary['phi_items_leaked']}")
    print(f"PHI LEAKAGE RATE:       {summary['phi_leakage_rate_pct']}%")
    print(f"  cases w/ PHI clean:   {summary['phi_cases_clean']}/{summary['phi_cases_total']}")
    print(f"AVG QUALITY (1-5):      {summary['avg_quality_overall']}")
    print(f"Runtime:                {summary['runtime_sec']}s   |   API calls: {usage['calls']}")
    print(f"Tokens in/out:          {usage['input_tokens']}/{usage['output_tokens']}")
    print(f"EST. COST THIS RUN:     ${usage['cost_usd']:.4f}")
    print("-" * 62)
    if cases_leaking:
        print("LEAKS:")
        for r in cases_leaking:
            print(f"  {r['id']} ({r['category']}): {r['phi_leaked']}")
    else:
        print("No PHI leaks detected across the test set.")
    print("Saved -> reports/eval_results.json")


if __name__ == "__main__":
    main()
