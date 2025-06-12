from pabutools.election.ballot.ordinalballot import OrdinalBallot
from pabutools.election.profile.ordinalprofile import OrdinalMultiProfile
import unittest2 as unittest
from pabutools.rules.pb_ear import pb_ear
from pabutools.election.instance import Instance, Project
from pabutools.election.profile import OrdinalProfile
from pabutools.rules.budgetallocation import BudgetAllocation
from pabutools.election.ballot.ordinalballot import FrozenOrdinalBallot


"""
Pytest test suite for validating the PB-EAR algorithm implementation.

This test file verifies:
- Edge cases like empty input or zero budget
- Correctness under randomized and large-scale scenarios
- Compliance with the IPSC axiom

Based on:
"Proportionally Representative Participatory Budgeting with Ordinal Preferences",
Haris Aziz and Barton E. Lee (2020),
https://arxiv.org/abs/1911.00864v2

Programmer: Vivian Umansky
"""

class TestPBEAR(unittest.TestCase):

    def test_empty_voters(self):
        instance = Instance([
            Project("a", 1.0),
            Project("b", 2.0)
        ], budget_limit=3.0)

        profile = OrdinalProfile([])

        result = pb_ear(instance, profile)
        self.assertIsInstance(result, BudgetAllocation)
        self.assertEqual(len(result), 0)

    def test_empty_candidates(self):
        instance = Instance([], budget_limit=3.0)
        profile = OrdinalMultiProfile()
        profile[FrozenOrdinalBallot(["a", "b"])] += 1.0  # הוספת קול עם משקל 1.0
        result = pb_ear(instance, profile)
        self.assertIsInstance(result, BudgetAllocation)
        self.assertEqual(len(result), 0)




    def test_zero_budget(self):
        instance = Instance([Project("a", 1.0), Project("b", 2.0)], budget_limit=0.0)
        profile = OrdinalMultiProfile()
        profile[FrozenOrdinalBallot(["a", "b"])] += 1.0
        result = pb_ear(instance, profile)
        self.assertIsInstance(result, BudgetAllocation)
        self.assertEqual(len(result), 0)



    def test_single_voter_single_project_enough_budget(self):
        instance = Instance([Project("a", 1.0)], budget_limit=1.0)
        profile = OrdinalMultiProfile()
        profile[FrozenOrdinalBallot(["a"])] += 1.0
        result = pb_ear(instance, profile)
        self.assertIsInstance(result, BudgetAllocation)

        selected_projects = {p.name for p in result}
        self.assertIn("a", selected_projects)



    def test_invalid_voter_type(self):
        instance = Instance([Project("a", 1.0)], budget_limit=1.0)
        profile = "invalid"  # not a profile at all

        with self.assertRaises(ValueError):
            pb_ear(instance, profile)



    def test_no_affordable_projects(self):
        instance = Instance([
            Project("a", 100.0),
            Project("b", 200.0)
        ], budget_limit=50.0)

        profile = OrdinalMultiProfile()
        profile[FrozenOrdinalBallot(["a", "b"])] += 1.0

        result = pb_ear(instance, profile)
        self.assertIsInstance(result, BudgetAllocation)
        self.assertEqual(len(result), 0)

       
    def test_large_input_uniform_preferences(self):
        """
        All voters have the same preferences and weight 1.
        They form a solid coalition over all 3 projects, each of cost 1.
        The algorithm should pick any 2 and satisfy IPSC.
        """
        num_voters = 1000
        projects = [Project("a", 1.0), Project("b", 1.0), Project("c", 1.0)]
        instance = Instance(projects, budget_limit=2.0)

        profile = OrdinalMultiProfile()
        profile[FrozenOrdinalBallot(["a", "b", "c"])] += num_voters  # add all at once

        result = pb_ear(instance, profile)
        self.assertIsInstance(result, BudgetAllocation)

        selected_cost = sum(p.cost for p in result)
        self.assertLessEqual(selected_cost, 2.0)


    def test_example_solid_coalition(self):
        projects = [
            Project("a", 1.0),
            Project("b", 1.0),
            Project("c", 1.0),
            Project("d", 1.0)
        ]
        instance = Instance(projects, budget_limit=3.0)

        profile = OrdinalMultiProfile()
        profile[FrozenOrdinalBallot(["a", "b", "c", "d"])] += 6
        profile[FrozenOrdinalBallot(["d", "c", "b", "a"])] += 2
        profile[FrozenOrdinalBallot(["c", "a", "b", "d"])] += 1

        result = pb_ear(instance, profile)
        selected = {p.name for p in result}

        self.assertEqual(selected, {"a", "b", "c"})


    def test_example_psc_unequal_costs(self):
        projects = [
            Project("a", 50.0),
            Project("b", 30.0),
            Project("c", 30.0),
            Project("d", 40.0)
        ]
        instance = Instance(projects, budget_limit=100.0)

        profile = OrdinalMultiProfile()
        profile[FrozenOrdinalBallot(["a", "b", "c", "d"])] += 30
        profile[FrozenOrdinalBallot(["d", "c", "b", "a"])] += 70

        result = pb_ear(instance, profile)
        selected = {p.name for p in result}

        self.assertEqual(selected, {"b", "c", "d"})


    def test_example_subcoalitions_joint_representation(self):
        projects = [
            Project("a", 50.0),
            Project("b", 30.0),
            Project("c", 30.0),
            Project("d", 40.0)
        ]
        instance = Instance(projects, budget_limit=100.0)

        profile = OrdinalMultiProfile()
        profile[FrozenOrdinalBallot(["a", "b", "c", "d"])] += 15
        profile[FrozenOrdinalBallot(["b", "a", "c", "d"])] += 15
        profile[FrozenOrdinalBallot(["d", "c", "b", "a"])] += 70

        result = pb_ear(instance, profile)
        selected = {p.name for p in result}

        self.assertEqual(selected, {"b", "c", "d"})



    def test_example_overlapping_coalitions(self):
        projects = [
            Project("a", 90.0),
            Project("b", 30.0),
            Project("c", 80.0),
            Project("d", 40.0)
        ]
        instance = Instance(projects, budget_limit=100.0)

        profile = OrdinalMultiProfile()
        profile[FrozenOrdinalBallot(["a", "b", "c", "d"])] += 14
        profile[FrozenOrdinalBallot(["a", "c", "b", "d"])] += 16
        profile[FrozenOrdinalBallot(["c", "a", "b", "d"])] += 70

        result = pb_ear(instance, profile)
        selected = {p.name for p in result}

        self.assertIn(selected, [{"a"}, {"c"}])  # Both are acceptable IPSC outcomes



    def test_example_single_voter_no_cpsc(self):
        projects = [
            Project("a", 3.0),
            Project("b", 2.0),
            Project("c", 2.0),
            Project("d", 2.0)
        ]
        instance = Instance(projects, budget_limit=4.0)

        profile = OrdinalMultiProfile()
        profile[FrozenOrdinalBallot(["a", "b", "c", "d"])] += 1

        result = pb_ear(instance, profile)
        selected = {p.name for p in result}

        self.assertEqual(selected, {"a"})


    def test_example_perfect_ipsc_three_groups(self):
        projects = [
            Project("a", 1.0),
            Project("b", 1.0),
            Project("c", 1.0),
            Project("d", 1.0)
        ]
        instance = Instance(projects, budget_limit=3.0)

        profile = OrdinalMultiProfile()
        profile[FrozenOrdinalBallot(["a", "b", "c", "d"])] += 2
        profile[FrozenOrdinalBallot(["b", "a", "c", "d"])] += 2
        profile[FrozenOrdinalBallot(["c", "d", "a", "b"])] += 2

        result = pb_ear(instance, profile)
        selected = {p.name for p in result}

        self.assertEqual(selected, {"a", "b", "c"})


    def test_example_big_group_expensive_project(self):
        projects = [
            Project("a", 9.0),
            Project("b", 1.0),
            Project("c", 1.0),
            Project("d", 1.0)
        ]
        instance = Instance(projects, budget_limit=10.0)

        profile = OrdinalMultiProfile()
        profile[FrozenOrdinalBallot(["a", "b", "c", "d"])] += 7
        profile[FrozenOrdinalBallot(["d", "c", "b", "a"])] += 3

        result = pb_ear(instance, profile)
        selected = {p.name for p in result}

        self.assertEqual(selected, {"b", "c", "d"})

    def test_example_complex_weights_and_preferences(self):
        projects = [
            Project("a", 50.0),
            Project("b", 40.0),
            Project("c", 35.0),
            Project("d", 30.0),
            Project("e", 20.0),
            Project("f", 15.0),
            Project("g", 10.0)
        ]
        instance = Instance(projects, budget_limit=100.0)

        profile = OrdinalMultiProfile()
        profile[FrozenOrdinalBallot(["a", "b", "c", "d", "e", "f", "g"])] += 0.5
        profile[FrozenOrdinalBallot(["a", "c", "d", "e", "b", "g", "f"])] += 1.5
        profile[FrozenOrdinalBallot(["a", "d", "b", "c", "e", "f", "g"])] += 1.0
        profile[FrozenOrdinalBallot(["b", "c", "d", "e", "a", "g", "f"])] += 1.0
        profile[FrozenOrdinalBallot(["b", "c", "e", "d", "g", "a", "f"])] += 0.8
        profile[FrozenOrdinalBallot(["c", "d", "e", "b", "g", "a", "f"])] += 1.2
        profile[FrozenOrdinalBallot(["d", "e", "f", "c", "g", "b", "a"])] += 1.0

        result = pb_ear(instance, profile)
        selected = {p.name for p in result}

        self.assertIn(selected, [{"c", "d", "e", "f"}, {"c", "d", "e", "g"}])
