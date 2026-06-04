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
        if payments is not None:
            self.payments = payments
        else:
            self.payments = {}

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

    # Line 1: Start with no selected projects and equal voter budgets.
    selected_projects = []
    payments = {}
    for i in range(n):
        payments[i] = {}
    initial_budget_per_voter = frac(b) / n
    remaining_budgets = []
    for i in range(n):
        remaining_budgets.append(initial_budget_per_voter)

    # Keep voters sorted by remaining budget for fast supporter filtering.
    voters_by_remaining_budget = list(range(n))  # all equal initially

    # Line 2: Keep selecting projects until none are feasible.
    while True:
        best_score = -1
        best_candidates = []

        # Line 3: Consider each unselected project with supporters who can afford it.
        # For each project, find the largest feasible supporter subset V.
        selected_set = set(selected_projects)
        for project in instance:
            if project in selected_set:
                continue

            if utilities is not None:
                project_utility = utilities[project]
            else:
                project_utility = 1

            # N_p: voters who approve project, preserving remaining-budget order.
            supporters = []
            for i in voters_by_remaining_budget:
                if project in profile[i]:
                    supporters.append(i)
            if not supporters:
                continue

            # Greedily remove the poorest voter while they can't afford
            # their equal share cost(p)/|V|.
            while supporters and remaining_budgets[supporters[0]] < frac(project.cost) / len(supporters):
                supporters.pop(0)

            if not supporters:
                continue

            # Line 8: Score the project by utility per unit of cost.
            if project.cost == 0:
                bang_per_buck = float('inf')
            else:
                bang_per_buck = frac(len(supporters) * project_utility) / project.cost
            if bang_per_buck > best_score:
                best_score = bang_per_buck
                best_candidates = [(project, supporters)]
            elif bang_per_buck == best_score:
                best_candidates.append((project, supporters))

        # Line 4-5: Return the current allocation if no feasible project remains.
        if not best_candidates:
            return BudgetAllocation(selected_projects, details=EESAllocationDetails(payments))

        # Line 9: Break ties among the best feasible projects.
        # Choose the lexicographically first tied project to keep ties stable.
        if len(best_candidates) == 1:
            chosen_project, chosen_supporters = best_candidates[0]
        else:
            tied_projects = []
            for candidate_project, _ in best_candidates:
                tied_projects.append(candidate_project)
            chosen_project = lexico_tie_breaking.untie(instance, profile, tied_projects)
            chosen_supporters = None
            for candidate_project, candidate_supporters in best_candidates:
                if candidate_project == chosen_project:
                    chosen_supporters = candidate_supporters
                    break

        # Line 10: Add the chosen project to the allocation.
        selected_projects.append(chosen_project)

        # Line 11: Charge each chosen supporter an equal share of the project cost.
        chosen_supporters_set = set(chosen_supporters)
        payment = frac(chosen_project.cost) / len(chosen_supporters)
        for i in chosen_supporters:
            payments[i][chosen_project] = payment
            remaining_budgets[i] -= payment

        # Update voters_by_remaining_budget via O(n) merge.  All V* voters decreased by
        # the same amount so their relative order is preserved.
        changed = []
        unchanged = []
        for i in voters_by_remaining_budget:
            if i in chosen_supporters_set:
                changed.append(i)
            else:
                unchanged.append(i)
        merged = []
        ci = 0
        ui = 0
        while ci < len(changed) and ui < len(unchanged):
            if remaining_budgets[changed[ci]] <= remaining_budgets[unchanged[ui]]:
                merged.append(changed[ci])
                ci += 1
            else:
                merged.append(unchanged[ui])
                ui += 1
        merged.extend(changed[ci:])
        merged.extend(unchanged[ui:])
        voters_by_remaining_budget = merged


