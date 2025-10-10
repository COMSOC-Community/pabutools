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
        self.do_verbose = [False]
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
            for verbose in self.do_verbose:
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
            for verbose in self.do_verbose:
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
            for verbose in self.do_verbose:
                with self.subTest(combination=combination):
                    selected_projects = cstv(self.instance, donors, combination, verbose=verbose)
                    self.assertEqual(
                        len(selected_projects), len(self.instance)
                    )

    def test_cstv_budgeting_with_budget_between_min_and_max(self):
        # Ensure the number of selected projects is 2 when total budget is between the minimum and maximum costs
        for donor in self.donors:
            donor[self.p1] = 5
            donor[self.p2] = 5
            donor[self.p3] = 5
        for combination in CSTV_Combination:
            for verbose in self.do_verbose:
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
            for verbose in self.do_verbose:
                with self.subTest(combination=combination):
                    selected_projects = cstv(self.instance, self.donors, combination, verbose=verbose)
                    self.assertEqual(
                        len(selected_projects), 3
                    )

    def test_cstv_budgeting_with_single_project_consuming_most_support(self):
        # Ensure all projects are selected when the total budget matches the required support exactly
        for combination in CSTV_Combination:
            self.donors = CumulativeProfile(
                [
                    CumulativeBallot({self.p1: 20, self.p2: 0, self.p3: 0}),
                    CumulativeBallot({self.p1: 20, self.p2: 0, self.p3: 0}),
                    CumulativeBallot({self.p1: 0, self.p2: 20, self.p3: 0}),
                ]
            )
            for verbose in self.do_verbose:
                with self.subTest(combination=combination):
                    selected_projects = cstv(self.instance, self.donors, combination, verbose=verbose)
                    self.assertEqual(
                        len(selected_projects), 2
                    )

    def test_cstv_budgeting_maximality_is_achieved_with_low_support(self):
        for combination in CSTV_Combination:
            self.p1 = Project("A", 10)
            self.p2 = Project("B", 10)
            self.p3 = Project("C", 10)
            self.p4 = Project("D", 10)
            self.instance = Instance([self.p1, self.p2, self.p3, self.p4])
            self.donors = CumulativeProfile(
                [
                    CumulativeBallot({self.p1: 10, self.p2: 5, self.p3: 0, self.p4: 0}),
                    CumulativeBallot({self.p1: 0, self.p2: 0, self.p3: 5, self.p4: 10}),
                ]
            )
        for verbose in self.do_verbose:
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

    def test_cstv_party_split(self):
        for combination in CSTV_Combination:
            projects = [
                Project('A1', 200),
                Project('A2', 120),
                Project('A3', 80),
                Project('B1', 150),
                Project('B2', 100),
                Project('B3', 70),
                Project('C1', 160),
                Project('C2', 90),
                Project('C3', 80),
            ]
            instance = Instance(projects)
            donors = CumulativeProfile(
                [
                    CumulativeBallot({projects[i]: 0 for i in range(len(projects))})
                    for _ in range(8)
                ]
            )
            donors[0][projects[0]] = 50
            donors[0][projects[1]] = 30
            donors[0][projects[2]] = 20
            donors[1][projects[0]] = 30
            donors[1][projects[1]] = 40
            donors[1][projects[2]] = 30
            donors[2][projects[0]] = 50
            donors[2][projects[1]] = 45
            donors[2][projects[2]] = 5

            donors[3][projects[3]] = 50
            donors[3][projects[4]] = 40
            donors[3][projects[5]] = 10
            donors[4][projects[3]] = 30
            donors[4][projects[4]] = 40
            donors[4][projects[5]] = 30
            donors[5][projects[3]] = 50
            donors[5][projects[4]] = 25
            donors[5][projects[5]] = 25

            donors[6][projects[6]] = 70
            donors[6][projects[7]] = 20
            donors[6][projects[8]] = 10
            donors[7][projects[6]] = 50
            donors[7][projects[7]] = 40
            donors[7][projects[8]] = 10

            with self.subTest(combination=combination):
                selected_projects = cstv(instance, donors, combination)
                match combination:
                    case CSTV_Combination.EWT | CSTV_Combination.EWTC:
                        self.assertSetEqual(set(selected_projects), {
                            projects[4], 
                            projects[1], 
                            projects[2], 
                            projects[7], 
                            projects[5], 
                            projects[3],
                            projects[6]
                            })
                    case CSTV_Combination.EWTS:
                        self.assertSetEqual(set(selected_projects), {
                            projects[4], 
                            projects[1],  
                            projects[6], 
                            projects[3], 
                            projects[5],
                            projects[0]
                            })
                    case CSTV_Combination.MT:
                        self.assertSetEqual(set(selected_projects), {
                            projects[4], 
                            projects[5],  
                            projects[1], 
                            projects[2],
                            projects[7],
                            projects[8],
                            projects[3]
                            })
                    case CSTV_Combination.MTC:
                        self.assertSetEqual(set(selected_projects), {
                            projects[4], 
                            projects[5],  
                            projects[1], 
                            projects[2],
                            projects[6],
                            projects[3],
                            projects[7]
                            })
                    case CSTV_Combination.MTS:
                        self.assertSetEqual(set(selected_projects), {
                            projects[4], 
                            projects[0],  
                            projects[3],
                            projects[6],
                            projects[2],
                            projects[5]
                            })

    def test_cstv_laminal1(self):
        for combination in CSTV_Combination:
            projects = [
                Project('L1', 200),
                Project('L2', 200),
                Project('A1', 150),
                Project('A2', 120),
                Project('A3', 100),
                Project('A4', 90),
                Project('A5', 80),
                Project('B1', 110),
                Project('B2', 100),
                Project('B3', 70),
                Project('B4', 60),
                Project('C1', 130),
                Project('C2', 110),
                Project('C3', 90),
                Project('C4', 70),
            ]
            instance = Instance(projects)
            donors = CumulativeProfile(
                [
                    CumulativeBallot({projects[i]: 0 for i in range(len(projects))})
                    for _ in range(9)
                ]
            )
            donors[0][projects[0]] = 20
            donors[0][projects[1]] = 10
            donors[0][projects[2]] = 30
            donors[0][projects[3]] = 20
            donors[0][projects[4]] = 10
            donors[0][projects[5]] = 5
            donors[0][projects[6]] = 5
            donors[1][projects[0]] = 40
            donors[1][projects[1]] = 10
            donors[1][projects[2]] = 10
            donors[1][projects[3]] = 10
            donors[1][projects[4]] = 10
            donors[1][projects[5]] = 10
            donors[1][projects[6]] = 10
            donors[2][projects[0]] = 25
            donors[2][projects[1]] = 5
            donors[2][projects[2]] = 15
            donors[2][projects[3]] = 5
            donors[2][projects[4]] = 25
            donors[2][projects[5]] = 15
            donors[2][projects[6]] = 10
            donors[3][projects[0]] = 5
            donors[3][projects[1]] = 25
            donors[3][projects[2]] = 20
            donors[3][projects[3]] = 5
            donors[3][projects[4]] = 5
            donors[3][projects[5]] = 5
            donors[3][projects[6]] = 35

            donors[4][projects[0]] = 35
            donors[4][projects[1]] = 5
            donors[4][projects[7]] = 25
            donors[4][projects[8]] = 25
            donors[4][projects[9]] = 5
            donors[4][projects[10]] = 5
            donors[5][projects[0]] = 5
            donors[5][projects[1]] = 15
            donors[5][projects[7]] = 35
            donors[5][projects[8]] = 15
            donors[5][projects[9]] = 25
            donors[5][projects[10]] = 5
            donors[6][projects[0]] = 15
            donors[6][projects[1]] = 15
            donors[6][projects[7]] = 25
            donors[6][projects[8]] = 15
            donors[6][projects[9]] = 15
            donors[6][projects[10]] = 15

            donors[7][projects[0]] = 25
            donors[7][projects[1]] = 5
            donors[7][projects[11]] = 25
            donors[7][projects[12]] = 15
            donors[7][projects[13]] = 25
            donors[7][projects[14]] = 5
            donors[8][projects[0]] = 15
            donors[8][projects[1]] = 15
            donors[8][projects[11]] = 35
            donors[8][projects[12]] = 15
            donors[8][projects[13]] = 5
            donors[8][projects[14]] = 15


            with self.subTest(combination=combination):
                selected_projects = cstv(instance, donors, combination)
                match combination:
                    case CSTV_Combination.EWT:
                        self.assertSetEqual(set(selected_projects), {
                            projects[0], 
                            projects[6],  
                            projects[7],
                            projects[9],
                            projects[10],
                            projects[11],
                            projects[4],
                            projects[2],
                            })
                    case CSTV_Combination.EWTC:
                        self.assertSetEqual(set(selected_projects), {
                            projects[0], 
                            projects[7],  
                            projects[9],
                            projects[6],
                            projects[4],
                            projects[1],
                            projects[11],
                            })
                    case CSTV_Combination.EWTS:
                        self.assertSetEqual(set(selected_projects), {
                            projects[0], 
                            projects[7],  
                            projects[6],
                            projects[1],
                            projects[2],
                            projects[11],
                            })
                    case CSTV_Combination.MT:
                        self.assertSetEqual(set(selected_projects), {
                            projects[0], 
                            projects[6],  
                            projects[9],
                            projects[7],
                            projects[10],
                            projects[14],
                            projects[4],
                            projects[5],
                            projects[13]
                            })
                    case CSTV_Combination.MTC:
                        self.assertSetEqual(set(selected_projects), {
                            projects[0], 
                            projects[7],  
                            projects[6],
                            projects[9],
                            projects[4],
                            projects[11],
                            projects[1],
                            })
                    case CSTV_Combination.MTS:
                        self.assertSetEqual(set(selected_projects), {
                            projects[0], 
                            projects[1],  
                            projects[7],
                            projects[2],
                            projects[13],
                            projects[10],
                            projects[6],
                            })
    
    def test_cstv_laminal2(self):
        for combination in CSTV_Combination:
            projects = [
                Project('L1', 200),
                Project('L2', 200),
                Project('ABC', 170),
                Project('AB1', 150),
                Project('AB2', 130),
                Project('AB3', 110),
                Project('A1', 80),
                Project('A2', 60),
                Project('B', 70),
                Project('C1', 90),
                Project('C2', 80),
                Project('C3', 60),
                Project('D1', 110),
                Project('D2', 90),
                Project('D3', 90),
            ]
            instance = Instance(projects)
            donors = CumulativeProfile(
                [
                    CumulativeBallot({projects[i]: 0 for i in range(len(projects))})
                    for _ in range(9)
                ]
            )
            donors[0][projects[0]] = 20
            donors[0][projects[1]] = 10
            donors[0][projects[2]] = 15
            donors[0][projects[3]] = 15
            donors[0][projects[4]] = 15
            donors[0][projects[5]] = 10
            donors[0][projects[6]] = 5
            donors[0][projects[7]] = 10
            donors[1][projects[0]] = 40
            donors[1][projects[1]] = 10
            donors[1][projects[2]] = 20
            donors[1][projects[3]] = 5
            donors[1][projects[4]] = 5
            donors[1][projects[5]] = 5
            donors[1][projects[6]] = 10
            donors[1][projects[7]] = 5
            donors[2][projects[0]] = 25
            donors[2][projects[1]] = 5
            donors[2][projects[2]] = 15
            donors[2][projects[3]] = 10
            donors[2][projects[4]] = 20
            donors[2][projects[5]] = 5
            donors[2][projects[8]] = 20
            donors[3][projects[0]] = 5
            donors[3][projects[1]] = 25
            donors[3][projects[2]] = 15
            donors[3][projects[3]] = 15
            donors[3][projects[4]] = 5
            donors[3][projects[5]] = 10
            donors[3][projects[8]] = 25

            donors[4][projects[0]] = 35
            donors[4][projects[1]] = 5
            donors[4][projects[2]] = 15
            donors[4][projects[9]] = 15
            donors[4][projects[10]] = 20
            donors[4][projects[11]] = 10
            donors[5][projects[0]] = 5
            donors[5][projects[1]] = 15
            donors[5][projects[2]] = 25
            donors[5][projects[9]] = 25
            donors[5][projects[10]] = 15
            donors[5][projects[11]] = 15

            donors[6][projects[0]] = 15
            donors[6][projects[1]] = 15
            donors[6][projects[12]] = 35
            donors[6][projects[13]] = 25
            donors[6][projects[14]] = 10
            donors[7][projects[0]] = 25
            donors[7][projects[1]] = 5
            donors[7][projects[12]] = 25
            donors[7][projects[13]] = 20
            donors[7][projects[14]] = 25
            donors[8][projects[0]] = 15
            donors[8][projects[1]] = 15
            donors[8][projects[12]] = 50
            donors[8][projects[13]] = 15
            donors[8][projects[14]] = 5


            with self.subTest(combination=combination):
                selected_projects = cstv(instance, donors, combination)
                match combination:
                    case CSTV_Combination.EWT:
                        self.assertSetEqual(set(selected_projects), {
                            projects[12], 
                            projects[0],  
                            projects[8],
                            projects[2],
                            projects[7],
                            projects[13],
                            projects[11],
                            projects[10],
                            })
                    case CSTV_Combination.EWTC:
                        self.assertSetEqual(set(selected_projects), {
                            projects[12], 
                            projects[0],  
                            projects[8],
                            projects[2],
                            projects[1],
                            projects[13],
                            projects[11],
                            })
                    case CSTV_Combination.EWTS:
                        self.assertSetEqual(set(selected_projects), {
                            projects[12], 
                            projects[0],  
                            projects[2],
                            projects[1],
                            projects[13],
                            projects[4],
                            })
                    case CSTV_Combination.MT:
                        self.assertSetEqual(set(selected_projects), {
                            projects[12], 
                            projects[0],  
                            projects[8],
                            projects[13],
                            projects[11],
                            projects[7],
                            projects[10],
                            projects[5],
                            projects[14],
                            })
                    case CSTV_Combination.MTC:
                        self.assertSetEqual(set(selected_projects), {
                            projects[12], 
                            projects[0],  
                            projects[13],
                            projects[8],
                            projects[2],
                            projects[1],
                            projects[11],
                            })
                    case CSTV_Combination.MTS:
                        self.assertSetEqual(set(selected_projects), {
                            projects[12], 
                            projects[0],  
                            projects[1],
                            projects[2],
                            projects[13],
                            projects[4],
                            })

    def test_cstv_EWT_v_MT(self):
        for combination in CSTV_Combination:
            projects = [
                Project('A', 20),
                Project('B', 26),
                Project('C', 30),
                Project('D', 30),
            ]
            instance = Instance(projects)
            donors = CumulativeProfile(
                [
                    CumulativeBallot({projects[0]: 15, projects[1]: 7, projects[2]: 0, projects[3]: 0}),
                    CumulativeBallot({projects[0]: 1, projects[1]: 7, projects[2]: 10, projects[3]: 4}),
                ]
            )
            with self.subTest(combination=combination):
                selected_projects = cstv(instance, donors, combination)
                match combination:
                    case CSTV_Combination.EWT | CSTV_Combination.EWTC | CSTV_Combination.EWTS:
                        self.assertSetEqual(set(selected_projects), {
                            projects[1], 
                            })
                    case CSTV_Combination.MT | CSTV_Combination.MTC | CSTV_Combination.MTS:
                        self.assertSetEqual(set(selected_projects), {
                            projects[0], 
                            })
    
    def test_cstv_Greedy_difference(self):
        for combination in CSTV_Combination:
            projects = [
                Project('A', 2200),
                Project('B', 1720),
                Project('C', 2800),
                Project('D', 400),
                Project('E', 400),
                Project('F', 400),
            ]
            instance = Instance(projects)
            donors = CumulativeProfile(
                [
                    CumulativeBallot({projects[0]: 2000, projects[1]: 10, projects[2]: 500, projects[3]: 5, projects[4]: 1, projects[5]: 1}),
                    CumulativeBallot({projects[0]: 10, projects[1]: 2000, projects[2]: 500, projects[3]: 1, projects[4]: 5, projects[5]: 1}),
                    CumulativeBallot({projects[0]: 500, projects[1]: 10, projects[2]: 2000, projects[3]: 1, projects[4]: 1, projects[5]: 5}),
                ]
            )
            with self.subTest(combination=combination):
                selected_projects = cstv(instance, donors, combination)
                match combination:
                    case CSTV_Combination.EWT | CSTV_Combination.MT:
                        self.assertSetEqual(set(selected_projects), {
                            projects[0], 
                            projects[2], 
                            projects[1], 
                            projects[4],
                            projects[5],
                            })
                    case CSTV_Combination.EWTC | CSTV_Combination.MTC:
                        self.assertSetEqual(set(selected_projects), {
                            projects[1], 
                            projects[2], 
                            projects[0], 
                            projects[3],
                            projects[5],
                            })
                    case CSTV_Combination.EWTS | CSTV_Combination.MTS:
                        self.assertSetEqual(set(selected_projects), {
                            projects[2], 
                            projects[0], 
                            projects[1], 
                            projects[4],
                            projects[3],
                            })
                        
    def test_cstv_small(self):
        for combination in CSTV_Combination:
            projects = [
                Project('A', 20),
                Project('B', 35),
                Project('C', 40),
                Project('D', 40),
                Project('E', 20),
            ]
            instance = Instance(projects)
            donors = CumulativeProfile(
                [
                    CumulativeBallot({projects[0]: 10, projects[1]: 7, projects[2]: 3, projects[3]: 0, projects[4]: 0}),
                    CumulativeBallot({projects[0]: 10, projects[1]: 8, projects[2]: 1, projects[3]: 1, projects[4]: 0}),
                    CumulativeBallot({projects[0]: 10, projects[1]: 0, projects[2]: 5, projects[3]: 3, projects[4]: 2}),
                    CumulativeBallot({projects[0]: 10, projects[1]: 0, projects[2]: 5, projects[3]: 5, projects[4]: 0}),
                ]
            )
            with self.subTest(combination=combination):
                selected_projects = cstv(instance, donors, combination)
                self.assertSetEqual(set(selected_projects), {
                    projects[0], 
                    projects[2], 
                    projects[4], 
                    })



