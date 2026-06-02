import random

from pabutools.election import Project, Instance, ApprovalBallot, ApprovalProfile, Cost_Sat, CardinalBallot, \
    CardinalProfile
from pabutools.rules.bos_equal_shares import bos_equal_shares, fractional_equal_shares
from pabutools.rules import method_of_equal_shares
from pabutools.analysis.cohesiveness import cohesive_groups


def check_bos_ejr_up_to_t(instance, profile, result):
    if not instance or not list(profile):
        return True

    c_max = max((p.cost for p in instance), default=0)
    n = profile.num_ballots()

    if not isinstance(list(profile)[0], ApprovalBallot):
        return True

    for group, project_set in cohesive_groups(instance, profile):
        S_len = len(group)
        if S_len == 0:
            continue

        t = ((n - S_len) / (2 * S_len)) * c_max
        cost_T = sum(p.cost for p in project_set)

        T_minus_W = [p for p in project_set if p not in result]
        condition_met = False

        for voter in group:
            u_i_W = sum(p.cost for p in result if p in voter)

            if not T_minus_W:
                if u_i_W >= cost_T - t - 1e-9:
                    condition_met = True
                    break
            else:
                if all(u_i_W >= cost_T - t - c.cost - 1e-9 for c in T_minus_W):
                    condition_met = True
                    break

        assert condition_met
    return True


def check_fres_fractional_ejr(instance, profile, fres_result):
    if not instance or not list(profile):
        return True

    if not isinstance(list(profile)[0], ApprovalBallot):
        return True

    for group, project_set in cohesive_groups(instance, profile):
        S_len = len(group)
        if S_len == 0:
            continue

        cost_T = sum(p.cost for p in project_set)
        condition_met = False

        for voter in group:
            u_i_W_frac = sum(p.cost * fres_result.get(p, 0) for p in instance if p in voter)
            if u_i_W_frac >= cost_T - 1e-9:
                condition_met = True
                break

        assert condition_met
    return True


def test_bos_basic_logic():
    p1, p2 = Project("p1", 1000), Project("p2", 100)
    instance = Instance([p1, p2], 1000)
    profile = ApprovalProfile([ApprovalBallot({p1}), ApprovalBallot({p2}), ApprovalBallot({p1})])

    out = bos_equal_shares(instance, profile)
    assert p1 in out
    assert p2 not in out


def test_fres_basic_logic():
    p1, p2 = Project("p1", 1000), Project("p2", 500)
    instance = Instance([p1, p2], 1100)
    profile = ApprovalProfile([ApprovalBallot({p1}), ApprovalBallot({p2})])

    assert fractional_equal_shares(instance, profile) == {p1: 0.55, p2: 1}


def test_empty_instance():
    instance = Instance([], 1000)
    profile = ApprovalProfile([])
    assert bos_equal_shares(instance, profile) == []


def test_over_budget_projects():
    p1 = Project("Overpriced", 2000)
    instance = Instance([p1], 1000)
    profile = ApprovalProfile([ApprovalBallot({p1})])
    assert bos_equal_shares(instance, profile) == []


def test_large():
    pA = Project("A", 300000)
    pB = Project("C", 400000)
    pC = Project("B", 300000)
    pD = Project("D", 240000)
    pE = Project("E", 170000)
    pF = Project("F", 100000)

    budget = 1000000

    instance = Instance([pA, pB, pC, pD, pE, pF], budget)

    profile = ApprovalProfile([ApprovalBallot({pA}),
                               ApprovalBallot({pA, pB, pC, pE}),
                               ApprovalBallot({pA, pB, pC}),
                               ApprovalBallot({pA, pB, pC}),
                               ApprovalBallot({pA, pB, pC}),
                               ApprovalBallot({pA, pB, pF}),
                               ApprovalBallot({pD, pE}),
                               ApprovalBallot({pD, pE}),
                               ApprovalBallot({pD, pE, pF}),
                               ApprovalBallot({pC, pD, pF})])

    assert sorted(bos_equal_shares(instance, profile)) == [pA, pC, pD, pF]
    assert fractional_equal_shares(instance, profile) == {pA: 1, pB: 0, pC: 0.8333333333333334, pD: 1.0,
                                                          pE: 0.6470588235294119, pF: 0.5}


def test_fairness_ejr_up_to_t():
    num_majority = 403
    num_minority = 11
    total_voters = num_majority + num_minority

    cost_project_a = 310000
    cost_project_b = 6000
    budget_limit = 310000

    pA = Project("A", cost_project_a)
    pB = Project("B", cost_project_b)
    instance = Instance([pA, pB], budget_limit)

    ballots = ([ApprovalBallot({pA})] * num_majority) + ([ApprovalBallot({pB})] * num_minority)
    profile = ApprovalProfile(ballots)

    result = bos_equal_shares(instance, profile)

    assert pA in result
    assert pB not in result

    c_max = max(p.cost for p in instance)
    t_bound = ((total_voters - num_majority) / (2 * num_majority)) * c_max

    required_min_utility = cost_project_a - t_bound

    actual_utility = sum(p.cost for p in result if p == pA)

    assert actual_utility >= required_min_utility

    t_b = ((total_voters - num_minority) / (2 * num_minority)) * c_max
    required_util_b = cost_project_b - t_b
    actual_util_b = sum(p.cost for p in result if p == pB)

    assert actual_util_b >= required_util_b


