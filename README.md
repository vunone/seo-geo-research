# SEO / GEO Conversion Research

A collection of reproducible experiments that ask a single, practical question:

> **What does it take for search citations to *convert* — to earn a click and a
> user — instead of merely existing?**

As AI-generated content and AI Overviews / generative engines (GEO) make it
trivial to *get cited*, the bottleneck shifts from visibility to **conversion**.
Each experiment here isolates one hypothesis about that gap, tests it against
real Google Search Console data, and reports an honest prove/bust verdict with
charts and reproducible code.

## Data provenance

Data comes from first-party search analytics for **[achiv.com](https://achiv.com)**
— a directory of AI apps that publishes both AI-generated app pages and
pain-point-driven blog posts:

- **Google Search Console** performance exports (Web search) — clicks,
  impressions, CTR, position — under each experiment's `gsc/` folder.
- **Bing AI Page Stats** exports — per-page citation counts in Bing's generative
  (GEO) answers — under `bing_ai/`, where available.

Each experiment folder records the exact export window used. No data is fetched
at runtime; experiments are fully offline and deterministic.

## Repository layout

```
research/
├── README.md                          # this file
├── requirements.txt                   # shared Python dependencies
└── 1_pain_driven_content_comparison/  # Experiment 1
    ├── README.md                      # the research write-up (start here)
    ├── gsc/                           # raw Google Search Console export
    ├── bing_ai/                       # raw Bing AI Page Stats export (GEO)
    ├── scripts/                       # reproducible analysis + charting
    └── outputs/                       # generated tables (.csv) and charts (.png)
```

Each experiment is self-contained: its `README.md` is a short research paper, its
`scripts/` reproduce every number, and its `outputs/` hold the derived tables and
figures.

## Table of contents

| # | Experiment | Question | Verdict |
|---|---|---|---|
| 1 | [AI pain-driven content vs simple AI content](1_pain_driven_content_comparison/README.md) | Do Reddit-pain-point blog posts rank & convert better than AI app pages? | ❌ Strong hypothesis busted — ranking is a tie, conversion gap real but inconclusive; the real lever is intent-to-click |
| — | *TBD* | — | — |

## Reproducing any experiment

```bash
python3 -m pip install -r requirements.txt
python3 1_pain_driven_content_comparison/scripts/main.py
```

Dependencies: `pandas`, `numpy`, `matplotlib`, `scipy` (see
[`requirements.txt`](requirements.txt)). Python 3.10+.
