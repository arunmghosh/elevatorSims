"""Statistical aggregation and confidence interval analysis for elevator simulation trials."""

import math
from dataclasses import dataclass
from typing import List, Tuple
import numpy as np
from scipy import stats


@dataclass
class ConfidenceInterval:
    """Represents a calculated confidence interval."""
    metric_name: str
    confidence_level: float
    sample_size: int
    mean: float
    std_dev: float
    std_error: float
    margin_of_error: float
    lower_bound: float
    upper_bound: float

    def __str__(self) -> str:
        return (
            f"{self.metric_name} ({self.confidence_level*100:.0f}% CI): "
            f"Mean = {self.mean:.4f} ± {self.margin_of_error:.4f} "
            f"[{self.lower_bound:.4f}, {self.upper_bound:.4f}]"
        )


def compute_confidence_interval(
    data: List[float],
    metric_name: str = "Metric",
    confidence: float = 0.90,
) -> ConfidenceInterval:
    """Computes confidence interval using Student's t-distribution.
    
    For N=365 trials, uses df = N - 1.
    """
    arr = np.array(data, dtype=np.float64)
    n = len(arr)
    if n < 2:
        val = float(arr[0]) if n == 1 else 0.0
        return ConfidenceInterval(
            metric_name=metric_name,
            confidence_level=confidence,
            sample_size=n,
            mean=val,
            std_dev=0.0,
            std_error=0.0,
            margin_of_error=0.0,
            lower_bound=val,
            upper_bound=val,
        )

    mean = float(np.mean(arr))
    std_dev = float(np.std(arr, ddof=1))
    std_error = std_dev / math.sqrt(n)

    # Student's t critical value for two-tailed (1 - confidence) / 2
    alpha = 1.0 - confidence
    t_crit = float(stats.t.ppf(1.0 - alpha / 2.0, df=n - 1))
    margin = t_crit * std_error

    return ConfidenceInterval(
        metric_name=metric_name,
        confidence_level=confidence,
        sample_size=n,
        mean=mean,
        std_dev=std_dev,
        std_error=std_error,
        margin_of_error=margin,
        lower_bound=mean - margin,
        upper_bound=mean + margin,
    )


def evaluate_confidence_interval_overlap(
    ci_traditional: ConfidenceInterval,
    ci_modern: ConfidenceInterval,
) -> Tuple[bool, float, str]:
    """Evaluates whether two confidence intervals have significant overlap.
    
    Returns:
        (has_overlap, overlap_amount, conclusion_text)
    """
    overlap_lower = max(ci_traditional.lower_bound, ci_modern.lower_bound)
    overlap_upper = min(ci_traditional.upper_bound, ci_modern.upper_bound)

    has_overlap = overlap_upper >= overlap_lower
    overlap_amount = max(0.0, overlap_upper - overlap_lower)

    if has_overlap:
        conclusion = (
            f"The 90% confidence intervals OVERLAP by {overlap_amount:.4f}. "
            "Conclusion: There is either no or only marginal benefit to implementing the newer system."
        )
    else:
        separation = overlap_lower - overlap_upper
        conclusion = (
            f"The 90% confidence intervals DO NOT OVERLAP (separation of {separation:.4f}). "
            "Conclusion: The modern advance destination notice system provides a statistically significant benefit."
        )

    return has_overlap, overlap_amount, conclusion
