"""
Implementation of the ballot-weighted lottery algorithms from:
  Aziz, Lu, Suzuki, Vollen, and Walsh (2024).
  "Fair Lotteries for Participatory Budgeting."
  AAAI 2024.

Two algorithms are provided:

* BW-GCR-PB (Algorithm 1): uses GCR as deterministic backbone, satisfies FJR.
* BW-MES-PB (Algorithm 2): uses MES as deterministic backbone, satisfies EJR.

Both algorithms return a fractional probability vector and apply BB1 dependent
rounding to produce a discrete lottery outcome.

Programmers: Dotan Danino, Naama Yahav.
"""

from __future__ import annotations

import logging
import random

from pabutools.election.ballot import ApprovalBallot
from pabutools.election.instance import Instance, Project, instance_from_project_costs
from pabutools.election.profile import AbstractProfile, Profile, approval_profile_from_matrix
from pabutools.election.satisfaction import AdditiveSatisfaction
from pabutools.rules.gcr import greedy_cohesive_rule
from pabutools.rules.mes import method_of_equal_shares

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Convenience aliases kept for backward compatibility
# ---------------------------------------------------------------------------

def build_instance(C: list, cost: dict, B: float) -> Instance:
    """Alias for :func:`~pabutools.election.instance.instance_from_project_costs`."""
    return instance_from_project_costs({c: cost[c] for c in C}, B)


def build_profile(N: list, ui: dict, instance: Instance) -> Profile:
    """Alias for :func:`~pabutools.election.profile.approval_profile_from_matrix`."""
    return approval_profile_from_matrix(N, ui, instance)


def approval_sat(instance: Instance, profile: Profile, ballot: ApprovalBallot):
    """
    Approval-based satisfaction function for use with MES.

    A voter receives satisfaction 1 from a project that appears in their ballot,
    and 0 otherwise.
    """
    def f(inst, prof, bal, project, *rest):
        return 1 if project in ballot else 0
    return AdditiveSatisfaction(instance, profile, ballot, func=f)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _gnz_calc(A_Nz_sorted: list, B: float, n: int, group_size: int) -> list:
    """Return the greedy set G_Nz of projects the group can afford collectively."""
    group_budget = group_size * (B / n)
    G_Nz = []
    spent = 0.0
    for proj in A_Nz_sorted:
        if spent + proj.cost <= group_budget:
            G_Nz.append(proj)
            spent += proj.cost
        else:
            break
    return G_Nz


# ---------------------------------------------------------------------------
# BB1 dependent rounding
# ---------------------------------------------------------------------------

