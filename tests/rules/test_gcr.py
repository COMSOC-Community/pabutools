"""
Tests for the Greedy Cohesive Rule (GCR) implementation.

Each test verifies a specific property of GCR:
  - Output is a feasible budget allocation
  - FJR: every (β,T)-cohesive group has ≥ β approved projects selected
  - Edge cases: no preferences, full budget available, single project
"""

from unittest import TestCase

from pabutools.election.ballot import ApprovalBallot
from pabutools.election.instance import Instance, Project, total_cost
from pabutools.election.profile import ApprovalProfile
from pabutools.rules.budgetallocation import BudgetAllocation
from pabutools.rules.gcr import GCRAllocationDetails, greedy_cohesive_rule


def check_fjr(instance, profile, allocation):
    """
    Returns True if the allocation satisfies Fair Justified Representation (FJR).

    FJR: for every positive integer β and every set T such that a group N'
    of active voters is weakly (β,T)-cohesive (all voters approve all of T,
    and |N'|·B ≥ β·|N|·cost(T)), at least ONE voter i ∈ N' must have
    ≥ β approved projects in the selected allocation.
    """
    n = profile.num_ballots()
    B = instance.budget_limit
    ballots = list(profile)
    projects = list(instance)

    # Pre-compute each voter's satisfaction (# approved projects selected)
    voter_sat = [
        sum(1 for p in allocation if p in ballots[i])
        for i in range(n)
    ]

    from itertools import combinations

    for r in range(1, len(projects) + 1):
        for T in combinations(projects, r):
            cost_T = total_cost(T)
            if cost_T <= 0:
                continue
            # N'(T) = voters who approve every project in T
            N_prime = [i for i in range(n) if all(p in ballots[i] for p in T)]
            if not N_prime:
                continue
            beta = int(len(N_prime) * B / (n * cost_T))
            if beta < 1:
                continue
            # FJR: at least one voter in N' has satisfaction >= beta
            if not any(voter_sat[i] >= beta for i in N_prime):
                return False
    return True


