"""
Phragmén's methods.
"""

from __future__ import annotations

import logging

from collections.abc import Collection
from copy import deepcopy

import numpy as np

from pabutools.rules.budgetallocation import BudgetAllocation
from pabutools.utils import Numeric

from pabutools.fractions import frac
from pabutools.election import (
    Instance,
    Project,
    total_cost,
    AbstractApprovalBallot,
    AbstractApprovalProfile, ApprovalMultiProfile,
)
from pabutools.tiebreaking import TieBreakingRule, lexico_tie_breaking


logger = logging.getLogger(__name__)

class PhragmenVoter:
    """
    Class used to summarise a voter during a run of the Phragmén's sequential rule.

    Parameters
    ----------
        ballot: :py:class:`~pabutools.election.ballot.approvalballot.AbstractApprovalBallot`
            The ballot of the voter.
        load: Numeric
            The initial load of the voter.
        multiplicity: int
            The multiplicity of the ballot.

    Attributes
    ----------
        ballot: :py:class:`~pabutools.election.ballot.approvalballot.AbstractApprovalBallot`
            The ballot of the voter.
        load: Numeric
            The initial load of the voter.
        multiplicity: int
            The multiplicity of the ballot.
    """

    def __init__(
        self, ballot: AbstractApprovalBallot, load: Numeric, multiplicity: int
    ):
        self.ballot = ballot
        self.load = load
        self.multiplicity = multiplicity

    def total_load(self):
        return self.multiplicity * self.load


def sequential_phragmen(
    instance: Instance,
    profile: AbstractApprovalProfile,
    initial_loads: list[Numeric] | None = None,
    initial_budget_allocation: Collection[Project] | None = None,
    tie_breaking: TieBreakingRule | None = None,
    resoluteness: bool = True,
) -> BudgetAllocation | list[BudgetAllocation]:
    """
    Phragmén's sequential rule. It works as follows. Voters receive money in a virtual currency. They all start with a
    budget of 0 and that budget continuously increases. As soon asa group of supporters have enough virtual currency to
    buy a project they all approve, the project is bought. The rule stops as soon as there is a project that could be
    bought  but only by violating the budget constraint.

    Note that this rule can only be applied to profile of approval ballots.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.approvalprofile.AbstractApprovalProfile`
            The profile.
        initial_loads: list[Numeric], optional
            A list of initial load, one per ballot in `profile`. By defaults, the initial load is `0`.
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
        :py:class:`~pabutools.rules.budgetallocation.BudgetAllocation` | list[:py:class:`~pabutools.rules.budgetallocation.BudgetAllocation`]
            The selected projects if resolute (:code:`resoluteness == True`), or the set of selected projects if irresolute
            (:code:`resoluteness == False`).
    """

    def aux(
        inst,
        projects,
        prof,
        voters,
        supporters,
        approval_scores,
        alloc,
        cost,
        allocs,
        resolute,
    ):
        if len(projects) == 0:
            alloc.sort()
            if alloc not in allocs:
                allocs.append(alloc)
        else:
            min_new_maxload = None
            arg_min_new_maxload = None
            for project in projects:
                if approval_scores[project] == 0:
                    new_maxload = float("inf")
                else:
                    new_maxload = frac(
                        sum(voters[i].total_load() for i in supporters[project])
                        + project.cost,
                        approval_scores[project],
                    )
                if min_new_maxload is None or new_maxload < min_new_maxload:
                    min_new_maxload = new_maxload
                    arg_min_new_maxload = [project]
                elif min_new_maxload == new_maxload:
                    arg_min_new_maxload.append(project)

            if any(
                cost + project.cost > inst.budget_limit
                for project in arg_min_new_maxload
            ):
                alloc.sort()
                if alloc not in allocs:
                    allocs.append(alloc)
            else:
                tied_projects = tie_breaking.order(inst, prof, arg_min_new_maxload)
                if resolute:
                    selected_project = tied_projects[0]
                    for voter in voters:
                        if selected_project in voter.ballot:
                            voter.load = min_new_maxload
                    alloc.append(selected_project)
                    projects.remove(selected_project)
                    aux(
                        inst,
                        projects,
                        prof,
                        voters,
                        supporters,
                        approval_scores,
                        alloc,
                        cost + selected_project.cost,
                        allocs,
                        resolute,
                    )
                else:
                    for selected_project in tied_projects:
                        new_voters = deepcopy(voters)
                        for voter in new_voters:
                            if selected_project in voter.ballot:
                                voter.load = min_new_maxload
                        new_alloc = deepcopy(alloc) + [selected_project]
                        new_cost = cost + selected_project.cost
                        new_projs = deepcopy(projects)
                        new_projs.remove(selected_project)
                        aux(
                            inst,
                            new_projs,
                            prof,
                            new_voters,
                            supporters,
                            approval_scores,
                            new_alloc,
                            new_cost,
                            allocs,
                            resolute,
                        )

    if not isinstance(profile, AbstractApprovalProfile):
        raise ValueError("The Sequential Phragmen Rule only applies to approval profiles.")

    if tie_breaking is None:
        tie_breaking = lexico_tie_breaking
    if initial_budget_allocation is None:
        initial_budget_allocation = BudgetAllocation()
    else:
        initial_budget_allocation = BudgetAllocation(initial_budget_allocation)
    current_cost = total_cost(initial_budget_allocation)

    initial_projects = set(
        p
        for p in instance
        if p not in initial_budget_allocation and p.cost <= instance.budget_limit
    )

    if initial_loads is None:
        voters_details = [PhragmenVoter(b, 0, profile.multiplicity(b)) for b in profile]
    else:
        voters_details = [
            PhragmenVoter(b, initial_loads[i], profile.multiplicity(b))
            for i, b in enumerate(profile)
        ]
    supps = {
        proj: [i for i, v in enumerate(voters_details) if proj in v.ballot]
        for proj in initial_projects
    }

    scores = {project: profile.approval_score(project) for project in instance}

    all_budget_allocations: list[BudgetAllocation] = []
    aux(
        instance,
        initial_projects,
        profile,
        voters_details,
        supps,
        scores,
        initial_budget_allocation,
        current_cost,
        all_budget_allocations,
        resoluteness,
    )

    if resoluteness:
        return all_budget_allocations[0]
    return all_budget_allocations


