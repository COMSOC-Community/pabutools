"""
An implementation of the algorithms in "Streamlining Equal Shares",
by Sonja Kraiczy, Isaac Robinson, Edith Elkind (2024),
https://arxiv.org/abs/2502.11797

Programmer: Yonatan Gabay
Date: 20-04-2026
"""

from __future__ import annotations

from pabutools.election.instance import Instance, Project
from pabutools.election.profile import AbstractApprovalProfile
from pabutools.fractions import frac
from pabutools.rules.budgetallocation import BudgetAllocation, AllocationDetails
from pabutools.tiebreaking import lexico_tie_breaking
from pabutools.utils import Numeric


class EESAllocationDetails(AllocationDetails):
    """
    Details of an EES rule run, storing per-voter payments.

    Attributes
    ----------
        payments : dict[int, dict[Project, Numeric]]
            payments[voter_index][project] = amount paid by voter for the project.
    """

    def __init__(self, payments: dict[int, dict[Project, Numeric]] | None = None):
        super().__init__()
        self.payments: dict[int, dict[Project, Numeric]] = payments if payments is not None else {}

    def __repr__(self):
        return f"EESAllocationDetails[payments={self.payments}]"


def exact_equal_shares(
    instance: Instance,
    profile: AbstractApprovalProfile,
    utilities: dict[Project, Numeric] | None = None,
) -> BudgetAllocation:
    """
    Algorithm 1: EES for uniform utilities.

    Iteratively selects projects that maximise bang-per-buck (|V|·u(p)/cost(p))
    among all feasible (project, supporter-subset) pairs, splitting costs
    equally among supporters.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance containing the projects and the budget limit.
        profile : :py:class:`~pabutools.election.profile.approvalprofile.AbstractApprovalProfile`
            The approval profile, one ballot per voter.
        utilities : dict[:py:class:`~pabutools.election.instance.Project`, Numeric] or None
            utilities[project] = u(p). When None, every project has utility 1
            (pure approval setting).

    Returns
    -------
        :py:class:`~pabutools.rules.budgetallocation.BudgetAllocation`
            The selected projects (in order of selection). The
            :py:attr:`~pabutools.rules.budgetallocation.BudgetAllocation.details` attribute
            is an :py:class:`EESAllocationDetails` holding per-voter payments.

    Examples
    --------
    >>> from pabutools.election import Instance, Project, ApprovalProfile, ApprovalBallot
    >>> p1, p2, p3 = Project("p1", 10), Project("p2", 16), Project("p3", 21)
    >>> inst = Instance([p1, p2, p3], budget_limit=40)
    >>> prof = ApprovalProfile([
    ...     ApprovalBallot([p1]),
    ...     ApprovalBallot([p1, p3]),
    ...     ApprovalBallot([p2, p3]),
    ...     ApprovalBallot([p2, p3]),
    ... ], instance=inst)
    >>> result = exact_equal_shares(inst, prof)
    >>> [p.name for p in result]
    ['p1', 'p2']
    """
    n = len(profile)
    if n == 0:
        return BudgetAllocation(details=EESAllocationDetails())

    b = instance.budget_limit

    # Line 1: W = ∅, X = 0^{n·m}, r_i = b/n for all i ∈ N
    W: list[Project] = []
    selected_set: set[Project] = set()
    payments: dict[int, dict[Project, Numeric]] = {i: {} for i in range(n)}
    r: list[Numeric] = [frac(b) / n] * n

    # Maintain a globally sorted list of voters by remaining budget.
    # Filtering this list to a project's supporters preserves sorted order
    # in O(n), avoiding an O(n log n) sort per project per iteration.
    sorted_voters: list[int] = list(range(n))  # all equal initially

    # Line 2: while true do
    while True:
        best_score: Numeric = -1
        best_candidates: list[tuple[Project, list[int]]] = []

        # Line 3: Φ = {(p ∈ P\W, V ⊆ N_p) | r_i ≥ cost(p)/|V|  ∀i ∈ V}
        # For each project, find the largest feasible supporter subset V.
        for p in instance:
            if p in selected_set:
                continue

            u_p = utilities[p] if utilities is not None else 1

            # N_p: voters who approve p, filtered from sorted_voters (preserves order)
            supporters = [i for i in sorted_voters if p in profile[i]]
            if not supporters:
                continue

            # Greedily remove the poorest voter while they can't afford
            # their equal share cost(p)/|V|.
            while supporters and r[supporters[0]] < frac(p.cost) / len(supporters):
                supporters.pop(0)

            if not supporters:
                continue

            # Line 8: score = |V|·u(p) / cost(p)
            if p.cost == 0:
                score = float('inf')
            else:
                score = frac(len(supporters) * u_p) / p.cost
            if score > best_score:
                best_score = score
                best_candidates = [(p, supporters)]
            elif score == best_score:
                best_candidates.append((p, supporters))

        # Line 4-5: if Φ = ∅ then return (W, X)
        if not best_candidates:
            return BudgetAllocation(W, details=EESAllocationDetails(payments))

        # Line 9: Choose (p*, V*) from Φ* using tiebreaking (p* ◁ p)
        # Use untie() (first/smallest name) so that unselected tied projects
        # have larger names.  The leximax (amount, selected_name) will then
        # NOT exceed (amount, unselected_name) under Python's default tuple
        # comparison, preventing spurious instability certificates.
        if len(best_candidates) == 1:
            p_star, V_star = best_candidates[0]
        else:
            tied_projects = [p for p, _ in best_candidates]
            p_star = lexico_tie_breaking.untie(instance, profile, tied_projects)
            V_star = next(V for p, V in best_candidates if p == p_star)

        # Line 10: W = W ∪ {p*}
        W.append(p_star)
        selected_set.add(p_star)

        # Line 11: x_{i,p*} = cost(p*)/|V*|, r_i = r_i − cost(p*)/|V*|  ∀i ∈ V*
        V_star_set = set(V_star)
        payment = frac(p_star.cost) / len(V_star)
        for i in V_star:
            payments[i][p_star] = payment
            r[i] -= payment

        # Update sorted_voters via O(n) merge.  All V* voters decreased by
        # the same amount so their relative order is preserved.
        changed = [i for i in sorted_voters if i in V_star_set]
        unchanged = [i for i in sorted_voters if i not in V_star_set]
        merged: list[int] = []
        ci, ui = 0, 0
        while ci < len(changed) and ui < len(unchanged):
            if r[changed[ci]] <= r[unchanged[ui]]:
                merged.append(changed[ci]); ci += 1
            else:
                merged.append(unchanged[ui]); ui += 1
        merged.extend(changed[ci:])
        merged.extend(unchanged[ui:])
        sorted_voters = merged


