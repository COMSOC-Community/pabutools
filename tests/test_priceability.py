"""
Module testing priceability / stable-priceability property.
"""
# fmt: off
import random
from unittest import TestCase

from pabutools.analysis.justifiedrepresentation import is_in_core_up_to_one
from pabutools.analysis.priceability import priceable, validate_price_system
from pabutools.election import Project, Instance, ApprovalProfile, ApprovalBallot, CardinalBallot, CardinalProfile, \
    get_random_approval_profile, Cost_Sat
from pabutools.election.instance import get_random_instance
from pabutools.election.profile.cardinalprofile import get_random_cost_utility_cardinal_profile


def approval_ballot_to_cardinal_ballot(ballot: ApprovalBallot) -> CardinalBallot:
    return CardinalBallot({c : 1 for c in ballot})

def approval_profile_to_cardinal_profile(profile: ApprovalProfile) -> CardinalProfile:
    voters = [approval_ballot_to_cardinal_ballot(ballot) for ballot in profile]
    return CardinalProfile(init=voters)


class TestPriceability(TestCase):
    def test_priceable_approval(self):
        # Example from https://arxiv.org/pdf/1911.11747.pdf page 2

        # +----+----+----+
        # | c4 | c5 | c6 |
        # +----+----+----+----+-----+-----+
        # |      c3      | c9 | c12 | c15 |
        # +--------------+----+-----+-----+
        # |      c2      | c8 | c11 | c14 |
        # +--------------+----+-----+-----+
        # |      c1      | c7 | c10 | c13 |
        # +===============================+
        # | v1 | v2 | v3 | v4 | v5  | v6  |

        p = [Project(str(i), cost=1) for i in range(16)]
        instance = Instance(p[1:], budget_limit=12)

        v1 = ApprovalBallot({p[1], p[2], p[3], p[4]})
        v2 = ApprovalBallot({p[1], p[2], p[3], p[5]})
        v3 = ApprovalBallot({p[1], p[2], p[3], p[6]})
        v4 = ApprovalBallot({p[7], p[8], p[9]})
        v5 = ApprovalBallot({p[10], p[11], p[12]})
        v6 = ApprovalBallot({p[13], p[14], p[15]})
        profile = ApprovalProfile(init=[v1, v2, v3, v4, v5, v6])

        allocation = p[1:4] + p[7:]
        self.assertFalse(priceable(instance, profile, allocation).validate())

        allocation = p[1:9] + p[10:12] + p[13:15]
        self.assertTrue(priceable(instance, profile, allocation).validate())

        res = priceable(instance, profile)
        self.assertTrue(priceable(instance, profile, res.allocation, res.voter_budget, res.payment_functions).validate())
        self.assertTrue(priceable(instance, profile, res.allocation).validate())

        self.assertTrue(validate_price_system(instance, profile, res.allocation, res.voter_budget, res.payment_functions))

    def test_priceable_approval_2(self):
        # Example from https://arxiv.org/pdf/1911.11747.pdf page 15 (k = 5)

        # +------------------------+
        # |           c10          |
        # +------------------------+
        # |           c9           |
        # +------------------------+
        # |           c8           |
        # +------------------------+
        # |           c7           |
        # +------------------------+
        # |           c6           |
        # +----+----+----+----+----+
        # | c1 | c2 | c3 | c4 | c5 |
        # +========================+
        # | v1 | v2 | v3 | v4 | v5 |

        p = [Project(str(i), cost=1) for i in range(11)]
        instance = Instance(p[1:], budget_limit=5)

        v1 = ApprovalBallot({p[1], p[6], p[7], p[8], p[9], p[10]})
        v2 = ApprovalBallot({p[2], p[6], p[7], p[8], p[9], p[10]})
        v3 = ApprovalBallot({p[3], p[6], p[7], p[8], p[9], p[10]})
        v4 = ApprovalBallot({p[4], p[6], p[7], p[8], p[9], p[10]})
        v5 = ApprovalBallot({p[5], p[6], p[7], p[8], p[9], p[10]})
        profile = ApprovalProfile(init=[v1, v2, v3, v4, v5])

        allocation = p[1:3]
        self.assertFalse(priceable(instance, profile, allocation).validate())

        allocation = p[1:6]
        self.assertTrue(priceable(instance, profile, allocation).validate())

        allocation = p[6:]
        self.assertTrue(priceable(instance, profile, allocation).validate())

        res = priceable(instance, profile)
        self.assertTrue(priceable(instance, profile, res.allocation, res.voter_budget, res.payment_functions).validate())
        self.assertTrue(priceable(instance, profile, res.allocation).validate())

        self.assertTrue(validate_price_system(instance, profile, res.allocation, res.voter_budget, res.payment_functions))

    def test_priceable_approval_3(self):
        # Example from http://www.cs.utoronto.ca/~nisarg/papers/priceability.pdf page 13

        # +--------------+--------------+--------------+
        # |      c6      |      c9      |      c12     |
        # +--------------+--------------+--------------+
        # |      c5      |      c8      |      c11     |
        # +--------------+--------------+--------------+
        # |      c4      |      c7      |      c10     |
        # +--------------+--------------+--------------+
        # |                     c3                     |
        # +--------------------------------------------+
        # |                     c2                     |
        # +--------------------------------------------+
        # |                     c1                     |
        # +============================================+
        # | v1 | v2 | v3 | v4 | v5 | v6 | v7 | v8 | v9 |

        p = [Project(str(i), cost=1) for i in range(13)]
        instance = Instance(p[1:], budget_limit=9)

        v1 = ApprovalBallot({p[1], p[2], p[3], p[4], p[5], p[6]})
        v2 = ApprovalBallot({p[1], p[2], p[3], p[4], p[5], p[6]})
        v3 = ApprovalBallot({p[1], p[2], p[3], p[4], p[5], p[6]})

        v4 = ApprovalBallot({p[1], p[2], p[3], p[7], p[8], p[9]})
        v5 = ApprovalBallot({p[1], p[2], p[3], p[7], p[8], p[9]})
        v6 = ApprovalBallot({p[1], p[2], p[3], p[7], p[8], p[9]})

        v7 = ApprovalBallot({p[1], p[2], p[3], p[10], p[11], p[12]})
        v8 = ApprovalBallot({p[1], p[2], p[3], p[10], p[11], p[12]})
        v9 = ApprovalBallot({p[1], p[2], p[3], p[10], p[11], p[12]})
        profile = ApprovalProfile(init=[v1, v2, v3, v4, v5, v6, v7, v8, v9])

        allocation = p[1:10]
        self.assertTrue(priceable(instance, profile, allocation).validate())

        allocation = p[1:6] + p[7:9] + p[10:12]
        self.assertTrue(priceable(instance, profile, allocation).validate())

        allocation = p[1:6] + p[7:9] + p[11:12]
        self.assertFalse(priceable(instance, profile, allocation).validate())

        res = priceable(instance, profile)
        self.assertTrue(priceable(instance, profile, res.allocation, res.voter_budget, res.payment_functions).validate())
        self.assertTrue(priceable(instance, profile, res.allocation).validate())

        self.assertTrue(validate_price_system(instance, profile, res.allocation, res.voter_budget, res.payment_functions))

    def test_priceable_approval_4(self):
        # Example from https://equalshares.net/explanation#example

        p = [
            Project("bike path", cost=700),
            Project("outdoor gym", cost=400),
            Project("new park", cost=250),
            Project("new playground", cost=200),
            Project("library for kids", cost=100),
        ]
        instance = Instance(p, budget_limit=1100)

        v1 = ApprovalBallot({p[0], p[1]})
        v2 = ApprovalBallot({p[0], p[1], p[2]})
        v3 = ApprovalBallot({p[0], p[1]})
        v4 = ApprovalBallot({p[0], p[1], p[2]})
        v5 = ApprovalBallot({p[0], p[1], p[2]})
        v6 = ApprovalBallot({p[0], p[1]})
        v7 = ApprovalBallot({p[2], p[3], p[4]})
        v8 = ApprovalBallot({p[3]})
        v9 = ApprovalBallot({p[3], p[4]})
        v10 = ApprovalBallot({p[2], p[3], p[4]})
        v11 = ApprovalBallot({p[0]})
        profile = ApprovalProfile(init=[v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11])

        allocation = [p[0], p[1]]
        self.assertFalse(priceable(instance, profile, allocation, stable=True).validate())

        allocation = [p[0], p[2], p[4]]
        self.assertFalse(priceable(instance, profile, allocation, stable=True).validate())

        allocation = p[1:]
        self.assertTrue(priceable(instance, profile, allocation, stable=True).validate())

        res = priceable(instance, profile, stable=True)
        self.assertTrue(priceable(instance, profile, res.allocation, res.voter_budget, res.payment_functions, stable=True).validate())
        self.assertTrue(priceable(instance, profile, res.allocation, stable=True).validate())

        self.assertTrue(validate_price_system(instance, profile, res.allocation, res.voter_budget, res.payment_functions, stable=True))

    def test_priceable_cardinal_reduces_to_approval_like_test_3(self):
        # If cardinal profile contains only binary utilities, the implementation should give the same exact solutions.
        # The election example is the same as in test_priceable_approval_3
        p = [Project(str(i), cost=1) for i in range(13)]
        instance = Instance(p[1:], budget_limit=9)

        v1 = ApprovalBallot({p[1], p[2], p[3], p[4], p[5], p[6]})
        v2 = ApprovalBallot({p[1], p[2], p[3], p[4], p[5], p[6]})
        v3 = ApprovalBallot({p[1], p[2], p[3], p[4], p[5], p[6]})

        v4 = ApprovalBallot({p[1], p[2], p[3], p[7], p[8], p[9]})
        v5 = ApprovalBallot({p[1], p[2], p[3], p[7], p[8], p[9]})
        v6 = ApprovalBallot({p[1], p[2], p[3], p[7], p[8], p[9]})

        v7 = ApprovalBallot({p[1], p[2], p[3], p[10], p[11], p[12]})
        v8 = ApprovalBallot({p[1], p[2], p[3], p[10], p[11], p[12]})
        v9 = ApprovalBallot({p[1], p[2], p[3], p[10], p[11], p[12]})
        approval_profile = ApprovalProfile(init=[v1, v2, v3, v4, v5, v6, v7, v8, v9])
        profile = approval_profile_to_cardinal_profile(approval_profile)

        allocation = p[1:10]
        self.assertTrue(priceable(instance, profile, allocation).validate())

        allocation = p[1:6] + p[7:9] + p[10:12]
        self.assertTrue(priceable(instance, profile, allocation).validate())

        allocation = p[1:6] + p[7:9] + p[11:12]
        self.assertFalse(priceable(instance, profile, allocation).validate())

        res = priceable(instance, profile)
        self.assertTrue(priceable(instance, profile, res.allocation, res.voter_budget, res.payment_functions).validate())
        self.assertTrue(priceable(instance, profile, res.allocation).validate())

        self.assertTrue(validate_price_system(instance, profile, res.allocation, res.voter_budget, res.payment_functions))

    # todo - implement the rest of the tests
    def test_priceable_cardinal_reduces_to_approval_random(self):
        for _ in range(100):
            projects_count = random.randint(5, 15)
            voters_count = random.randint(5, 15)
            min_project_cost = random.randint(1, 15)
            max_project_cost = random.randint(min_project_cost + 1, 100)

            instance = get_random_instance(projects_count, min_project_cost, max_project_cost)
            approval_profile = get_random_approval_profile(instance, voters_count)
            cardinal_profile = approval_profile_to_cardinal_profile(approval_profile)

            approval_original_res = priceable(instance, approval_profile)
            cardinal_res_with_approval_allocation = priceable(instance, cardinal_profile, budget_allocation=approval_original_res.allocation)
            self.assertEqual(approval_original_res.validate(), cardinal_res_with_approval_allocation.validate())

            cardinal_original_res = priceable(instance, cardinal_profile)
            approval_res_with_cardinal_allocation = priceable(instance, approval_profile, budget_allocation=cardinal_original_res.allocation)
            self.assertEqual(cardinal_original_res.validate(), approval_res_with_cardinal_allocation.validate())

    def test_stable_priceable_cardinal_reduces_to_approval_like_test_4(self):
        # If cardinal profile contains only binary utilities, the implementation should give the same exact solutions.
        # The election example is the same as in test_priceable_approval_4
        p = [
            Project("bike path", cost=700),
            Project("outdoor gym", cost=400),
            Project("new park", cost=250),
            Project("new playground", cost=200),
            Project("library for kids", cost=100),
        ]
        instance = Instance(p, budget_limit=1100)

        v1 = ApprovalBallot({p[0], p[1]})
        v2 = ApprovalBallot({p[0], p[1], p[2]})
        v3 = ApprovalBallot({p[0], p[1]})
        v4 = ApprovalBallot({p[0], p[1], p[2]})
        v5 = ApprovalBallot({p[0], p[1], p[2]})
        v6 = ApprovalBallot({p[0], p[1]})
        v7 = ApprovalBallot({p[2], p[3], p[4]})
        v8 = ApprovalBallot({p[3]})
        v9 = ApprovalBallot({p[3], p[4]})
        v10 = ApprovalBallot({p[2], p[3], p[4]})
        v11 = ApprovalBallot({p[0]})
        approval_profile = ApprovalProfile(init=[v1, v2, v3, v4, v5, v6, v7, v8, v9, v10, v11])
        profile = approval_profile_to_cardinal_profile(approval_profile)

        allocation = [p[0], p[1]]
        self.assertFalse(priceable(instance, profile, allocation, stable=True).validate())

        allocation = [p[0], p[2], p[4]]
        self.assertFalse(priceable(instance, profile, allocation, stable=True).validate())

        allocation = p[1:]
        self.assertTrue(priceable(instance, profile, allocation, stable=True).validate())

        res = priceable(instance, profile, stable=True)
        self.assertTrue(priceable(instance, profile, res.allocation, res.voter_budget, res.payment_functions, stable=True).validate())
        self.assertTrue(priceable(instance, profile, res.allocation, stable=True).validate())

        self.assertTrue(validate_price_system(instance, profile, res.allocation, res.voter_budget, res.payment_functions, stable=True))

    def test_stable_priceable_cardinal_reduces_to_approval_random(self):
        for _ in range(100):
            projects_count = random.randint(5, 10)
            voters_count = random.randint(5, 10)
            min_project_cost = random.randint(1, 15)
            max_project_cost = random.randint(min_project_cost + 1, 100)

            instance = get_random_instance(projects_count, min_project_cost, max_project_cost)
            approval_profile = get_random_approval_profile(instance, voters_count)
            cardinal_profile = approval_profile_to_cardinal_profile(approval_profile)

            approval_original_res = priceable(instance, approval_profile, stable=True)
            cardinal_res_with_approval_allocation = priceable(instance, cardinal_profile, budget_allocation=approval_original_res.allocation, stable=True)
            self.assertEqual(approval_original_res.validate(), cardinal_res_with_approval_allocation.validate())

            cardinal_original_res = priceable(instance, cardinal_profile, stable=True)
            approval_res_with_cardinal_allocation = priceable(instance, approval_profile, budget_allocation=cardinal_original_res.allocation, stable=True)
            self.assertEqual(cardinal_original_res.validate(), approval_res_with_cardinal_allocation.validate())

    def test_stable_priceable_implies_core_up_to_one(self):
        for _ in range(10):
            projects_count = random.randint(5, 10)
            voters_count = random.randint(5, 10)
            min_project_cost = random.randint(1, 15)
            max_project_cost = random.randint(min_project_cost + 1, 100)

            instance = get_random_instance(projects_count, min_project_cost, max_project_cost)
            profile = get_random_cost_utility_cardinal_profile(instance, voters_count)

            res = priceable(instance, profile, stable=True)
            if res.validate():
                self.assertTrue(is_in_core_up_to_one(instance, profile, Cost_Sat, res.allocation))



    def test_stable_priceable_cardinal_1(self):

        pass

    def test_stable_priceable_cardinal_2(self):
        pass