def greedy_sequential_phragmen(
    instance: Instance,
    profile: AbstractApprovalProfile,
    tie_breaking: TieBreakingRule = lexico_tie_breaking
) -> BudgetAllocation:
    """
    Implementation of the Greedy Sequential Phragmén rule from: "Proportionally Representative Participatory Budgeting:
    Axioms and Algorithms" by Haris Aziz, Bettina Klaus, Jérôme Lang, and Markus Brill (2017)

    Contributed by Shlomi Asraf.

    Parameters
    ----------
    instance : Instance
        The instance including all projects and the total budget.
    profile : ApprovalProfile
        The approval profile of the voters.
    tie_breaking : TieBreakingRule, optional
        The rule to apply when multiple projects have equal impact.

    Returns
    -------
    List[Project]
        A list of selected projects.

    Examples
    --------
    Example 1:
      Algorithm 6: GPseq - Greedy Phragmen Sequence algorithm.

    Selects a subset of projects to minimize the maximal load on any voter.

    Parameters
    ----------
    instance : Instance
        The instance including all projects and the total budget.
    profile : ApprovalProfile
        The approval profile of the voters.
    tie_breaking : TieBreakingRule, optional
        The rule to apply when multiple projects have equal impact.

    Returns
    -------
    List[Project]
        A list of selected projects.

    Examples
    --------
    >>> p1 = Project("c1", cost=2)
    >>> p2 = Project("c2", cost=2)
    >>> p3 = Project("c3", cost=1)
    >>> instance = Instance([p1, p2, p3], budget_limit=3)
    >>> profile = ApprovalProfile([ApprovalBallot([p1]), ApprovalBallot([p1]), ApprovalBallot([p2]), ApprovalBallot([p2])])
    >>> result = greedy_sequential_phragmen(instance, profile)
    >>> [p.name for p in result]
    ['c1', 'c3']

    >>> p1 = Project("c1", cost=1)
    >>> instance = Instance([p1], budget_limit=1)
    >>> profile = ApprovalProfile([ApprovalBallot([p1])])
    >>> result = greedy_sequential_phragmen(instance, profile)
    >>> [p.name for p in result]
    ['c1']

    >>> p1 = Project("c1", cost=1)
    >>> p2 = Project("c2", cost=2)
    >>> instance = Instance([p1, p2], budget_limit=2)
    >>> profile = ApprovalProfile([ApprovalBallot([p1]), ApprovalBallot([p1]), ApprovalBallot([p1]), ApprovalBallot([p2])])
    >>> result = greedy_sequential_phragmen(instance, profile)
    >>> [p.name for p in result]
    ['c1']

    >>> p1 = Project("c1", cost=2)
    >>> p2 = Project("c2", cost=1.5)
    >>> p3 = Project("c3", cost=1.5)
    >>> instance = Instance([p1, p2, p3], budget_limit=3)
    >>> profile = ApprovalProfile([ApprovalBallot([p1, p2]), ApprovalBallot([p1, p2]), ApprovalBallot([p1, p2]), ApprovalBallot([p1, p2]), ApprovalBallot([p3]), ApprovalBallot([p3])])
    >>> result = greedy_sequential_phragmen(instance, profile)
    >>> [p.name for p in result]
    ['c2', 'c3']

    >>> p1 = Project("c1", cost=2)
    >>> p2 = Project("c2", cost=2)
    >>> p3 = Project("c3", cost=0.8)
    >>> instance = Instance([p1, p2, p3], budget_limit=2)
    >>> profile = ApprovalProfile([ApprovalBallot([p1, p2]), ApprovalBallot([p1, p2]), ApprovalBallot([p1, p2]), ApprovalBallot([p1, p2]), ApprovalBallot([p3]), ApprovalBallot([p3])])
    >>> result = greedy_sequential_phragmen(instance, profile)
    >>> [p.name for p in result]
    ['c3']

    >>> p1 = Project("c1", cost=1.5)
    >>> p2 = Project("c2", cost=1.5)
    >>> p3 = Project("c3", cost=1.0)
    >>> instance = Instance([p1, p2, p3], budget_limit=3)
    >>> profile = ApprovalProfile([ApprovalBallot([p1, p2]), ApprovalBallot([p1]), ApprovalBallot([p2, p3]), ApprovalBallot([p3])])
    >>> result = greedy_sequential_phragmen(instance, profile)
    >>> [p.name for p in result]
    ['c3', 'c1']
    """

    # THIS IS UNDER REVIEW AND SHOULD NOT BE CONSIDERED CORRECT

    logger.info("Starting GPseq algorithm")

    if not isinstance(profile, AbstractApprovalProfile):
        raise ValueError("The Greedy Sequential Phragmen Rule only applies to approval profiles.")
    if isinstance(profile, ApprovalMultiProfile):
        raise ValueError("The Greedy Sequential Phragmen Rule currently does not support MultiProfile")

    for project in instance:
        if project.cost < 0:
            raise ValueError(f"Project {project.name} has negative cost: {project.cost}")

    logger.info(f"Initial budget: {instance.budget_limit}")
    logger.info(f"Projects: {[f'{p.name} (cost={p.cost})' for p in instance]}")
    logger.info(f"Profile: {[[p.name for p in ballot] for ballot in profile]}")

    budget = instance.budget_limit
    remaining_budget = budget
    selected_projects: list[Project] = []
    current_loads = np.zeros(profile.num_ballots())
    available_projects = set(instance)

    while True:
        approvers_map = {
            p: [i for i, ballot in enumerate(profile) if p in ballot]
            for p in available_projects
            if p.cost <= remaining_budget and any(p in ballot for ballot in profile)
        }

        logger.debug(f"Feasible projects this round: {[p.name for p in approvers_map]}")
        if not approvers_map:
            logger.info("No more feasible approved projects. Exiting main loop.")
            break

        project_to_load = {
            p: _compute_new_max_load(p, approvers_map[p], current_loads)
            for p in approvers_map
        }

        min_load = min(project_to_load.values())
        candidates = [p for p in project_to_load if project_to_load[p] == min_load]
        logger.debug(f"Minimum load: {min_load}, Candidates: {[p.name for p in candidates]}")

        chosen = tie_breaking.untie(instance, profile, candidates)
        logger.info(f"Chosen project: {chosen.name} with cost {chosen.cost} and {min_load} max load")

        selected_projects.append(chosen)
        remaining_budget -= chosen.cost
        approvers = approvers_map[chosen]
        cost_per_voter = frac(chosen.cost, len(approvers))
        for voter in approvers:
            current_loads[voter] += float(cost_per_voter)

        logger.debug(f"Updated voter loads: {current_loads}")
        logger.debug(f"Remaining budget: {remaining_budget}")
        available_projects.remove(chosen)

    logger.info("Starting post-processing step")

    for p in tie_breaking.order(instance, profile, available_projects):
        if p.cost <= remaining_budget:
            selected_projects.append(p)
            remaining_budget -= p.cost
            logger.info(f"Post-processed addition: {p.name}, remaining budget: {remaining_budget}")

    logger.info(f"Final selected projects: {[p.name for p in selected_projects]}")
    return BudgetAllocation(selected_projects)

def _compute_new_max_load(project: Project, approvers: list[int], current_loads: np.ndarray) -> float:
    """
    Computes the new maximal load if we add the given project,
    distributing its cost evenly among its supporters.

    Parameters
    ----------
    project : Project
        The project being considered.
    approvers : List[int]
        The list of voter indices who approve this project.
    current_loads : np.ndarray
        The current load vector of all voters.

    Returns
    -------
    float
        The maximal load after distributing the project cost among its approvers.

    """
    if not approvers:
        return float('inf')
    cost_per_voter = float(frac(project.cost, len(approvers)))
    new_loads = current_loads.copy()
    for voter in approvers:
        new_loads[voter] += cost_per_voter
    logger.info(f"project: {project.name} with cost {project.cost} and {float(max(new_loads))} max load")
    return float(max(new_loads))
