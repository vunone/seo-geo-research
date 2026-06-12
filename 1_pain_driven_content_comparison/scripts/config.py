"""Shared configuration: paths, cohort definitions, palette, and small stats helpers.

Kept dependency-light so future experiments can copy the pattern. All cohort
logic lives in ``classify_url`` so the rest of the pipeline never hard-codes a
URL pattern.
"""
from __future__ import annotations

import math
from pathlib import Path
from urllib.parse import urlparse

# --- Paths -------------------------------------------------------------------
EXPERIMENT_DIR = Path(__file__).resolve().parent.parent
GSC_DIR = EXPERIMENT_DIR / "gsc"
BING_AI_DIR = EXPERIMENT_DIR / "bing_ai"
OUTPUTS_DIR = EXPERIMENT_DIR / "outputs"

PAGES_CSV = GSC_DIR / "Pages.csv"
QUERIES_CSV = GSC_DIR / "Queries.csv"
CHART_CSV = GSC_DIR / "Chart.csv"


def bing_ai_report():
    """Path to the Bing 'AI Page Stats' export (filename carries an export date).
    Returns the newest matching .csv, or None if the report is absent."""
    if not BING_AI_DIR.exists():
        return None
    reports = sorted(p for p in BING_AI_DIR.glob("*AIPageStatsReport*.csv"))
    return reports[-1] if reports else None

# --- Study window (from gsc/Filters.csv) -------------------------------------
WINDOW_LABEL = "1 Apr 2026 - 1 Jun 2026"  # 2 months; starts after both cohorts indexed
SITE = "achiv.com"
BRAND_TERM = "achiv"  # navigational/branded query marker

# --- Cohorts -----------------------------------------------------------------
# Canonical labels used everywhere downstream.
PAIN_DRIVEN = "blog (pain-driven)"
SIMPLE_AI = "product (simple AI)"
CATEGORY = "category (context)"
PRODUCT_SUB = "product subpages (context)"
OTHER = "other (home/nav)"

# Cohorts that form the primary head-to-head comparison.
PRIMARY_COHORTS = [PAIN_DRIVEN, SIMPLE_AI]

# Consistent colours across every figure.
PALETTE = {
    PAIN_DRIVEN: "#d1495b",   # red  -> pain-driven
    SIMPLE_AI: "#30638e",     # blue -> simple AI app pages
    CATEGORY: "#8d99ae",
    PRODUCT_SUB: "#a8c686",
    OTHER: "#c0c0c0",
}

# Position bands for the position-controlled CTR comparison.
POSITION_BANDS = [(1, 3, "1-3"), (4, 10, "4-10"), (11, 20, "11-20"), (21, 1000, "21+")]


def classify_url(url: str) -> str:
    """Map a GSC page URL to one of the cohort labels above.

    Cohort rules (see README methodology):
      * ``/blog/<uuid>-slug/``  -> pain-driven article (the bare ``/blog/`` index
        is navigation, NOT an article, so it is excluded -> OTHER).
      * ``/product/<slug>/``    -> simple-AI app page (canonical, one per app).
      * ``/product/<slug>/...`` -> product subpage (e.g. /feedback/) -> context.
      * ``/category/...``       -> category, context only.
      * everything else (home, /about, /directory, /blog/ index) -> OTHER.
    """
    path = urlparse(url).path
    segments = [s for s in path.split("/") if s]

    if not segments:
        return OTHER  # homepage

    head = segments[0]
    if head == "blog":
        # Article only when there is a slug after /blog/. Bare /blog/ -> OTHER.
        return PAIN_DRIVEN if len(segments) >= 2 else OTHER
    if head == "product":
        if len(segments) == 2:
            return SIMPLE_AI            # /product/<slug>/
        if len(segments) >= 3:
            return PRODUCT_SUB          # /product/<slug>/feedback/ etc.
        return OTHER                    # bare /product/
    if head == "category":
        return CATEGORY
    return OTHER


def position_band(pos: float) -> str:
    for lo, hi, label in POSITION_BANDS:
        if lo <= pos <= hi:
            return label
    return "21+"


# --- Stats helpers -----------------------------------------------------------
def wilson_interval(clicks: int, impressions: int, z: float = 1.96):
    """95% Wilson score interval for a CTR (clicks / impressions).

    Robust at tiny counts and at p=0 (where the normal approximation collapses),
    which is exactly the regime of the blog cohort here.
    Returns (point_estimate, low, high) as proportions.
    """
    n = impressions
    if n == 0:
        return 0.0, 0.0, 0.0
    p = clicks / n
    denom = 1 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = (z * math.sqrt((p * (1 - p) + z**2 / (4 * n)) / n)) / denom
    return p, max(0.0, centre - half), min(1.0, centre + half)