def get_leftover_budgets(
    instance: Instance,
    profile: AbstractApprovalProfile,
    current_solution: BudgetAllocation,
) -> dict[int, Numeric]:
    """
    Compute leftover budget for each voter.

    leftover[i] = b/n - sum of payments by voter i across all selected projects.
    """
    n = len(profile)
    b = instance.budget_limit
    details: EESAllocationDetails = current_solution.details
    leftover = {}
    for i in range(n):
        paid = sum(details.payments.get(i, {}).values())
        leftover[i] = frac(b) / n - paid
    return leftover


def get_leximax_payment(
    current_solution: BudgetAllocation,
    voter: int,
    instance: Instance,
) -> tuple[Numeric, str]:
    """
    Return the leximax payment of a voter as ``(amount, project_name)``.

    The leximax payment c_i = (x_i, p_i) where x_i is the maximum payment
    and p_i is the project with that payment that comes first in the total
    order ⊲ (alphabetical by name, i.e. smallest name).  When the voter
    made no payments, x_i = 0 and p_i is the first project in ⊲
    (smallest name), so that non-paying voters never certify instability.
    """
    details: EESAllocationDetails = current_solution.details
    voter_payments = details.payments.get(voter, {})
    if not voter_payments:
        min_project_name = min(p.name for p in instance)
        return (0, min_project_name)
    max_amount = max(voter_payments.values())
    max_projects = [p for p, v in voter_payments.items() if v == max_amount]
    min_project = min(max_projects, key=lambda p: p.name)
    return (max_amount, min_project.name)


