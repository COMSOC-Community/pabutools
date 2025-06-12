
from __future__ import annotations
from collections import defaultdict
from pabutools.election.instance import Instance
from pabutools.election.profile import AbstractProfile, OrdinalProfile
from pabutools.election.profile.ordinalprofile import AbstractOrdinalProfile
from pabutools.rules.budgetallocation import BudgetAllocation

"""
An implementation of the PB-EAR algorithm from:

"Proportionally Representative Participatory Budgeting with Ordinal Preferences",
Haris Aziz and Barton E. Lee (2020),
https://arxiv.org/abs/1911.00864v2

Programmer: Vivian Umansky
Date: 2025-04-23
"""

def pb_ear(
    instance: Instance,
    profile: AbstractProfile,
    verbose: bool = False
) -> BudgetAllocation:
    """
    PB-EAR Algorithm — Proportional Representation via Inclusion-PSC (IPSC) under Ordinal Preferences.

    This algorithm selects a subset of projects within a given budget, ensuring proportional representation
    for solid coalitions based on voters' weighted ordinal preferences. It supports both `OrdinalProfile`
    and `OrdinalMultiProfile` inputs.

    Parameters
    ----------
    instance : Instance
        The budgeting instance containing all candidate projects and the total budget limit.
        Each project has a unique name and a positive cost.

    profile : AbstractOrdinalProfile
        A profile of voters' preferences. Each voter submits a strict ranking over a subset of projects,
        and is assigned a positive weight. Can be an `OrdinalProfile` or `OrdinalMultiProfile`.

    verbose : bool, optional
        If True, enables detailed logging output for debugging or analysis (default is False).

    Returns
    -------
    BudgetAllocation
        An allocation object containing the selected projects. These projects:
        - Respect the overall budget constraint
        - Satisfy the Inclusion Proportionality for Solid Coalitions (IPSC) axiom

    Raises
    ------
    ValueError
        If the input profile is not an instance of `AbstractOrdinalProfile`.
        """
    # Ensure the profile is ordinal (either OrdinalProfile or OrdinalMultiProfile)
    if not isinstance(profile, AbstractOrdinalProfile):
        raise ValueError("PB-EAR only supports ordinal profiles (OrdinalProfile or OrdinalMultiProfile).")

    # If there are no voters, return an empty allocation
    if len(profile) == 0:
        return BudgetAllocation()

    # Extract basic input data
    budget = instance.budget_limit
    project_cost = {p.name: p.cost for p in instance}
    all_projects = set(project_cost)

    # Convert the profile to a list of (weight, preference list) pairs
    voters = [(profile[ballot], list(ballot)) for ballot in profile]
    initial_n = sum(w for w, _ in voters)  # Total weight
    voter_weights = {i: weight for i, (weight, _) in enumerate(voters)}  # Mutable copy for updates

    j = 1  # Rank threshold level
    selected_projects = set()
    remaining_budget = budget

    while True:
        # Identify which projects are still affordable
        available_projects = [
            p for p in all_projects - selected_projects if project_cost[p] <= remaining_budget
        ]
        if not available_projects:
            break  # No more projects can be selected

        # Build approval sets: for each voter, include all projects up to their j-th most preferred one
        approvals = defaultdict(set)
        for i, (_, prefs) in enumerate(voters):
            if j <= len(prefs):
                threshold = prefs[j - 1]
                rank_threshold = prefs.index(threshold)
                approvals[i] = set(prefs[:rank_threshold + 1])
            else:
                approvals[i] = set(prefs)  # If j exceeds length, approve everything

        # Aggregate support for each candidate project
        candidate_support = defaultdict(float)
        for i, approved_set in approvals.items():
            for p in approved_set:
                if p not in selected_projects:
                    candidate_support[p] += voter_weights[i]

        # Identify projects whose support justifies their cost (IPSC condition)
        C_star = {
            c for c in available_projects
            if round(candidate_support[c], 6) >= round((initial_n * project_cost[c]) / budget, 6)
        }

        if not C_star:
            # If no justifiable projects and we haven't exhausted all ranks, increase threshold j
            if j > max(len(prefs) for _, prefs in voters):
                break  # All ranks checked
            j += 1
            continue

        # Select an arbitrary justifiable project
        c_star = next(iter(C_star))
        selected_projects.add(c_star)
        remaining_budget -= project_cost[c_star]

        # Reduce weight of voters who approved c_star proportionally
        N_prime = [i for i in range(len(voters)) if c_star in approvals[i]]
        total_weight_to_reduce = (initial_n * project_cost[c_star]) / budget

        if N_prime:
            sum_supporters = sum(voter_weights[i] for i in N_prime)
            weight_fraction = total_weight_to_reduce / sum_supporters if sum_supporters > 0 else 0
            for i in N_prime:
                voter_weights[i] *= (1 - weight_fraction)

    # Construct the final BudgetAllocation object
    allocation = BudgetAllocation()
    for name in sorted(selected_projects):
        allocation.append(instance.get_project(name))

    return allocation



