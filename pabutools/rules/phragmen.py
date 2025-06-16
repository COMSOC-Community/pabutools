"""
Phragmén's methods.
"""

from __future__ import annotations

import logging

from collections.abc import Collection
from copy import deepcopy
from pulp import LpProblem, LpVariable, lpSum, LpMinimize, LpStatusOptimal, value
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
    tie_breaking: TieBreakingRule = lexico_tie_breaking,
    mode: str = "uniform"  # or "optimal"
) -> BudgetAllocation:
    """
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
    >>> result = gpseq(instance, profile)
    >>> [p.name for p in result]
    ['c1', 'c3']

    >>> p1 = Project("c1", cost=1)
    >>> instance = Instance([p1], budget_limit=1)
    >>> profile = ApprovalProfile([ApprovalBallot([p1])])
    >>> result = gpseq(instance, profile)
    >>> [p.name for p in result]
    ['c1']

    >>> p1 = Project("c1", cost=1)
    >>> p2 = Project("c2", cost=2)
    >>> instance = Instance([p1, p2], budget_limit=2)
    >>> profile = ApprovalProfile([ApprovalBallot([p1]), ApprovalBallot([p1]), ApprovalBallot([p1]), ApprovalBallot([p2])])
    >>> result = gpseq(instance, profile)
    >>> [p.name for p in result]
    ['c1']

    >>> p1 = Project("c1", cost=2)
    >>> p2 = Project("c2", cost=1.5)
    >>> p3 = Project("c3", cost=1.5)
    >>> instance = Instance([p1, p2, p3], budget_limit=3)
    >>> profile = ApprovalProfile([ApprovalBallot([p1, p2]), ApprovalBallot([p1, p2]), ApprovalBallot([p1, p2]), ApprovalBallot([p1, p2]), ApprovalBallot([p3]), ApprovalBallot([p3])])
    >>> result = gpseq(instance, profile)
    >>> [p.name for p in result]
    ['c2', 'c3']

    >>> p1 = Project("c1", cost=2)
    >>> p2 = Project("c2", cost=2)
    >>> p3 = Project("c3", cost=0.8)
    >>> instance = Instance([p1, p2, p3], budget_limit=2)
    >>> profile = ApprovalProfile([ApprovalBallot([p1, p2]), ApprovalBallot([p1, p2]), ApprovalBallot([p1, p2]), ApprovalBallot([p1, p2]), ApprovalBallot([p3]), ApprovalBallot([p3])])
    >>> result = gpseq(instance, profile)
    >>> [p.name for p in result]
    ['c3']

    >>> p1 = Project("c1", cost=1.5)
    >>> p2 = Project("c2", cost=1.5)
    >>> p3 = Project("c3", cost=1.0)
    >>> instance = Instance([p1, p2, p3], budget_limit=3)
    >>> profile = ApprovalProfile([ApprovalBallot([p1, p2]), ApprovalBallot([p1]), ApprovalBallot([p2, p3]), ApprovalBallot([p3])])
    >>> result = gpseq(instance, profile)
    >>> [p.name for p in result]
    ['c3', 'c1']
    """
    logging.info("Starting GPseq algorithm")

    if hasattr(profile, "is_multiprofile") and profile.is_multiprofile():
        raise ValueError("GPseq currently does not support MultiProfile")

    for project in instance:
        if project.cost < 0:
            raise ValueError(f"Project {project.name} has negative cost")

    budget = instance.budget_limit
    remaining_budget = budget
    selected_projects: list[Project] = []
    available_projects = set(instance)

    while True:
        approvers_map = {
            p: [i for i, ballot in enumerate(profile) if p in ballot]
            for p in available_projects
            if p.cost <= remaining_budget and any(p in ballot for ballot in profile)
        }

        if not approvers_map:
            break

        if mode == "uniform":
            project_to_load = {
                p: compute_uniform_load(p, approvers_map[p], len(profile))
                for p in approvers_map
            }
        elif mode == "optimal":
            project_to_load = {
                p: compute_optimal_load(selected_projects + [p], profile)
                for p in approvers_map
            }
        else:
            raise ValueError(f"Unknown mode '{mode}', must be 'uniform' or 'optimal'")

        min_load = min(project_to_load.values())
        candidates = [p for p in project_to_load if project_to_load[p] == min_load]
        chosen = tie_breaking.untie(instance, profile, candidates)

        selected_projects.append(chosen)
        remaining_budget -= chosen.cost
        available_projects.remove(chosen)

    for p in sorted(available_projects, key=lambda x: x.name):
        if p.cost <= remaining_budget:
            selected_projects.append(p)
            remaining_budget -= p.cost

    return BudgetAllocation(selected_projects)

def compute_optimal_load(projects, profile):
    """
    Solves the LP relaxation from Algorithm 1 (GPseq) to minimize the max load.
    
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

    status = prob.solve()
    if status != LpStatusOptimal:
        raise RuntimeError("LP did not converge")

    return value(z)
    
def compute_uniform_load(project: Project, approvers: list[int], num_voters: int) -> float:
    """
    Computes max load assuming uniform cost distribution among approvers.
    """
    if not approvers:
        return float("inf")
    per_voter = project.cost / len(approvers)
    loads = [0.0] * num_voters
    for i in approvers:
        loads[i] += per_voter
    return max(loads)

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
