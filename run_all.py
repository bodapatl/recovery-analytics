"""One-command full reproduction:

    raw -> staging -> clean -> golden -> reports -> dashboard data -> notebook
"""
from __future__ import annotations

import subprocess
import sys


def run(cmd: list[str]) -> None:
    print("\n=== ", " ".join(cmd), " ===", flush=True)
    result = subprocess.run([sys.executable, "-X", "utf8", *cmd], cwd=".")
    if result.returncode != 0:
        raise SystemExit(f"step failed: {cmd}")


def main() -> None:
    run(["-m", "src.pipeline"])              # SQL pipeline + golden exports
    run(["-m", "src.forensics"])             # data quality report (auto-numbers)
    run(["-m", "src.analysis"])              # stats + counterfactual + investment
    run(["-m", "src.verify"])                # reproducibility + reconciliation tests
    run(["-m", "src.driver_matrix"])         # driver results matrix
    run(["-m", "src.export_dashboard"])      # dashboard/data.js
    run(["-m", "src.build_notebook"])        # regenerate notebook
    try:
        subprocess.run(
            [sys.executable, "-m", "jupyter", "nbconvert", "--to", "notebook",
             "--execute", "--inplace", "analysis/analysis_notebook.ipynb"],
            check=True, capture_output=True, text=True,
        )
        print("notebook executed")
    except subprocess.CalledProcessError as e:
        print("notebook execution skipped/failed:", e.stderr[-400:] if e.stderr else e)
    print("\nAll deliverables regenerated. Open dashboard/index.html.")


if __name__ == "__main__":
    main()
