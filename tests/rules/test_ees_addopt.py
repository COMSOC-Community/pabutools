"""
Tests for EES (Algorithm 1), GreedyProjectChange (Algorithm 2) and add-opt (Algorithm 3).

Programmer: Yonatan Gabay
Since: 2026-04
"""

import pytest

from pabutools.election.instance import Instance, Project
from pabutools.election.profile import ApprovalProfile
from pabutools.election.ballot import ApprovalBallot
from pabutools.rules.budgetallocation import BudgetAllocation
from pabutools.rules.ees_addopt import (
    exact_equal_shares,
    greedy_project_change,
    add_opt,
    EESAllocationDetails,
    get_leftover_budgets,
    get_leximax_payment,
)


# ---- helpers ----

def _make_instance_profile(project_costs, budget, approval_sets):
    """
    Build an Instance + ApprovalProfile from simple descriptions.

    Parameters
    ----------
    project_costs : dict[str, float]
        Mapping from project name to cost.
    budget : float
        Budget limit.
    approval_sets : list[set[str]]
        One set of approved project names per voter.

    Returns
    -------
    tuple[Instance, ApprovalProfile, dict[str, Project]]
        The instance, profile, and a name→Project lookup dict.
    """
    projects = {name: Project(name, cost) for name, cost in project_costs.items()}
    inst = Instance(projects.values(), budget_limit=budget)
    ballots = [
        ApprovalBallot([projects[pname] for pname in approved])
        for approved in approval_sets
    ]
    prof = ApprovalProfile(ballots, instance=inst)
    return inst, prof, projects


def _selected_names(result):
    """Return project names from a BudgetAllocation."""
    return [p.name for p in result]


def _get_payments(result):
    """Return the payments dict from a BudgetAllocation's EESAllocationDetails."""
    return result.details.payments


####### EES tests


# empty input should return empty result
def test_ees_nothing_to_select():
    inst = Instance([], budget_limit=0)
    prof = ApprovalProfile([], instance=inst)

    result = exact_equal_shares(inst, prof)
    assert _selected_names(result) == []
    assert _get_payments(result) == {}


# project above budget should not be selected
def test_ees_single_project_too_expensive():
    inst, prof, projects = _make_instance_profile(
        {"p1": 200}, 50, [{"p1"}, {"p1"}]
    )
    result = exact_equal_shares(inst, prof)
    assert projects["p1"] not in result


# one approved project should split cost evenly
def test_ees_cost_split_equally():
    inst, prof, projects = _make_instance_profile(
        {"p1": 10}, 10, [{"p1"}, {"p1"}]
    )
    result = exact_equal_shares(inst, prof)
    assert projects["p1"] in result
    payments = _get_payments(result)
    assert payments[0][projects["p1"]] == pytest.approx(5)
    assert payments[1][projects["p1"]] == pytest.approx(5)


# paper example
def test_ees_multiple_projects():
    inst, prof, projects = _make_instance_profile(
        {"p1": 10, "p2": 16, "p3": 21},
        40,
        [{"p1"}, {"p1", "p3"}, {"p2", "p3"}, {"p2", "p3"}],
    )
    result = exact_equal_shares(inst, prof)
    assert _selected_names(result) == ["p1", "p2"]
    payments = _get_payments(result)
    assert payments[0][projects["p1"]] == 5
    assert payments[1][projects["p1"]] == 5
    assert payments[2][projects["p2"]] == 8
    assert payments[3][projects["p2"]] == 8


# no approvals
def test_ees_no_approvals_means_nothing_funded():
    inst, prof, projects = _make_instance_profile(
        {"p1": 10, "p2": 15},
        100,
        [set(), set(), set()],
    )
    result = exact_equal_shares(inst, prof)
    assert _selected_names(result) == []


# payments should stay within budget
def test_ees_budget_feasibility():
    inst, prof, projects = _make_instance_profile(
        {"p1": 2, "p2": 3.2, "p3": 6},
        10,
        [{"p1"}, {"p1", "p3"}, {"p2", "p3"}, {"p2", "p3"}, {"p3"}],
    )
    result = exact_equal_shares(inst, prof)
    payments = _get_payments(result)

    total_paid = sum(
        payments.get(i, {}).get(p, 0)
        for i in range(len(prof))
        for p in result
    )
    assert total_paid <= inst.budget_limit

    # Each funded project is fully covered
    for proj in result:
        paid_for_proj = sum(
            payments.get(i, {}).get(proj, 0)
            for i in range(len(prof))
        )
        assert paid_for_proj == pytest.approx(proj.cost)


