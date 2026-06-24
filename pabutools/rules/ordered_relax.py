'''
An implementation of the algorithm described in:

"Maxmin Participatory Budgeting", by Gogulapati Sreedurga , Mayank Ratan Bhardwaj and Y. Narahari, 2022, https://arxiv.org/pdf/2204.13923

Programmer: Nevo Biton
Date: 2026-04-29
'''

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
    if isinstance(profile, ApprovalMultiProfile):
        raise NotImplementedError(
            "The Ordered-Relax rule currently does not support multiprofiles."
        )

    if not resoluteness:
        raise NotImplementedError(
            "The Ordered-Relax rule currently does not support irresolute outcomes."
        )

    logger.info("Starting the Ordered-Relax rule")

    if tie_breaking is None:
        tie_breaking = lexico_tie_breaking
        logger.debug("No tie-breaking rule was provided. Using lexicographic tie-breaking.")

    if initial_budget_allocation is None:
        budget_allocation = BudgetAllocation()
        logger.debug("No initial budget allocation was provided.")
    else:
        budget_allocation = BudgetAllocation(initial_budget_allocation)
        logger.debug(
            "Initial budget allocation: %s",
            [project.name for project in budget_allocation],
        )

    initial_cost = total_cost(budget_allocation)
    remaining_budget = instance.budget_limit - initial_cost

    logger.debug("Number of projects in the instance: %d", len(list(instance)))
    logger.debug("Number of voters in the profile: %d", profile.num_ballots())
    logger.debug("Budget limit: %s", instance.budget_limit)
    logger.debug("Initial allocation cost: %s", initial_cost)
    logger.debug("Remaining budget before Ordered-Relax: %s", remaining_budget)

    if remaining_budget < 0:
        logger.error(
            "Initial budget allocation exceeds the budget limit: cost=%s, budget=%s",
            initial_cost,
            instance.budget_limit,
        )
        raise ValueError("The initial budget allocation exceeds the budget limit.")

    available_projects = [
        project
        for project in instance
        if project not in budget_allocation
        and 0 <= project.cost <= instance.budget_limit
    ]

    logger.debug(
        "Available projects before solving the LP: %s",
        [(project.name, project.cost) for project in available_projects],
    )

    if len(available_projects) == 0:
        logger.info("No available projects. Returning the initial budget allocation.")
        return BudgetAllocation(budget_allocation)

    if profile.num_ballots() == 0:
        logger.info("The profile is empty. Returning the initial budget allocation.")
        return BudgetAllocation(budget_allocation)

    logger.info("Solving the MPB LP relaxation.")

    lp_values = _solve_mpb_lp_relaxation(
        available_projects,
        profile,
        remaining_budget,
        initial_budget_allocation=budget_allocation,
    )

    logger.debug(
        "LP relaxation values: %s",
        {project.name: lp_values[project] for project in available_projects},
    )

    logger.debug(
        "Ordered-Relax scores: %s",
        {
            project.name: _relaxed_score(project, lp_values)
            for project in available_projects
        },
    )

    logger.info("Ordering projects by their relaxed scores.")

    ordered_projects = _order_projects_by_relaxed_score(
        instance,
        profile,
        available_projects,
        lp_values,
        tie_breaking,
    )

    logger.debug(
        "Project order after tie-breaking: %s",
        [
            (project.name, project.cost, _relaxed_score(project, lp_values))
            for project in ordered_projects
        ],
    )

    logger.info("Starting the ordered-fill phase.")

    for project in ordered_projects:
        logger.debug(
            "Considering project %s with cost %s. Remaining budget: %s",
            project.name,
            project.cost,
            remaining_budget,
        )

        if project.cost <= remaining_budget:
            budget_allocation.append(project)
            remaining_budget -= project.cost

            logger.debug(
                "Selected project %s. Current allocation: %s. Remaining budget: %s",
                project.name,
                [p.name for p in budget_allocation],
                remaining_budget,
            )
        else:
            logger.info(
                "Stopping ordered-fill: project %s with cost %s does not fit "
                "the remaining budget %s.",
                project.name,
                project.cost,
                remaining_budget,
            )
            break

    logger.info(
        "Ordered-Relax finished. Selected projects: %s. Total cost: %s",
        [project.name for project in budget_allocation],
        total_cost(budget_allocation),
    )

    return BudgetAllocation(budget_allocation)


