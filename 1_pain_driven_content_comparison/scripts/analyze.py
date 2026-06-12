"""Load the GSC export, segment pages into cohorts, and compute every metric and
statistical test used by the report. All derived tables are written to
``outputs/`` (these CSVs ARE the report's data) and also returned in-memory for
the charting step.

Run via ``main.py``; can also be imported (``analyze.run()``).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.stats import mannwhitneyu

try:  # support both "python -m scripts.main" and "python scripts/main.py"
    from . import config as C
except ImportError:  # pragma: no cover
    import config as C


# --- Loading -----------------------------------------------------------------
def load_pages() -> pd.DataFrame:
    """Read Pages.csv, attach a cohort label, and recompute CTR from raw counts
    (more reliable than the rounded percentage string GSC exports)."""
    df = pd.read_csv(C.PAGES_CSV)
    df.columns = ["url", "clicks", "impressions", "ctr_raw", "position"]
    df["clicks"] = df["clicks"].astype(int)
    df["impressions"] = df["impressions"].astype(int)
    df["position"] = df["position"].astype(float)
    df["cohort"] = df["url"].map(C.classify_url)
    df["ctr"] = np.where(df["impressions"] > 0, df["clicks"] / df["impressions"], 0.0)
    df["position_band"] = df["position"].map(C.position_band)
    return df


def load_queries() -> pd.DataFrame:
    df = pd.read_csv(C.QUERIES_CSV)
    df.columns = ["query", "clicks", "impressions", "ctr_raw", "position"]
    df["clicks"] = df["clicks"].astype(int)
    df["impressions"] = df["impressions"].astype(int)
    df["is_branded"] = df["query"].str.contains(C.BRAND_TERM, case=False, na=False)
    return df


# --- Metrics -----------------------------------------------------------------
def _weighted_mean(values: pd.Series, weights: pd.Series) -> float:
    w = weights.sum()
    return float((values * weights).sum() / w) if w > 0 else float("nan")


def cohort_summary(pages: pd.DataFrame) -> pd.DataFrame:
    """One row per cohort with volume, rate, and ranking metrics + Wilson CTR CI."""
    rows = []
    # Order: primary cohorts first, then context cohorts.
    order = C.PRIMARY_COHORTS + [C.CATEGORY, C.PRODUCT_SUB, C.OTHER]
    for cohort in order:
        g = pages[pages["cohort"] == cohort]
        if g.empty:
            continue
        clicks, impr = int(g["clicks"].sum()), int(g["impressions"].sum())
        ctr, lo, hi = C.wilson_interval(clicks, impr)
        rows.append({
            "cohort": cohort,
            "pages": len(g),
            "clicks": clicks,
            "impressions": impr,
            "ctr": ctr,
            "ctr_ci_low": lo,
            "ctr_ci_high": hi,
            "impr_per_page": impr / len(g),
            "clicks_per_page": clicks / len(g),
            "mean_position": float(g["position"].mean()),
            "wmean_position": _weighted_mean(g["position"], g["impressions"]),
            "median_position": float(g["position"].median()),
            "pct_top3": float((g["position"] <= 3).mean() * 100),
            "pct_top10": float((g["position"] <= 10).mean() * 100),
        })
    return pd.DataFrame(rows)


def position_distribution(pages: pd.DataFrame) -> pd.DataFrame:
    """Quantile profile of per-page average position, per cohort (for the box plot
    and to document spread, not just the mean)."""
    rows = []
    for cohort in C.PRIMARY_COHORTS + [C.CATEGORY]:
        g = pages[pages["cohort"] == cohort]["position"]
        if g.empty:
            continue
        rows.append({
            "cohort": cohort, "pages": len(g),
            "min": float(g.min()), "p25": float(g.quantile(0.25)),
            "median": float(g.median()), "p75": float(g.quantile(0.75)),
            "max": float(g.max()), "mean": float(g.mean()),
        })
    return pd.DataFrame(rows)


def ctr_by_position_band(pages: pd.DataFrame) -> pd.DataFrame:
    """CTR within each position band for the primary cohorts. Controls for rank:
    if blog ranks BETTER yet clicks the same or less band-for-band, the conversion
    gap is real and not a side effect of where pages sit."""
    rows = []
    for cohort in C.PRIMARY_COHORTS:
        g = pages[pages["cohort"] == cohort]
        for _, _, label in C.POSITION_BANDS:
            b = g[g["position_band"] == label]
            clicks, impr = int(b["clicks"].sum()), int(b["impressions"].sum())
            rows.append({
                "cohort": cohort, "position_band": label,
                "pages": len(b), "clicks": clicks, "impressions": impr,
                "ctr": (clicks / impr) if impr > 0 else 0.0,
            })
    return pd.DataFrame(rows)


def branded_breakdown(queries: pd.DataFrame) -> pd.DataFrame:
    """Branded vs non-branded split of query-level clicks/impressions. Shows how
    much of all 'conversion' is just brand-name search (which no content strategy
    can claim credit for)."""
    g = queries.groupby("is_branded").agg(
        queries=("query", "count"),
        clicks=("clicks", "sum"),
        impressions=("impressions", "sum"),
    ).reset_index()
    g["segment"] = np.where(g["is_branded"], "branded (\"%s\")" % C.BRAND_TERM, "non-branded")
    g["ctr"] = np.where(g["impressions"] > 0, g["clicks"] / g["impressions"], 0.0)
    total_clicks = g["clicks"].sum()
    g["click_share"] = np.where(total_clicks > 0, g["clicks"] / total_clicks, 0.0)
    return g[["segment", "is_branded", "queries", "clicks", "impressions", "ctr", "click_share"]]


def load_ai_citations():
    """Read the Bing 'AI Page Stats' export (citations a page received in Bing's
    generative answers). Returns None if the report isn't present.

    NOTE: this is a *Bing* GEO signal and is NOT directly comparable to the
    *Google* clicks/impressions above — different engines. It is used as an
    independent corroboration of which content type AI engines surface, never
    stitched into a single Google funnel."""
    path = C.bing_ai_report()
    if path is None:
        return None
    df = pd.read_csv(path, encoding="utf-8-sig")
    df.columns = ["url", "citations"]
    df["citations"] = df["citations"].astype(int)
    df["cohort"] = df["url"].map(C.classify_url)
    return df


def ai_citations_by_cohort(ai: pd.DataFrame) -> pd.DataFrame:
    """Per-cohort Bing AI-citation totals and intensity (citations per cited page)."""
    rows = []
    for cohort in C.PRIMARY_COHORTS + [C.OTHER]:
        g = ai[ai["cohort"] == cohort]
        if g.empty:
            continue
        rows.append({
            "cohort": cohort,
            "pages_cited": len(g),
            "citations": int(g["citations"].sum()),
            "citations_per_cited_page": g["citations"].mean(),
        })
    return pd.DataFrame(rows)


def ranking_test(pages: pd.DataFrame) -> dict:
    """Mann-Whitney U on per-page average position, blog vs product.
    Alternative='less': blog positions are *smaller* (= better rank). Non-parametric,
    so it tolerates the skewed, non-normal position distributions."""
    blog = pages.loc[pages["cohort"] == C.PAIN_DRIVEN, "position"]
    prod = pages.loc[pages["cohort"] == C.SIMPLE_AI, "position"]
    u, p = mannwhitneyu(blog, prod, alternative="less")
    # Rank-biserial effect size (probability a random blog page outranks a random product page).
    prob_superior = u / (len(blog) * len(prod))
    return {
        "test": "Mann-Whitney U (blog position < product position)",
        "n_blog": int(len(blog)), "n_product": int(len(prod)),
        "blog_median_pos": float(blog.median()), "product_median_pos": float(prod.median()),
        "U": float(u), "p_value": float(p),
        "prob_blog_outranks_product": float(prob_superior),
    }


# --- Orchestration -----------------------------------------------------------
def run() -> dict:
    C.OUTPUTS_DIR.mkdir(exist_ok=True)
    pages = load_pages()
    queries = load_queries()

    summary = cohort_summary(pages)
    pos_dist = position_distribution(pages)
    band = ctr_by_position_band(pages)
    branded = branded_breakdown(queries)
    test = ranking_test(pages)

    summary.to_csv(C.OUTPUTS_DIR / "summary_metrics.csv", index=False)
    pos_dist.to_csv(C.OUTPUTS_DIR / "position_distribution.csv", index=False)
    band.to_csv(C.OUTPUTS_DIR / "ctr_by_position_band.csv", index=False)
    branded.to_csv(C.OUTPUTS_DIR / "branded_vs_nonbranded.csv", index=False)
    pd.DataFrame([test]).to_csv(C.OUTPUTS_DIR / "statistical_tests.csv", index=False)

    ai = load_ai_citations()
    ai_by_cohort = None
    if ai is not None:
        ai_by_cohort = ai_citations_by_cohort(ai)
        ai_by_cohort.to_csv(C.OUTPUTS_DIR / "ai_citations_by_cohort.csv", index=False)

    return {
        "pages": pages, "queries": queries, "summary": summary,
        "position_distribution": pos_dist, "ctr_by_band": band,
        "branded": branded, "ranking_test": test,
        "ai_citations": ai, "ai_citations_by_cohort": ai_by_cohort,
    }


if __name__ == "__main__":
    res = run()
    pd.set_option("display.width", 160, "display.max_columns", 20)
    print(res["summary"].to_string(index=False))
    print("\nRanking test:", res["ranking_test"])
