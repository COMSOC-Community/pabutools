"""
Tests for the algorithm described in:

"Maxmin Participatory Budgeting", by Gogulapati Sreedurga , Mayank Ratan Bhardwaj and Y. Narahari, 2022, https://arxiv.org/pdf/2204.13923

Programmer: Nevo Biton
Date: 2026-04-29
"""

from itertools import combinations
import random
import unittest

from pulp import (
    HiGHS,
    LpMaximize,
    LpProblem,
    LpStatusOptimal,
    LpVariable,
    lpSum,
    value,
)

from pabutools.election import (
    ApprovalBallot,
    ApprovalMultiProfile,
    ApprovalProfile,
    Instance,
    Project,
    total_cost,
)
from pabutools.rules import ordered_relax
from pabutools.rules.budgetallocation import BudgetAllocation


EPS = 1e-7


def make_election(costs_by_name, budget, approvals_by_name):
    projects_by_name = {
        name: Project(name, cost)
        for name, cost in costs_by_name.items()
    }
    instance = Instance(projects_by_name.values(), budget_limit=budget)
    profile = ApprovalProfile(
        [
            ApprovalBallot({projects_by_name[name] for name in ballot})
            for ballot in approvals_by_name
        ]
    )
    return instance, profile, projects_by_name


def selected_names(outcome):
    return {p.name for p in outcome}


def voter_utility(outcome, ballot):
    return sum(p.cost for p in outcome if p in ballot)


def mpb_value(outcome, profile):
    if len(profile) == 0:
        return 0.0
    return min(voter_utility(outcome, ballot) for ballot in profile)


def assert_valid_budget_allocation(outcome, instance):
    assert isinstance(outcome, BudgetAllocation)
    assert set(outcome) <= set(instance)
    assert total_cost(outcome) <= instance.budget_limit + EPS


def exact_mpb_value_by_ilp(instance, profile):
    """
    Compute the exact MPB optimum by solving the binary ILP.

    This is used only inside tests to check the additive guarantee from
    Lemma 1.
    """
    if len(profile) == 0:
        return 0.0

    projects = list(instance)
    prob = LpProblem("ExactMPB", LpMaximize)
    x = {
        p: LpVariable(f"x_{idx}", cat="Binary")
        for idx, p in enumerate(projects)
    }
    q = LpVariable("q", lowBound=0)

    for ballot in profile:
        prob += q <= lpSum(p.cost * x[p] for p in projects if p in ballot)

    prob += lpSum(p.cost * x[p] for p in projects) <= instance.budget_limit
    prob += q
    status = prob.solve(HiGHS(msg=False))
    assert status == LpStatusOptimal
    return float(value(q) or 0.0)


def assert_ordered_relax_additive_guarantee(outcome, instance, profile):
    """
    Check Lemma 1:

        ALG >= OPT - eta * (b - OPT)

    where:
        ALG = min_i u_i(S)
        OPT = exact MPB optimum
        eta = |A_j \\ S| / |S \\ A_j|
        j = argmin_i u_i(S)

    Degenerate cases in which the denominator is 0 are skipped, because the
    formula is not numerically defined there.
    """
    if len(profile) == 0:
        return

    selected = set(outcome)
    alg = mpb_value(outcome, profile)
    opt = exact_mpb_value_by_ilp(instance, profile)
    utilities = [voter_utility(outcome, ballot) for ballot in profile]
    worst_utility = min(utilities)
    worst_indices = [
        idx
        for idx, utility in enumerate(utilities)
        if abs(utility - worst_utility) <= EPS
    ]
    eta = None

    for idx in worst_indices:
        ballot = set(profile[idx])
        denominator = len(selected - ballot)
        if denominator > 0:
            eta = len(ballot - selected) / denominator
            break

    if eta is None:
        raise unittest.SkipTest("Lemma 1 eta is undefined for all worst-off voters.")

    lower_bound = opt - eta * (instance.budget_limit - opt)
    assert alg + EPS >= lower_bound