def dependent_rounding_bb1(p_vec_list: list, projects: list) -> list:
    """
    Dependent Randomized Rounding (BB1) — converts a fractional probability
    vector into a discrete set of projects.

    This guarantees ex-post Budget Balance up to 1 project (BB1).

    Parameters
    ----------
    p_vec_list : list[float]
        Fractional probabilities, one per project, in the same order as `projects`.
    projects : list[Project]
        Ordered list of Project objects.

    Returns
    -------
    list[Project]
        The selected projects after rounding.

    Examples
    --------
    (All examples use deterministic probabilities of 1.0 or 0.0.)

    Example 1: mix of 1.0 and 0.0
    >>> pa = Project("a", 12000); pb = Project("b", 12000); pc = Project("c", 8000); pd = Project("d", 8000)
    >>> dependent_rounding_bb1([1.0, 1.0, 1.0, 0.0], [pa, pb, pc, pd])
    [a, b, c]

    Example 2: all 1.0
    >>> pa = Project("a", 21000); pb = Project("b", 10000); pc = Project("c", 2000)
    >>> dependent_rounding_bb1([1.0, 1.0, 1.0], [pa, pb, pc])
    [a, b, c]

    Example 3: all 0.0
    >>> pa = Project("a", 21000); pb = Project("b", 10000); pc = Project("c", 2000)
    >>> dependent_rounding_bb1([0.0, 0.0, 0.0], [pa, pb, pc])
    []
    """
    logger.info("Starting BB1 dependent rounding with %d projects.", len(projects))
    p = {projects[i]: p_vec_list[i] for i in range(len(projects))}
    iteration = 1

    while True:
        fractional = [proj for proj, prob in p.items() if 0.0001 < prob < 0.9999]

        if not fractional:
            logger.info("BB1 complete in %d iterations.", iteration)
            break

        if len(fractional) == 1:
            proj = fractional[0]
            logger.info("Single fractional project %s (%.4f). Rounding independently.", proj, p[proj])
            p[proj] = 1.0 if random.random() < p[proj] else 0.0
            break

        pi, pj = fractional[0], fractional[1]
        logger.debug("Iteration %d: pair %s (%.4f) and %s (%.4f).", iteration, pi, p[pi], pj, p[pj])

        # Option A: increase pi, decrease pj
        alpha = min(1.0 - p[pi], p[pj] * (pj.cost / pi.cost))
        beta  = alpha * (pi.cost / pj.cost)

        # Option B: decrease pi, increase pj
        gamma = min(p[pi], (1.0 - p[pj]) * (pj.cost / pi.cost))
        delta = gamma * (pi.cost / pj.cost)

        q = gamma / (alpha + gamma) if (alpha + gamma) > 0 else 0.0

        if random.random() < q:
            p[pi] += alpha
            p[pj] -= beta
        else:
            p[pi] -= gamma
            p[pj] += delta

        iteration += 1

    W = [proj for proj, prob in p.items() if prob >= 0.9999]
    logger.info("BB1 finished. Selected %d projects.", len(W))
    return W


# ---------------------------------------------------------------------------
# Algorithm 1: BW-GCR-PB
# ---------------------------------------------------------------------------

def BW_GCR_PB(instance: Instance, profile: AbstractProfile, analytics: bool = False) -> list:
    """
    Algorithm 1 (BW-GCR-PB): ballot-weighted lottery backed by the Greedy
    Cohesive Rule (GCR).

    Satisfies strong UFS and Fair Justified Representation (FJR).

    Parameters
    ----------
    instance : Instance
        The PB instance (projects + budget limit).
    profile : AbstractProfile
        The voters' approval ballots.
    analytics : bool, optional
        Reserved for future use. Defaults to False.

    Returns
    -------
    list[float]
        Fractional probability for each project, sorted alphabetically by name.
    """
    n = profile.num_ballots()
    B = instance.budget_limit
    projects = sorted(instance, key=lambda p: p.name)
    ballots = list(profile)

    logger.info("BW_GCR_PB: %d voters, %d projects, budget %f.", n, len(projects), B)

    try:
        gcr_allocation = greedy_cohesive_rule(instance=instance, profile=profile)
        selected = set(gcr_allocation)
        logger.info("GCR selected %d projects.", len(selected))
    except Exception as e:
        logger.error("GCR failed: %s", e)
        selected = set()

    # Line 2: initialize probability vector
    p_vec = {proj: (1.0 if proj in selected else 0.0) for proj in projects}

    # Lines 3-4: track per-voter budget allocations
    b = {i: 0.0 for i in range(n)}
    N_tilde: set = set()

    # Line 5: group voters by identical approval set
    groups: dict = {}
    for idx, ballot in enumerate(ballots):
        key = frozenset(ballot)
        groups.setdefault(key, []).append(idx)

    logger.info("Identified %d unanimous groups.", len(groups))

    # Line 6: process each unanimous group
    for group_idx, (approved_set, group_indices) in enumerate(groups.items()):
        group_size = len(group_indices)
        A_Nz = list(approved_set)
        A_Nz_sorted = sorted(A_Nz, key=lambda proj: (proj.cost, proj.name))
        G_Nz = _gnz_calc(A_Nz_sorted, B, n, group_size)

        # Line 7: check intersection condition
        intersect = [proj for proj in A_Nz if proj in selected]
        if len(intersect) != len(G_Nz):
            continue

        # Lines 8-9
        N_tilde.update(group_indices)
        cost_G = sum(proj.cost for proj in G_Nz)
        for i in group_indices:
            b[i] = (B / n) - (1 / group_size) * cost_G

        # Line 10: spend leftover on cheapest approved projects
        leftover = group_size * (B / n) - cost_G
        logger.debug("Group %d leftover budget: %f.", group_idx + 1, leftover)

        for proj in A_Nz_sorted:
            if p_vec[proj] < 1.0 and leftover > 0:
                increase = min(1.0 - p_vec[proj], leftover / proj.cost)
                p_vec[proj] += increase
                leftover -= increase * proj.cost

    # Line 11: fill remaining budget arbitrarily
    expected_cost = sum(p_vec[proj] * proj.cost for proj in projects)
    remaining = B - expected_cost
    logger.info("After groups: expected cost %f, remaining %f.", expected_cost, remaining)

    if remaining < -0.0001:
        logger.warning("Remaining budget is negative (%f).", remaining)

    for proj in projects:
        if remaining <= 0.0001:
            break
        if p_vec[proj] < 1.0:
            headroom = 1.0 - p_vec[proj]
            needed = headroom * proj.cost
            if remaining >= needed:
                p_vec[proj] = 1.0
                remaining -= needed
            else:
                p_vec[proj] += remaining / proj.cost
                remaining = 0

    logger.info("BW_GCR_PB completed.")
    return [p_vec[proj] for proj in projects]


