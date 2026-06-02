"""
Implementation of the Greedy Cohesive Rule (GCR) from:
  Peters, Pierczyński, and Skowron (2021).
  "Proportional Participatory Budgeting with Additive Utilities."
  NeurIPS 2021.

Used as the deterministic backbone of BW-GCR-PB in:
  Aziz, Lu, Suzuki, Vollen, and Walsh (2024).
  "Fair Lotteries for Participatory Budgeting."
  AAAI 2024.

Per Definition 5.3 of the AAAI 2024 paper, a group S is weakly (β,T)-cohesive if:
  (1) |S| · B/n  ≥  cost(T)          [size: group's fair share covers T]
  (2) |Aᵢ ∩ T|  ≥  β  for all i ∈ S  [β = min approvals of T across S]

GCR maximises β, breaks ties by smaller cost(T), then by larger |S|.

Programmers: Dotan Danino, Naama Yahav.
Date: 1/6/2026

"""

from __future__ import annotations

from itertools import combinations

from pabutools.election.instance import Instance, total_cost
from pabutools.election.profile import AbstractProfile
from pabutools.rules.budgetallocation import BudgetAllocation
from pabutools.rules.gcr.gcr_details import GCRAllocationDetails, GCRIteration


def greedy_cohesive_rule(
    instance: Instance,
    profile: AbstractProfile,
    analytics: bool = False,
    max_subset_size: int | None = None,
) -> BudgetAllocation:
    """
    The Greedy Cohesive Rule (GCR) for participatory budgeting.

    Per Definition 5.3 of Aziz et al. (2024), a group S of active voters is
    weakly (β,T)-cohesive for a project set T if:

        |S| · B/n  ≥  cost(T)               [size condition — once, no β factor]
        |Aᵢ ∩ T|   ≥  β  for all i ∈ S      [β = how many projects of T each voter approves]

    In each iteration GCR finds the (S, T) pair maximising β, breaking ties
    by smaller cost(T) then larger |S|.  T is added to W and S is deactivated.
    Terminates when no weakly (β,T)-cohesive group exists for any β ≥ 1.

    Parameters
    ----------
    instance : Instance
        The PB instance (projects + budget limit).
    profile : AbstractProfile
        The voters' approval ballots.
    analytics : bool, optional
        If True, attaches a :class:`GCRAllocationDetails` object to the result.
    max_subset_size : int or None, optional
        Caps |T| in the search (None = unlimited, exponential but correct).

    Returns
    -------
    BudgetAllocation
        The projects selected by GCR.

    Examples
    --------
    >>> from pabutools.election.instance import Instance, Project
    >>> from pabutools.election.profile import ApprovalProfile
    >>> from pabutools.election.ballot import ApprovalBallot
    >>> p1 = Project("p1", cost=30)
    >>> p2 = Project("p2", cost=30)
    >>> p3 = Project("p3", cost=30)
    >>> instance = Instance([p1, p2, p3], budget_limit=60)
    >>> profile = ApprovalProfile([
    ...     ApprovalBallot([p1, p2]),
    ...     ApprovalBallot([p1, p2]),
    ...     ApprovalBallot([p3]),
    ... ])
    >>> result = greedy_cohesive_rule(instance, profile)
    >>> sorted(p.name for p in result)
    ['p1', 'p2']
    """
    n = profile.num_ballots()
    B = instance.budget_limit

    W: set = set()
    selected: list = []
    active: list[int] = list(range(n))
    ballots: list = list(profile)
    details = GCRAllocationDetails() if analytics else None

    while active:
        unselected = [p for p in instance if p not in W]
        if not unselected:
            break

        max_size = max_subset_size if max_subset_size is not None else len(unselected)

        best_score: tuple | None = None  # (beta, -cost_T, len_N_prime)
        best_T: tuple | None = None
        best_N_prime: list | None = None

        for r in range(1, max_size + 1):
            for T in combinations(unselected, r):
                cost_T = total_cost(T)
                if cost_T <= 0 or cost_T > B:
                    continue

                # For each active voter, count how many projects in T they approve.
                # β = min across S of |Aᵢ ∩ T|.  We try the largest feasible β first:
                # start with k = r (everyone approves all of T) and decrease until
                # the size condition is met.
                approval_counts = [
                    sum(1 for p in T if p in ballots[i])
                    for i in active
                ]

                for k in range(r, 0, -1):
                    # S = active voters who approve ≥ k projects from T
                    N_prime = [
                        active[idx]
                        for idx, cnt in enumerate(approval_counts)
                        if cnt >= k
                    ]
                    if not N_prime:
                        continue
                    # Size condition: |S| · B/n ≥ cost(T)
                    if len(N_prime) * B < n * cost_T:
                        continue
                    # Valid: β = k for this (T, S) pair
                    score = (k, -float(cost_T), len(N_prime))
                    if best_score is None or score > best_score:
                        best_score = score
                        best_T = T
                        best_N_prime = N_prime
                    break  # k is the best achievable for this T; lower k can't improve

        if best_T is None:
            break  # no weakly cohesive group remains; terminate

        selected.extend(best_T)
        W.update(best_T)

        deactivated = set(best_N_prime)
        active = [i for i in active if i not in deactivated]

        if analytics:
            details.iterations.append(
                GCRIteration(
                    beta=best_score[0],
                    selected_projects=list(best_T),
                    deactivated_voters=list(deactivated),
                    active_voters_remaining=len(active),
                )
            )

    allocation = BudgetAllocation(selected)
    if analytics:
        allocation.details = details
    return allocation