####### GPC tests


def _make_solution(selected_names, payments_by_voter, projects):
    """
    Build a BudgetAllocation with EESAllocationDetails from simple descriptions.

    Parameters
    ----------
    selected_names : list[str]
        Names of selected projects.
    payments_by_voter : dict[int, dict[str, float]]
        payments_by_voter[voter_index][project_name] = payment.
    projects : dict[str, Project]
        Name→Project lookup.
    """
    selected = [projects[n] for n in selected_names]
    pay = {}
    for voter_idx, voter_payments in payments_by_voter.items():
        pay[voter_idx] = {projects[pname]: amount for pname, amount in voter_payments.items()}
    return BudgetAllocation(selected, details=EESAllocationDetails(pay))


# zero-cost project should return zero delta
def test_gpc_free_project_needs_zero_increase():
    inst, prof, projects = _make_instance_profile(
        {"p1": 0}, 10, [{"p1"}]
    )
    solution = _make_solution([], {}, projects)
    leftover = get_leftover_budgets(inst, prof, solution)
    leximax = {i: get_leximax_payment(solution, i, inst) for i in range(len(prof))}
    delta = greedy_project_change(inst, prof, solution, projects["p1"], leftover, leximax)
    assert delta == pytest.approx(0)


# enough leftover should return zero delta
def test_gpc_leftover_covers_cost_exactly():
    inst, prof, projects = _make_instance_profile(
        {"p1": 12}, 15, [{"p1"}, {"p1"}, {"p1"}]
    )
    solution = _make_solution([], {}, projects)
    leftover = get_leftover_budgets(inst, prof, solution)
    leximax = {i: get_leximax_payment(solution, i, inst) for i in range(len(prof))}
    delta = greedy_project_change(inst, prof, solution, projects["p1"], leftover, leximax)
    assert delta == pytest.approx(0)


# not enough leftover should return positive delta
def test_gpc_not_enough_leftover():
    inst, prof, projects = _make_instance_profile(
        {"p1": 30}, 6, [{"p1"}, {"p1"}, {"p1"}]
    )
    solution = _make_solution([], {}, projects)
    leftover = get_leftover_budgets(inst, prof, solution)
    leximax = {i: get_leximax_payment(solution, i, inst) for i in range(len(prof))}
    delta = greedy_project_change(inst, prof, solution, projects["p1"], leftover, leximax)
    assert delta > 0


# paper example
def test_gpc_paper_example():
    inst, prof, projects = _make_instance_profile(
        {"p1": 2, "p2": 3.2, "p3": 6},
        10,
        [{"p1"}, {"p1", "p3"}, {"p2", "p3"}, {"p2", "p3"}, {"p3"}],
    )
    solution = _make_solution(
        ["p1", "p2"],
        {0: {"p1": 1}, 1: {"p1": 1}, 2: {"p2": 1.6}, 3: {"p2": 1.6}, 4: {}},
        projects,
    )
    leftover = get_leftover_budgets(inst, prof, solution)
    leximax = {i: get_leximax_payment(solution, i, inst) for i in range(len(prof))}
    delta = greedy_project_change(inst, prof, solution, projects["p3"], leftover, leximax)
    assert delta == pytest.approx(0.5)


# some projects are already funded
def test_gpc_with_existing_selection():
    inst, prof, projects = _make_instance_profile(
        {"p1": 5, "p2": 8},
        10,
        [{"p1", "p2"}, {"p1", "p2"}],
    )
    solution = _make_solution(
        ["p1"],
        {0: {"p1": 5.0}, 1: {}},
        projects,
    )
    leftover = get_leftover_budgets(inst, prof, solution)
    leximax = {i: get_leximax_payment(solution, i, inst) for i in range(len(prof))}
    delta = greedy_project_change(inst, prof, solution, projects["p2"], leftover, leximax)
    assert delta >= 0


####### add-opt tests


# empty input should return non-negative or infinite
def test_addopt_nothing_to_add():
    inst = Instance([], budget_limit=0)
    prof = ApprovalProfile([], instance=inst)
    solution = BudgetAllocation([], details=EESAllocationDetails({}))

    delta = add_opt(inst, prof, solution)
    assert delta >= 0 or delta == float("inf")


