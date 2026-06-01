"""
Demo script for the algorithms in:
"Fair Lotteries for Participatory Budgeting"
by Haris Aziz, Xinhang Lu, Mashbat Suzuki, Jeremy Vollen, Toby Walsh (2024)
https://ojs.aaai.org/index.php/AAAI/article/view/28801

Programmers: Dotan Danino, Naama Yahav.
Date: 19/4/2026

The actual implementations live in:
    pabutools/rules/lottery/lottery_rule.py
"""

from pabutools.rules.lottery import (
    BW_GCR_PB,
    BW_GCR_PB_from_lists,
    BW_GCR_PB_wrapped,
    BW_MES_PB,
    BW_MES_PB_from_lists,
    BW_MES_PB_wrapped,
    build_instance,
    build_profile,
    dependent_rounding_bb1,
    approval_sat,
)

# Re-export for backward compatibility with tests and notebooks that import
# these names directly from this module.
__all__ = [
    "BW_GCR_PB", "BW_GCR_PB_from_lists", "BW_GCR_PB_wrapped",
    "BW_MES_PB", "BW_MES_PB_from_lists", "BW_MES_PB_wrapped",
    "build_instance", "build_profile", "dependent_rounding_bb1", "approval_sat",
]

if __name__ == "__main__":
    import doctest
    import logging

    # Route all debug logs to a file to keep the console clean.
    logging.basicConfig(
        level=logging.DEBUG,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        handlers=[
            logging.FileHandler("algorithms_run.log", mode='w', encoding='utf-8')
        ]
    )

    import pabutools.rules.lottery.lottery_rule as _lottery_module

    print("=" * 60)
    print("1. RUNNING INTERNAL DOCTESTS")
    print("=" * 60)

    test_results = doctest.testmod(_lottery_module)
    if test_results.failed == 0:
        print("All internal doctests passed successfully!\n")
    else:
        print("Warning: %d out of %d doctests failed.\n" % (test_results.failed, test_results.attempted))

    print("=" * 60)
    print("2. RUNNING LIVE EXECUTION EXAMPLES")
    print("=" * 60)

    # -----------------------------------------------------------------
    # EXAMPLE A: Standard Balanced Scenario
    # -----------------------------------------------------------------
    print("\n--- EXAMPLE A: Standard Balanced Scenario ---")
    N_A = ['1', '2', '3', '4']
    C_A = ['Park', 'Library', 'Roads']
    cost_A = {'Park': 10000, 'Library': 15000, 'Roads': 5000}
    B_A = 20000
    ui_A = {
        '1': {'Park': 1, 'Library': 1, 'Roads': 0},
        '2': {'Park': 1, 'Library': 0, 'Roads': 1},
        '3': {'Park': 0, 'Library': 1, 'Roads': 1},
        '4': {'Park': 0, 'Library': 1, 'Roads': 0}
    }
    instance_A = build_instance(C_A, cost_A, B_A)
    profile_A  = build_profile(N_A, ui_A, instance_A)
    print("Budget: %d | Projects: %s" % (B_A, str(C_A)))

    gcr_p, gcr_w = BW_GCR_PB_wrapped(instance_A, profile_A)
    print("GCR Probabilities: %s -> Selected: %s" % (str(gcr_p), str(list(gcr_w))))

    mes_p, mes_w = BW_MES_PB_wrapped(instance_A, profile_A)
    print("MES Probabilities: %s -> Selected: %s" % (str(mes_p), str(list(mes_w))))

    # -----------------------------------------------------------------
    # EXAMPLE B: Tight Budget & High Costs (Triggers Fractional Splits)
    # -----------------------------------------------------------------
    print("\n--- EXAMPLE B: Extreme Tight Budget & High Costs ---")
    N_B = ['1', '2', '3']
    C_B = ['Subway', 'Hospital', 'School']
    cost_B = {'Subway': 50000, 'Hospital': 40000, 'School': 20000}
    B_B = 30000
    ui_B = {
        '1': {'Subway': 1, 'Hospital': 0, 'School': 1},
        '2': {'Subway': 0, 'Hospital': 1, 'School': 1},
        '3': {'Subway': 1, 'Hospital': 1, 'School': 0}
    }
    instance_B = build_instance(C_B, cost_B, B_B)
    profile_B  = build_profile(N_B, ui_B, instance_B)
    print("Budget: %d | Projects: %s" % (B_B, str(C_B)))

    gcr_p, gcr_w = BW_GCR_PB_wrapped(instance_B, profile_B)
    print("GCR Probabilities: %s -> Selected: %s" % (str(gcr_p), str(list(gcr_w))))

    mes_p, mes_w = BW_MES_PB_wrapped(instance_B, profile_B)
    print("MES Probabilities: %s -> Selected: %s" % (str(mes_p), str(list(mes_w))))

    # -----------------------------------------------------------------
    # EXAMPLE C: Completely Disjoint Preferences (Tests Unanimous Groups)
    # -----------------------------------------------------------------
    print("\n--- EXAMPLE C: Disjoint Voter Preferences ---")
    N_C = ['1', '2', '3']
    C_C = ['North_Pool', 'South_Bridge']
    cost_C = {'North_Pool': 12000, 'South_Bridge': 12000}
    B_C = 12000
    ui_C = {
        '1': {'North_Pool': 1, 'South_Bridge': 0},
        '2': {'North_Pool': 1, 'South_Bridge': 0},
        '3': {'North_Pool': 0, 'South_Bridge': 1}
    }
    instance_C = build_instance(C_C, cost_C, B_C)
    profile_C  = build_profile(N_C, ui_C, instance_C)
    print("Budget: %d | Projects: %s" % (B_C, str(C_C)))

    gcr_p, gcr_w = BW_GCR_PB_wrapped(instance_C, profile_C)
    print("GCR Probabilities: %s -> Selected: %s" % (str(gcr_p), str(list(gcr_w))))

    mes_p, mes_w = BW_MES_PB_wrapped(instance_C, profile_C)
    print("MES Probabilities: %s -> Selected: %s" % (str(mes_p), str(list(mes_w))))

    print("\n" + "=" * 60)
    print("EXECUTION FINISHED")
    print("Please open 'algorithms_run.log' to view the detailed inner steps.")
    print("=" * 60)
