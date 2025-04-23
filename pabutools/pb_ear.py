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
    Algorithm 1: PB-EAR — selects projects that satisfy Inclusion PSC (IPSC) under ordinal preferences and a budget constraint.

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
    >>> pb_ear(voters, candidates, budget)
    ['a', 'b', 'c']

    >>> # Example 2: PSC with unequal costs — each group gets projects they can afford
    >>> voters = (
    ...     [(1.0, ["a", "b", "c", "d"])] * 30 +
    ...     [(1.0, ["d", "c", "b", "a"])] * 70
    ... )
    >>> candidates = [("a", 40.0), ("b", 50.0), ("c", 30.0), ("d", 30.0)]
    >>> budget = 100.0
    >>> pb_ear(voters, candidates, budget)
    ['b', 'd', 'c']

    >>> # Example 3: Two sub-coalitions disagree on top choice, but deserve joint representation
    >>> voters = (
    ...     [(1.0, ["a", "b", "c", "d"])] * 15 +
    ...     [(1.0, ["b", "a", "c", "d"])] * 15 +
    ...     [(1.0, ["d", "c", "b", "a"])] * 70
    ... )
    >>> candidates = [("a", 50.0), ("b", 30.0), ("c", 30.0), ("d", 40.0)]
    >>> budget = 100.0
    >>> pb_ear(voters, candidates, budget)
    ['b', 'c', 'd']

    >>> # Example 4: Overlapping coalitions; best justified inclusion must be found
    >>> voters = (
    ...     [(1.0, ["a", "b", "c", "d"])] * 14 +
    ...     [(1.0, ["a", "c", "b", "d"])] * 16 +
    ...     [(1.0, ["c", "a", "b", "d"])] * 70
    ... )
    >>> candidates = [("a", 90.0), ("b", 30.0), ("c", 80.0), ("d", 40.0)]
    >>> budget = 100.0
    >>> pb_ear(voters, candidates, budget)
    ['a']

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
    >>> pb_ear(voters, candidates, budget)
    ['a', 'b', 'c']

    >>> # Example 7: Big group wants expensive project, but PB-EAR picks cheaper ones
    >>> voters = (
    ...     [(1.0, ["a", "b", "c", "d"])] * 7 +
    ...     [(1.0, ["d", "c", "b", "a"])] * 3
    ... )
    >>> candidates = [("a", 9.0), ("b", 1.0), ("c", 1.0), ("d", 1.0)]
    >>> budget = 10.0
    >>> pb_ear(voters, candidates, budget)
    ['b', 'd', 'c']

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
    >>> pb_ear(voters, candidates, budget)
    [a,c,g]


    """
    return []
