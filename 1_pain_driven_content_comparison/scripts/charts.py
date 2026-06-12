"""Render the report figures into ``outputs/*.png`` from the tables computed in
analyze.py. Deterministic: same input -> identical images. No display backend
required (Agg)."""
from __future__ import annotations

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

try:
    from . import config as C
except ImportError:  # pragma: no cover
    import config as C

plt.rcParams.update({
    "figure.dpi": 130,
    "savefig.bbox": "tight",
    "font.size": 11,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
})

SHORT = {
    C.PAIN_DRIVEN: "Blog\n(pain-driven)",
    C.SIMPLE_AI: "Product\n(simple AI)",
    C.CATEGORY: "Category",
    C.PRODUCT_SUB: "Product\nsubpages",
    C.OTHER: "Other",
}


def _save(fig, name):
    path = C.OUTPUTS_DIR / name
    fig.savefig(path)
    plt.close(fig)
    return path


def avg_position(summary):
    """Chart 1 — impression-weighted average position. Lower = better rank."""
    d = summary[summary["cohort"].isin(C.PRIMARY_COHORTS + [C.CATEGORY])]
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    labels = [SHORT[c] for c in d["cohort"]]
    colors = [C.PALETTE[c] for c in d["cohort"]]
    bars = ax.bar(labels, d["wmean_position"], color=colors, width=0.6)
    ax.invert_yaxis()  # better rank (smaller) sits at the top
    ax.set_ylabel("Avg. position (impression-weighted)")
    ax.set_title("Where impressions land: avg position by cohort\n(lower = better; page-for-page blog vs product is statistically tied)")
    for b, v in zip(bars, d["wmean_position"]):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.2f}", ha="center", va="bottom", fontweight="bold")
    return _save(fig, "1_avg_position.png")


def position_box(pages):
    """Chart 2 — distribution (not just mean) of per-page position."""
    cohorts = C.PRIMARY_COHORTS + [C.CATEGORY]
    data = [pages.loc[pages["cohort"] == c, "position"].values for c in cohorts]
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    bp = ax.boxplot(data, labels=[SHORT[c] for c in cohorts], patch_artist=True,
                    medianprops={"color": "black"}, showfliers=True,
                    flierprops={"marker": ".", "markersize": 4, "alpha": 0.4})
    for patch, c in zip(bp["boxes"], cohorts):
        patch.set_facecolor(C.PALETTE[c])
        patch.set_alpha(0.85)
    ax.invert_yaxis()
    ax.set_ylabel("Per-page avg. position")
    ax.set_title("Position distribution by cohort (lower = better)")
    return _save(fig, "2_position_distribution.png")


def impressions_per_page(summary):
    """Chart 3 — visibility / citations earned per page."""
    d = summary[summary["cohort"].isin(C.PRIMARY_COHORTS + [C.CATEGORY])]
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    labels = [SHORT[c] for c in d["cohort"]]
    colors = [C.PALETTE[c] for c in d["cohort"]]
    bars = ax.bar(labels, d["impr_per_page"], color=colors, width=0.6)
    ax.set_ylabel("Impressions per page")
    ax.set_title("App pages earn more impressions per page\n(blog targets lower-volume long-tail queries)")
    for b, v in zip(bars, d["impr_per_page"]):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.1f}", ha="center", va="bottom", fontweight="bold")
    return _save(fig, "3_impressions_per_page.png")


def ctr_with_ci(summary):
    """Chart 4 — CTR with 95% Wilson intervals for the primary cohorts."""
    d = summary[summary["cohort"].isin(C.PRIMARY_COHORTS)]
    fig, ax = plt.subplots(figsize=(6.5, 4.2))
    labels = [SHORT[c] for c in d["cohort"]]
    colors = [C.PALETTE[c] for c in d["cohort"]]
    ctr = d["ctr"].values * 100
    lo = (d["ctr"] - d["ctr_ci_low"]).values * 100
    hi = (d["ctr_ci_high"] - d["ctr"]).values * 100
    bars = ax.bar(labels, ctr, color=colors, width=0.5,
                  yerr=[lo, hi], capsize=8, error_kw={"elinewidth": 1.5})
    ax.set_ylabel("CTR (%)")
    ax.set_title("Click-through rate with 95% confidence intervals\n(intervals overlap -> conversion gap is not conclusive)")
    for b, v in zip(bars, ctr):
        ax.text(b.get_x() + b.get_width() / 2, v, f"{v:.2f}%", ha="center", va="bottom", fontweight="bold")
    return _save(fig, "4_ctr_with_ci.png")