def BW_GCR_PB_from_lists(N: list, C: list, cost: dict, B: float, ui: dict) -> list:
    """
    Convenience wrapper for :func:`BW_GCR_PB` that accepts raw lists and dicts.

    Parameters
    ----------
    N : list
        Voter identifiers.
    C : list
        Project identifiers (must be in a consistent order — returned probabilities
        match this order).
    cost : dict
        Maps each project identifier to its cost.
    B : float
        Total available budget.
    ui : dict
        Maps each voter to a dict ``{project_id: 1/0}``.

    Returns
    -------
    list[float]
        Fractional probability for each project, in the same order as `C`.

    Examples
    --------
    Example 1: Enough budget for all projects:
    >>> N = ['1', '2']
    >>> C = ['a', 'b', 'c']
    >>> cost = {'a': 21000, 'b': 10000, 'c': 2000}
    >>> B = 33000
    >>> ui = {
    ... '1': {'a': 1, 'b': 1, 'c': 0},
    ... '2': {'a': 0, 'b': 1, 'c': 1}
    ... }
    >>> BW_GCR_PB_from_lists(N, C, cost, B, ui)
    [1.0, 1.0, 1.0]

    Example 2: Different output for each algorithm:
    >>> N = ['1', '2', '3']
    >>> C = ['a', 'b', 'c', 'd']
    >>> cost = {'a': 8000, 'b': 8000, 'c': 12000, 'd': 12000}
    >>> B = 30000
    >>> ui = {
    ... '1': {'a': 1, 'b': 0, 'c': 1, 'd': 0},
    ... '2': {'a': 0, 'b': 0, 'c': 1, 'd': 1},
    ... '3': {'a': 0, 'b': 1, 'c': 0, 'd': 1}
    ... }
    >>> BW_GCR_PB_from_lists(N, C, cost, B, ui)
    [1.0, 1.0, 1.0, 0.16666666666666666]

    Example 3: tight budget:
    >>> N = ['1', '2', '3', '4']
    >>> C = ['a', 'b']
    >>> cost = {'a': 1000, 'b': 5000}
    >>> B = 5000
    >>> ui = {
    ... '1': {'a': 1, 'b': 1},
    ... '2': {'a': 0, 'b': 1},
    ... '3': {'a': 0, 'b': 1},
    ... '4': {'a': 0, 'b': 1}
    ... }
    >>> BW_GCR_PB_from_lists(N, C, cost, B, ui)
    [1.0, 0.8]

    Example 4: many projects (GCR output varies with set iteration order):
    >>> N = ['1', '2', '3', '4', '5', '6', '7', '8']
    >>> C = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
    >>> cost = {'a': 8000, 'b': 15000, 'c': 10000, 'd': 10000, 'e': 6000, 'f': 12000, 'g': 9000, 'h': 9000, 'i': 5000, 'j': 5000}
    >>> B = 80000
    >>> ui = {
    ... '1': {'a': 1, 'b': 1, 'c': 1, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
    ... '2': {'a': 1, 'b': 1, 'c': 1, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
    ... '3': {'a': 1, 'b': 1, 'c': 0, 'd': 1, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
    ... '4': {'a': 1, 'b': 1, 'c': 0, 'd': 1, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
    ... '5': {'a': 1, 'b': 1, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
    ... '6': {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 1, 'f': 1, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
    ... '7': {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 1, 'h': 1, 'i': 0, 'j': 0},
    ... "8": {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 1, 'j': 1}
    ... }
    >>> result = BW_GCR_PB_from_lists(N, C, cost, B, ui)
    >>> abs(sum(p * cost[c] for p, c in zip(result, C)) - B) < 0.01
    True
    >>> all(0.0 <= p <= 1.0 for p in result)
    True

    Example 5: not covering all code lines:
    >>> N = ['1', '2', '3']
    >>> C = ['a', 'b', 'c']
    >>> cost = {'a': 5000, 'b': 5000, 'c': 6000}
    >>> B = 15000
    >>> ui = {
    ... '1': {'a': 1, 'b': 1, 'c': 1},
    ... '2': {'a': 1, 'b': 1, 'c': 1},
    ... '3': {'a': 1, 'b': 1, 'c': 0}
    ... }
    >>> BW_GCR_PB_from_lists(N, C, cost, B, ui)
    [1.0, 1.0, 0.8333333333333334]
    """
    instance = build_instance(C, cost, B)
    profile = build_profile(N, ui, instance)
    projects_sorted = sorted(instance, key=lambda p: p.name)
    probs = BW_GCR_PB(instance, profile)
    name_to_prob = {proj.name: prob for proj, prob in zip(projects_sorted, probs)}
    return [name_to_prob[c] for c in C]


