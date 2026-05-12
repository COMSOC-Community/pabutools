"""
The Ordered-Relax rule.
"""

from __future__ import annotations

import logging
from collections.abc import Collection
from math import isclose

from pulp import (
    HiGHS,
    LpMaximize,
    LpProblem,
    LpStatusOptimal,
    LpVariable,
    lpSum,
    value,
)

from pabutools.election import (
    AbstractApprovalProfile,
    ApprovalMultiProfile,
    Instance,
    Project,
    total_cost,
)
from pabutools.rules.budgetallocation import BudgetAllocation
from pabutools.tiebreaking import TieBreakingRule, lexico_tie_breaking

logger = logging.getLogger(__name__)


def ordered_relax(
    instance: Instance,
    profile: AbstractApprovalProfile,
    initial_budget_allocation: Collection[Project] | None = None,
    tie_breaking: TieBreakingRule | None = None,
    resoluteness: bool = True,
) -> BudgetAllocation:
    """
    The Ordered-Relax rule for Maxmin Participatory Budgeting.

    Ordered-Relax is an LP-rounding algorithm for the Maxmin Participatory
    Budgeting (MPB) objective. It first solves the LP relaxation of the MPB
    integer linear program. Each project p is then assigned the score
    ``p.cost * x[p]``, where ``x[p]`` is the value of p in the optimal relaxed
    solution. Projects are considered in decreasing order of this score and are
    added to the budget allocation until the next project in the order does not
    fit within the remaining budget.

    Contributed by Nevo Biton.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.approvalprofile.AbstractApprovalProfile`
            The approval profile.
        initial_budget_allocation : Iterable[:py:class:`~pabutools.election.instance.Project`]
            An initial budget allocation, typically empty.
        tie_breaking : :py:class:`~pabutools.tiebreaking.TieBreakingRule`, optional
            The tie-breaking rule used to order projects with the same Ordered-Relax score.
            Defaults to the lexicographic tie-breaking.
        resoluteness : bool, optional
            Set to `False` to obtain an irresolute outcome, where all tied budget allocations are returned.
            Defaults to True.

    Returns
    -------
        :py:class:`~pabutools.rules.budgetallocation.BudgetAllocation`
            The selected projects.

    Examples
    --------
        >>> from pabutools.election import Instance, Project, ApprovalBallot, ApprovalProfile
        >>> def make_election(costs, budget, approvals):
        ...     projects = {name: Project(name, cost) for name, cost in costs.items()}
        ...     instance = Instance(projects.values(), budget_limit=budget)
        ...     profile = ApprovalProfile([
        ...         ApprovalBallot({projects[name] for name in ballot})
        ...         for ballot in approvals
        ...     ])
        ...     return instance, profile
        >>> def selected_names(allocation):
        ...     return {project.name for project in allocation}

        Example 1.

        >>> instance, profile = make_election(
        ...     {"p1": 5},
        ...     5,
        ...     [
        ...         {"p1"},
        ...     ],
        ... )
        >>> selected_names(ordered_relax(instance, profile)) == {"p1"}
        True

        Example 2.

        >>> instance, profile = make_election(
        ...     {"p1": 4, "p2": 3},
        ...     4,
        ...     [
        ...         {"p1"},
        ...         {"p2"},
        ...     ],
        ... )
        >>> selected_names(ordered_relax(instance, profile)) == {"p1"}
        True

        Example 3.

        >>> instance, profile = make_election(
        ...     {"p1": 3, "p2": 3, "p3": 2},
        ...     5,
        ...     [
        ...         {"p1", "p2"},
        ...         {"p2"},
        ...         {"p3"},
        ...     ],
        ... )
        >>> selected_names(ordered_relax(instance, profile)) == {"p2", "p3"}
        True

        Example 4.

        >>> instance, profile = make_election(
        ...     {
        ...         "p0": 2,
        ...         "p1": 3,
        ...         "p2": 3,
        ...         "p3": 3,
        ...         "p4": 3,
        ...     },
        ...     8,
        ...     [
        ...         {"p0", "p1"},
        ...         {"p0", "p2"},
        ...         {"p0", "p3"},
        ...         {"p0", "p4"},
        ...     ],
        ... )
        >>> selected_names(ordered_relax(instance, profile)) == {"p0", "p1", "p2"}
        True

        Example 5.

        >>> instance, profile = make_election(
        ...     {
        ...         "p0": 23,
        ...         "p1": 68,
        ...         "p2": 198,
        ...         "p3": 189,
        ...         "p4": 146,
        ...         "p5": 38,
        ...     },
        ...     341,
        ...     [
        ...         {"p4"},
        ...         {"p1", "p2"},
        ...         {"p1", "p3", "p5"},
        ...     ],
        ... )
        >>> selected_names(ordered_relax(instance, profile)) == {"p4"}
        True

        Example 6.

        >>> instance, profile = make_election(
        ...     {
        ...         "p0": 18,
        ...         "p1": 45,
        ...         "p2": 43,
        ...         "p3": 32,
        ...         "p4": 28,
        ...         "p5": 32,
        ...         "p6": 5,
        ...         "p7": 37,
        ...         "p8": 43,
        ...         "p9": 17,
        ...     },
        ...     124,
        ...     [
        ...         {"p0", "p3", "p7"},
        ...         {"p1", "p4", "p6", "p7"},
        ...         {"p0", "p2", "p4", "p5"},
        ...         {"p1", "p6", "p9"},
        ...         {"p1", "p2", "p6", "p7", "p8"},
        ...         {"p1", "p3", "p4", "p6", "p8"},
        ...     ],
        ... )
        >>> selected_names(ordered_relax(instance, profile)) == {"p1", "p2"}
        True

    Notes
    -----
        Ordered-Relax is not guaranteed to return an optimal MPB outcome on
        every instance. It is an approximation algorithm based on LP rounding.

        The utility of a voter from a budget allocation is the total cost of the
        selected projects approved by that voter.
    """
    pass
