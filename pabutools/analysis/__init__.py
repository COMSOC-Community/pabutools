"""
Module containing all kinds of tools to analyse participatory budgeting elections and their outcomes.
"""

from pabutools.analysis.category import category_proportionality
from pabutools.analysis.instanceproperties import (
    sum_project_cost,
    funding_scarcity,
    avg_project_cost,
    median_project_cost,
    std_dev_project_cost,
)
from pabutools.analysis.profileproperties import (
    avg_ballot_length,
    median_ballot_length,
    avg_ballot_cost,
    median_ballot_cost,
    avg_approval_score,
    median_approval_score,
    avg_total_score,
    median_total_score,
)
from pabutools.analysis.priceability import (
     validate_price_system,
     priceable,
     PriceableResult,
)
from pabutools.analysis.mesanalytics import (
    ProjectLoss,
    calculate_project_loss,
    calculate_effective_supports,
    calculate_effective_support,
)
from pabutools.analysis.votersatisfaction import (
    avg_satisfaction,
    gini_coefficient_of_satisfaction,
    percent_non_empty_handed,
    satisfaction_histogram,
)

__all__ = [
    "ProjectLoss",
    "calculate_project_loss",
    "calculate_effective_supports",
    "calculate_effective_support",
    "category_proportionality",
    "sum_project_cost",
    "funding_scarcity",
    "avg_project_cost",
    "median_project_cost",
    "std_dev_project_cost",
    "avg_ballot_length",
    "median_ballot_length",
    "avg_ballot_cost",
    "median_ballot_cost",
    "avg_approval_score",
    "median_approval_score",
    "avg_total_score",
    "median_total_score",
    "validate_price_system",
    "priceable",
    "PriceableResult",
    "avg_satisfaction",
    "gini_coefficient_of_satisfaction",
    "percent_non_empty_handed",
    "satisfaction_histogram",
]