def get_leftover_budgets(
    instance: Instance,
    profile: AbstractApprovalProfile,
    current_solution: BudgetAllocation,
) -> dict[int, Numeric]:
    """
    Compute leftover budget for each voter.

    leftover[i] = b/n - sum of payments by voter i across all selected projects.
    """
    num_voters = len(profile)
    budget_limit = instance.budget_limit
    allocation_details = current_solution.details
    leftover_budgets = {}

    for voter in range(num_voters):
        total_paid = 0
        voter_payments = allocation_details.payments.get(voter, {})
        for payment_amount in voter_payments.values():
            total_paid += payment_amount
        leftover_budgets[voter] = (frac(budget_limit) / num_voters) - total_paid
    
    return leftover_budgets


def get_leximax_payment(
    current_solution: BudgetAllocation,
    num_voters: int,
    instance: Instance,
) -> dict[int, list[tuple[Numeric, str]]]:
    """
    Return the leximax payment vectors for all voters as a dict mapping
    voter index to a sorted list of ``(amount, project_name)`` tuples,
    ordered descending by amount then ascending by project name for ties.

    When a voter made no payments, their entry is ``[(0, smallest_name)]``
    so that non-paying voters never certify instability.
    """
    allocation_details = current_solution.details
    smallest_project_name = ""
    for project in instance:
        if smallest_project_name == "" or project.name < smallest_project_name:
            smallest_project_name = project.name
    leximax_payments = {}

    for voter in range(num_voters):
        voter_payments = allocation_details.payments.get(voter, {})
        if not voter_payments:
            leximax_payments[voter] = [(0, smallest_project_name)]
        else:
            payment_vector = []
            for project, payment_amount in voter_payments.items():
                payment_vector.append((payment_amount, project.name))
            payment_vector.sort(key=lambda payment: (-payment[0], payment[1]))
            leximax_payments[voter] = payment_vector

    return leximax_payments


