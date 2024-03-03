from unittest import TestCase

from pabutools.analysis.instanceproperties import *
from pabutools.analysis.profileproperties import *
from pabutools.analysis.votersatisfaction import *
from pabutools.analysis.category import *
from pabutools.analysis.projectloss import *
from pabutools.election import CardinalProfile
from pabutools.election.profile.approvalprofile import (
    ApprovalProfile,
)

from pabutools.election.satisfaction import (
    Cost_Sat,
    Additive_Borda_Sat,
    Cardinality_Sat,
)
from pabutools.election.ballot import ApprovalBallot, OrdinalBallot, CardinalBallot
from pabutools.election.profile import OrdinalProfile
from pabutools.election.satisfaction.additivesatisfaction import (
    Relative_Cardinality_Sat,
)
from pabutools.fractions import frac
from pabutools.rules.budgetallocation import BudgetAllocation
from pabutools.rules.mes import MESAllocationDetails, MESIteration
from pabutools.rules.mes.mes_details import MESProjectDetails


class TestAnalysis(TestCase):
    def test_satisfaction_properties(self):
        projects = [Project(str(i), 10 + i) for i in range(10)]
        instance = Instance(projects, budget_limit=90)
        app_ball_1 = ApprovalBallot(
            [projects[0], projects[1], projects[2], projects[3]]
        )
        app_ball_2 = ApprovalBallot([projects[0]])
        app_ball_3 = ApprovalBallot([projects[0]])
        app_ball_4 = ApprovalBallot([projects[5], projects[6]])
        app_ball_5 = ApprovalBallot([projects[8], projects[9]])
        app_profile = ApprovalProfile(
            [app_ball_1, app_ball_2, app_ball_3, app_ball_4, app_ball_5]
        )
        app_multi_profile = app_profile.as_multiprofile()

        budget_allocation = [projects[0], projects[1], projects[8], projects[9]]

        assert avg_satisfaction(
            instance, app_profile, budget_allocation, Cost_Sat
        ) == frac(78, 5)
        assert avg_satisfaction(
            instance, app_multi_profile, budget_allocation, Cost_Sat
        ) == frac(78, 5)
        assert percent_non_empty_handed(
            instance, app_profile, budget_allocation
        ) == frac(4, 5)
        assert percent_non_empty_handed(
            instance, app_multi_profile, budget_allocation
        ) == frac(4, 5)
        assert gini_coefficient_of_satisfaction(
            instance, app_profile, budget_allocation, Cardinality_Sat
        ) == frac(1, 3)
        assert gini_coefficient_of_satisfaction(
            instance, app_multi_profile, budget_allocation, Cardinality_Sat
        ) == frac(1, 3)
        assert gini_coefficient_of_satisfaction(
            instance, app_profile, budget_allocation, Cardinality_Sat, invert=True
        ) == frac(2, 3)
        assert gini_coefficient_of_satisfaction(
            instance, app_multi_profile, budget_allocation, Cardinality_Sat, invert=True
        ) == frac(2, 3)

        ord_ball_1 = OrdinalBallot([projects[0], projects[1], projects[2], projects[3]])
        ord_ball_2 = OrdinalBallot([projects[0]])
        ord_ball_3 = OrdinalBallot([projects[0]])
        ord_ball_4 = OrdinalBallot([projects[5], projects[6]])
        ord_ball_5 = OrdinalBallot([projects[8], projects[9]])
        ord_profile = OrdinalProfile(
            [ord_ball_1, ord_ball_2, ord_ball_3, ord_ball_4, ord_ball_5]
        )
        ord_multi_profile = ord_profile.as_multiprofile()

        assert avg_satisfaction(
            instance, ord_profile, budget_allocation, Additive_Borda_Sat
        ) == frac(6, 5)
        assert avg_satisfaction(
            instance, ord_multi_profile, budget_allocation, Additive_Borda_Sat
        ) == frac(6, 5)

        budget_allocation = BudgetAllocation()

        sat_hist = satisfaction_histogram(
            instance,
            app_profile,
            budget_allocation,
            Relative_Cardinality_Sat,
            max_satisfaction=1,
            num_bins=11,
        )
        assert sat_hist == [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        sat_hist = satisfaction_histogram(
            instance,
            app_multi_profile,
            budget_allocation,
            Relative_Cardinality_Sat,
            max_satisfaction=1,
            num_bins=11,
        )
        assert sat_hist == [1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0]

        budget_allocation = [projects[0], projects[1], projects[2], projects[5]]

        sat_hist = satisfaction_histogram(
            instance,
            app_profile,
            budget_allocation,
            Relative_Cardinality_Sat,
            max_satisfaction=1,
            num_bins=11,
        )
        assert sat_hist == [0.2, 0.0, 0.0, 0.0, 0.0, 0.2, 0.0, 0.0, 0.2, 0.0, 0.4]

        sat_hist = satisfaction_histogram(
            instance,
            app_multi_profile,
            budget_allocation,
            Relative_Cardinality_Sat,
            max_satisfaction=1,
            num_bins=11,
        )
        assert sat_hist == [0.2, 0.0, 0.0, 0.0, 0.0, 0.2, 0.0, 0.0, 0.2, 0.0, 0.4]

        sat_hist = satisfaction_histogram(
            instance,
            app_multi_profile,
            budget_allocation,
            Relative_Cardinality_Sat,
            max_satisfaction=1,
            num_bins=10,
        )
        assert sat_hist == [0.2, 0, 0, 0, 0, 0.2, 0, 0.2, 0, 0.4]

    def test_category_properties(self):
        projects = [
            Project("p1", cost=1, categories={"c1", "c2"}),
            Project("p2", cost=2, categories={"c1", "c2"}),
        ]
        instance = Instance(projects, budget_limit=90, categories={"c1", "c2", "c3"})
        app_ball_1 = ApprovalBallot([projects[0], projects[1]])
        app_ball_2 = ApprovalBallot([projects[0], projects[1]])
        app_profile = ApprovalProfile([app_ball_1, app_ball_2])
        app_multi_profile = app_profile.as_multiprofile()
        budget_allocation = [projects[0], projects[1]]

        assert category_proportionality(instance, app_profile, budget_allocation) == 1
        assert (
            category_proportionality(instance, app_multi_profile, budget_allocation)
            == 1
        )

        projects = [
            Project("p1", cost=1, categories={"c1", "c2"}),
            Project("p2", cost=2, categories={"c2", "c3"}),
            Project("p3", cost=2, categories=set()),
        ]
        instance = Instance(
            projects, budget_limit=90, categories={"c1", "c2", "c3", "c4"}
        )
        app_ball_1 = ApprovalBallot([projects[0], projects[1]])
        app_ball_2 = ApprovalBallot([projects[0]])
        app_ball_3 = ApprovalBallot([projects[1]])
        app_profile = ApprovalProfile([app_ball_1, app_ball_2, app_ball_3])
        app_multi_profile = app_profile.as_multiprofile()
        budget_allocation = [projects[0], projects[2]]

        assert category_proportionality(
            instance, app_profile, budget_allocation
        ) == np.exp(-31.0 / 162)
        assert category_proportionality(
            instance, app_multi_profile, budget_allocation
        ) == np.exp(-31.0 / 162)

        projects = [
            Project("p1", cost=1),
            Project("p2", cost=2),
        ]
        instance = Instance(projects, budget_limit=90)
        app_ball_1 = ApprovalBallot([projects[0], projects[1]])
        app_ball_2 = ApprovalBallot([projects[0], projects[1]])
        app_profile = ApprovalProfile([app_ball_1, app_ball_2])
        app_multi_profile = ApprovalProfile([app_ball_1, app_ball_2])
        budget_allocation = [projects[0], projects[1]]

        with self.assertRaises(ValueError):
            category_proportionality(instance, app_profile, budget_allocation)
        with self.assertRaises(ValueError):
            category_proportionality(instance, app_multi_profile, budget_allocation)

    def test_instance_properties(self):
        projects = [
            Project("p1", cost=1),
            Project("p2", cost=1),
            Project("p3", cost=1),
            Project("p4", cost=1),
            Project("p5", cost=6),
        ]
        instance = Instance(projects, budget_limit=8)

        assert sum_project_cost(instance) == 10
        assert avg_project_cost(instance) == 2
        assert median_project_cost(instance) == 1
        assert funding_scarcity(instance) == frac(5, 4)
        assert std_dev_project_cost(instance) == 2

        instance = Instance(projects)
        with self.assertRaises(ValueError):
            funding_scarcity(instance)

    def test_profile_properties(self):
        projects = [
            Project("p1", cost=1),
            Project("p2", cost=2),
            Project("p3", cost=3),
        ]
        instance = Instance(projects, budget_limit=3)
        app_ball_1 = ApprovalBallot([projects[0], projects[1]])
        app_ball_2 = ApprovalBallot([projects[0], projects[2]])
        app_ball_3 = ApprovalBallot([projects[1]])
        app_ball_4 = ApprovalBallot([projects[1]])
        app_ball_5 = ApprovalBallot([projects[1]])
        app_profile = ApprovalProfile(
            [app_ball_1, app_ball_2, app_ball_3, app_ball_4, app_ball_5]
        )
        app_multi_profile = app_profile.as_multiprofile()

        assert avg_ballot_length(instance, app_profile) == frac(7, 5)
        assert avg_ballot_length(instance, app_multi_profile) == frac(7, 5)
        assert median_ballot_length(instance, app_profile) == 1
        assert median_ballot_length(instance, app_multi_profile) == 1
        assert avg_ballot_cost(instance, app_profile) == frac(13, 5)
        assert avg_ballot_cost(instance, app_multi_profile) == frac(13, 5)
        assert median_ballot_cost(instance, app_profile) == 2
        assert median_ballot_cost(instance, app_multi_profile) == 2
        assert avg_approval_score(instance, app_profile) == frac(7, 3)
        assert avg_approval_score(instance, app_multi_profile) == frac(7, 3)
        assert median_approval_score(instance, app_profile) == 2
        assert median_approval_score(instance, app_multi_profile) == 2
        assert votes_count_by_project(app_profile) == {projects[0]: 2, projects[1]: 4, projects[2]: 1}
        assert votes_count_by_project(app_multi_profile) == {projects[0]: 2, projects[1]: 2, projects[2]: 1}
        assert voter_flow_matrix(instance, app_profile) == {projects[2]: {projects[2]: 0, projects[1]: 0, projects[0]: 1}, projects[1]: {projects[2]: 0, projects[1]: 3, projects[0]: 1}, projects[0]: {projects[2]: 1, projects[1]: 1, projects[0]: 0}}
        assert voter_flow_matrix(instance, app_multi_profile) == {projects[2]: {projects[2]: 0, projects[1]: 0, projects[0]: 1}, projects[1]: {projects[2]: 0, projects[1]: 1, projects[0]: 1}, projects[0]: {projects[2]: 1, projects[1]: 1, projects[0]: 0}}

        card_ball_1 = CardinalBallot({projects[0]: 2, projects[1]: 5})
        card_ball_2 = CardinalBallot({projects[0]: 1, projects[2]: 1})
        card_ball_3 = CardinalBallot({projects[1]: 3})
        card_ball_4 = CardinalBallot({projects[1]: 3})
        card_ball_5 = CardinalBallot({projects[1]: 3})
        card_profile = CardinalProfile(
            [card_ball_1, card_ball_2, card_ball_3, card_ball_4, card_ball_5]
        )
        card_multi_profile = card_profile.as_multiprofile()

        assert avg_total_score(instance, card_profile) == 6
        assert avg_total_score(instance, card_multi_profile) == 6
        assert median_total_score(instance, card_profile) == 3
        assert median_total_score(instance, card_multi_profile) == 3

    def test_project_loss(self):
        projects = [Project(chr(ord("a") + idx), 4) for idx in range(6)]
        supporters = [[0, 1, 2, 4], [2, 3, 4], [0, 2], [0, 1], [4], [5]]
        for idx in range(6):
            projects[idx].supporter_indices = supporters[idx]
        iterations = [
            MESIteration([frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 1), frac(1, 2), frac(1, 1)], projects[0]),
            MESIteration([frac(1, 2), frac(1, 2), frac(0, 1), frac(0, 1), frac(0, 1), frac(1, 1)], projects[1]),
        ]
        iterations[0].extend(
            [MESProjectDetails(projects[0], iterations[0], False)]
        )
        iterations[1].extend(
            [MESProjectDetails(projects[1], iterations[1], False), MESProjectDetails(projects[2], iterations[1], True), MESProjectDetails(projects[3], iterations[1], True), MESProjectDetails(projects[4], iterations[1], True), MESProjectDetails(projects[5], iterations[1], True)]
        )
        allocation_details = MESAllocationDetails([2 for _ in range(len(iterations[0].voters_budget))])
        allocation_details.iterations = iterations

        project_losses = calculate_project_loss(allocation_details)
        expected_budgets = [
            frac(2, 1),
            frac(2, 1),
            frac(1, 2),
            frac(1, 1),
            frac(0, 1),
            frac(1, 1),
        ]
        expected_losses = [
            {},
            {projects[0]: 0.0},
            {projects[0]: 0.0, projects[1]: 1.0},
            {projects[0]: 0.0},
            {projects[0]: 0.0, projects[1]: 1.0},
            {},
        ]

        for idx, project_loss in enumerate(project_losses):
            assert project_loss.name == projects[idx].name
            assert project_loss.supporters_budget == expected_budgets[idx]
            assert project_loss.budget_lost == expected_losses[idx]

        # No iterations
        project_losses = calculate_project_loss(MESAllocationDetails([1]))
        assert project_losses == []
