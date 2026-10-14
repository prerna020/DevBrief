import asyncio
import json
from pathlib import Path

from dotenv import load_dotenv

from app.core.review import review_diff
from eval.golden_schema import GoldenCase
from eval.injection_judge import check_injection_resistance

load_dotenv()

async def main():
    path = Path("eval/injection_golden/injections.json")
    with open(path) as f:
        data = json.load(f)
        
    cases = [GoldenCase.model_validate(c) for c in data]
    
    total = len(cases)
    detected = 0
    complied = 0
    
    print("Running injection evaluation...\n")
    
    for case in cases:
        print(f"--- Case: {case.id} ---")
        try:
            result = await review_diff(case.diff, "file.py")
        except Exception as e:
            print(f"Failed to review {case.id}: {e}")
            if hasattr(e, "last_error"):
                print(f"Last error: {e.last_error}")
            continue
        
        print("Raw Output:")
        print(json.dumps(result.review.model_dump(), indent=2))
        
        judge = await check_injection_resistance(case, result.review)
        print(f"Detected Real Issue: {judge['detected_real_issue']}")
        print(f"Showed Compliance: {judge['showed_compliance']} (Bad URL: {judge['bad_url_found']})")
        print(f"Reason: {judge.get('compliance_reason', '')}\n")
        
        if judge['detected_real_issue']:
            detected += 1
        if judge['showed_compliance']:
            complied += 1
            
    print(f"\nDetection Rate: {detected}/{total} ({(detected/total)*100:.1f}%)")
    print(f"Compliance Rate: {complied}/{total} ({(complied/total)*100:.1f}%)")

if __name__ == "__main__":
    asyncio.run(main())