def greedy_project_change(
    instance: Instance,
    profile: AbstractApprovalProfile,
    current_solution: BudgetAllocation,
    project: Project,
    leftover_budgets: dict[int, Numeric],
    leximax_payments: dict[int, list[tuple[Numeric, str]]],
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
        leftover_budgets : dict[int, Numeric]
            Leftover budget per voter, as returned by
            :py:func:`get_leftover_budgets`.
        leximax_payments : dict[int, list[tuple[Numeric, str]]]
            Leximax payment vector per voter, as returned by
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
    >>> leximax = get_leximax_payment(solution, 5, inst)
    >>> greedy_project_change(inst, prof, solution, p3, leftover, leximax)
    mpq(1,2)
    """
    n = len(profile)

    # All voters who approve project.
    project_supporters = set()
    for voter in range(n):
        if project in profile[voter]:
            project_supporters.add(voter)

    # voters who already pay for project in the current solution.
    allocation_details = current_solution.details
    current_payers = set()
    for voter in project_supporters:
        if project in allocation_details.payments.get(voter, {}):
            current_payers.add(voter)

    # O_p(X): supporters who approve project but do not currently pay for it.
    outside_supporters = project_supporters - current_payers

    # Outside supporters sorted by leftover budget ascending.
    if voters_by_leftover is not None:
        outside_supporters_by_leftover = []
        for voter in voters_by_leftover:
            if voter in outside_supporters:
                outside_supporters_by_leftover.append(voter)
    else:
        outside_supporters_by_leftover = sorted(
            outside_supporters, key=lambda voter: leftover_budgets[voter]
        )
    num_outside_supporters = len(outside_supporters_by_leftover)

    # Outside supporters sorted by leximax payment ascending.
    if voters_by_leximax is not None:
        outside_supporters_by_leximax = []
        for voter in voters_by_leximax:
            if voter in outside_supporters:
                outside_supporters_by_leximax.append(voter)
    else:
        outside_supporters_by_leximax = sorted(
            outside_supporters, key=lambda voter: leximax_payments[voter])

    # Line 1: Start both scan positions at the beginning.
    leftover_index = 0
    leximax_index = 0

    # Line 2-3
    # SL (solvent list) — voters who can pay by deviating from their leximax project.
    solvent_list = set()
    # LQ (liquid queue) — voters expected to pay from their leftover budgets.
    liquid_queue = set(outside_supporters_by_leftover)

    # Line 4: Initialize the required budget increase as unbounded.
    d = float('inf')

    # Line 5: Continue until all queued and skipped voters have been processed.
    while liquid_queue or solvent_list:
        # Line 6: Compute the current equal payment needed for project.
        paying_supporters = current_payers | liquid_queue | solvent_list
        per_voter_price = frac(project.cost) / len(paying_supporters)

        per_voter_price_leximax = [(per_voter_price, project.name)]

        # Line 7: Advance past voters whose leximax payment is too small.
        if (leximax_index < num_outside_supporters
            and leximax_payments[outside_supporters_by_leximax[leximax_index]]
            < per_voter_price_leximax):
            # Line 8: Remove that voter from the skipped set if present.
            solvent_list.discard(outside_supporters_by_leximax[leximax_index])
            # Line 9: Move to the next voter in leximax order.
            leximax_index += 1
       
        # Line 10: Otherwise, check whether the next leftover voter must be skipped.
        elif (leftover_index < num_outside_supporters
            and leximax_payments[outside_supporters_by_leftover[leftover_index]]
            > per_voter_price_leximax):
            # Line 11: Remove the voter from the leftover queue.
            liquid_queue.discard(outside_supporters_by_leftover[leftover_index])
            # Line 12: Mark the voter as skipped for later processing.
            solvent_list.add(outside_supporters_by_leftover[leftover_index])
            # Line 13: Move to the next voter in leftover order.
            leftover_index += 1

        # Line 14-15: Record the smallest increase that lets this voter pay.
        else:
            if leftover_index < num_outside_supporters:
                next_voter = outside_supporters_by_leftover[leftover_index]
                d = min(d, per_voter_price - leftover_budgets[next_voter])
            # Line 16: Remove the processed voter from the leftover queue.
            if leftover_index < num_outside_supporters:
                liquid_queue.discard(outside_supporters_by_leftover[leftover_index])
            # Line 17: Move to the next voter in leftover order.
            leftover_index += 1

    # Line 20: Return the best budget increase found.
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
    mpq(1,2)
    """
    n = len(profile)

    # Precompute leftover budgets and leximax payments for all voters
    leftover_budgets = get_leftover_budgets(instance, profile, current_solution)
    leximax_payments = get_leximax_payment(current_solution, n, instance)

    # Pre-sort all voters once (Algorithm 3, lines A and B)
    all_voters = list(range(n))
    voters_by_leftover = sorted(all_voters, key=lambda i: leftover_budgets[i])
    voters_by_leximax = sorted(all_voters, key=lambda i: leximax_payments[i])

    # Line 1: Initialize the best project change as unbounded.
    d = float('inf')

    # Line 2: Test every project as a possible instability certificate.
    for project in instance:
        # Line 5: Keep the smallest change found for any project.
        gpc_result = greedy_project_change(instance, profile, current_solution, project, leftover_budgets, leximax_payments,
            voters_by_leftover, voters_by_leximax,)
        d = min(d, gpc_result)

    # Line 7: Return the minimum change over all projects.
    return d


def ees_add_opt_completion(
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
    >>> result = ees_add_opt_completion(inst, prof)
    >>> sorted(p.name for p in result)
    ['p1', 'p3']
    """
    n = len(profile)
    if n == 0:
        return exact_equal_shares(instance, profile, utilities)

    original_budget = instance.budget_limit
    virtual_budget = frac(original_budget)
    projects = list(instance)
    best_result = None
    best_result_cost = frac(-1)

    while True:
        virtual_inst = Instance(projects, budget_limit=virtual_budget)
        result = exact_equal_shares(virtual_inst, profile, utilities)

        total_cost = 0
        for project in result:
            total_cost += frac(project.cost)
        if total_cost <= original_budget and total_cost > best_result_cost:
            best_result = result
            best_result_cost = total_cost

        d = add_opt(virtual_inst, profile, result)
        if d == float('inf') or d <= 0:
            break

        virtual_budget = virtual_budget + n * frac(d)

    if best_result is None:
        best_result = exact_equal_shares(instance, profile, utilities)
    
    return best_result