def ctr_by_band(band):
    """Chart 5 — CTR within each position band (rank-controlled). If blog ranked
    well but simply 'sat where CTR is low', its bars would rise with product's in
    the top bands. They don't: blog is 0 in every band -> the gap is not a ranking
    artifact. Each bar is annotated with clicks/impressions so the zeros read as
    real (sampled) zeros, not missing data."""
    bands = [lbl for _, _, lbl in C.POSITION_BANDS]
    fig, ax = plt.subplots(figsize=(7.0, 4.4))
    width = 0.38
    xs = range(len(bands))
    for i, c in enumerate(C.PRIMARY_COHORTS):
        sub = band[band["cohort"] == c].set_index("position_band").reindex(bands)
        offs = [x + (i - 0.5) * width for x in xs]
        bars = ax.bar(offs, sub["ctr"].fillna(0) * 100, width=width,
                      color=C.PALETTE[c], label=SHORT[c].replace("\n", " "))
        for b, (_, row) in zip(bars, sub.iterrows()):
            n = 0 if row.isna().all() else int(row["impressions"])
            clk = 0 if row.isna().all() else int(row["clicks"])
            ax.text(b.get_x() + b.get_width() / 2, b.get_height(),
                    f"{clk}/{n}", ha="center", va="bottom", fontsize=8)
    ax.set_xticks(list(xs))
    ax.set_xticklabels([f"pos {b}" for b in bands])
    ax.set_ylabel("CTR (%)")
    ax.set_title("Rank-controlled CTR: blog converts 0 in every band\n(labels = clicks / impressions per band)")
    ax.legend(frameon=False)
    return _save(fig, "5_ctr_by_position_band.png")


def branded_split(branded):
    """Chart 6 — share of clicks from branded vs non-branded queries."""
    d = branded.sort_values("is_branded", ascending=False)
    fig, ax = plt.subplots(figsize=(5.6, 4.6))
    colors = ["#2a9d8f", "#e9c46a"]
    wedges, _texts, autotexts = ax.pie(
        d["clicks"], labels=d["segment"], colors=colors[: len(d)],
        autopct=lambda p: f"{p:.0f}%\n({p/100*d['clicks'].sum():.0f} clicks)",
        startangle=90, wedgeprops={"width": 0.42, "edgecolor": "white"})
    for t in autotexts:
        t.set_fontsize(9)
    ax.set_title("Most clicks are brand search, not content\n(query-level; rare queries omitted by GSC)")
    return _save(fig, "6_branded_vs_nonbranded.png")


def ai_citations(ai_by_cohort):
    """Chart 7 — Bing generative-engine (GEO) citations by cohort. Independent
    corroboration: AI answers surface app pages far more than pain-driven posts.
    (Bing signal — deliberately NOT merged with Google clicks.)"""
    d = ai_by_cohort[ai_by_cohort["cohort"].isin(C.PRIMARY_COHORTS)]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(9.0, 4.2))
    labels = [SHORT[c] for c in d["cohort"]]
    colors = [C.PALETTE[c] for c in d["cohort"]]
    for ax, col, title, fmt in [
        (ax1, "citations", "Total AI citations", "{:.0f}"),
        (ax2, "citations_per_cited_page", "Citations per cited page", "{:.1f}"),
    ]:
        bars = ax.bar(labels, d[col], color=colors, width=0.55)
        ax.set_title(title)
        for b, v in zip(bars, d[col]):
            ax.text(b.get_x() + b.get_width() / 2, v, fmt.format(v),
                    ha="center", va="bottom", fontweight="bold")
    fig.suptitle("Bing generative engine cites app pages far more than pain-driven posts",
                 fontweight="bold")
    return _save(fig, "7_ai_citations.png")


def render_all(results) -> list:
    C.OUTPUTS_DIR.mkdir(exist_ok=True)
    paths = [
        avg_position(results["summary"]),
        position_box(results["pages"]),
        impressions_per_page(results["summary"]),
        ctr_with_ci(results["summary"]),
        ctr_by_band(results["ctr_by_band"]),
        branded_split(results["branded"]),
    ]
    if results.get("ai_citations_by_cohort") is not None:
        paths.append(ai_citations(results["ai_citations_by_cohort"]))
    return paths
