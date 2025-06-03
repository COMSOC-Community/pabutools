import logging
from collections import defaultdict
from pabutools.utils_formatting import format_table
from datetime import datetime
import os
from pabutools.logging_config import logger
from itertools import combinations
from typing import List, Tuple, Set


"""
An implementation of the PB-EAR algorithm from:

"Proportionally Representative Participatory Budgeting with Ordinal Preferences",
Haris Aziz and Barton E. Lee (2020),
https://arxiv.org/abs/1911.00864v2

Programmer: Vivian Umansky
Date: 2025-04-23
"""

def pb_ear(voters: list[tuple[float, list[str]]], candidates: list[tuple[str, float]], budget: float) -> list[str]:
    """
    Algorithm : PB-EAR — selects projects that satisfy Inclusion PSC (IPSC) under ordinal preferences and a budget constraint.

    This algorithm takes into account voters with weights and computes a selection of projects
    that guarantees proportional representation for solid coalitions based on their weight.

    Parameters
    ----------
    voters : list of (float, list of str)
        A list where each item is a tuple: (voter_weight, ranked_preferences).
        Each ranked_preferences is a list of project names ordered by preference.
    candidates : list of tuple of (str, float)
        Each tuple represents a candidate project and its cost: (project_name, cost).
    budget : float
        The total available budget.

    Returns
    -------
    list of str
        A list of selected project names, such that their combined cost is within the budget
        and the outcome satisfies the IPSC criterion for fair representation.

    Examples
    --------
    >>> # Example 1: Solid coalition of 9 voters prefers a, b, c; budget allows 3 projects
    >>> voters = [
    ...     (1.0, ["a", "b", "c", "d"]), (1.0, ["a", "b", "c", "d"]), (1.0, ["a", "b", "c", "d"]),
    ...     (1.0, ["a", "b", "c", "d"]), (1.0, ["a", "b", "c", "d"]), (1.0, ["a", "b", "c", "d"]),
    ...     (1.0, ["d", "c", "b", "a"]), (1.0, ["d", "c", "b", "a"]),
    ...     (1.0, ["c", "a", "b", "d"])
    ... ]
    >>> candidates = [("a", 1.0), ("b", 1.0), ("c", 1.0), ("d", 1.0)]
    >>> budget = 3.0
    >>> sorted(pb_ear(voters, candidates, budget))
    ['a', 'b', 'c']


    >>> # Example 2: PSC with unequal costs — each group gets projects they can afford
    >>> voters = (
    ...     [(1.0, ["a", "b", "c", "d"])] * 30 +
    ...     [(1.0, ["d", "c", "b", "a"])] * 70
    ... )
    >>> candidates = [("a", 50.0), ("b", 30.0), ("c", 30.0), ("d", 40.0)]
    >>> budget = 100.0
    >>> sorted(pb_ear(voters, candidates, budget)) == sorted(['b', 'c', 'd'])
    True



    >>> # Example 3: Two sub-coalitions disagree on top choice, but deserve joint representation
    >>> voters = (
    ...     [(1.0, ["a", "b", "c", "d"])] * 15 +
    ...     [(1.0, ["b", "a", "c", "d"])] * 15 +
    ...     [(1.0, ["d", "c", "b", "a"])] * 70
    ... )
    >>> candidates = [("a", 50.0), ("b", 30.0), ("c", 30.0), ("d", 40.0)]
    >>> budget = 100.0
    >>> sorted(pb_ear(voters, candidates, budget))
    ['b', 'c', 'd']

    >>> # Example 4: Overlapping coalitions; best justified inclusion must be found
    >>> voters = (
    ...     [(1.0, ["a", "b", "c", "d"])] * 14 +
    ...     [(1.0, ["a", "c", "b", "d"])] * 16 +
    ...     [(1.0, ["c", "a", "b", "d"])] * 70
    ... )
    >>> candidates = [("a", 90.0), ("b", 30.0), ("c", 80.0), ("d", 40.0)]
    >>> budget = 100.0
    >>> sorted(pb_ear(voters, candidates, budget)) in [['a'], ['c']]
    True


    >>> # Example 5: Single voter — no fair solution under CPSC
    >>> voters = [(1.0, ["a", "b", "c", "d"])]
    >>> candidates = [("a", 3.0), ("b", 2.0), ("c", 2.0), ("d", 2.0)]
    >>> budget = 4.0
    >>> pb_ear(voters, candidates, budget)
    ['a']

    >>> # Example 6: Perfect IPSC — 3 balanced groups and 3 projects
    >>> voters = (
    ...     [(1.0, ["a", "b", "c", "d"])] * 2 +
    ...     [(1.0, ["b", "a", "c", "d"])] * 2 +
    ...     [(1.0, ["c", "d", "a", "b"])] * 2
    ... )
    >>> candidates = [("a", 1.0), ("b", 1.0), ("c", 1.0), ("d", 1.0)]
    >>> budget = 3.0
    >>> sorted(pb_ear(voters, candidates, budget))
    ['a', 'b', 'c']

    >>> # Example 7: Big group wants expensive project, but PB-EAR picks cheaper ones
    >>> voters = (
    ...     [(1.0, ["a", "b", "c", "d"])] * 7 +
    ...     [(1.0, ["d", "c", "b", "a"])] * 3
    ... )
    >>> candidates = [("a", 9.0), ("b", 1.0), ("c", 1.0), ("d", 1.0)]
    >>> budget = 10.0
    >>> sorted(pb_ear(voters, candidates, budget)) == ['b', 'c', 'd']
    True

    >>> # Example 8: Complex weights and long preferences
    >>> voters = [
    ...     (0.5, ["a", "b", "c", "d", "e", "f", "g"]),
    ...     (1.5, ["a", "c", "d", "e", "b", "g", "f"]),
    ...     (1.0, ["a", "d", "b", "c", "e", "f", "g"]),
    ...     (1.0, ["b", "c", "d", "e", "a", "g", "f"]),
    ...     (0.8, ["b", "c", "e", "d", "g", "a", "f"]),
    ...     (1.2, ["c", "d", "e", "b", "g", "a", "f"]),
    ...     (1.0, ["d", "e", "f", "c", "g", "b", "a"])
    ... ]
    >>> candidates = [
    ...     ("a", 50.0), ("b", 40.0), ("c", 35.0), ("d", 30.0),
    ...     ("e", 20.0), ("f", 15.0), ("g", 10.0)
    ... ]
    >>> budget = 100.0
    >>> sorted(pb_ear(voters, candidates, budget)) in [['c', 'd', 'e', 'f'], ['c', 'd', 'e', 'g']]
    True



    """
    j = 1
    selected_projects = set()
    remaining_budget = budget
    voter_weights = {i: weight for i, (weight, _) in enumerate(voters)}
    initial_n = sum(w for w, _ in voters)
    project_cost = dict(candidates)
    all_projects = set(project_cost)


    logger.info("=" * 30 + f" NEW RUN: PB-EAR on {datetime.now().strftime('%Y-%m-%d')} " + "=" * 30)
    logger.debug("Number of voters = %d budget=%.2f", initial_n, budget)

    while True:
        # Step 2: Determine available projects that fit within the remaining budget
        available_projects = [p for p in all_projects - selected_projects if project_cost[p] <= remaining_budget]
        logger.debug("Step j=%d — available_projects=%s, remaining_budget=%.2f", j, available_projects, remaining_budget)

        if not available_projects:
            logger.debug("No more projects can be added without exceeding the budget.")
            break

        # Step 3–4: Construct A_i^(j) for each voter – top j preferences
        approvals = defaultdict(set)
        for i, (_, prefs) in enumerate(voters):
            if j <= len(prefs):
                threshold = prefs[j - 1]
                rank_threshold = prefs.index(threshold)
                approvals[i] = set(prefs[:rank_threshold + 1])
            else:
                approvals[i] = set(prefs)

        # Step 5: Compute candidate support across all voters
        candidate_support = defaultdict(float)
        for i, approved_set in approvals.items():
            for p in approved_set:
                if p not in selected_projects:
                    candidate_support[p] += voter_weights[i]

        # Log support table (for transparency)
        table = [(p, f"{candidate_support[p]:.2f}", f"{project_cost[p]:.2f}", f"{(initial_n * project_cost[p]) / budget:.2f}")
                 for p in available_projects]
        headers = ["Project", "Support", "Cost", "Threshold"]
        logger.debug("\n%s", format_table(headers, table))

        # Step 6: Identify candidates that meet the threshold
        C_star = {
            c for c in available_projects
            if round(candidate_support[c], 6) >= round((initial_n * project_cost[c]) / budget, 6)
        }

        logger.debug("Step j=%d — selected_candidates_meeting_threshold (C*) = %s", j, sorted(C_star))

        # Step 7–8: If no candidate qualifies, expand j and retry
        if not C_star:
            if j > max(len(prefs) for _, prefs in voters):
                logger.info("No candidates meet support threshold and no further preferences left j=%d", j)
                break
            logger.info("No candidates meet support threshold at j=%d, increasing j", j)
            j += 1
            continue

        # Step 9–10: Select one candidate from C*
        c_star = next(iter(C_star))
        selected_projects.add(c_star)
        remaining_budget -= project_cost[c_star]
        logger.info("Selected candidate: %s | cost=%.2f | remaining_budget=%.2f", c_star, project_cost[c_star], remaining_budget)

        # Step 11–12: Reduce total weight from voters approving c_star by exactly (n * cost / budget)
        N_prime = [i for i in range(len(voters)) if c_star in approvals[i]]
        total_weight_to_reduce = (initial_n * project_cost[c_star]) / budget

        if N_prime:
            sum_supporters = sum(voter_weights[i] for i in N_prime)
            weight_fraction = total_weight_to_reduce / sum_supporters if sum_supporters > 0 else 0
            for i in N_prime:
                old_weight = voter_weights[i]
                voter_weights[i] = voter_weights[i] * (1 - weight_fraction)
                logger.debug("Reducing weight for voter index=%d — old_weight=%.4f new_weight=%.4f", i, old_weight, voter_weights[i])

    logger.info("Final selected projects: %s (total=%d)", sorted(selected_projects), len(selected_projects))
    return list(selected_projects)

