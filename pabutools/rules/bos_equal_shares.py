"""
An implementation of the algorithms found in:
"Method of Equal Shares with Bounded Overspending"
https://www.ac.tuwien.ac.at/comsoc2025/comsoc2025-papers/50.pdf

Programmer: Ivan Gorbachev
Date: 17/04/2026
"""
import doctest
from pabutools.election import Project, Instance, ApprovalBallot, ApprovalProfile


def bos_equal_shares(instance, profile):
    """
       Algorithm "BOS Equal Shares" - The algorithm selects a subset of projects such that the resulting subset is both
           affordable under the budget while also exhausting it and guaranteeing fairness
        Example:
        >>> p1, p2 = Project("p1", 1000), Project("p2", 100)
        >>> instance = Instance([p1, p2], 1000)
        >>> profile = ApprovalProfile([ApprovalBallot({p1}), ApprovalBallot({p2}), ApprovalBallot({p1})])
        >>> print(bos_equal_shares(instance, profile))
        ['p1']
    """
    return []