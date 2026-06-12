"""Entrypoint: reproduce every table and figure for Experiment 1 from the raw
GSC export. Writes only into ``outputs/``; reads only from ``gsc/``.

    python3 1_pain_driven_content_comparison/scripts/main.py
    # or, from the experiment folder:
    python3 scripts/main.py
"""
from __future__ import annotations

import pandas as pd

try:
    from . import analyze, charts, config as C
except ImportError:  # run as a plain script
    import analyze
    import charts
    import config as C


def main() -> None:
    print(f"Experiment 1 — pain-driven vs simple AI content | window: {C.WINDOW_LABEL}\n")
    results = analyze.run()

    pd.set_option("display.width", 180, "display.max_columns", 25)
    print("Cohort summary:")
    print(results["summary"].round(4).to_string(index=False))
    print("\nBranded vs non-branded (query-level):")
    print(results["branded"].round(4).to_string(index=False))
    print("\nRanking test (Mann-Whitney U):")
    for k, v in results["ranking_test"].items():
        print(f"  {k}: {v}")

    paths = charts.render_all(results)
    print("\nWrote tables + figures to:", C.OUTPUTS_DIR)
    for p in paths:
        print("  -", p.name)


if __name__ == "__main__":
    main()
