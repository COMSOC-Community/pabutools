
from __future__ import annotations
from collections import defaultdict
from collections.abc import Collection

from pabutools.election import total_cost
from pabutools.election.instance import Instance
from pabutools.election.profile.ordinalprofile import AbstractOrdinalProfile
from pabutools.rules.budgetallocation import BudgetAllocation
from pabutools.utils import format_table
from pabutools.fractions import frac
from pabutools.election.instance import Project

import logging
logger = logging.getLogger(__name__)

def pb_ear(
    instance: Instance,
    profile: AbstractOrdinalProfile,
    initial_budget_allocation: Collection[Project] | None = None,
    resoluteness: bool = True,
    verbose: bool = False,
    rounding_precision: int = 6
) -> BudgetAllocation:
    """
    PB-EAR Algorithm — Proportional Representation via Inclusion-PSC (IPSC) under Ordinal Preferences.

    This algorithm selects a subset of projects within a given budget while ensuring proportional representation
    for solid coalitions based on voters' ordinal preferences. It supports both `OrdinalProfile` and `OrdinalMultiProfile`.

    Contributed by Vivian Umansky.

    Parameters
    ----------
        instance : Instance
            The budgeting instance, including all candidate projects and a total budget limit.
        profile : AbstractOrdinalProfile
            A profile of voters' preferences. Each voter submits a strict ranking over a subset of projects,
            and is assigned a positive weight. Can be an `OrdinalProfile` or `OrdinalMultiProfile`.
        resoluteness : bool, optional
            Set to `False` to obtain an irresolute outcome, where all tied budget allocations are returned.
            Defaults to True.
        verbose : bool, optional
            If True, enables detailed debug logging (default is False).
        rounding_precision : int, optional
            The number of decimal places to round values for threshold comparisons and logging (default is 6).

    Returns
    -------
        BudgetAllocation
            An allocation containing the selected projects that respect the budget and satisfy the IPSC criterion.
    """

    if not isinstance(profile, AbstractOrdinalProfile):
        raise ValueError("PB-EAR only supports ordinal profiles.")

    if not resoluteness:
        raise NotImplementedError("PB-EAR only supports resoluteness = True.")

    if profile.num_ballots() == 0:
        return BudgetAllocation()

    if verbose:
        logger.info("=" * 30 + " NEW RUN: PB-EAR " + "=" * 30)

    voter_weights = defaultdict(int)
    for ballot in profile:
        voter_weights[ballot] += profile.multiplicity(ballot)
    initial_n = sum(voter_weights.values())

    j = 1
    if initial_budget_allocation is None:
        budget_allocation = BudgetAllocation()
    else:
        budget_allocation = BudgetAllocation(initial_budget_allocation)

    remaining_budget = instance.budget_limit - total_cost(budget_allocation)

    available_projects = [
        p for p in instance
        if p not in budget_allocation and p.cost <= remaining_budget
    ]

    while True:
        available_projects = [
            p for p in available_projects
            if p.cost <= remaining_budget
        ]

        if verbose:
            logger.debug("Step j=%d — available_projects=%s, remaining_budget=%.2f", j, available_projects, remaining_budget)

        if not available_projects:
            break

        approvals = defaultdict(set)
        for ballot in profile:
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
                if p not in budget_allocation:
                    candidate_support[p] += voter_weights[ballot]

        if verbose:
            headers = ["Project", "Support", "Cost", "Threshold"]
            table = [
                (
                    p,
                    f"{round(candidate_support[p], rounding_precision)}",
                    f"{round(p.cost, rounding_precision)}",
                    f"{round(frac((int(initial_n * p.cost)), (int(instance.budget_limit))), rounding_precision)}"
                )
                for p in available_projects
            ]
            logger.debug("\n%s", format_table(headers, table))

        C_star = {
            c for c in available_projects
            if round(candidate_support[c], rounding_precision) >= round(
                frac(int(initial_n * c.cost), int(instance.budget_limit)), rounding_precision
            )
        }

        if not C_star:
            max_rank = max(len(list(ballot)) for ballot in profile)
            if j > max_rank:
                break
            j += 1
            continue

        c_star = next(iter(C_star))
        budget_allocation.append(c_star)
        available_projects.remove(c_star)
        remaining_budget -= c_star.cost

        if verbose:
            logger.info("Selected candidate: %s | cost=%.2f | remaining_budget=%.2f", c_star, c_star.cost, remaining_budget)

        N_prime = [ballot for ballot in approvals if c_star in approvals[ballot]]
        total_weight_to_reduce = frac(int(initial_n * c_star.cost), int(instance.budget_limit))

        if N_prime:
            sum_supporters = sum(voter_weights[b] for b in N_prime)
            if sum_supporters > 0:
                weight_fraction = frac(int(total_weight_to_reduce), int(sum_supporters))
            else:
                weight_fraction = 0

            for ballot in N_prime:
                old_weight = voter_weights[ballot]
                voter_weights[ballot] = voter_weights[ballot] * (1 - weight_fraction)

                if verbose:
                    logger.debug("Reducing weight — old_weight=%.4f new_weight=%.4f", old_weight, voter_weights[ballot])

    if verbose:
        logger.info(
            "Final selected projects: %s (total=%d)",
            [p.name for p in sorted(budget_allocation, key=lambda p: p.name)],
            len(budget_allocation)
        )
    return budget_allocation
