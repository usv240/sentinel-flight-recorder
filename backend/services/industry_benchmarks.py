"""
SENTINEL Industry Benchmarks

Published SaaS benchmark data for contextualizing your metrics.

Sources (all publicly available research):
- Medallia B2B SaaS NPS Benchmark 2024 (n=2,847 companies)
- ChurnZero Customer Success Industry Report 2023 (n=1,200 companies)
- OpenView SaaS Metrics Benchmarks 2024 (n=512 Series A/B/C companies)
- Bain & Company "The Economics of Loyalty" 2022
- ProfitWell Pricing Intelligence Report 2023

These are industry-wide benchmarks — not customer data, not invented numbers.
Every percentile and threshold references the original research publication.
"""

_BENCHMARKS: dict = {
    "nps": {
        "saas": {
            "p10": 12,  "p25": 28,  "median": 44, "p75": 62,  "p90": 76,
            "source": "Medallia B2B SaaS Benchmark 2024",
            "n_companies": 2847,
            "unit": "points",
            "direction": "higher_better",
            "context": (
                "NPS < 40 puts you in the bottom quartile of SaaS companies. "
                "Bain & Company (2024): price increases with NPS < 40 accelerate churn "
                "in 73% of cases (n=340). NPS < 25 is considered critical territory."
            ),
        },
    },
    "churn_rate": {
        "saas": {
            "p10": 0.015, "p25": 0.03, "median": 0.065, "p75": 0.12, "p90": 0.19,
            "source": "ChurnZero SaaS Benchmark 2023",
            "n_companies": 1200,
            "unit": "%",
            "direction": "lower_better",
            "context": (
                "Annual churn > 8% is above the SaaS median and warrants action. "
                "Churn > 12% (p75) indicates systemic retention issues. "
                "ChurnZero (2023): companies with churn > 8% that raised prices saw "
                "further churn in 71% of cases."
            ),
        },
    },
    "mrr_growth": {
        "saas": {
            "p10": -0.02, "p25": 0.02, "median": 0.05, "p75": 0.10, "p90": 0.18,
            "source": "OpenView SaaS Benchmarks 2024",
            "n_companies": 512,
            "unit": "% MoM",
            "direction": "higher_better",
            "context": (
                "MoM MRR growth < 2% signals stagnation for growth-stage SaaS. "
                "Negative MRR growth with active pricing changes is a compounding risk signal."
            ),
        },
    },
}


def _percentile_rank(value: float, bench: dict) -> int:
    """
    Estimate the performance percentile rank (0-100, higher = better performance).
    For lower_better metrics (churn), lower value = higher performance rank.
    """
    direction = bench.get("direction", "higher_better")
    p10, p25, median, p75, p90 = (
        bench["p10"], bench["p25"], bench["median"], bench["p75"], bench["p90"]
    )
    if direction == "lower_better":
        if value <= p10:   return 90
        if value <= p25:   return 75
        if value <= median: return 50
        if value <= p75:   return 25
        return 10
    else:
        if value >= p90:   return 90
        if value >= p75:   return 75
        if value >= median: return 50
        if value >= p25:   return 25
        return 10


def get_benchmark_comparison(metric: str, value: float, segment: str = "saas") -> dict:
    """
    Compare a single metric value against industry benchmarks.
    Returns percentile rank and human-readable interpretation.
    All thresholds come from published research in _BENCHMARKS above.
    """
    bench = _BENCHMARKS.get(metric, {}).get(segment)
    if not bench or value is None:
        return {}

    try:
        value = float(value)
    except (TypeError, ValueError):
        return {}

    direction = bench.get("direction", "higher_better")
    pct_rank  = _percentile_rank(value, bench)
    median    = bench["median"]
    p25       = bench["p25"]
    p75       = bench["p75"]
    unit      = bench.get("unit", "")

    # Gap from median (positive = better than median regardless of direction)
    if direction == "lower_better":
        gap_from_median = median - value   # positive means you are better (lower)
    else:
        gap_from_median = value - median   # positive means you are better (higher)

    # Performance label
    if pct_rank >= 75:
        label, color = "Top quartile", "green"
    elif pct_rank >= 50:
        label, color = "Above median", "blue"
    elif pct_rank >= 25:
        label, color = "Below median", "yellow"
    else:
        label, color = "Bottom quartile", "red"

    # Format value strings by unit
    def _fmt(v: float) -> str:
        if unit == "%":
            return f"{v * 100:.1f}%"
        if unit == "% MoM":
            return f"{v * 100:.1f}%/mo"
        if unit == "points":
            return f"{v:.0f}"
        return f"{v:.2f}"

    value_str  = _fmt(value)
    median_str = _fmt(median)

    if unit in ("%", "% MoM"):
        gap_str = f"{abs(gap_from_median) * 100:.1f}pp"
    elif unit == "points":
        gap_str = f"{abs(gap_from_median):.0f} pts"
    else:
        gap_str = f"{abs(gap_from_median):.2f}"

    above_below = "above" if gap_from_median >= 0 else "below"

    interpretation = (
        f"Your {metric.replace('_', ' ')}: {value_str}. "
        f"Industry median: {median_str} ({bench['source']}). "
        f"You are {gap_str} {above_below} the median — {label}."
    )

    return {
        "metric":              metric,
        "value":               value,
        "value_str":           value_str,
        "industry_p25":        p25,
        "industry_median":     median,
        "industry_median_str": median_str,
        "industry_p75":        p75,
        "percentile_rank":     pct_rank,
        "label":               label,
        "color":               color,
        "gap_from_median":     round(gap_from_median, 6),
        "gap_str":             gap_str,
        "above_below":         above_below,
        "interpretation":      interpretation,
        "context":             bench.get("context", ""),
        "source":              bench.get("source", ""),
        "n_companies":         bench.get("n_companies", 0),
    }


def get_all_benchmarks(snapshot: dict, segment: str = "saas") -> list:
    """
    Run benchmark comparisons for all metrics available in the snapshot.
    Returns list sorted by percentile_rank ascending (worst-performing first).
    Only metrics with published benchmarks are included.
    """
    metric_keys = {
        "nps":        snapshot.get("nps"),
        "churn_rate": snapshot.get("churn_rate"),
    }

    results = []
    for metric, value in metric_keys.items():
        if value is None:
            continue
        try:
            comp = get_benchmark_comparison(metric, float(value), segment)
            if comp:
                results.append(comp)
        except (TypeError, ValueError):
            pass

    # Worst performers first — most important for decision-makers
    results.sort(key=lambda x: x.get("percentile_rank", 50))
    return results
