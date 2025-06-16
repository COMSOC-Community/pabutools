"""
Implementation of the GPseq algorithm from:

"Proportionally Representative Participatory Budgeting: Axioms and Algorithms"
by Haris Aziz, Barton Lee, Nimrod Talmon.
https://arxiv.org/abs/1711.08226

Programmer: <Shlomi Asraf>
Date: 2025-05-13
"""

from __future__ import annotations
import logging
import numpy as np
import cvxpy as cp
from pabutools.fractions import frac
from pabutools.election.instance import Instance, Project
from pabutools.election.profile import AbstractApprovalProfile
from pabutools.rules.budgetallocation import BudgetAllocation
from pabutools.tiebreaking import TieBreakingRule, lexico_tie_breaking

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def gpseq(
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

    # Variables: x[c][i] = load that voter i takes for project c
    x = {
        (p, i): cp.Variable(nonneg=True)
        for p in projects for i in voter_ids
    }

    constraints = []

    # Constraint: x[p][i] = 0 if i doesn't approve p
    for p in projects:
        for i in voter_ids:
            if p not in profile[i]:
                constraints.append(x[p, i] == 0)

    # Constraint: total load assigned per project equals cost
    for p in projects:
        constraints.append(cp.sum([x[p, i] for i in voter_ids]) == p.cost)

    # Voter total load
    voter_load = [cp.sum([x[p, i] for p in projects]) for i in voter_ids]

    # Minimize max voter load
    z = cp.Variable()
    for i in voter_ids:
        constraints.append(voter_load[i] <= z)

    prob = cp.Problem(cp.Minimize(z), constraints)
    prob.solve(solver=cp.ECOS)  # You can also try SCS or OSQP

    if prob.status != cp.OPTIMAL:
        raise RuntimeError("LP did not converge")

    return z.value
    
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