# ---------------------------------------------------------------------------
# Algorithm 2: BW-MES-PB
# ---------------------------------------------------------------------------

def BW_MES_PB(instance: Instance, profile: AbstractProfile, analytics: bool = False) -> list:
    """
    Algorithm 2 (BW-MES-PB): ballot-weighted lottery backed by the Method of
    Equal Shares (MES).

    Satisfies strong UFS and Extended Justified Representation (EJR).

    Parameters
    ----------
    instance : Instance
        The PB instance (projects + budget limit).
    profile : AbstractProfile
        The voters' approval ballots.
    analytics : bool, optional
        Reserved for future use. Defaults to False.

    Returns
    -------
    list[float]
        Fractional probability for each project, sorted alphabetically by name.
    """
    n = profile.num_ballots()
    B = instance.budget_limit
    projects = sorted(instance, key=lambda p: p.name)
    ballots = list(profile)

    logger.info("BW_MES_PB: %d voters, %d projects, budget %f.", n, len(projects), B)

    # Line 1: run MES
    allocation = None
    try:
        allocation = method_of_equal_shares(
            instance, profile, sat_class=approval_sat, analytics=True
        )
        W: set = set(allocation)
        logger.info("MES selected %d projects.", len(W))
    except Exception as e:
        logger.error("MES failed: %s", e)
        W = set()

    # Line 2: initialize probability vector
    p_vec = {proj: (1.0 if proj in W else 0.0) for proj in projects}

    # Lines 3-4: remaining budget per voter after MES
    budget_per_voter = B / n
    remaining = {i: budget_per_voter for i in range(n)}

    if allocation is not None and allocation.details and allocation.details.iterations:
        for iteration in reversed(allocation.details.iterations):
            if iteration.selected_project is not None:
                for idx in range(n):
                    remaining[idx] = iteration.voters_budget_after_selection[idx]
                break

    # Line 5: N_prime — voters with budget who approve an unselected project
    N_prime = [
        i for i in range(n)
        if remaining[i] > 0 and any(proj not in W and proj in ballots[i] for proj in projects)
    ]
    logger.info("N_prime size: %d.", len(N_prime))

    # Lines 6-8: each N_prime voter spends on approved unselected projects
    for i in N_prime:
        liked = sorted(
            [proj for proj in projects if proj not in W and proj in ballots[i]],
            key=lambda proj: (proj.cost, proj.name)
        )
        for proj in liked:
            if remaining[i] <= 0:
                break
            needed = proj.cost * (1 - p_vec[proj])
            if needed <= 0:
                continue
            payment = min(remaining[i], needed)
            remaining[i] -= payment
            p_vec[proj] += payment / proj.cost

    # Lines 9-10: N_minus voters dump leftover on first unselected project
    N_prime_set = set(N_prime)
    N_minus = [i for i in range(n) if i not in N_prime_set]
    unselected = [proj for proj in projects if proj not in W]

    if unselected:
        first = unselected[0]
        total = sum(remaining[i] for i in N_minus)
        if total > 0:
            needed = first.cost * (1 - p_vec[first])
            if needed > 0:
                payment = min(total, needed)
                p_vec[first] += payment / first.cost
                for i in N_minus:
                    remaining[i] = 0

    # Line 11: normalize near-1 probabilities
    EPS = 1e-9
    for proj in projects:
        if p_vec[proj] >= 1 - EPS:
            p_vec[proj] = 1.0
            W.add(proj)

    logger.info("BW_MES_PB completed.")
    return [float(p_vec[proj]) for proj in projects]


