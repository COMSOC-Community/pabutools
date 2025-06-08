import pytest
import random
from pabutools.rules.pb_ear import pb_ear ,assert_IPSC_satisfied

"""
Pytest test suite for validating the PB-EAR algorithm implementation.

This test file verifies:
- Edge cases like empty input or zero budget
- Correctness under randomized and large-scale scenarios
- Compliance with the IPSC axiom

Based on:
"Proportionally Representative Participatory Budgeting with Ordinal Preferences",
Haris Aziz and Barton E. Lee (2020),
https://arxiv.org/abs/1911.00864v2

Programmer: Vivian Umansky
"""
def test_empty_voters():
    voters = []
    candidates = [("a", 1.0), ("b", 2.0)]
    budget = 3.0
    result = pb_ear(voters, candidates, budget)
    assert isinstance(result, list)

def test_empty_candidates():
    voters = [(1.0, ["a", "b"])]
    candidates = []
    budget = 3.0
    result = pb_ear(voters, candidates, budget)
    assert result == []

def test_zero_budget():
    voters = [(1.0, ["a", "b"])]
    candidates = [("a", 1.0), ("b", 2.0)]
    budget = 0.0
    result = pb_ear(voters, candidates, budget)
    assert result == []

def test_single_voter_single_project_enough_budget():
    voters = [(1.0, ["a"])]
    candidates = [("a", 1.0)]
    budget = 1.0
    result = pb_ear(voters, candidates, budget)

    assert "a" in result or result == []
    assert_IPSC_satisfied(voters, candidates, budget, result)


def test_invalid_voter_type():
    voters = ["a", "b", "c"]  # should be list of (weight, preferences)
    candidates = [("a", 1.0)]
    budget = 1.0
    with pytest.raises(Exception):
        pb_ear(voters, candidates, budget)

def test_no_affordable_projects():
    voters = [(1.0, ["a", "b"])]
    candidates = [("a", 100.0), ("b", 200.0)]
    budget = 50.0
    result = pb_ear(voters, candidates, budget)

    assert result == []
    assert_IPSC_satisfied(voters, candidates, budget, result)

       
def test_large_input_uniform_preferences():
    """
    All voters have the same preferences and weight 1.
    They form a solid coalition over all 3 projects, each of cost 1.
    The algorithm should pick any 2 and satisfy IPSC.
    """
    num_voters = 1000
    voters = [(1.0, ["a", "b", "c"])] * num_voters
    candidates = [("a", 1.0), ("b", 1.0), ("c", 1.0)]
    budget = 2.0

    result = pb_ear(voters, candidates, budget)

    # Budget respected
    selected_cost = sum(cost for name, cost in candidates if name in result)
    assert selected_cost <= budget

    # IPSC compliance: this is a perfect solid coalition scenario
    assert_IPSC_satisfied(voters, candidates, budget, result)


def test_random_voters_and_check_budget_respected():
    """
    Randomized input. Verifies that the total cost is within budget
    and that the IPSC condition is satisfied with normalized weights.
    """
    random.seed(42)
    names = [chr(97 + i) for i in range(10)]  # 'a' to 'j'
    candidates = [(name, random.uniform(1, 10)) for name in names]
    budget = 50.0
    num_voters = 100

    # Generate normalized weights
    raw_weights = [random.uniform(0.5, 2.0) for _ in range(num_voters)]
    total = sum(raw_weights)
    normalized_weights = [w * num_voters / total for w in raw_weights]

    voters = [
        (normalized_weights[i], random.sample(names, len(names)))
        for i in range(num_voters)
    ]

    result = pb_ear(voters, candidates, budget)

    # Budget respected
    selected_cost = sum(cost for name, cost in candidates if name in result)
    assert selected_cost <= budget

    # IPSC must be satisfied
    assert_IPSC_satisfied(voters, candidates, budget, result)



def test_IPSC_no_violation_in_pb_ear():
    
    random.seed(42)
    num_voters = 100
    project_names = [chr(97 + i) for i in range(10)]
    candidates = [(name, random.uniform(5, 15)) for name in project_names]
    budget = 60.0

    # Step 1: random raw weights
    raw_weights = [random.uniform(0.5, 2.0) for _ in range(num_voters)]
    total_weight = sum(raw_weights)
    normalized_weights = [w * num_voters / total_weight for w in raw_weights]

    # Step 2: assign preferences
    voters = [
        (normalized_weights[i], random.sample(project_names, len(project_names)))
        for i in range(num_voters)
    ]

    result = pb_ear(voters, candidates, budget)
    assert_IPSC_satisfied(voters, candidates, budget, result)


