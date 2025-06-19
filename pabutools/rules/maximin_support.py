"""
The maximin support rule.
"""

from __future__ import annotations

import logging

from collections.abc import Collection

from pulp import LpProblem, LpMinimize, LpVariable, lpSum, LpStatusOptimal, value, PULP_CBC_CMD

from pabutools.election import (
    Instance,
    Project,
    total_cost,
    AbstractApprovalProfile,
    ApprovalMultiProfile,
)
from pabutools.rules.budgetallocation import BudgetAllocation
from pabutools.tiebreaking import TieBreakingRule, lexico_tie_breaking

logger = logging.getLogger(__name__)

def maximin_support(
    instance: Instance,
    profile: AbstractApprovalProfile,
    initial_budget_allocation: Collection[Project] | None = None,
    tie_breaking: TieBreakingRule | None = None,
    resoluteness: bool = True,
) -> BudgetAllocation:
    """
    The maximin support rule (also introduced as "Generalised Sequential Phragmén" by Aziz, Lee and Talmon (2018)).

    Contributed by Shlomi Asraf.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.approvalprofile.AbstractApprovalProfile`
            The profile.
        initial_budget_allocation : Iterable[:py:class:`~pabutools.election.instance.Project`]
            An initial budget allocation, typically empty.
        tie_breaking : :py:class:`~pabutools.tiebreaking.TieBreakingRule`, optional
            The tie-breaking rule used.
            Defaults to the lexicographic tie-breaking.
        resoluteness : bool, optional
            Set to `False` to obtain an irresolute outcome, where all tied budget allocations are returned.
            Defaults to True.

    Returns
    -------
        :py:class:`~pabutools.rules.budgetallocation.BudgetAllocation`
            The selected projects.

    """
    if isinstance(profile, ApprovalMultiProfile):
        raise NotImplementedError("The maximin support rule currently does not support multiprofiles.")

    if not resoluteness:
        raise NotImplementedError("The maximin support rule currently does not support irresolute outcomes.")

    logging.info("Starting the maximin support rule")

    if tie_breaking is None:
        tie_breaking = lexico_tie_breaking
    if initial_budget_allocation is None:
        budget_allocation = BudgetAllocation()
    else:
        budget_allocation = BudgetAllocation(initial_budget_allocation)

    remaining_budget = instance.budget_limit - total_cost(budget_allocation)

    available_projects = set(
        p
        for p in instance
        if p not in budget_allocation and 0 <= p.cost <= instance.budget_limit
    )

    approvers_map = {}
    for p in available_projects:
        approvers = [i for i, ballot in enumerate(profile) if p in ballot]
        if approvers:
            approvers_map[p] = approvers

    while True:
        available_projects = [p for p in available_projects if p.cost <= remaining_budget]

        if len(available_projects) == 0:
            break

        min_new_maxload = None
        arg_min_new_maxload = None
        for p in available_projects:
            new_maxload = _compute_optimal_load(budget_allocation + [p], profile)
            if min_new_maxload is None or new_maxload < min_new_maxload:
                min_new_maxload = new_maxload
                arg_min_new_maxload = [p]
            elif min_new_maxload == new_maxload:
                arg_min_new_maxload.append(p)

        chosen = tie_breaking.untie(instance, profile, arg_min_new_maxload)

        budget_allocation.append(chosen)
        remaining_budget -= chosen.cost
        available_projects.remove(chosen)

    return BudgetAllocation(budget_allocation)


def _compute_optimal_load(projects, profile):
    """
    Solves the LP relaxation to minimize the max load.

    Parameters
    ----------
    projects : list of Project
        The projects considered so far (W ∪ {c'}).
    profile : AbstractApprovalProfile
        The approval profile of the voters.

    Returns
    -------
    float
        The minimum max load (z) over voters given optimal distribution of costs.
    """
    num_voters = profile.num_ballots()
    voter_ids = range(num_voters)

    prob = LpProblem("MinMaxLoad", LpMinimize)

    # Decision variables: load each voter i takes for project p
    x = {
        (p, i): LpVariable(f"x_{p.name}_{i}", lowBound=0)
        for p in projects for i in voter_ids
    }

    z = LpVariable("max_load", lowBound=0)

    # Constraints
    for p in projects:
        for i in voter_ids:
            if p not in profile[i]:
                prob += x[p, i] == 0

    for p in projects:
        prob += lpSum(x[p, i] for i in voter_ids) == p.cost

    for i in voter_ids:
        prob += lpSum(x[p, i] for p in projects) <= z

    prob += z  # Objective: minimize max load

    status = prob.solve(PULP_CBC_CMD(msg=False))

    # This can mean a project that no one approves of for instance
    if status != LpStatusOptimal:
        return float("inf")

    return value(z)
