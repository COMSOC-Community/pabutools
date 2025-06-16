"""
An implementation of the algorithms in:
"Participatory Budgeting with Cumulative Votes", by Piotr Skowron, Arkadii Slinko, Stanisaw Szufa,
Nimrod Talmon (2020), https://arxiv.org/pdf/2009.02690
Programmer: Achiya Ben Natan
Date: 2024/05/16.
"""

import unittest
from copy import deepcopy

from pabutools.election import Project, CumulativeBallot, Instance, CumulativeProfile
from pabutools.fractions import frac, FRACTION, FLOAT_FRAC
import pabutools.fractions
from pabutools.rules.cstv import cstv, CSTV_Combination
import random


class TestFunctions(unittest.TestCase):
    def setUp(self):
        self.p1 = Project("A", 27)
        self.p2 = Project("B", 30)
        self.p3 = Project("C", 40)
        self.instance = Instance([self.p1, self.p2, self.p3])
        self.donors = CumulativeProfile(
            [
                CumulativeBallot({self.p1: 5, self.p2: 10, self.p3: 5}),
                CumulativeBallot({self.p1: 10, self.p2: 10, self.p3: 0}),
                CumulativeBallot({self.p1: 0, self.p2: 15, self.p3: 5}),
                CumulativeBallot({self.p1: 0, self.p2: 0, self.p3: 20}),
                CumulativeBallot({self.p1: 15, self.p2: 5, self.p3: 0}),
            ]
        )

    def test_cstv_budgeting_with_zero_budget(self):
        # Ensure no projects are selected when budget is zero
        for donor in self.donors:
            for key in donor.keys():
                donor[key] = 0
        for combination in CSTV_Combination:
            for verbose in [True, False]:
                with self.subTest(combination=combination):
                    selected_projects = cstv(self.instance, self.donors, combination, verbose=verbose)
                    self.assertEqual(
                        len(selected_projects), 0
                    )

    def test_cstv_budgeting_with_budget_less_than_min_project_cost(self):
        # Ensure no projects are selected when total budget is less than the minimum project cost
        for donor in self.donors:
            donor[self.p1] = 1
            donor[self.p2] = 1
            donor[self.p3] = 1
        for combination in CSTV_Combination:
            for verbose in [True, False]:
                with self.subTest(combination=combination):
                    selected_projects = cstv(self.instance, self.donors, combination, verbose=verbose)
                    self.assertEqual(
                        len(selected_projects), 0
                    )

    def test_cstv_budgeting_with_budget_greater_than_max_total_needed_support(self):
        # Ensure all projects are selected when budget exceeds the total needed support
        donors = deepcopy(self.donors)
        for donor in donors:
            for key in donor.keys():
                donor[key] = 100
        for combination in CSTV_Combination:
            for verbose in [True, False]:
                with self.subTest(combination=combination):
                    selected_projects = cstv(self.instance, donors, combination, verbose=verbose)
                    self.assertEqual(
                        len(selected_projects), len(self.instance)
                    )

    def test_cstv_budgeting_with_budget_between_min_and_max(self):
        # Ensure the number of selected projects is 2 when total budget is between the minimum and maximum costs
        for combination in CSTV_Combination:
            for verbose in [True, False]:
                with self.subTest(combination=combination):
                    selected_projects = cstv(self.instance, self.donors, combination, verbose=verbose)
                    self.assertEqual(
                        len(selected_projects), 2
                    )

    def test_cstv_budgeting_with_budget_exactly_matching_required_support(self):
        # Ensure all projects are selected when the total budget matches the required support exactly
        for combination in CSTV_Combination:
            for donor in self.donors:
                donor[self.p1] = frac(self.p1.cost, len(self.donors))
                donor[self.p2] = frac(self.p2.cost, len(self.donors))
                donor[self.p3] = frac(self.p3.cost, len(self.donors))
            for verbose in [True, False]:
                with self.subTest(combination=combination):
                    selected_projects = cstv(self.instance, self.donors, combination, verbose=verbose)
                    self.assertEqual(
                        len(selected_projects), 3
                    )

    def test_cstv_budgeting_large_input(self):
        # Ensure the number of selected projects does not exceed the total number of projects
        for combination in CSTV_Combination:
            projects = [Project(f"Project_{i}", 50) for i in range(50)]
            projects += [Project(f"Project_{i+50}", 151) for i in range(50)]
            instance = Instance(projects)
            donors = CumulativeProfile(
                [
                    CumulativeBallot({projects[i]: 1 for i in range(len(projects))})
                    for _ in range(100)
                ]
            )
            with self.subTest(combination=combination):
                selected_projects = cstv(instance, donors, combination)
                self.assertLessEqual(
                    len(selected_projects), len(projects)
                )

    def test_cstv_budgeting_large_random_input(self):
        pabutools.fractions.FRACTION = FLOAT_FRAC
        for combination in CSTV_Combination:
            projects = [
                Project(f"Project_{i}", random.randint(100, 1000)) for i in range(100)
            ]
            instance = Instance(projects)

            # Function to generate a list of donations that sums up to total_donation
            def generate_donations(total_donation, m):
                donations = [0] * m
                for _ in range(total_donation):
                    donations[random.randint(0, m - 1)] += 1
                return donations

            # Generate the donations for each donor
            donors = CumulativeProfile(
                [
                    CumulativeBallot(
                        {
                            projects[i]: donation
                            for i, donation in enumerate(
                                generate_donations(20, len(projects))
                            )
                        }
                    )
                    for _ in range(100)
                ]
            )
            num_projects = len(projects)
            positive_excess = sum(
                1
                for p in projects
                if sum(donor.get(p, 0) for donor in donors) - p.cost >= 0
            )
            support = sum(sum(donor.values()) for donor in donors)

            with self.subTest(combination=combination):
                selected_projects = cstv(instance, donors, combination)
                total_cost = sum(project.cost for project in selected_projects)
                # Ensure the number of selected projects does not exceed the total number of projects
                self.assertLessEqual(len(selected_projects), num_projects)
                # Ensure the number of selected projects is at least the number of projects with non-negative excess support
                self.assertGreaterEqual(len(selected_projects), positive_excess)
                # Ensure the total initial support from donors is at least the total cost of the selected projects
                self.assertGreaterEqual(support, total_cost)
