
from __future__ import annotations
from collections import defaultdict
from pabutools.election.instance import Instance
from pabutools.election.profile import AbstractProfile, OrdinalProfile
from pabutools.election.profile.ordinalprofile import AbstractOrdinalProfile
from pabutools.rules.budgetallocation import BudgetAllocation
import logging
from pabutools.utils_formatting import format_table
from pabutools.fractions import frac
from pabutools.election.instance import Project


"""
An implementation of the PB-EAR algorithm from:

"Proportionally Representative Participatory Budgeting with Ordinal Preferences",
Haris Aziz and Barton E. Lee (2020),
https://arxiv.org/abs/1911.00864v2

Programmer: Vivian Umansky
Date: 2025-04-23
"""

logger = logging.getLogger(__name__)

def pb_ear(
    instance: Instance,
    profile: AbstractProfile,
    verbose: bool = False,
    rounding_precision: int = 6
) -> BudgetAllocation:
    """
    PB-EAR Algorithm — Proportional Representation via Inclusion-PSC (IPSC) under Ordinal Preferences.

    This algorithm selects a subset of projects within a given budget while ensuring proportional representation
    for solid coalitions based on voters' ordinal preferences. It supports both `OrdinalProfile` and `OrdinalMultiProfile`.

    Parameters
    ----------
    instance : Instance
        The budgeting instance, including all candidate projects and a total budget limit.

    profile : AbstractOrdinalProfile
        A profile of voters' preferences. Each voter submits a strict ranking over a subset of projects,
        and is assigned a positive weight. Can be an `OrdinalProfile` or `OrdinalMultiProfile`.

    verbose : bool, optional
        If True, enables detailed debug logging (default is False).

    rounding_precision : int, optional
        The number of decimal places to round values for threshold comparisons and logging (default is 6).

    Returns
    -------
    BudgetAllocation
        An allocation containing the selected projects that respect the budget and satisfy the IPSC criterion.

    Raises
    ------
    ValueError
        If the profile is not an instance of `AbstractOrdinalProfile`.
    """

    if not isinstance(profile, AbstractOrdinalProfile):
        raise ValueError("PB-EAR only supports ordinal profiles.")

    if len(profile) == 0:
        return BudgetAllocation()

    budget = instance.budget_limit
    project_cost = {p.name: p.cost for p in instance}
    project_by_name = {p.name: p for p in instance}
    all_projects = set(project_cost)

    if verbose:
        logger.info("=" * 30 + " NEW RUN: PB-EAR " + "=" * 30)

    voters = [(ballot, profile.multiplicity(ballot)) for ballot in profile]
    voter_weights = {ballot: weight for ballot, weight in voters}
    initial_n = sum(voter_weights.values())

    j = 1
    selected_projects: set[Project] = set()
    remaining_budget = budget

    while True:
        available_projects = [
            p for p in all_projects - {proj.name for proj in selected_projects}
            if project_cost[p] <= remaining_budget
        ]

        if verbose:
            logger.debug("Step j=%d — available_projects=%s, remaining_budget=%.2f", j, available_projects, remaining_budget)

        if not available_projects:
            break

        approvals = defaultdict(set)
        for ballot, _ in voters:
            prefs = list(ballot)
            if j <= len(prefs):
                threshold = prefs[j - 1]
                rank_threshold = prefs.index(threshold)
                approvals[ballot] = set(prefs[:rank_threshold + 1])
            else:
                approvals[ballot] = set(prefs)

        candidate_support = defaultdict(float)
        for ballot, approved in approvals.items():
            for p in approved:
                if p not in {proj.name for proj in selected_projects}:
                    candidate_support[p] += voter_weights[ballot]

        table = [
            (
                p,
                f"{round(candidate_support[p], rounding_precision)}",
                f"{round(project_cost[p], rounding_precision)}",
                f"{round(frac((int(initial_n * project_cost[p])),(int(budget))), rounding_precision)}"
            )
            for p in available_projects
        ]
        headers = ["Project", "Support", "Cost", "Threshold"]
        if verbose:
            logger.debug("\n%s", format_table(headers, table))

        C_star = {
            c for c in available_projects
            if round(candidate_support[c], rounding_precision) >= round(
                frac((int(initial_n * project_cost[c])),(int(budget))), rounding_precision
            )
        }


        if not C_star:
            max_rank = max(len(list(ballot)) for ballot, _ in voters)
            if j > max_rank:
                break
            j += 1
            continue

        c_star = next(iter(C_star))
        selected_projects.add(project_by_name[c_star])
        remaining_budget -= project_cost[c_star]

        if verbose:
            logger.info("Selected candidate: %s | cost=%.2f | remaining_budget=%.2f", c_star, project_cost[c_star], remaining_budget)

        N_prime = [ballot for ballot in approvals if c_star in approvals[ballot]]
        total_weight_to_reduce = frac(
    (int(initial_n * project_cost[c_star])),
    (int(budget))
)


        if N_prime:
            sum_supporters = sum(voter_weights[b] for b in N_prime)
            weight_fraction = (
    frac((int(total_weight_to_reduce)), (int(sum_supporters)))
    if sum_supporters > 0 else 0
)

            for ballot in N_prime:
                old_weight = voter_weights[ballot]
                voter_weights[ballot] = voter_weights[ballot] * (1 - weight_fraction)
                logger.debug("Reducing weight — old_weight=%.4f new_weight=%.4f", old_weight, voter_weights[ballot])

    allocation = BudgetAllocation()
    for project in sorted(selected_projects, key=lambda p: p.name):
        allocation.append(project)

    logger.info(
        "Final selected projects: %s (total=%d)",
        [p.name for p in sorted(selected_projects, key=lambda p: p.name)],
        len(selected_projects)
    )
    return allocation