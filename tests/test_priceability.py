"""
Module testing priceability / stable-priceability property.
"""

# fmt: off

from unittest import TestCase

from pabutools.election import Project, Instance, ApprovalProfile, ApprovalBallot




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

        try:
            from pabutools.analysis.priceability import priceable, validate_price_system
        except ImportError:
            return

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

        try:
            from pabutools.analysis.priceability import priceable, validate_price_system
        except ImportError:
            return

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

        try:
            from pabutools.analysis.priceability import priceable, validate_price_system
        except ImportError:
            return

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

        try:
            from pabutools.analysis.priceability import priceable, validate_price_system
        except ImportError:
            return

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