def greedy_project_change(
    instance: Instance,
    profile: AbstractApprovalProfile,
    current_solution: BudgetAllocation,
    project: Project,
    leftover: dict[int, Numeric],
    leximax: dict[int, tuple[Numeric, str]],
    voters_by_leftover: list[int] | None = None,
    voters_by_leximax: list[int] | None = None,
) -> Numeric:
    """
    Algorithm 2: GreedyProjectChange (GPC).

    Computes the minimum per-voter budget increase d > 0 such that
    *project* certifies instability of the current equal-shares solution
    for instance E(b + n·d).
    The algorithm walks two sorted arrays simultaneously:
    - leftover_budgets  (A'): residual budgets of Op(X) voters, sorted ascending.
    - leximax_payments   (B'): leximax payment vectors of Op(X) voters,
      sorted lex-ascending.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance containing the projects and the budget limit.
        profile : :py:class:`~pabutools.election.profile.approvalprofile.AbstractApprovalProfile`
            The approval profile, one ballot per voter.
        current_solution : :py:class:`~pabutools.rules.budgetallocation.BudgetAllocation`
            The current EES solution. Its
            :py:attr:`~pabutools.rules.budgetallocation.BudgetAllocation.details` attribute
            must be an :py:class:`EESAllocationDetails` holding per-voter payments.
        project : :py:class:`~pabutools.election.instance.Project`
            The candidate project p to test instability for.
        leftover : dict[int, Numeric]
            Leftover budget per voter, as returned by
            :py:func:`get_leftover_budgets`.
        leximax : dict[int, tuple[Numeric, str]]
            Leximax payment per voter, as returned by
            :py:func:`get_leximax_payment`.
        voters_by_leftover : list[int] or None
            All voters pre-sorted by leftover ascending.  When provided the
            function filters this list to O_p(X) in O(n) instead of sorting
            per project.  Used by :py:func:`add_opt` for O(mn) total.
        voters_by_leximax : list[int] or None
            All voters pre-sorted by leximax ascending.

    Returns
    -------
        Numeric
            Minimum per-voter budget increase d.

    Examples
    --------
    >>> from pabutools.election import Instance, Project, ApprovalProfile, ApprovalBallot
    >>> p1, p2, p3 = Project("p1", 2), Project("p2", 3.2), Project("p3", 6)
    >>> inst = Instance([p1, p2, p3], budget_limit=10)
    >>> prof = ApprovalProfile([
    ...     ApprovalBallot([p1]),
    ...     ApprovalBallot([p1, p3]),
    ...     ApprovalBallot([p2, p3]),
    ...     ApprovalBallot([p2, p3]),
    ...     ApprovalBallot([p3]),
    ... ], instance=inst)
    >>> details = EESAllocationDetails({0: {p1: 1}, 1: {p1: 1}, 2: {p2: 1.6}, 3: {p2: 1.6}, 4: {}})
    >>> solution = BudgetAllocation([p1, p2], details=details)
    >>> leftover = get_leftover_budgets(inst, prof, solution)
    >>> leximax = {i: get_leximax_payment(solution, i, inst) for i in range(5)}
    >>> greedy_project_change(inst, prof, solution, p3, leftover, leximax)
    0.5
    """
    n = len(profile)
    p = project

    # All voters who approve p
    all_supporters = {i for i in range(n) if p in profile[i]}

    # N_p(X): voters who pay for project p in the current solution
    details: EESAllocationDetails = current_solution.details
    N_p_X = {i for i in all_supporters if p in details.payments.get(i, {})}
    # O_p(X) = N_p \ N_p(X): voters who approve p but don't pay for it
    O_p_X = all_supporters - N_p_X

    # O_p(X) sorted by leftover budget ascending: v_1, ..., v_k
    if voters_by_leftover is not None:
        O_p = [i for i in voters_by_leftover if i in O_p_X]
    else:
        O_p = sorted(O_p_X, key=lambda i: leftover[i])
    k = len(O_p)

    # Leximax payments of O_p(X) voters, sorted ascending: w_1, ..., w_k
    if voters_by_leximax is not None:
        O_p_by_leximax = [i for i in voters_by_leximax if i in O_p_X]
    else:
        O_p_by_leximax = sorted(O_p_X, key=lambda i: leximax[i])

    # Line 1: i, j ← 1, 1 (1-indexed in paper, 0-indexed here)
    i = 0
    j = 0

    # Line 2-3: SL ← ∅, LQ ← O_p(X)
    SL: set[int] = set()
    LQ: set[int] = set(O_p)

    # Line 4: d ← +∞
    d = float('inf')

    # Line 5: while LQ ∪ SL ≠ ∅
    while LQ or SL:
        # Line 6: PvP ← cost(p) / |N_p(X) ∪ LQ ∪ SL|
        B = N_p_X | LQ | SL
        PvP = frac(p.cost) / len(B)

        pvp_lex = (PvP, p.name)

        # Line 7: if j ≤ |O_p(X)| and c_{w_j} <_lex (PvP, p)
        if j < k and leximax[O_p_by_leximax[j]] < pvp_lex:
            # Line 8: SL ← SL \ {w_j}
            SL.discard(O_p_by_leximax[j])
            # Line 9: j ← j + 1
            j += 1
        # Line 10: else if c_{v_i} >_lex (PvP, p)
        elif i < k and leximax[O_p[i]] > pvp_lex:
            # Line 11: LQ ← LQ \ {v_i}
            LQ.discard(O_p[i])
            # Line 12: SL ← SL ∪ {v_i}
            SL.add(O_p[i])
            # Line 13: i ← i + 1
            i += 1
        else:
            # Line 14-15: d ← min{d, PvP - r_{v_i}}
            if i < k:
                d = min(d, PvP - leftover[O_p[i]])
            # Line 16: LQ ← LQ \ {v_i}
            if i < k:
                LQ.discard(O_p[i])
            # Line 17: i ← i + 1
            i += 1

    # Line 20: return d
    return max(0, d)


