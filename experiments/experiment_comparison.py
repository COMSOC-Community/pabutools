"""
Section A – Performance comparison of EES algorithms vs. other PB rules.

Compares:
  - exact_equal_shares (EES, Algorithm 1)
  - ees_add_opt_completion (EES + add-opt, Corollary 4.7)
  - method_of_equal_shares (MES, the standard library implementation)
  - greedy_utilitarian_welfare (Greedy welfare)

Metrics:
  - runtime (seconds)
  - total_cost (budget utilisation)
  - num_selected (number of selected projects)
  - social_welfare (total approval score of selected projects)

Uses the experiments-csv library.
"""

import logging
import signal
import sys
import time

import experiments_csv

# ── make the repo root importable ──────────────────────────────────────
sys.path.insert(0, ".")

from pabutools.election import (
    Instance,
    Project,
    ApprovalProfile,
    ApprovalBallot,
    Cost_Sat,
)
from pabutools.election.instance import get_random_instance
from pabutools.election.profile.approvalprofile import get_random_approval_profile
from pabutools.rules import greedy_utilitarian_welfare, method_of_equal_shares
from pabutools.rules.ees_addopt import exact_equal_shares, ees_add_opt_completion

TIME_LIMIT = 60  # seconds per single run

# ── algorithm registry ─────────────────────────────────────────────────
ALGORITHMS = {
    "EES": lambda inst, prof: exact_equal_shares(inst, prof),
    "EES_AddOpt": lambda inst, prof: ees_add_opt_completion(inst, prof),
    "MES": lambda inst, prof: method_of_equal_shares(
        inst, prof, sat_class=Cost_Sat, resoluteness=True
    ),
    "Greedy": lambda inst, prof: greedy_utilitarian_welfare(
        inst, prof, sat_class=Cost_Sat, resoluteness=True
    ),
}


# ── single experiment function ─────────────────────────────────────────
def run_single(num_projects: int, num_voters: int, algorithm: str, seed: int):
    """Run a single experiment: generate a random instance, run the algorithm,
    and return measured outputs."""
    import random as _random

    _random.seed(seed)

    # Generate random instance and profile
    instance = get_random_instance(num_projects, min_cost=1, max_cost=100)
    profile = get_random_approval_profile(instance, num_voters)

    algo_fn = ALGORITHMS[algorithm]

    start = time.perf_counter()
    try:
        result = algo_fn(instance, profile)
    except TimeoutError:
        return {
            "runtime": TIME_LIMIT,
            "total_cost": -1,
            "num_selected": -1,
            "social_welfare": -1,
            "budget_limit": int(instance.budget_limit),
        }
    elapsed = time.perf_counter() - start

    total_cost = sum(p.cost for p in result)
    num_selected = len(result)

    # Social welfare: total number of approvals for the selected projects
    social_welfare = 0
    for project in result:
        social_welfare += profile.approval_score(project)

    return {
        "runtime": round(elapsed, 4),
        "total_cost": int(total_cost),
        "num_selected": num_selected,
        "social_welfare": social_welfare,
        "budget_limit": int(instance.budget_limit),
    }


# ── main ───────────────────────────────────────────────────────────────
RESULTS_DIR = "experiments/results"
CSV_FILE = "comparison.csv"
BACKUPS_DIR = "experiments/results/backups"


def run_experiments():
    """Run the full comparison experiment."""
    ex = experiments_csv.Experiment(RESULTS_DIR, CSV_FILE, BACKUPS_DIR)
    ex.logger.setLevel(logging.INFO)

    input_ranges = {
        "num_projects": [5, 10, 15, 20, 30, 40, 50, 70, 100],
        "num_voters": [20, 50],
        "algorithm": list(ALGORITHMS.keys()),
        "seed": list(range(1, 4)),  # 3 repetitions per combination
    }

    ex.run(run_single, input_ranges)
    print(f"\nExperiment data saved to {RESULTS_DIR}/{CSV_FILE}")


def plot_results():
    """Generate comparison plots from the CSV results."""
    import pandas as pd
    from matplotlib import pyplot as plt

    csv_path = f"{RESULTS_DIR}/{CSV_FILE}"
    df = pd.read_csv(csv_path)

    VOTER_COUNTS = [20, 50]
    metrics = [
        ("runtime", "Runtime (seconds)"),
        ("total_cost", "Total Cost"),
        ("social_welfare", "Social Welfare (total approvals)"),
        ("num_selected", "Number of Selected Projects"),
    ]

    for metric, ylabel in metrics:
        for n_voters in VOTER_COUNTS:
            plt.figure(figsize=(8, 5))
            subset = df[df["num_voters"] == n_voters]
            grouped = subset.groupby(["num_projects", "algorithm"])[metric].mean().reset_index()

            for algo in sorted(grouped["algorithm"].unique()):
                algo_data = grouped[grouped["algorithm"] == algo]
                plt.plot(
                    algo_data["num_projects"],
                    algo_data[metric],
                    marker="o",
                    label=algo,
                )

            plt.title(f"{ylabel} vs. Number of Projects (voters={n_voters})")
            plt.xlabel("Number of Projects")
            plt.ylabel(ylabel)
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            save_path = f"{RESULTS_DIR}/{metric}_voters_{n_voters}.png"
            plt.savefig(save_path, dpi=150)
            plt.close()
            print(f"Saved {save_path}")

    print("\nAll plots saved.")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "plot":
        plot_results()
    else:
        run_experiments()
        plot_results()
