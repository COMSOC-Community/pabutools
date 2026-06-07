"""
Running example for all algorithms in pabutools.rules.ees_addopt.

Demonstrates:
  1. exact_equal_shares      (Algorithm 1 – EES)
  2. get_leftover_budgets    (leftover budget helper)
  3. get_leximax_payment      (leximax payment helper)
  4. greedy_project_change   (Algorithm 2 – GPC)
  5. add_opt                 (Algorithm 3 – add-opt)
  6. ees_add_opt_completion  (EES completion via add-opt)
"""

import logging

from pabutools.election import Instance, Project, ApprovalProfile, ApprovalBallot
from pabutools.fractions import frac
from pabutools.rules.budgetallocation import BudgetAllocation
from pabutools.rules.ees_addopt import (
    EESAllocationDetails,
    exact_equal_shares,
    get_leftover_budgets,
    get_leximax_payment,
    greedy_project_change,
    add_opt,
    ees_add_opt_completion,
)

# Show all log messages from the module.
logging.basicConfig(
    level=logging.DEBUG,
    format="%(name)s  %(levelname)s  %(message)s",
    stream=__import__("sys").stdout,
)

SEPARATOR = "\n" + "=" * 70 + "\n"


# A small PB instance with 5 voters and 3 projects.
# Projects:  p1 (cost 2),  p2 (cost 3.2),  p3 (cost 6)
# Budget:    10
# Voter 0 approves {p1}
# Voter 1 approves {p1, p3}
# Voter 2 approves {p2, p3}
# Voter 3 approves {p2, p3}
# Voter 4 approves {p3}

p1 = Project("p1", 2)
p2 = Project("p2", 3.2)
p3 = Project("p3", 6)
projects = [p1, p2, p3]
budget = 10

instance = Instance(projects, budget_limit=budget)
profile = ApprovalProfile(
    [
        ApprovalBallot([p1]),
        ApprovalBallot([p1, p3]),
        ApprovalBallot([p2, p3]),
        ApprovalBallot([p2, p3]),
        ApprovalBallot([p3]),
    ],
    instance=instance,
)

num_voters = len(profile)
print("Instance")
print(f"  Budget      : {budget}")
print(f"  Projects    : {[(p.name, p.cost) for p in projects]}")
print(f"  Num voters  : {num_voters}")
print(f"  Approvals   :")
for i, ballot in enumerate(profile):
    print(f"    Voter {i}: {sorted(p.name for p in ballot)}")


# 1. exact_equal_shares (Algorithm 1)
print(SEPARATOR)
print("1. exact_equal_shares (Algorithm 1 – EES)")
print("-" * 42)

ees_result = exact_equal_shares(instance, profile)

print(f"\n  Selected projects : {[p.name for p in ees_result]}")
total_cost = sum(frac(p.cost) for p in ees_result)
print(f"  Total cost        : {total_cost}")

payments = ees_result.details.payments
print("  Per-voter payments:")
for voter in range(num_voters):
    voter_pay = payments.get(voter, {})
    items = [(p.name, float(v)) for p, v in voter_pay.items()]
    print(f"    Voter {voter}: {items if items else '(none)'}")


# 2. get_leftover_budgets
print(SEPARATOR)
print("2. get_leftover_budgets")
print("-" * 42)

leftover = get_leftover_budgets(instance, profile, ees_result)

print("  Leftover budget per voter:")
for voter in range(num_voters):
    print(f"    Voter {voter}: {float(leftover[voter]):.4f}")


# 3. get_leximax_payment
print(SEPARATOR)
print("3. get_leximax_payment")
print("-" * 42)

leximax = get_leximax_payment(ees_result, num_voters, instance)

print("  Leximax payment vectors:")
for voter in range(num_voters):
    formatted = [(float(amt), name) for amt, name in leximax[voter]]
    print(f"    Voter {voter}: {formatted}")


# 4. greedy_project_change (Algorithm 2 – GPC)
print(SEPARATOR)
print("4. greedy_project_change (Algorithm 2 – GPC)")
print("-" * 42)

print("  Testing each project as instability certificate:")
for proj in projects:
    d = greedy_project_change(
        instance, profile, ees_result, proj, leftover, leximax
    )
    print(f"    Project '{proj.name}' (cost={proj.cost}):  d = {d}  ({float(d):.4f})")


# 5. add_opt (Algorithm 3)
print(SEPARATOR)
print("5. add_opt (Algorithm 3)")
print("-" * 42)

d_min = add_opt(instance, profile, ees_result)

print(f"\n  Minimum d over all projects: {d_min}  ({float(d_min):.4f})")
print(f"  Per-voter budget increase  : {float(d_min):.4f}")
print(f"  Total budget increase (n*d): {float(num_voters * d_min):.4f}")


# 6. ees_add_opt_completion (EES completion via add-opt)
print(SEPARATOR)
print("6. ees_add_opt_completion (EES completed via add-opt)")
print("-" * 42)

completed = ees_add_opt_completion(instance, profile)

print(f"\n  Selected projects : {sorted(p.name for p in completed)}")
completed_cost = sum(frac(p.cost) for p in completed)
print(f"  Total cost        : {completed_cost}  (budget = {budget})")

if hasattr(completed.details, "payments"):
    print("  Per-voter payments:")
    for voter in range(num_voters):
        voter_pay = completed.details.payments.get(voter, {})
        items = [(p.name, float(v)) for p, v in voter_pay.items()]
        print(f"    Voter {voter}: {items if items else '(none)'}")


# Comparison
print(SEPARATOR)
print("Summary comparison")
print("-" * 42)
print(f"  EES alone       : {str([p.name for p in ees_result]):30s}  cost = {float(total_cost)}")
print(f"  EES + add-opt   : {str(sorted(p.name for p in completed)):30s}  cost = {float(completed_cost)}")