def _solve_mpb_lp_relaxation(
    projects: Collection[Project],
    profile: AbstractApprovalProfile,
    budget: float,
    initial_budget_allocation: Collection[Project] | None = None,
) -> dict[Project, float]:
    """
    Solve the LP relaxation of the MPB integer linear program.

    Parameters
    ----------
    projects : Collection[:py:class:`~pabutools.election.instance.Project`]
        The projects considered by the LP.
    profile : :py:class:`~pabutools.election.profile.approvalprofile.AbstractApprovalProfile`
        The approval profile.
    budget : float
        The available budget.
    initial_budget_allocation : Collection[:py:class:`~pabutools.election.instance.Project`], optional
        Projects that have already been selected before running the LP.

    Returns
    -------
    dict[:py:class:`~pabutools.election.instance.Project`, float]
        A mapping from each project to its value in the optimal relaxed solution.

    Examples
    --------
        >>> from pabutools.election import Project, ApprovalBallot, ApprovalProfile
        >>> p1 = Project("p1", 4)
        >>> p2 = Project("p2", 3)
        >>> profile = ApprovalProfile([
        ...     ApprovalBallot({p1}),
        ...     ApprovalBallot({p2}),
        ... ])
        >>> values = _solve_mpb_lp_relaxation([p1, p2], profile, 4)
        >>> round(values[p1], 6)
        0.5
        >>> round(values[p2], 6)
        0.666667

    """
    projects = list(projects)

    if initial_budget_allocation is None:
        initial_budget_allocation = BudgetAllocation()
    else:
        initial_budget_allocation = BudgetAllocation(initial_budget_allocation)

    logger.debug(
        "Building LP relaxation with %d projects, %d voters, and budget %s.",
        len(projects),
        profile.num_ballots(),
        budget,
    )

    problem = LpProblem("OrderedRelaxLP", LpMaximize)

    x = {
        project: LpVariable(f"x_{idx}", lowBound=0, upBound=1)
        for idx, project in enumerate(projects)
    }

    q = LpVariable("q", lowBound=0)

    for voter_index, ballot in enumerate(profile):
        initial_utility = total_cost(
            project for project in initial_budget_allocation if project in ballot
        )

        problem += q <= initial_utility + lpSum(
            project.cost * x[project]
            for project in projects
            if project in ballot
        )

        logger.debug(
            "Added utility constraint for voter %d with initial utility %s.",
            voter_index,
            initial_utility,
        )

    problem += lpSum(project.cost * x[project] for project in projects) <= budget
    problem += q

    logger.debug("Solving Ordered-Relax LP relaxation using HiGHS.")

    status = problem.solve(HiGHS(msg=False))

    if status != LpStatusOptimal:
        logger.error("The LP relaxation could not be solved optimally.")
        raise RuntimeError("Could not solve the LP relaxation of Ordered-Relax.")

    lp_values = {
        project: float(value(x[project]) or 0.0)
        for project in projects
    }

    logger.debug(
        "LP relaxation solved successfully. q=%s, x=%s",
        value(q),
        {project.name: lp_values[project] for project in projects},
    )

    return lp_values


def _relaxed_score(project: Project, lp_values: dict[Project, float]) -> float:
    """
    Return the Ordered-Relax score of a project.

    The score of a project p is defined as ``p.cost * x[p]``, where ``x[p]``
    is the value of p in the optimal LP-relaxation solution.

    Parameters
    ----------
    project : :py:class:`~pabutools.election.instance.Project`
        The project.
    lp_values : dict[:py:class:`~pabutools.election.instance.Project`, float]
        The LP-relaxation values.

    Returns
    -------
    float
        The relaxed score of the project.

    Examples
    --------
        >>> from pabutools.election import Project
        >>> p = Project("p1", 5)
        >>> _relaxed_score(p, {p: 0.6})
        3.0

    """
    return project.cost * lp_values[project]


def _order_projects_by_relaxed_score(
    instance: Instance,
    profile: AbstractApprovalProfile,
    projects: Collection[Project],
    lp_values: dict[Project, float],
    tie_breaking: TieBreakingRule,
    eps: float = 1e-7,
) -> list[Project]:
    """
    Order projects by decreasing ``p.cost * x[p]``.

    Ties are resolved using the given tie-breaking rule.

    Parameters
    ----------
    instance : :py:class:`~pabutools.election.instance.Instance`
        The instance.
    profile : :py:class:`~pabutools.election.profile.approvalprofile.AbstractApprovalProfile`
        The approval profile.
    projects : Collection[:py:class:`~pabutools.election.instance.Project`]
        The projects to order.
    lp_values : dict[:py:class:`~pabutools.election.instance.Project`, float]
        The values of the projects in the relaxed LP solution.
    tie_breaking : :py:class:`~pabutools.tiebreaking.TieBreakingRule`
        The tie-breaking rule used.
    eps : float, optional
        Tolerance used for detecting equal scores.

    Returns
    -------
    list[:py:class:`~pabutools.election.instance.Project`]
        The ordered list of projects.

    Examples
    --------
        >>> from pabutools.election import Instance, Project, ApprovalBallot, ApprovalProfile
        >>> from pabutools.tiebreaking import lexico_tie_breaking
        >>> p1 = Project("p1", 4)
        >>> p2 = Project("p2", 3)
        >>> p3 = Project("p3", 2)
        >>> instance = Instance([p1, p2, p3], budget_limit=5)
        >>> profile = ApprovalProfile([
        ...     ApprovalBallot({p1, p2}),
        ...     ApprovalBallot({p2}),
        ...     ApprovalBallot({p3}),
        ... ])
        >>> lp_values = {
        ...     p1: 0.0,
        ...     p2: 1.0,
        ...     p3: 1.0,
        ... }
        >>> ordered = _order_projects_by_relaxed_score(
        ...     instance,
        ...     profile,
        ...     [p1, p2, p3],
        ...     lp_values,
        ...     lexico_tie_breaking,
        ... )
        >>> [p.name for p in ordered]
        ['p2', 'p3', 'p1']

    """
    scored_projects = sorted(
        [(_relaxed_score(project, lp_values), project) for project in projects],
        key=lambda item: item[0],
        reverse=True,
    )

    logger.debug(
        "Projects sorted into score groups before tie-breaking: %s",
        [(project.name, score) for score, project in scored_projects],
    )

    ordered_projects = []
    index = 0

    while index < len(scored_projects):
        score = scored_projects[index][0]
        tied_projects = []

        while index < len(scored_projects) and isclose(
            scored_projects[index][0],
            score,
            abs_tol=eps,
        ):
            tied_projects.append(scored_projects[index][1])
            index += 1

        logger.debug(
            "Tie group with score %s: %s",
            score,
            [project.name for project in tied_projects],
        )

        while tied_projects:
            chosen = tie_breaking.untie(instance, profile, tied_projects)
            ordered_projects.append(chosen)
            tied_projects.remove(chosen)

            logger.debug(
                "Tie-breaking selected project %s. Remaining tied projects: %s",
                chosen.name,
                [project.name for project in tied_projects],
            )

    return ordered_projects