class TestGreedyCohesiveRule(TestCase):

    def _make_instance(self, costs, budget):
        projects = [Project(name, cost) for name, cost in costs.items()]
        return Instance(projects, budget_limit=budget)

    def _make_profile(self, instance, ballots_spec):
        """ballots_spec: list of sets of project names"""
        proj_map = {p.name: p for p in instance}
        ballots = [
            ApprovalBallot([proj_map[name] for name in names])
            for names in ballots_spec
        ]
        return ApprovalProfile(ballots, instance=instance)

    # ------------------------------------------------------------------
    # Basic feasibility tests
    # ------------------------------------------------------------------

    def test_output_is_budget_allocation(self):
        instance = self._make_instance({"a": 30, "b": 30}, budget=60)
        profile = self._make_profile(instance, [{"a"}, {"b"}])
        result = greedy_cohesive_rule(instance, profile)
        self.assertIsInstance(result, BudgetAllocation)

    def test_allocation_is_feasible(self):
        instance = self._make_instance({"a": 30, "b": 40, "c": 20}, budget=60)
        profile = self._make_profile(instance, [{"a", "b"}, {"b", "c"}, {"a", "c"}])
        result = greedy_cohesive_rule(instance, profile)
        self.assertTrue(instance.is_feasible(result))

    # ------------------------------------------------------------------
    # Correctness: simple hand-verifiable cases
    # ------------------------------------------------------------------

    def test_unanimous_single_project(self):
        """All voters approve the same project; it must be selected."""
        instance = self._make_instance({"p1": 50}, budget=100)
        profile = self._make_profile(instance, [{"p1"}, {"p1"}, {"p1"}])
        result = greedy_cohesive_rule(instance, profile)
        names = {p.name for p in result}
        self.assertIn("p1", names)

    def test_two_disjoint_groups(self):
        """
        Two equally-sized disjoint groups with equal-cost projects.
        GCR should select both (one project per group, budget covers both).
        """
        instance = self._make_instance({"a": 30, "b": 30}, budget=60)
        profile = self._make_profile(instance, [{"a"}, {"a"}, {"b"}, {"b"}])
        result = greedy_cohesive_rule(instance, profile)
        names = {p.name for p in result}
        self.assertIn("a", names)
        self.assertIn("b", names)

    def test_larger_group_wins_tiebreak(self):
        """
        Two projects with equal cost; one approved by 3 of 4 voters, other by 1.
        Budget is 80, so the majority group (3 voters) is barely β=1 cohesive
        (3*80 = 240 >= 1*4*60 = 240), while the minority (1 voter) is not.
        GCR must select 'maj'.
        """
        instance = self._make_instance({"maj": 60, "min": 60}, budget=80)
        profile = self._make_profile(
            instance, [{"maj"}, {"maj"}, {"maj"}, {"min"}]
        )
        result = greedy_cohesive_rule(instance, profile)
        names = {p.name for p in result}
        self.assertIn("maj", names)

    def test_empty_approval_selects_nothing(self):
        """When no voter approves anything, GCR returns an empty allocation."""
        instance = self._make_instance({"a": 10, "b": 10}, budget=100)
        profile = self._make_profile(instance, [set(), set()])
        result = greedy_cohesive_rule(instance, profile)
        self.assertEqual(len(result), 0)

    def test_two_disjoint_voters_both_selected(self):
        """
        Two voters with disjoint preferences, budget covers both projects.
        GCR selects x first (higher β), deactivates voter 0, then selects y.
        Both projects end up in the allocation.
        """
        instance = self._make_instance({"x": 10, "y": 20}, budget=100)
        profile = self._make_profile(instance, [{"x"}, {"y"}])
        result = greedy_cohesive_rule(instance, profile)
        names = {p.name for p in result}
        self.assertIn("x", names)
        self.assertIn("y", names)

    # ------------------------------------------------------------------
    # FJR property
    # ------------------------------------------------------------------

    def test_fjr_three_voters_three_projects(self):
        """GCR output satisfies FJR on a small instance."""
        instance = self._make_instance({"a": 10, "b": 10, "c": 10}, budget=20)
        profile = self._make_profile(
            instance,
            [{"a", "b"}, {"a", "c"}, {"b", "c"}],
        )
        result = greedy_cohesive_rule(instance, profile)
        self.assertTrue(check_fjr(instance, profile, result))

    def test_fjr_disjoint_groups(self):
        instance = self._make_instance({"a": 30, "b": 30, "c": 30}, budget=60)
        profile = self._make_profile(
            instance,
            [{"a"}, {"a"}, {"b"}, {"b"}, {"c"}],
        )
        result = greedy_cohesive_rule(instance, profile)
        self.assertTrue(check_fjr(instance, profile, result))

    # ------------------------------------------------------------------
    # Analytics
    # ------------------------------------------------------------------

    def test_analytics_structure(self):
        instance = self._make_instance({"a": 30, "b": 30}, budget=60)
        profile = self._make_profile(instance, [{"a"}, {"a"}, {"b"}, {"b"}])
        result = greedy_cohesive_rule(instance, profile, analytics=True)
        self.assertIsInstance(result.details, GCRAllocationDetails)
        self.assertGreater(len(result.details.iterations), 0)
        first = result.details.iterations[0]
        self.assertGreaterEqual(first.beta, 1)
        self.assertIsInstance(first.selected_projects, list)
        self.assertIsInstance(first.deactivated_voters, list)

    def test_analytics_none_without_flag(self):
        instance = self._make_instance({"a": 30}, budget=60)
        profile = self._make_profile(instance, [{"a"}])
        result = greedy_cohesive_rule(instance, profile, analytics=False)
        self.assertIsNone(result.details)

    # ------------------------------------------------------------------
    # max_subset_size parameter
    # ------------------------------------------------------------------

    def test_max_subset_size_one_still_feasible(self):
        """With max_subset_size=1, output must still be feasible."""
        instance = self._make_instance(
            {"a": 20, "b": 20, "c": 20}, budget=40
        )
        profile = self._make_profile(
            instance, [{"a", "b"}, {"a", "c"}, {"b", "c"}]
        )
        result = greedy_cohesive_rule(instance, profile, max_subset_size=1)
        self.assertTrue(instance.is_feasible(result))
