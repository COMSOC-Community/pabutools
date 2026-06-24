"""
test for the algorithms in:
"lottery_rule"
by Haris Aziz, Xinhang Lu, Mashbat Suzuki, Jeremy Vollen, Toby Walsh (2024)
https://ojs.aaai.org/index.php/AAAI/article/view/28801

Programmers: Dotan Danino, Naama Yahav.
Date: 19/4/2026

"""

import numpy as np
import random
import unittest
from pabutools.election.instance import Instance, Project
from pabutools.election.profile import Profile
from pabutools.rules.lottery import (
    BW_GCR_PB_wrapped,
    BW_MES_PB_wrapped,
    build_instance,
    build_profile,
)
from pabutools.analysis.justifiedrepresentation import (
    check_FJR,
    check_EJR,
    check_strong_UFS,
)


class TestAlgorithms(unittest.TestCase):

    def test_raise(self):
        # Empty instance (no projects)
        instance = Instance([], budget_limit=33000)
        profile = Profile([])
        with self.assertRaises(ValueError):
            BW_GCR_PB_wrapped(instance, profile)
        with self.assertRaises(ValueError):
            BW_MES_PB_wrapped(instance, profile)

        # budget_limit = 0
        p = Project('a', 21000)
        instance_b0 = Instance([p], budget_limit=0)
        profile_b0 = Profile([])
        with self.assertRaises(ValueError):
            BW_GCR_PB_wrapped(instance_b0, profile_b0)
        with self.assertRaises(ValueError):
            BW_MES_PB_wrapped(instance_b0, profile_b0)

    def test_none_raise(self):
        N = ['1', '2']
        C = ['a', 'b', 'c']
        cost = {'a': 21000, 'b': 10000, 'c': 2000}
        B = 33000.0
        ui = {
            '1': {'a': 1, 'b': 1, 'c': 0},
            '2': {'a': 0, 'b': 1, 'c': 1}
        }
        instance = build_instance(C, cost, B)
        profile = build_profile(N, ui, instance)

        with self.assertRaises(ValueError):
            BW_GCR_PB_wrapped(None, profile)
        with self.assertRaises(ValueError):
            BW_MES_PB_wrapped(None, profile)
        with self.assertRaises(ValueError):
            BW_GCR_PB_wrapped(instance, None)
        with self.assertRaises(ValueError):
            BW_MES_PB_wrapped(instance, None)

    def test_annotation_raise(self):
        N = ['1', '2']
        C = ['a', 'b', 'c']
        cost = {'a': 21000, 'b': 10000, 'c': 2000}
        B = 33000.0
        ui = {
            '1': {'a': 1, 'b': 1, 'c': 0},
            '2': {'a': 0, 'b': 1, 'c': 1}
        }
        instance = build_instance(C, cost, B)
        profile = build_profile(N, ui, instance)

        with self.assertRaises(ValueError):
            BW_GCR_PB_wrapped("not_an_instance", profile)
        with self.assertRaises(ValueError):
            BW_MES_PB_wrapped("not_an_instance", profile)
        with self.assertRaises(ValueError):
            BW_GCR_PB_wrapped(instance, "not_a_profile")
        with self.assertRaises(ValueError):
            BW_MES_PB_wrapped(instance, "not_a_profile")

    def test_not_exceed_budget(self):
        N = list(np.arange(1, random.randint(10, 100)))
        C = list(np.arange(1, random.randint(10, 100)))
        cost = {c: random.randint(1, 1000) for c in C}
        B = float(random.randint(1000, 20000))
        ui = {n: {c: random.randint(0, 1) for c in C} for n in N}

        instance = build_instance(C, cost, B)
        profile = build_profile(N, ui, instance)
        p2, s2 = BW_MES_PB_wrapped(instance, profile)

        if s2:
            total_cost_s2 = sum(proj.cost for proj in s2)
            self.assertLessEqual(
                total_cost_s2,
                B + max(proj.cost for proj in s2),
                msg=f"MES exceeded budget: total_cost={total_cost_s2}, budget={B}"
            )

    def test_not_exceed_budget_GCR(self):
        N = list(np.arange(1, random.randint(3, 5)))
        C = list(np.arange(1, random.randint(6, 10)))
        cost = {c: random.randint(1, 1000) for c in C}
        B = float(random.randint(100, 600))
        ui = {n: {c: random.randint(0, 1) for c in C} for n in N}

        instance = build_instance(C, cost, B)
        profile = build_profile(N, ui, instance)
        p1, s1 = BW_GCR_PB_wrapped(instance, profile)

        if s1:
            total_cost_s1 = sum(proj.cost for proj in s1)
            self.assertLessEqual(
                total_cost_s1,
                B + max(proj.cost for proj in s1),
                msg=f"GCR exceeded budget: total_cost={total_cost_s1}, budget={B}"
            )

    def test_Many_Projects_Many_Citizens(self):
        N = list(np.arange(1, random.randint(10, 100)))
        C = list(np.arange(1, random.randint(10, 100)))
        cost = {c: random.randint(1, 1000) for c in C}
        B = float(random.randint(1000, 20000))
        ui = {n: {c: random.randint(0, 1) for c in C} for n in N}

        instance = build_instance(C, cost, B)
        profile = build_profile(N, ui, instance)
        p2, s2 = BW_MES_PB_wrapped(instance, profile)

        for name, p_vec in [("MES", p2)]:
            self.assertTrue(
                check_strong_UFS(N, C, cost, B, ui, p_vec),
                msg=f"{name} failed for group s"
            )

    def test_EJR_MES(self):
        N = list(np.arange(1, random.randint(10, 40)))
        C = list(np.arange(1, random.randint(10, 40)))
        cost = {c: random.randint(1, 100) for c in C}
        B = float(random.randint(500, 5000))
        ui = {n: {c: random.randint(0, 1) for c in C} for n in N}

        instance = build_instance(C, cost, B)
        profile = build_profile(N, ui, instance)
        p, s = BW_MES_PB_wrapped(instance, profile)

        self.assertTrue(
            check_EJR(N, cost, C, B, ui, s),
            msg="EJR failed"
        )

    def test_FJR_GCR(self):
        N = list(np.arange(1, random.randint(3, 5)))
        C = list(np.arange(1, random.randint(6, 10)))
        cost = {c: random.randint(1, 100) for c in C}
        B = float(random.randint(20, 100))
        ui = {n: {c: random.randint(0, 1) for c in C} for n in N}

        instance = build_instance(C, cost, B)
        profile = build_profile(N, ui, instance)
        p, s = BW_GCR_PB_wrapped(instance, profile)

        self.assertTrue(
            check_FJR(N, cost, C, B, ui, s),
            msg="FJR failed"
        )


if __name__ == '__main__':
    unittest.main()
