"""Runs the whole pipeline with one command:
  python run_all.py                      brief → plan → copy + images → guardrail panel
  python run_all.py --scenario vp_edits  ...then also checks a copy with the VP's edits
Then open the review queue with:  streamlit run app.py"""
import subprocess
import sys

steps = [["run_planner.py"], ["run_creative.py"], ["run_checks.py"]]
if "--scenario" in sys.argv:
    steps.append(["run_checks.py", "--scenario", sys.argv[sys.argv.index("--scenario") + 1]])

for step in steps:
    print(f"\n===== {' '.join(step)} =====")
    subprocess.run([sys.executable, *step], check=True)

print("\nDone. Open the review queue with:  streamlit run app.py")