# if all projects funded should not improve
def test_addopt_all_projects_already_funded():
    inst, prof, projects = _make_instance_profile(
        {"p1": 5}, 10, [{"p1"}]
    )
    solution = _make_solution(["p1"], {0: {"p1": 5.0}}, projects)
    delta = add_opt(inst, prof, solution)
    assert delta >= 0 or delta == float("inf")


# paper example
def test_addopt_finds_improvement():
    inst, prof, projects = _make_instance_profile(
        {"p1": 2, "p2": 3.2, "p3": 6},
        10,
        [{"p1"}, {"p1", "p3"}, {"p2", "p3"}, {"p2", "p3"}, {"p3"}],
    )
    solution = _make_solution(
        ["p1", "p2"],
        {0: {"p1": 1}, 1: {"p1": 1}, 2: {"p2": 1.6}, 3: {"p2": 1.6}, 4: {}},
        projects,
    )
    delta = add_opt(inst, prof, solution)
    assert delta == pytest.approx(0.5)


####### random tests


@pytest.mark.parametrize("num_voters, num_projects", [
    (3, 20),
    (20, 2),
    (20, 20),
])
# random instances should stay valid after EES, GPC, and rerun EES
def test_random_ees_gpc_rerun(num_voters, num_projects, test_times=5, approval_prob=0.4, budget_factor=(0.4, 0.8)):
    """
    Full random test:
    1. Generate random instance
    2. Run EES and validate result
    3. Choose unselected project and run GPC
    4. Run EES with bigger budget
    5. Validate new EES result
    6. Check GPC project now selected
    """
    import random
    rng = random.Random()

    for seed in range(test_times):
        rng.seed(seed)

        project_names = [f"p{i}" for i in range(num_projects)]
        costs = {name: rng.randint(0, 100) for name in project_names}
        projects_map = {name: Project(name, c) for name, c in costs.items()}
        all_projects = list(projects_map.values())

        total_cost = sum(costs.values())
        budget = int(total_cost * rng.uniform(*budget_factor))

        inst = Instance(all_projects, budget_limit=budget)

        # build approval ballots
        ballots = []
        for _ in range(num_voters):
            approved = [projects_map[name] for name in project_names if rng.random() < approval_prob]
            ballots.append(ApprovalBallot(approved))
        prof = ApprovalProfile(ballots, instance=inst)

        # run EES
        result = exact_equal_shares(inst, prof)
        payments = _get_payments(result)

        # validate EES result
        total = sum(
            payments.get(i, {}).get(p, 0)
            for i in range(num_voters)
            for p in result
        )
        assert total <= budget, f"seed={seed}: EES exceeded budget"
        for p in result:
            paid = sum(payments.get(i, {}).get(p, 0) for i in range(num_voters))
            assert paid == pytest.approx(p.cost), f"seed={seed}: project {p.name} not covered"

        # find unselected project that has support
        selected_set = set(result)
        unselected = []
        for proj in all_projects:
            if proj in selected_set:
                continue
            has_supporter = any(proj in ballot for ballot in prof)
            if has_supporter:
                unselected.append(proj)
        if not unselected:
            continue
        target_project = rng.choice(unselected)

        # run GPC
        leftover = get_leftover_budgets(inst, prof, result)
        leximax = {i: get_leximax_payment(result, i, inst) for i in range(num_voters)}
        delta = greedy_project_change(inst, prof, result, target_project, leftover, leximax)
        assert delta >= 0, f"seed={seed}: GPC returned negative delta"

        # run EES with new budget
        new_budget = budget + num_voters * delta
        new_inst = Instance(all_projects, budget_limit=new_budget)
        new_result = exact_equal_shares(new_inst, prof)
        new_payments = _get_payments(new_result)

        # validate new EES result
        new_total = sum(
            new_payments.get(i, {}).get(p, 0)
            for i in range(num_voters)
            for p in new_result
        )
        assert new_total <= new_budget, f"seed={seed}: new EES exceeded budget"
        for p in new_result:
            paid = sum(new_payments.get(i, {}).get(p, 0) for i in range(num_voters))
            assert paid == pytest.approx(p.cost), f"seed={seed}: project {p.name} not covered after increase"

        # Per Remark 1 in the paper, GPC for a single project
        # guarantees instability but not that the project is selected.
        # Verify the EES outcome changed instead.
        assert set(new_result) != set(result) or _get_payments(new_result) != _get_payments(result), (
            f"seed={seed}: GPC said delta={delta} for '{target_project.name}' "
            f"but EES returned the same result with budget={new_budget}"
        )


if __name__ == "__main__":
    pytest.main(["-v", __file__])
