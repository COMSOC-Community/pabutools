import pytest
import random
from pabutools.pb_ear import pb_ear

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
       
def test_large_input_uniform_preferences():
    """
    All voters have the same preferences, and enough budget to fund 2 out of 3 equally priced projects.
    Checks both budget constraint and IPSC compliance.
    """
    voters = [(1.0, ["a", "b", "c"])] * 1000
    candidates = [("a", 1.0), ("b", 1.0), ("c", 1.0)]
    budget = 2.0
    result = pb_ear(voters, candidates, budget)

    # Check budget constraint
    selected_cost = sum(cost for name, cost in candidates if name in result)
    assert selected_cost <= budget

    # Check IPSC: this solid coalition supports all 3 projects equally
    # They have full weight  full budget  must get projects that match their top-ranked
    supported_set = set(result)
    assert supported_set.issubset({"a", "b", "c"})
    assert len(result) == 2  # At least two out of three preferred should be selected

def test_random_voters_and_check_budget_respected():
    """
    Randomized input. Verifies that the total cost is within budget
    and no project that could be afforded by a solid coalition is wrongly excluded.
    """
    names = [chr(97 + i) for i in range(10)]  # 'a' to 'j'
    candidates = [(name, random.uniform(1, 10)) for name in names]
    voters = [
        (random.uniform(0.5, 2.0), random.sample(names, len(names)))
        for _ in range(100)
    ]
    budget = 50.0
    result = pb_ear(voters, candidates, budget)

    # Check budget respected
    selected_cost = sum(cost for name, cost in candidates if name in result)
    assert selected_cost <= budget

    # IPSC compliance check — look for any clear violation
    total_weight = sum(weight for weight, _ in voters)

    for i in range(1, len(names) + 1):
        proj_group = names[:i]  # try prefix subsets
        # voters who weakly prefer this group
        group_voters = [
            (w, prefs) for (w, prefs) in voters
            if all(p in prefs[:len(proj_group)] for p in proj_group)
        ]
        if not group_voters:
            continue

        group_weight = sum(w for w, _ in group_voters)
        rel_budget = group_weight * budget / total_weight
        supported_cost = sum(
            cost for name, cost in candidates
            if name in proj_group and name in result
        )

        for name, cost in candidates:
            if (
                name in proj_group and
                name not in result and
                supported_cost + cost <= rel_budget
            ):
                raise AssertionError(
                    f"IPSC violation: project '{name}' could have been funded by solid coalition"
                )


def test_random_IPSC_violation_not_possible():
    # Generate a list of 100 voters with random weights and random preferences
    num_voters = 100
    project_names = [chr(97 + i) for i in range(10)]  # Projects 'a' to 'j'
    candidates = [(name, random.uniform(5, 15)) for name in project_names]
    budget = 60.0

    # Create voters with random weights and shuffled rankings
    voters = []
    for _ in range(num_voters):
        weight = random.uniform(0.5, 2.0)
        ranking = random.sample(project_names, len(project_names))
        voters.append((weight, ranking))

    # Run the PB-EAR algorithm
    result = pb_ear(voters, candidates, budget)

    # Calculate total voter weight
    total_weight = sum(weight for weight, _ in voters)

    # Loop over possible subsets of candidate projects
    for i in range(1, len(project_names) + 1):
        for proj_group in [project_names[:i]]:
            # Find all voters who support all the projects in the current group
            supporting_voters = [
                (w, prefs) for (w, prefs) in voters
                if all(p in prefs for p in proj_group)
            ]
            if not supporting_voters:
                continue

            # Calculate the group's total weight and relative budget share
            group_weight = sum(w for w, _ in supporting_voters)
            rel_budget = group_weight * budget / total_weight

            # Calculate the total cost of supported projects in the outcome
            supported_cost = sum(
                cost for name, cost in candidates
                if name in proj_group and name in result
            )

            # Check if there exists a candidate in the group that was NOT selected
            # but could have been added without exceeding the group's proportional budget
            for c_name, c_cost in candidates:
                if (
                    c_name in proj_group and
                    c_name not in result and
                    supported_cost + c_cost <= rel_budget
                ):
                    raise AssertionError(
                        f"IPSC violation: project {c_name} could be afforded "
                        f"by solid coalition and was excluded"
                    )