def add_opt(
    instance: Instance,
    profile: AbstractApprovalProfile,
    current_solution: BudgetAllocation,
) -> Numeric:
    """
    Algorithm 3: add-opt.

    Iterates over every project p in the instance, restricts the sorted
    leftover-budget and leximax-payment arrays to the voters in Op(X), and
    calls GreedyProjectChange to find the minimum per-voter budget increase
    that makes p certify instability. Returns the global minimum.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance containing the projects and the budget limit.
        profile : :py:class:`~pabutools.election.profile.approvalprofile.AbstractApprovalProfile`
            The approval profile, one ballot per voter.
        current_solution : :py:class:`~pabutools.rules.budgetallocation.BudgetAllocation`
            The current EES solution. Its
            :py:attr:`~pabutools.rules.budgetallocation.BudgetAllocation.details` attribute
            must be an :py:class:`EESAllocationDetails` holding per-voter payments.

    Returns
    -------
        Numeric
            Minimum per-voter budget increase d > 0 such that the current
            solution is unstable for E(b + n·d). Returns ``float('inf')``
            when the solution is stable for every finite budget increase.

    Examples
    --------
    >>> from pabutools.election import Instance, Project, ApprovalProfile, ApprovalBallot
    >>> p1, p2, p3 = Project("p1", 2), Project("p2", 3.2), Project("p3", 6)
    >>> inst = Instance([p1, p2, p3], budget_limit=10)
    >>> prof = ApprovalProfile([
    ...     ApprovalBallot([p1]),
    ...     ApprovalBallot([p1, p3]),
    ...     ApprovalBallot([p2, p3]),
    ...     ApprovalBallot([p2, p3]),
    ...     ApprovalBallot([p3]),
    ... ], instance=inst)
    >>> details = EESAllocationDetails({0: {p1: 1}, 1: {p1: 1}, 2: {p2: 1.6}, 3: {p2: 1.6}, 4: {}})
    >>> solution = BudgetAllocation([p1, p2], details=details)
    >>> add_opt(inst, prof, solution)
    0.5
    """
    n = len(profile)

    # Precompute leftover budgets and leximax payments for all voters
    leftover = get_leftover_budgets(instance, profile, current_solution)
    leximax = {i: get_leximax_payment(current_solution, i, instance) for i in range(n)}

    # Pre-sort all voters once (Algorithm 3, lines A and B)
    voters_by_leftover = sorted(range(n), key=lambda i: leftover[i])
    voters_by_leximax = sorted(range(n), key=lambda i: leximax[i])

    # Line 1: d ← +∞
    d = float('inf')

    # Line 2: for p ∈ P do
    for p in instance:
        # Line 5: d ← min{d, GreedyProjectChange(E, (W, X), p, A', B')}
        d = min(d, greedy_project_change(
            instance, profile, current_solution, p, leftover, leximax,
            voters_by_leftover, voters_by_leximax,
        ))

    # Line 7: return d
    return d


