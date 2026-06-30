"""
Ballot-weighted lottery rules for participatory budgeting.

Implements the algorithms from:
  Aziz, Lu, Suzuki, Vollen, and Walsh (2024).
  "Fair Lotteries for Participatory Budgeting." AAAI 2024.

The two main entry points are:

* :func:`~pabutools.rules.lottery.BW_GCR_PB_wrapped` — GCR-backed lottery (FJR)
* :func:`~pabutools.rules.lottery.BW_MES_PB_wrapped` — MES-backed lottery (EJR)
"""

from pabutools.election.instance import instance_from_project_costs
from pabutools.election.profile import approval_profile_from_matrix
from pabutools.rules.lottery.lottery_rule import (
    # BB1 rounding
    dependent_rounding_bb1,
    # Algorithm 1 (GCR)
    BW_GCR_PB,
    BW_GCR_PB_from_lists,
    BW_GCR_PB_wrapped,
    # Algorithm 2 (MES)
    BW_MES_PB,
    BW_MES_PB_from_lists,
    BW_MES_PB_wrapped,
    # Backward-compatible aliases
    build_instance,
    build_profile,
    approval_sat,
)

__all__ = [
    "dependent_rounding_bb1",
    "BW_GCR_PB",
    "BW_GCR_PB_from_lists",
    "BW_GCR_PB_wrapped",
    "BW_MES_PB",
    "BW_MES_PB_from_lists",
    "BW_MES_PB_wrapped",
    # Preferred names
    "instance_from_project_costs",
    "approval_profile_from_matrix",
    # Backward-compatible aliases
    "build_instance",
    "build_profile",
    "approval_sat",
]
