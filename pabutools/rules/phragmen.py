"""
Phragmén's methods.
"""

from __future__ import annotations

from collections.abc import Collection
from copy import deepcopy

from pabutools.rules.budgetallocation import BudgetAllocation
from pabutools.utils import Numeric

from pabutools.fractions import frac
from pabutools.election import (
    Instance,
    Project,
    total_cost,
    AbstractApprovalBallot,
    AbstractApprovalProfile,
)
from pabutools.tiebreaking import TieBreakingRule, lexico_tie_breaking



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
        max_load: Numeric, optional
            The maximum load of the voter. If the load exceeds this value, the voter no longer considered.

    Attributes
    ----------
        ballot: :py:class:`~pabutools.election.ballot.approvalballot.AbstractApprovalBallot`
            The ballot of the voter.
        load: Numeric
            The initial load of the voter.
        multiplicity: int
            The multiplicity of the ballot.
        max_load: Numeric
            The maximum load of the voter.
    """

    def __init__(
        self, ballot: AbstractApprovalBallot, load: Numeric, multiplicity: int, max_load: Numeric = None
    ):
        self.ballot = ballot
        self.load = load
        self.multiplicity = multiplicity
        self.max_load = max_load

    def total_load(self):
        return self.multiplicity * self.load


def sequential_phragmen(
    instance: Instance,
    profile: AbstractApprovalProfile,
    initial_loads: list[Numeric] | None = None,
    global_max_load: Numeric | None = None,
    initial_budget_allocation: Collection[Project] | None = None,
    tie_breaking: TieBreakingRule | None = None,
    resoluteness: bool = True,
) -> BudgetAllocation | list[BudgetAllocation]:
    """
    Phragmén's sequential rule. It works as follows. Voters receive money in a virtual currency. They all start with a
    budget of 0 and that budget continuously increases. As soon asa group of supporters have enough virtual currency to
    buy a project they all approve, the project is bought. The rule stops as soon as there is a project that could be
    bought  but only by violating the budget constraint.

    Note that this rule can only be applied to profiles of approval ballots.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.approvalprofile.AbstractApprovalProfile`
            The profile.
        initial_loads: list[Numeric], optional
            A list of initial load, one per ballot in `profile`. By defaults, the initial load is `0`.
        global_max_load: Numeric, optional
            A maximum load. The rule stops when any voter would exceed this limit.
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
        projects,
        voters,
        alloc,
        cost,
        allocs,
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

            # Stop if any of the potential projects cost too much
            if any(
                cost + project.cost > instance.budget_limit
                for project in arg_min_new_maxload
            ):
                alloc.sort()
                if alloc not in allocs:
                    allocs.append(alloc)
            # Stop if selecting any project would exceed the global max load bound.
            elif global_max_load is not None and min_new_maxload > global_max_load:
                alloc.sort()
                if alloc not in allocs:
                    allocs.append(alloc)
            else:
                tied_projects = tie_breaking.order(instance, profile, arg_min_new_maxload)
                if resoluteness:
                    selected_project = tied_projects[0]
                    for voter in voters:
                        if selected_project in voter.ballot:
                            voter.load = min_new_maxload
                    alloc.append(selected_project)
                    projects.remove(selected_project)
                    aux(
                        projects,
                        voters,
                        alloc,
                        cost + selected_project.cost,
                        allocs,
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
                            new_projs,
                            new_voters,
                            new_alloc,
                            new_cost,
                            allocs,
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
    supporters = {
        proj: [i for i, v in enumerate(voters_details) if proj in v.ballot]
        for proj in initial_projects
    }

    approval_scores = {project: profile.approval_score(project) for project in instance}

    print("\n")
    all_budget_allocations: list[BudgetAllocation] = []
    aux(
        initial_projects,
        voters_details,
        initial_budget_allocation,
        current_cost,
        all_budget_allocations,
    )

    if resoluteness:
        return all_budget_allocations[0]
    return all_budget_allocations