def test_budget_constraint():
    p1 = Project("p1", 600)
    p2 = Project("p2", 600)
    instance = Instance([p1, p2], 1000)

    ballot = ApprovalBallot({p1, p2})
    profile = ApprovalProfile([ballot, ballot])

    result = bos_equal_shares(instance, profile)
    total_cost = sum(p.cost for p in result)

    assert total_cost <= instance.budget_limit


def test_tail_utilities():
    pA = Project("A", 1)
    pB = Project("B", 1)
    instance = Instance([pA, pB], 1)

    ballots = [CardinalBallot({pA: 100, pB: 2}) for _ in range(99)]
    ballots.append(CardinalBallot({pA: 1, pB: 2}))

    profile = CardinalProfile(ballots)

    result = bos_equal_shares(instance, profile)

    assert pA in result
    assert pB not in result


def test_random():
    random.seed(42)
    budget = random.randint(500, 5000)
    num_projects = 100

    projects = [Project(str(i), random.randint(500, 1000)) for i in range(num_projects)]

    instance = Instance(projects, budget)

    num_voters = 500
    ballots = []
    for _ in range(num_voters):
        num_approvals = min(random.randint(1, num_projects), len(projects))
        voter_selection = set(random.sample(projects, num_approvals))
        ballots.append(ApprovalBallot(voter_selection))

    profile = ApprovalProfile(ballots)

    mes_result = method_of_equal_shares(instance, profile, sat_class=Cost_Sat)
    bos_result = bos_equal_shares(instance, profile)
    fres_result = fractional_equal_shares(instance, profile)

    mes_spending = sum(p.cost for p in mes_result)
    bos_spending = sum(p.cost for p in bos_result)
    fres_spending = sum(p.cost * fres_result[p] for p in fres_result)

    assert bos_spending >= mes_spending
    assert fres_spending >= mes_spending


def test_random_with_EJR():
    random.seed(42)
    budget = random.randint(500, 5000)
    num_projects = 15

    projects = [Project(str(i), random.randint(500, 1000)) for i in range(num_projects)]

    instance = Instance(projects, budget)

    num_voters = 10
    ballots = []
    for _ in range(num_voters):
        num_approvals = min(random.randint(1, num_projects), len(projects))
        voter_selection = set(random.sample(projects, num_approvals))
        ballots.append(ApprovalBallot(voter_selection))

    profile = ApprovalProfile(ballots)

    bos_result = bos_equal_shares(instance, profile)
    fres_result = fractional_equal_shares(instance, profile)

    check_bos_ejr_up_to_t(instance, profile, bos_result)
    check_fres_fractional_ejr(instance, profile, fres_result)


def test_budget_constraint_with_EJR():
    p1 = Project("p1", 600)
    p2 = Project("p2", 600)
    instance = Instance([p1, p2], 1000)

    ballot = ApprovalBallot({p1, p2})
    profile = ApprovalProfile([ballot, ballot])

    bos_out = bos_equal_shares(instance, profile)
    fres_out = fractional_equal_shares(instance, profile)

    check_bos_ejr_up_to_t(instance, profile, bos_out)
    check_fres_fractional_ejr(instance, profile, fres_out)


def test_large_with_EJR():
    pA = Project("A", 300000)
    pB = Project("C", 400000)
    pC = Project("B", 300000)
    pD = Project("D", 240000)
    pE = Project("E", 170000)
    pF = Project("F", 100000)

    budget = 1000000
    instance = Instance([pA, pB, pC, pD, pE, pF], budget)

    profile = ApprovalProfile([ApprovalBallot({pA}),
                               ApprovalBallot({pA, pB, pC, pE}),
                               ApprovalBallot({pA, pB, pC}),
                               ApprovalBallot({pA, pB, pC}),
                               ApprovalBallot({pA, pB, pC}),
                               ApprovalBallot({pA, pB, pF}),
                               ApprovalBallot({pD, pE}),
                               ApprovalBallot({pD, pE}),
                               ApprovalBallot({pD, pE, pF}),
                               ApprovalBallot({pC, pD, pF})])

    bos_out = bos_equal_shares(instance, profile)
    fres_out = fractional_equal_shares(instance, profile)

    check_bos_ejr_up_to_t(instance, profile, bos_out)
    check_fres_fractional_ejr(instance, profile, fres_out)


def test_bos_basic_logic_with_EJR():
    p1, p2 = Project("p1", 1000), Project("p2", 100)
    instance = Instance([p1, p2], 1000)
    profile = ApprovalProfile([ApprovalBallot({p1}), ApprovalBallot({p2}), ApprovalBallot({p1})])

    bos_out = bos_equal_shares(instance, profile)
    fres_out = fractional_equal_shares(instance, profile)

    check_bos_ejr_up_to_t(instance, profile, bos_out)
    check_fres_fractional_ejr(instance, profile, fres_out)


def test_empty_instance_with_EJR():
    instance = Instance([], 1000)
    profile = ApprovalProfile([])

    bos_out = bos_equal_shares(instance, profile)
    fres_out = fractional_equal_shares(instance, profile)

    check_bos_ejr_up_to_t(instance, profile, bos_out)
    check_fres_fractional_ejr(instance, profile, fres_out)


def test_over_budget_projects_with_EJR():
    p1 = Project("Overpriced", 2000)
    instance = Instance([p1], 1000)
    profile = ApprovalProfile([ApprovalBallot({p1})])

    bos_out = bos_equal_shares(instance, profile)
    fres_out = fractional_equal_shares(instance, profile)

    check_bos_ejr_up_to_t(instance, profile, bos_out)
    check_fres_fractional_ejr(instance, profile, fres_out)