def BW_MES_PB_from_lists(N: list, C: list, cost: dict, B: float, ui: dict) -> list:
    """
    Convenience wrapper for :func:`BW_MES_PB` that accepts raw lists and dicts.

    Parameters
    ----------
    N : list
        Voter identifiers.
    C : list
        Project identifiers.
    cost : dict
        Maps each project identifier to its cost.
    B : float
        Total available budget.
    ui : dict
        Maps each voter to a dict ``{project_id: 1/0}``.

    Returns
    -------
    list[float]
        Fractional probability for each project, in the same order as `C`.

    Examples
    --------
    Example 1: Enough budget for all projects:
    >>> N = ['1', '2']
    >>> C = ['a', 'b', 'c']
    >>> cost = {'a': 21000, 'b': 10000, 'c': 2000}
    >>> B = 33000
    >>> ui = {
    ... '1': {'a': 1, 'b': 1, 'c': 0},
    ... '2': {'a': 0, 'b': 1, 'c': 1}
    ... }
    >>> BW_MES_PB_from_lists(N, C, cost, B, ui)
    [1.0, 1.0, 1.0]

    Example 2: Different output for each algorithm:
    >>> N = ['1', '2', '3']
    >>> C = ['a', 'b', 'c', 'd']
    >>> cost = {'a': 8000, 'b': 8000, 'c': 12000, 'd': 12000}
    >>> B = 30000
    >>> ui = {
    ... '1': {'a': 1, 'b': 0, 'c': 1, 'd': 0},
    ... '2': {'a': 0, 'b': 0, 'c': 1, 'd': 1},
    ... '3': {'a': 0, 'b': 1, 'c': 0, 'd': 1}
    ... }
    >>> BW_MES_PB_from_lists(N, C, cost, B, ui)
    [0.5, 1.0, 1.0, 0.5]

    Example 3: tight budget:
    >>> N = ['1', '2', '3', '4']
    >>> C = ['a', 'b']
    >>> cost = {'a': 1000, 'b': 5000}
    >>> B = 5000
    >>> ui = {
    ... '1': {'a': 1, 'b': 1},
    ... '2': {'a': 0, 'b': 1},
    ... '3': {'a': 0, 'b': 1},
    ... '4': {'a': 0, 'b': 1}
    ... }
    >>> BW_MES_PB_from_lists(N, C, cost, B, ui)
    [1.0, 0.8]

    Example 4: many projects and voters:
    >>> N = ['1', '2', '3', '4', '5', '6', '7', '8']
    >>> C = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
    >>> cost = {'a': 8000, 'b': 15000, 'c': 10000, 'd': 10000, 'e': 6000, 'f': 12000, 'g': 9000, 'h': 9000, 'i': 5000, 'j': 5000}
    >>> B = 80000
    >>> ui = {
    ... '1': {'a': 1, 'b': 1, 'c': 1, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
    ... '2': {'a': 1, 'b': 1, 'c': 1, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
    ... '3': {'a': 1, 'b': 1, 'c': 0, 'd': 1, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
    ... '4': {'a': 1, 'b': 1, 'c': 0, 'd': 1, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
    ... '5': {'a': 1, 'b': 1, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
    ... '6': {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 1, 'f': 1, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
    ... '7': {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 1, 'h': 1, 'i': 0, 'j': 0},
    ... "8": {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 1, 'j': 1}
    ... }
    >>> BW_MES_PB_from_lists(N, C, cost, B, ui)
    [1.0, 1.0, 1.0, 1.0, 1.0, 0.9166666666666667, 1.0, 0.1111111111111111, 1.0, 1.0]
    """
    instance = build_instance(C, cost, B)
    profile = build_profile(N, ui, instance)
    projects_sorted = sorted(instance, key=lambda p: p.name)
    probs = BW_MES_PB(instance, profile)
    name_to_prob = {proj.name: prob for proj, prob in zip(projects_sorted, probs)}
    return [name_to_prob[c] for c in C]