def generate_random_election(
    seed,
    num_voters,
    num_projects,
    min_cost=1,
    max_cost=50,
    approval_probability=0.3,
):
    rng = random.Random(seed)
    costs_by_name = {
        f"p{i}": rng.randint(min_cost, max_cost)
        for i in range(num_projects)
    }
    total = sum(costs_by_name.values())
    budget = rng.randint(max(1, total // 4), max(1, total // 2))
    project_names = list(costs_by_name)
    approvals_by_name = []

    for _ in range(num_voters):
        ballot = {
            p
            for p in project_names
            if rng.random() < approval_probability
        }
        if not ballot:
            ballot.add(rng.choice(project_names))
        approvals_by_name.append(ballot)

    return make_election(costs_by_name, budget, approvals_by_name)


class TestOrderedRelax(unittest.TestCase):
    # ---------------------------------------------------------
    # Manual examples
    # ---------------------------------------------------------

    def test_ordered_relax_example_1_size_1(self):
        instance, profile, _ = make_election(
            costs_by_name={"p1": 5},
            budget=5,
            approvals_by_name=[{"p1"}],
        )
        outcome = ordered_relax(instance, profile)
        self.assertEqual(selected_names(outcome), {"p1"})
        assert_valid_budget_allocation(outcome, instance)
        assert_ordered_relax_additive_guarantee(outcome, instance, profile)

    def test_ordered_relax_example_2_size_2(self):
        instance, profile, _ = make_election(
            costs_by_name={"p1": 4, "p2": 3},
            budget=4,
            approvals_by_name=[{"p1"}, {"p2"}],
        )
        outcome = ordered_relax(instance, profile)
        self.assertEqual(selected_names(outcome), {"p1"})
        assert_valid_budget_allocation(outcome, instance)
        assert_ordered_relax_additive_guarantee(outcome, instance, profile)

    def test_ordered_relax_example_3_size_3(self):
        instance, profile, _ = make_election(
            costs_by_name={"p1": 3, "p2": 3, "p3": 2},
            budget=5,
            approvals_by_name=[{"p1", "p2"}, {"p2"}, {"p3"}],
        )
        outcome = ordered_relax(instance, profile)
        self.assertEqual(selected_names(outcome), {"p2", "p3"})
        assert_valid_budget_allocation(outcome, instance)
        assert_ordered_relax_additive_guarantee(outcome, instance, profile)

    def test_ordered_relax_example_4_optimal_case(self):
        instance, profile, _ = make_election(
            costs_by_name={"p0": 2, "p1": 3, "p2": 3, "p3": 3, "p4": 3},
            budget=8,
            approvals_by_name=[
                {"p0", "p1"},
                {"p0", "p2"},
                {"p0", "p3"},
                {"p0", "p4"},
            ],
        )
        outcome = ordered_relax(instance, profile)
        self.assertEqual(selected_names(outcome), {"p0", "p1", "p2"})
        assert_valid_budget_allocation(outcome, instance)
        assert_ordered_relax_additive_guarantee(outcome, instance, profile)

    def test_ordered_relax_example_5_bad_case(self):
        instance, profile, _ = make_election(
            costs_by_name={"p0": 23, "p1": 68, "p2": 198, "p3": 189, "p4": 146, "p5": 38},
            budget=341,
            approvals_by_name=[{"p4"}, {"p1", "p2"}, {"p1", "p3", "p5"}],
        )
        outcome = ordered_relax(instance, profile)
        self.assertEqual(selected_names(outcome), {"p4"})
        assert_valid_budget_allocation(outcome, instance)
        assert_ordered_relax_additive_guarantee(outcome, instance, profile)

    def test_ordered_relax_example_6_large_manual_case(self):
        instance, profile, _ = make_election(
            costs_by_name={
                "p0": 18, "p1": 45, "p2": 43, "p3": 32, "p4": 28,
                "p5": 32, "p6": 5, "p7": 37, "p8": 43, "p9": 17,
            },
            budget=124,
            approvals_by_name=[
                {"p0", "p3", "p7"},
                {"p1", "p4", "p6", "p7"},
                {"p0", "p2", "p4", "p5"},
                {"p1", "p6", "p9"},
                {"p1", "p2", "p6", "p7", "p8"},
                {"p1", "p3", "p4", "p6", "p8"},
            ],
        )
        outcome = ordered_relax(instance, profile)
        self.assertEqual(selected_names(outcome), {"p1", "p2"})
        assert_valid_budget_allocation(outcome, instance)
        assert_ordered_relax_additive_guarantee(outcome, instance, profile)

    # ---------------------------------------------------------
    # Edge cases
    # ---------------------------------------------------------

    def test_ordered_relax_empty_instance_and_empty_profile(self):
        instance = Instance([], budget_limit=10)
        profile = ApprovalProfile([])
        outcome = ordered_relax(instance, profile)
        self.assertEqual(selected_names(outcome), set())
        assert_valid_budget_allocation(outcome, instance)

    def test_ordered_relax_no_projects_some_empty_ballots(self):
        instance = Instance([], budget_limit=10)
        profile = ApprovalProfile([ApprovalBallot(), ApprovalBallot()])
        outcome = ordered_relax(instance, profile)
        self.assertEqual(selected_names(outcome), set())
        assert_valid_budget_allocation(outcome, instance)

    def test_ordered_relax_zero_budget_returns_empty_allocation(self):
        instance, profile, _ = make_election(
            costs_by_name={"p1": 5, "p2": 7},
            budget=0,
            approvals_by_name=[{"p1"}, {"p2"}],
        )
        outcome = ordered_relax(instance, profile)
        self.assertEqual(selected_names(outcome), set())
        assert_valid_budget_allocation(outcome, instance)

    def test_ordered_relax_project_too_expensive_is_not_selected(self):
        instance, profile, _ = make_election(
            costs_by_name={"p1": 100}, budget=10, approvals_by_name=[{"p1"}]
        )
        outcome = ordered_relax(instance, profile)
        self.assertEqual(selected_names(outcome), set())
        assert_valid_budget_allocation(outcome, instance)

    def test_ordered_relax_initial_budget_allocation_is_preserved(self):
        instance, profile, projects = make_election(
            costs_by_name={"p1": 2, "p2": 3, "p3": 4},
            budget=5,
            approvals_by_name=[{"p1", "p2"}, {"p1", "p3"}],
        )
        outcome = ordered_relax(instance, profile, initial_budget_allocation=[projects["p1"]])
        self.assertIn(projects["p1"], outcome)
        assert_valid_budget_allocation(outcome, instance)

    def test_ordered_relax_initial_budget_allocation_over_budget_raises_value_error(self):
        instance, profile, projects = make_election(
            costs_by_name={"p1": 10}, budget=5, approvals_by_name=[{"p1"}]
        )
        with self.assertRaises(ValueError):
            ordered_relax(instance, profile, initial_budget_allocation=[projects["p1"]])

    def test_ordered_relax_irresolute_outcome_not_supported(self):
        instance, profile, _ = make_election(
            costs_by_name={"p1": 1}, budget=1, approvals_by_name=[{"p1"}]
        )
        with self.assertRaises(NotImplementedError):
            ordered_relax(instance, profile, resoluteness=False)

    def test_ordered_relax_multiprofile_not_supported(self):
        instance, profile, _ = make_election(
            costs_by_name={"p1": 1}, budget=1, approvals_by_name=[{"p1"}]
        )
        multiprofile = ApprovalMultiProfile(profile=profile)
        with self.assertRaises(NotImplementedError):
            ordered_relax(instance, multiprofile)

    # ---------------------------------------------------------
    # Random tests
    # ---------------------------------------------------------

    def test_ordered_relax_random_small_instances(self):
        for seed in range(20):
            with self.subTest(seed=seed):
                instance, profile, _ = generate_random_election(
                    seed=seed,
                    num_voters=5,
                    num_projects=12,
                    min_cost=1,
                    max_cost=30,
                    approval_probability=0.4,
                )
                outcome = ordered_relax(instance, profile)
                assert_valid_budget_allocation(outcome, instance)
                assert_ordered_relax_additive_guarantee(outcome, instance, profile)

    def test_ordered_relax_random_medium_instances(self):
        for seed in range(20, 30):
            with self.subTest(seed=seed):
                instance, profile, _ = generate_random_election(
                    seed=seed,
                    num_voters=8,
                    num_projects=20,
                    min_cost=1,
                    max_cost=50,
                    approval_probability=0.35,
                )
                outcome = ordered_relax(instance, profile)
                assert_valid_budget_allocation(outcome, instance)
                assert_ordered_relax_additive_guarantee(outcome, instance, profile)

    def test_ordered_relax_random_big_instances_with_ilp_guarantee(self):
        """
        These are larger tests. They still check the additive guarantee, but they
        solve an exact ILP to compute OPT, so they are kept as a separate test.
        """
        for seed in range(100, 103):
            with self.subTest(seed=seed):
                instance, profile, _ = generate_random_election(
                    seed=seed,
                    num_voters=15,
                    num_projects=35,
                    min_cost=1,
                    max_cost=80,
                    approval_probability=0.25,
                )
                outcome = ordered_relax(instance, profile)
                assert_valid_budget_allocation(outcome, instance)
                assert_ordered_relax_additive_guarantee(outcome, instance, profile)


if __name__ == "__main__":
    unittest.main()
