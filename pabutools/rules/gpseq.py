"""
Implementation of the GPseq algorithm from:

"Proportionally Representative Participatory Budgeting: Axioms and Algorithms"
by Haris Aziz, Bettina Klaus, Jérôme Lang, and Markus Brill (2017)
https://arxiv.org/abs/1711.08226

Programmer: <Shlomi Asraf>
Date: 2025-05-13
"""

from __future__ import annotations
from pabutools.election.instance import Instance, Project
from pabutools.election.profile.approvalprofile import ApprovalProfile
from pabutools.election.ballot.approvalballot import ApprovalBallot
from pabutools.tiebreaking import TieBreakingRule, lexico_tie_breaking
import numpy as np
import logging
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def gpseq(
    instance: Instance,
    profile: ApprovalProfile,
    tie_breaking: TieBreakingRule = lexico_tie_breaking
) -> list[Project]:
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

    for project in instance:
        if project.cost < 0:
            raise ValueError(f"Project {project.name} has negative cost: {project.cost}")

    logging.info(f"Initial budget: {instance.budget_limit}")
    logging.info(f"Projects: {[f'{p.name} (cost={p.cost})' for p in instance]}")
    logging.info(f"Profile: {[[p.name for p in ballot] for ballot in profile]}")

    # Initialize variables
    budget = instance.budget_limit
    remaining_budget = budget
    selected_projects = []
    current_loads = np.zeros(len(profile))  # Load per voter
    available_projects = set(instance)  # Instance is a set of projects

    while True:
        # Build map of feasible projects with their approver indices
        approvers_map = {
            p: [i for i, ballot in enumerate(profile) if p in ballot]
            for p in available_projects
            if p.cost <= remaining_budget and any(p in ballot for ballot in profile)
        }

        logging.debug(f"Feasible projects this round: {[p.name for p in approvers_map]}")
        if not approvers_map:
            logging.info("No more feasible approved projects. Exiting main loop.")
            break

        # Compute the maximal load that would result from adding each project
        project_to_load = {
            p: compute_load(p, approvers_map[p], current_loads)
            for p in approvers_map
        }

        min_load = min(project_to_load.values())

        candidates = [p for p in project_to_load if project_to_load[p] == min_load]
        logging.debug(f"Minimum load: {min_load}, Candidates: {[p.name for p in candidates]}")
        chosen = tie_breaking.untie(instance, profile, candidates)
        logging.info(f"Chosen project: {chosen.name} with cost {chosen.cost} and {min_load} max load")
        # Update selected projects, budget and voter loads
        selected_projects.append(chosen)
        remaining_budget -= chosen.cost
        approvers = approvers_map[chosen]
        cost_per_voter = chosen.cost / len(approvers)
        for voter in approvers:
            current_loads[voter] += cost_per_voter


        logging.debug(f"Updated voter loads: {current_loads}")
        logging.debug(f"Remaining budget: {remaining_budget}")
        available_projects.remove(chosen)
        logging.debug(f"Added project {chosen.name}, remaining budget: {remaining_budget}")

    # Post-processing: Add remaining projects that fit in the remaining budget (not necessarily approved)
    # Sort lexicographically to match paper's suggestion
    logging.info("Starting post-processing step")
    for p in sorted(available_projects, key=lambda x: x.name):
        if p.cost <= remaining_budget:
            selected_projects.append(p)
            remaining_budget -= p.cost
            logging.info(f"Post-processed addition: {p.name}, remaining budget: {remaining_budget}")
    logging.info(f"Final selected projects: {[p.name for p in selected_projects]}")
    logging.info(f">>>>>>>>>>>>>>>>>>>>>")
    return selected_projects

def compute_load(project: Project, approvers: list[int], current_loads: np.ndarray) -> float:
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

    Examples
    --------
    >>> project = Project("c1", cost=2)
    >>> compute_load(project, [0, 1], np.array([0.0, 0.0]))
    1.0
    """
    if not approvers:
        return float('inf') # Cannot assign project with no approvers
    cost_per_voter = project.cost / len(approvers)
    new_loads = current_loads.copy()
    for voter in approvers:
        new_loads[voter] += cost_per_voter
    logging.info(f"project: {project.name} with cost {project.cost} and {float(max(new_loads))} max load")
    return float(max(new_loads))