def is_solidly_supported(prefs: List[str], group: Set[str]) -> bool:
    """
    Check whether the given voter preferences weakly rank all projects in `group`
    above any project not in the group.

    Parameters
    ----------
    prefs : list of str
        A list of project names in order of the voter's preference (most preferred first).
    group : set of str
        A set of project names forming a candidate coalition.

    Returns
    -------
    bool
        True if the voter weakly prefers all projects in `group` over any project not in `group`.
        False otherwise.

    Examples
    --------

    >>> is_solidly_supported(['a', 'b', 'c', 'd'], {'a', 'b'})
    True
    >>> is_solidly_supported(['a', 'b', 'c', 'd'], {'b', 'd'})
    False
    """
    other_projects = set(prefs) - group
    for c in group:
        for d in other_projects:
            if prefs.index(c) > prefs.index(d):
                return False
    return True

def calculate_group_weight(voters: List[Tuple[float, List[str]]], group: Set[str]) -> float:
    """
    Calculate the total weight of voters who solidly support a given project group.

    Parameters
    ----------
    voters : list of tuples
        Each tuple is (weight, preference_list), where preference_list is a ranking of projects.
    group : set of str
        A group of projects to test for solid support.

    Returns
    -------
    float
        The sum of weights of voters who solidly support the group.

    Examples
    --------

    >>> calculate_group_weight([(1.0, ['a', 'b', 'c']), (2.0, ['c', 'b', 'a'])], {'a', 'b'})
    1.0
    """
    return sum(w for w, prefs in voters if is_solidly_supported(prefs, group))