# ---------------------------------------------------------------------------
# Wrapped entry points (validation + BB1 rounding)
# ---------------------------------------------------------------------------

def _generic_pb_wrapper(
    algo_func,
    instance: Instance,
    profile: AbstractProfile,
) -> tuple[list, list]:
    """
    Validate inputs, run the core algorithm, and apply BB1 dependent rounding.

    Parameters
    ----------
    algo_func : callable
        :func:`BW_GCR_PB` or :func:`BW_MES_PB`.
    instance : Instance
    profile : AbstractProfile

    Returns
    -------
    tuple[list[float], list[Project]]
        The fractional probability vector and the discrete project selection.

    Raises
    ------
    ValueError
        If any input is None, the wrong type, or empty.
    """
    logger.info("Starting wrapped execution for %s.", algo_func.__name__)

    if instance is None or profile is None:
        logger.critical("instance or profile is None.")
        raise ValueError("One or more of the parameters is null")

    if not isinstance(instance, Instance):
        logger.error("instance expected Instance, got %s.", type(instance))
        raise ValueError("Parameter instance is not of the expected type")
    if not isinstance(profile, AbstractProfile):
        logger.error("profile expected AbstractProfile, got %s.", type(profile))
        raise ValueError("Parameter profile is not of the expected type")

    if len(instance) == 0 or profile.num_ballots() == 0 or instance.budget_limit == 0:
        logger.critical("instance or profile is empty / budget is 0.")
        raise ValueError("One or more of the parameters is empty")

    p_vec = algo_func(instance, profile)
    projects = sorted(instance, key=lambda p: p.name)
    final_proj = dependent_rounding_bb1(p_vec, projects)

    logger.info("%s finished. Selected %d projects.", algo_func.__name__, len(final_proj))
    return p_vec, final_proj


def BW_GCR_PB_wrapped(instance: Instance, profile: AbstractProfile) -> tuple[list, list]:
    """
    Run :func:`BW_GCR_PB` with input validation and BB1 dependent rounding.

    Parameters
    ----------
    instance : Instance
    profile : AbstractProfile

    Returns
    -------
    tuple[list[float], list[Project]]
        Probability vector and discrete project selection.
    """
    return _generic_pb_wrapper(BW_GCR_PB, instance, profile)


def BW_MES_PB_wrapped(instance: Instance, profile: AbstractProfile) -> tuple[list, list]:
    """
    Run :func:`BW_MES_PB` with input validation and BB1 dependent rounding.

    Parameters
    ----------
    instance : Instance
    profile : AbstractProfile

    Returns
    -------
    tuple[list[float], list[Project]]
        Probability vector and discrete project selection.
    """
    return _generic_pb_wrapper(BW_MES_PB, instance, profile)
