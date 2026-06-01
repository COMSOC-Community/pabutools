"""
Ballot-weighted lottery rules for participatory budgeting.

Implements the algorithms from:
  Aziz, Lu, Suzuki, Vollen, and Walsh (2024).
  "Fair Lotteries for Participatory Budgeting." AAAI 2024.

The two main entry points are:

* :func:`~pabutools.rules.lottery.BW_GCR_PB_wrapped` — GCR-backed lottery (FJR)
* :func:`~pabutools.rules.lottery.BW_MES_PB_wrapped` — MES-backed lottery (EJR)
"""

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
    # Conversion utilities
    build_instance,
    build_profile,
    clean_number,
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
    "build_instance",
    "build_profile",
    "clean_number",
    "approval_sat",
]
