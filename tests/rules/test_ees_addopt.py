"""
Tests for EES (Algorithm 1), GreedyProjectChange (Algorithm 2) and add-opt (Algorithm 3).

Programmer: Yonatan Gabay
Since: 2026-04
"""

import unittest

from pabutools.election.instance import Instance, Project
from pabutools.election.profile import ApprovalProfile
from pabutools.election.ballot import ApprovalBallot
from pabutools.rules.budgetallocation import BudgetAllocation
from pabutools.rules.ees_addopt import (
    exact_equal_shares,
    greedy_project_change,
    add_opt,
    ees_add_opt_completion,
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
    projects = {}
    for name, cost in project_costs.items():
        projects[name] = Project(name, cost)
    inst = Instance(projects.values(), budget_limit=budget)
    ballots = []
    for approved in approval_sets:
        ballot_projects = []
        for pname in approved:
            ballot_projects.append(projects[pname])
        ballots.append(ApprovalBallot(ballot_projects))
    prof = ApprovalProfile(ballots, instance=inst)
    return inst, prof, projects


def _selected_names(result):
    """Return project names from a BudgetAllocation."""
    names = []
    for p in result:
        names.append(p.name)
    return names


def _get_payments(result):
    """Return the payments dict from a BudgetAllocation's EESAllocationDetails."""
    return result.details.payments


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
    selected = []
    for name in selected_names:
        selected.append(projects[name])
    pay = {}
    for voter_idx, voter_payments in payments_by_voter.items():
        voter_pay = {}
        for pname, amount in voter_payments.items():
            voter_pay[projects[pname]] = amount
        pay[voter_idx] = voter_pay
    return BudgetAllocation(selected, details=EESAllocationDetails(pay))


####### EES tests

class TestEES(unittest.TestCase):

    def test_ees_nothing_to_select(self):
        """empty input should return empty result"""
        inst = Instance([], budget_limit=0)
        prof = ApprovalProfile([], instance=inst)

        result = exact_equal_shares(inst, prof)
        self.assertEqual(_selected_names(result), [])
        self.assertEqual(_get_payments(result), {})

    def test_ees_single_project_too_expensive(self):
        """project above budget should not be selected"""
        inst, prof, projects = _make_instance_profile(
            {"p1": 200}, 50, [{"p1"}, {"p1"}]
        )
        result = exact_equal_shares(inst, prof)
        self.assertNotIn(projects["p1"], result)

    def test_ees_cost_split_equally(self):
        """one approved project should split cost evenly"""
        inst, prof, projects = _make_instance_profile(
            {"p1": 10}, 10, [{"p1"}, {"p1"}]
        )
        result = exact_equal_shares(inst, prof)
        self.assertIn(projects["p1"], result)
        payments = _get_payments(result)
        self.assertAlmostEqual(payments[0][projects["p1"]], 5)
        self.assertAlmostEqual(payments[1][projects["p1"]], 5)

    def test_ees_multiple_projects(self):
        """paper example"""
        inst, prof, projects = _make_instance_profile(
            {"p1": 10, "p2": 16, "p3": 21},
            40,
            [{"p1"}, {"p1", "p3"}, {"p2", "p3"}, {"p2", "p3"}],
        )
        result = exact_equal_shares(inst, prof)
        self.assertEqual(_selected_names(result), ["p1", "p2"])
        payments = _get_payments(result)
        self.assertAlmostEqual(payments[0][projects["p1"]], 5)
        self.assertAlmostEqual(payments[1][projects["p1"]], 5)
        self.assertAlmostEqual(payments[2][projects["p2"]], 8)
        self.assertAlmostEqual(payments[3][projects["p2"]], 8)

    def test_ees_no_approvals_means_nothing_funded(self):
        """no approvals"""
        inst, prof, projects = _make_instance_profile(
            {"p1": 10, "p2": 15},
            100,
            [set(), set(), set()],
        )
        result = exact_equal_shares(inst, prof)
        self.assertEqual(_selected_names(result), [])

    def test_ees_budget_feasibility(self):
        """payments should stay within budget"""
        inst, prof, projects = _make_instance_profile(
            {"p1": 2, "p2": 3.2, "p3": 6},
            10,
            [{"p1"}, {"p1", "p3"}, {"p2", "p3"}, {"p2", "p3"}, {"p3"}],
        )
        result = exact_equal_shares(inst, prof)
        payments = _get_payments(result)

        total_paid = 0
        for i in range(len(prof)):
            for p in result:
                total_paid += payments.get(i, {}).get(p, 0)
        self.assertLessEqual(total_paid, inst.budget_limit)

        # Each funded project is fully covered
        for proj in result:
            paid_for_proj = 0
            for i in range(len(prof)):
                paid_for_proj += payments.get(i, {}).get(proj, 0)
            self.assertAlmostEqual(paid_for_proj, proj.cost)


####### get_leftover_budgets tests

class TestGetLeftoverBudgets(unittest.TestCase):

    def test_leftover_no_payments(self):
        """no payments means full leftover for each voter"""
        inst, prof, projects = _make_instance_profile({"p1": 10}, 20, [{"p1"}, {"p1"}])
        solution = _make_solution([], {0: {}, 1: {}}, projects)
        leftover = get_leftover_budgets(inst, prof, solution)
        # b/n = 20/2 = 10 per voter
        self.assertAlmostEqual(leftover[0], 10)
        self.assertAlmostEqual(leftover[1], 10)

    def test_leftover_after_payments(self):
        """leftover should equal b/n minus total payments"""
        inst, prof, projects = _make_instance_profile({"p1": 2, "p2": 3.2}, 10, [{"p1", "p2"}, {"p1", "p2"}])
        solution = _make_solution(["p1", "p2"], {0: {"p1": 1, "p2": 1.6}, 1: {"p1": 1, "p2": 1.6}}, projects)
        leftover = get_leftover_budgets(inst, prof, solution)
        # b/n = 10/2 = 5, each voter paid 2.6
        self.assertAlmostEqual(leftover[0], 2.4)
        self.assertAlmostEqual(leftover[1], 2.4)

    def test_leftover_uneven_payments(self):
        """voter who paid nothing has full leftover; voter who paid has less"""
        inst, prof, projects = _make_instance_profile({"p1": 5}, 10, [{"p1"}, {"p1"}])
        solution = _make_solution(["p1"], {0: {"p1": 5.0}, 1: {}}, projects)
        leftover = get_leftover_budgets(inst, prof, solution)
        # b/n = 5
        self.assertAlmostEqual(leftover[0], 0)
        self.assertAlmostEqual(leftover[1], 5)

    def test_leftover_paper_example(self):
        """paper example"""
        inst, prof, projects = _make_instance_profile(
            {"p1": 2, "p2": 3.2, "p3": 6}, 10,
            [{"p1"}, {"p1", "p3"}, {"p2", "p3"}, {"p2", "p3"}, {"p3"}],
        )
        solution = _make_solution(
            ["p1", "p2"],
            {0: {"p1": 1}, 1: {"p1": 1}, 2: {"p2": 1.6}, 3: {"p2": 1.6}, 4: {}},
            projects,
        )
        leftover = get_leftover_budgets(inst, prof, solution)
        # b/n = 10/5 = 2
        self.assertAlmostEqual(leftover[0], 1)
        self.assertAlmostEqual(leftover[1], 1)
        self.assertAlmostEqual(leftover[2], 0.4)
        self.assertAlmostEqual(leftover[3], 0.4)
        self.assertAlmostEqual(leftover[4], 2)


####### get_leximax_payment tests

class TestGetLeximaxPayment(unittest.TestCase):

    def test_leximax_no_payments(self):
        """non-paying voter gets [(0, smallest_project_name)]"""
        inst, prof, projects = _make_instance_profile({"p1": 10, "p2": 5}, 20, [{"p1"}, {"p2"}])
        solution = _make_solution([], {0: {}, 1: {}}, projects)
        leximax = get_leximax_payment(solution, len(prof), inst)
        # smallest project name is "p1"
        self.assertEqual(leximax[0], [(0, "p1")])
        self.assertEqual(leximax[1], [(0, "p1")])

    def test_leximax_single_payment(self):
        """single payment produces a one-element vector"""
        inst, prof, projects = _make_instance_profile({"p1": 10}, 10, [{"p1"}, {"p1"}])
        solution = _make_solution(["p1"], {0: {"p1": 5}, 1: {"p1": 5}}, projects)
        leximax = get_leximax_payment(solution, len(prof), inst)
        self.assertEqual(leximax[0], [(5, "p1")])
        self.assertEqual(leximax[1], [(5, "p1")])

    def test_leximax_multiple_payments_sorted(self):
        """multiple payments sorted descending by amount, then ascending by name"""
        inst, prof, projects = _make_instance_profile({"p1": 2, "p2": 6}, 10, [{"p1", "p2"}])
        solution = _make_solution(["p1", "p2"], {0: {"p1": 2, "p2": 6}}, projects)
        leximax = get_leximax_payment(solution, len(prof), inst)
        # descending by amount: 6 before 2
        self.assertEqual(leximax[0], [(6, "p2"), (2, "p1")])

    def test_leximax_tiebreak_by_name(self):
        """equal amounts should be sorted ascending by project name"""
        inst, prof, projects = _make_instance_profile({"a": 4, "b": 4}, 10, [{"a", "b"}])
        solution = _make_solution(["a", "b"], {0: {"a": 4, "b": 4}}, projects)
        leximax = get_leximax_payment(solution, len(prof), inst)
        # same amount, ascending by name: "a" before "b"
        self.assertEqual(leximax[0], [(4, "a"), (4, "b")])

    def test_leximax_paper_example(self):
        """paper example"""
        inst, prof, projects = _make_instance_profile(
            {"p1": 2, "p2": 3.2, "p3": 6}, 10,
            [{"p1"}, {"p1", "p3"}, {"p2", "p3"}, {"p2", "p3"}, {"p3"}],
        )
        solution = _make_solution(
            ["p1", "p2"],
            {0: {"p1": 1}, 1: {"p1": 1}, 2: {"p2": 1.6}, 3: {"p2": 1.6}, 4: {}},
            projects,
        )
        leximax = get_leximax_payment(solution, len(prof), inst)
        self.assertEqual(leximax[0], [(1, "p1")])
        self.assertEqual(leximax[1], [(1, "p1")])
        self.assertEqual(leximax[2], [(1.6, "p2")])
        self.assertEqual(leximax[3], [(1.6, "p2")])
        self.assertEqual(leximax[4], [(0, "p1")])  # non-payer gets smallest name


####### GPC tests

class TestGPC(unittest.TestCase):

    def test_gpc_free_project_needs_zero_increase(self):
        """zero-cost project should return zero delta"""
        inst, prof, projects = _make_instance_profile(
            {"p1": 0}, 10, [{"p1"}]
        )
        solution = _make_solution([], {}, projects)
        leftover = get_leftover_budgets(inst, prof, solution)
        leximax = get_leximax_payment(solution, len(prof), inst)
        delta = greedy_project_change(inst, prof, solution, projects["p1"], leftover, leximax)
        self.assertAlmostEqual(delta, 0)

    def test_gpc_leftover_covers_cost_exactly(self):
        """enough leftover should return zero delta"""
        inst, prof, projects = _make_instance_profile(
            {"p1": 12}, 15, [{"p1"}, {"p1"}, {"p1"}]
        )
        solution = _make_solution([], {}, projects)
        leftover = get_leftover_budgets(inst, prof, solution)
        leximax = get_leximax_payment(solution, len(prof), inst)
        delta = greedy_project_change(inst, prof, solution, projects["p1"], leftover, leximax)
        self.assertAlmostEqual(delta, 0)

    def test_gpc_not_enough_leftover(self):
        """not enough leftover should return positive delta"""
        inst, prof, projects = _make_instance_profile(
            {"p1": 30}, 6, [{"p1"}, {"p1"}, {"p1"}]
        )
        solution = _make_solution([], {}, projects)
        leftover = get_leftover_budgets(inst, prof, solution)
        leximax = get_leximax_payment(solution, len(prof), inst)
        delta = greedy_project_change(inst, prof, solution, projects["p1"], leftover, leximax)
        self.assertGreater(delta, 0)

    def test_gpc_paper_example(self):
        """paper example"""
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
        leximax = get_leximax_payment(solution, len(prof), inst)
        delta = greedy_project_change(inst, prof, solution, projects["p3"], leftover, leximax)
        self.assertAlmostEqual(delta, 0.5)

    def test_gpc_with_existing_selection(self):
        """some projects are already funded"""
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
        leximax = get_leximax_payment(solution, len(prof), inst)
        delta = greedy_project_change(inst, prof, solution, projects["p2"], leftover, leximax)
        self.assertGreaterEqual(delta, 0)


####### add-opt tests

class TestAddOpt(unittest.TestCase):

    def test_addopt_nothing_to_add(self):
        """empty input should return non-negative or infinite"""
        inst = Instance([], budget_limit=0)
        prof = ApprovalProfile([], instance=inst)
        solution = BudgetAllocation([], details=EESAllocationDetails({}))

        delta = add_opt(inst, prof, solution)
        self.assertTrue(delta >= 0 or delta == float("inf"))

    def test_addopt_all_projects_already_funded(self):
        """if all projects funded should not improve"""
        inst, prof, projects = _make_instance_profile(
            {"p1": 5}, 10, [{"p1"}]
        )
        solution = _make_solution(["p1"], {0: {"p1": 5.0}}, projects)
        delta = add_opt(inst, prof, solution)
        self.assertTrue(delta >= 0 or delta == float("inf"))

    def test_addopt_finds_improvement(self):
        """paper example"""
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
        self.assertAlmostEqual(delta, 0.5)


####### random tests

class TestRandom(unittest.TestCase):

    def _run_random_ees_gpc_rerun(self, num_voters, num_projects, test_times=5, approval_prob=0.4, budget_factor=(0.4, 0.8)):
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
            with self.subTest(num_voters=num_voters, num_projects=num_projects, seed=seed):
                rng.seed(seed)

                project_names = []
                for i in range(num_projects):
                    project_names.append(f"p{i}")
                costs = {}
                for name in project_names:
                    costs[name] = rng.randint(0, 100)
                projects_map = {}
                for name, c in costs.items():
                    projects_map[name] = Project(name, c)
                all_projects = list(projects_map.values())

                total_cost = sum(costs.values())
                budget = int(total_cost * rng.uniform(*budget_factor))

                inst = Instance(all_projects, budget_limit=budget)

                # build approval ballots
                ballots = []
                for _ in range(num_voters):
                    approved = []
                    for name in project_names:
                        if rng.random() < approval_prob:
                            approved.append(projects_map[name])
                    ballots.append(ApprovalBallot(approved))
                prof = ApprovalProfile(ballots, instance=inst)

                # run EES
                result = exact_equal_shares(inst, prof)
                payments = _get_payments(result)

                # validate EES result
                total = 0
                for i in range(num_voters):
                    for p in result:
                        total += payments.get(i, {}).get(p, 0)
                self.assertLessEqual(total, budget, msg=f"seed={seed}: EES exceeded budget")
                for p in result:
                    paid = 0
                    for i in range(num_voters):
                        paid += payments.get(i, {}).get(p, 0)
                    self.assertAlmostEqual(paid, p.cost, msg=f"seed={seed}: project {p.name} not covered")

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
                leximax = get_leximax_payment(result, num_voters, inst)
                delta = greedy_project_change(inst, prof, result, target_project, leftover, leximax)
                self.assertGreaterEqual(delta, 0, msg=f"seed={seed}: GPC returned negative delta")

                # run EES with new budget
                new_budget = budget + num_voters * delta
                new_inst = Instance(all_projects, budget_limit=new_budget)
                new_result = exact_equal_shares(new_inst, prof)
                new_payments = _get_payments(new_result)

                # validate new EES result
                new_total = 0
                for i in range(num_voters):
                    for p in new_result:
                        new_total += new_payments.get(i, {}).get(p, 0)
                self.assertLessEqual(new_total, new_budget, msg=f"seed={seed}: new EES exceeded budget")
                for p in new_result:
                    paid = 0
                    for i in range(num_voters):
                        paid += new_payments.get(i, {}).get(p, 0)
                    self.assertAlmostEqual(paid, p.cost, msg=f"seed={seed}: project {p.name} not covered after increase")

                # Per Remark 1 in the paper, GPC for a single project
                # guarantees instability but not that the project is selected.
                # Verify the EES outcome changed instead.
                self.assertTrue(
                    set(new_result) != set(result) or _get_payments(new_result) != _get_payments(result),
                    msg=(
                        f"seed={seed}: GPC said delta={delta} for '{target_project.name}' "
                        f"but EES returned the same result with budget={new_budget}"
                    ),
                )

    def test_random_ees_gpc_rerun_3_voters_20_projects(self):
        self._run_random_ees_gpc_rerun(num_voters=3, num_projects=20)

    def test_random_ees_gpc_rerun_20_voters_3_projects(self):
        self._run_random_ees_gpc_rerun(num_voters=20, num_projects=3)

    def test_random_ees_gpc_rerun_20_voters_20_projects(self):
        self._run_random_ees_gpc_rerun(num_voters=20, num_projects=20)


####### ees_add_opt_completion tests

class TestEESAddOptCompletion(unittest.TestCase):

    def test_completion_empty_profile(self):
        """empty profile returns empty result"""
        inst = Instance([], budget_limit=10)
        prof = ApprovalProfile([], instance=inst)
        result = ees_add_opt_completion(inst, prof)
        self.assertEqual(len(result), 0)

    def test_completion_paper_example(self):
        """
        paper example from §4.1 Example 4.3
        5 voters, 3 projects: p1(2), p2(3.2), p3(6), budget=10
        EES alone picks {p1,p2} (cost 5.2), completion should pick {p1,p3} (cost 8)
        """
        inst, prof, projects = _make_instance_profile(
            {"p1": 2, "p2": 3.2, "p3": 6},
            10,
            [{"p1"}, {"p1", "p3"}, {"p2", "p3"}, {"p2", "p3"}, {"p3"}],
        )
        result = ees_add_opt_completion(inst, prof)
        names = sorted(_selected_names(result))
        self.assertEqual(names, ["p1", "p3"])

    def test_completion_budget_feasible(self):
        """result should always be budget-feasible"""
        inst, prof, projects = _make_instance_profile(
            {"p1": 2, "p2": 3.2, "p3": 6},
            10,
            [{"p1"}, {"p1", "p3"}, {"p2", "p3"}, {"p2", "p3"}, {"p3"}],
        )
        result = ees_add_opt_completion(inst, prof)
        total = 0
        for p in result:
            total += p.cost
        self.assertLessEqual(total, inst.budget_limit)

    def test_completion_single_voter_single_project(self):
        """single voter, single affordable project"""
        inst, prof, projects = _make_instance_profile(
            {"p1": 5}, 10, [{"p1"}]
        )
        result = ees_add_opt_completion(inst, prof)
        self.assertEqual(_selected_names(result), ["p1"])

    def test_completion_all_projects_selected(self):
        """all projects are affordable from the start"""
        inst, prof, projects = _make_instance_profile(
            {"p1": 2, "p2": 3},
            10,
            [{"p1", "p2"}, {"p1", "p2"}],
        )
        result = ees_add_opt_completion(inst, prof)
        names = sorted(_selected_names(result))
        self.assertEqual(names, ["p1", "p2"])

    def test_completion_no_affordable_project(self):
        """no project is affordable (cost exceeds budget)"""
        inst, prof, projects = _make_instance_profile(
            {"p1": 100}, 10, [{"p1"}]
        )
        result = ees_add_opt_completion(inst, prof)
        self.assertEqual(len(result), 0)

    def test_completion_remark1_example(self):
        """
        Remark 1 example: p1(2),p2(98),p3(100),p4(51), budget=150, 3 voters
        A1={p1,p2}, A2={p2,p3}, A3={p3,p4}. EES selects {p1,p3}.
        Completion should produce a feasible result with total cost <= 150.
        """
        inst, prof, projects = _make_instance_profile(
            {"p1": 2, "p2": 98, "p3": 100, "p4": 51},
            150,
            [{"p1", "p2"}, {"p2", "p3"}, {"p3", "p4"}],
        )
        result = ees_add_opt_completion(inst, prof)
        total = 0
        for p in result:
            total += p.cost
        self.assertLessEqual(total, 150)
        # should at least select the base EES result {p1, p3}
        names = sorted(_selected_names(result))
        self.assertIn("p1", names)
        self.assertIn("p3", names)

    def test_completion_spends_at_least_as_much_as_ees(self):
        """completion should spend at least as much as base EES"""
        inst, prof, projects = _make_instance_profile(
            {"p1": 2, "p2": 3.2, "p3": 6},
            10,
            [{"p1"}, {"p1", "p3"}, {"p2", "p3"}, {"p2", "p3"}, {"p3"}],
        )
        ees_result = exact_equal_shares(inst, prof)
        ees_cost = 0
        for p in ees_result:
            ees_cost += p.cost

        completion_result = ees_add_opt_completion(inst, prof)
        completion_cost = 0
        for p in completion_result:
            completion_cost += p.cost

        self.assertGreaterEqual(completion_cost, ees_cost)


if __name__ == "__main__":
    unittest.main()