def ees_completion(
    instance: Instance,
    profile: AbstractApprovalProfile,
    utilities: dict[Project, Numeric] | None = None,
) -> BudgetAllocation:
    """
    Completion of EES via add-opt (§4.2, Corollary 4.7).

    Iteratively runs EES with increasing virtual per-voter budgets until
    the outcome is exhaustive (no project can certify instability).
    Returns the budget-feasible outcome with the highest total spending.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance containing the projects and the budget limit.
        profile : :py:class:`~pabutools.election.profile.approvalprofile.AbstractApprovalProfile`
            The approval profile, one ballot per voter.
        utilities : dict[:py:class:`~pabutools.election.instance.Project`, Numeric] or None
            utilities[project] = u(p). When None, every project has utility 1
            (pure approval setting).

    Returns
    -------
        :py:class:`~pabutools.rules.budgetallocation.BudgetAllocation`
            The completed EES outcome — a feasible outcome whose total cost
            is at most ``instance.budget_limit``.

    Examples
    --------
    >>> from pabutools.election import Instance, Project, ApprovalProfile, ApprovalBallot
    >>> p1, p2, p3 = Project("p1", 2), Project("p2", 3.2), Project("p3", 6)
    >>> inst = Instance([p1, p2, p3], budget_limit=10)
    >>> prof = ApprovalProfile([
    ...     ApprovalBallot([p1]),
    ...     ApprovalBallot([p1, p3]),
    ...     ApprovalBallot([p2, p3]),
    ...     ApprovalBallot([p2, p3]),
    ...     ApprovalBallot([p3]),
    ... ], instance=inst)
    >>> result = ees_completion(inst, prof)
    >>> sorted(p.name for p in result)
    ['p1', 'p3']
    """
    n = len(profile)
    if n == 0:
        return exact_equal_shares(instance, profile, utilities)

    original_budget = instance.budget_limit
    budget = frac(original_budget)
    projects = list(instance)
    best: BudgetAllocation | None = None
    best_cost = frac(-1)

    while True:
        virtual_inst = Instance(projects, budget_limit=budget)
        result = exact_equal_shares(virtual_inst, profile, utilities)

        total_cost = sum(frac(p.cost) for p in result)
        if total_cost <= original_budget and total_cost > best_cost:
            best = result
            best_cost = total_cost

        d = add_opt(virtual_inst, profile, result)
        if d == float('inf') or d <= 0:
            break

        budget = budget + n * frac(d)

    if best is None:
        best = exact_equal_shares(instance, profile, utilities)
    return best
