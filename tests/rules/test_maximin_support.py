from unittest import TestCase

from pabutools.election import Instance, ApprovalProfile, Project, ApprovalBallot
from pabutools.rules.maximin_support import maximin_support


class TestMaximinSupport(TestCase):

    def test_empty_input(self):
        instance = Instance([], 10)
        profile = ApprovalProfile([])
        result = maximin_support(instance, profile)
        self.assertEqual(result, [])

    def test_invalid_input(self):
        p1 = Project("c1", cost=5)
        instance = Instance([p1], 1)
        profile = ApprovalProfile([ApprovalBallot([p1])])
        with self.assertRaises(NotImplementedError):
            maximin_support(instance, profile.as_multiprofile())

    def test_small_input(self):
        p1 = Project("c1", cost=1)
        instance = Instance([p1], 1)
        profile = ApprovalProfile([ApprovalBallot([p1])])
        result = maximin_support(instance, profile)
        self.assertEqual([p.name for p in result], ["c1"])

    def test_medium_input(self):
        p1 = Project("c1", cost=1.5)
        p2 = Project("c2", cost=1.5)
        p3 = Project("c3", cost=1.0)
        instance = Instance([p1, p2, p3], 3)
        profile = ApprovalProfile([
            ApprovalBallot([p1, p2]),
            ApprovalBallot([p1]),
            ApprovalBallot([p2, p3]),
            ApprovalBallot([p2]),
        ])
        result = maximin_support(instance, profile)
        names = set(p.name for p in result)
        self.assertTrue(names == {"c2", "c1"})

    def test_large_input_random_structure_with_fairness(self):
        import random
        num_projects = 30
        projects = [Project(f"c{i + 1}", cost=random.randint(1, 5)) for i in range(num_projects)]
        instance = Instance(projects, 50)

        approvals = [
            ApprovalBallot(random.sample(projects, random.randint(3, 5)))
            for _ in range(100)
        ]
        profile = ApprovalProfile(approvals)

        result = maximin_support(instance, profile)

        project_to_index = {p: i for i, p in enumerate(projects)}
        approval_counts = [0] * num_projects
        for ballot in profile:
            for project in ballot:
                i = project_to_index[project]
                approval_counts[i] += 1

        ratios = [(approval_counts[i] / projects[i].cost, projects[i]) for i in range(num_projects)]
        ratios.sort(reverse=True)
        best_ratio_projects = [p for _, p in ratios[:len(result)]]

        selected_names = set(p.name for p in result)
        best_names = set(p.name for p in best_ratio_projects)
        overlap = selected_names & best_names
        self.assertGreaterEqual(len(overlap), len(result) // 2)