def calculate_periphery(voters: List[Tuple[float, List[str]]], group: Set[str], all_projects: List[str]) -> Set[str]:
    """
    Get all the top ranked projects (according to each voter) that are as good or better than the worst project in the group.
    Parameters
    ----------
    voters : list of tuples
        A list of (weight, preference list) for each voter. Only voters supporting the group are used.
    group : set of str
        The set of projects for which we compute the periphery.
    all_projects : list of str
        The full set of project names.

    Returns
    -------
    set of str
        Projects that appear in the prefix of any voter's preferences up to the worst-ranked project in group.

    Examples
    --------

    >>> calculate_periphery([(1.0, ['a', 'b', 'c'])], {'a', 'b'}, ['a', 'b', 'c']) == {'a', 'b'}
    True

    >>> calculate_periphery([(1.0, ['a', 'b', 'c'])], {'b'}, ['a', 'b', 'c']) == {'a', 'b'}
    True

    """
    periphery = set()
    for _, prefs in voters:
        try:
            highest_index = max(prefs.index(x) for x in group)
            periphery.update(prefs[:highest_index + 1])
        except ValueError:
            continue
    return periphery

def assert_IPSC_satisfied(
    voters: List[Tuple[float, List[str]]],
    candidates: List[Tuple[str, float]],
    budget: float,
    result: List[str],
    max_group_size: int = 10,
):
    """
    Asserts that the output result satisfies the IPSC axiom
    from the PB-EAR paper, using group sizes up to max_group_size.

    Raises AssertionError if a violating group is found.

    >>> voters = [(1, ['a', 'b']), (1, ['a', 'b']), (1, ['b', 'a'])]
    >>> candidates = [('a', 2), ('b', 1)]
    >>> budget = 2
    >>> result = ['b']
    >>> assert_IPSC_satisfied(voters, candidates, budget, result)


    >>> voters = [(1, ['a', 'b']), (1, ['a', 'b']), (1, ['b', 'a'])]
    >>> candidates = [('a', 1), ('b', 1)]
    >>> budget = 2
    >>> result = ['b']
    >>> assert_IPSC_satisfied(voters, candidates, budget, result)
    Traceback (most recent call last):
        ...
    AssertionError: IPSC violation: group {'a'}, candidate a could be afforded ...
    """
    project_names = [name for name, _ in candidates]
    project_cost = dict(candidates)
    total_weight = sum(w for w, _ in voters)
    result_set = set(result)

    for r in range(1, max_group_size + 1):
        for group_tuple in combinations(project_names, r):
            group = set(group_tuple)

            supporting_voters = [(w, prefs) for (w, prefs) in voters if is_solidly_supported(prefs, group)]
            if not supporting_voters:
                continue

            group_weight = calculate_group_weight(voters, group)
            rel_budget = group_weight * budget / total_weight

            periphery = calculate_periphery(supporting_voters, group, project_names)
            selected_from_periphery = periphery & result_set
            selected_cost = sum(project_cost[c] for c in selected_from_periphery)

            for c in group:
                if c not in result_set:
                    added_cost = project_cost[c]
                    total_if_added = selected_cost + added_cost
                    if total_if_added <= rel_budget:
                        raise AssertionError(
                            f"IPSC violation: group {group}, candidate {c} "
                            f"could be afforded (selected_cost={selected_cost:.2f}, "
                            f"c_cost={added_cost:.2f}, rel_budget={rel_budget:.2f})"
                        )
                    
if __name__ == "__main__":
    # Example demo run
    voters = [
        (1.0, ["a", "b", "c", "d"]),
        (1.0, ["b", "a", "c", "d"]),
        (1.0, ["c", "b", "a", "d"]),
        (1.0, ["a", "c", "b", "d"]),
    ]
    candidates = [
        ("a", 30.0),
        ("b", 25.0),
        ("c", 20.0),
        ("d", 50.0),
    ]
    budget = 60.0

    logger.info("===== Manual demo run (from __main__) =====")
    result = pb_ear(voters, candidates, budget)
    logger.info("Selected projects: %s", result)


