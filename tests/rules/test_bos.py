import random
from pabutools.election import Project, Instance, ApprovalBallot, ApprovalProfile, Cost_Sat
from pabutools.rules.bos_equal_shares import bos_equal_shares
from pabutools.rules import method_of_equal_shares


def test_bos_basic_logic():
    p1, p2 = Project("p1", 1000), Project("p2", 100)
    instance = Instance([p1, p2], 1000)
    profile = ApprovalProfile([ApprovalBallot({p1}), ApprovalBallot({p2}), ApprovalBallot({p1})])

    out = bos_equal_shares(instance, profile)
    assert p1 in out
    assert p2 not in out


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
    pB = Project("B", 400000)
    pC = Project("C", 300000)
    pD = Project("D", 240000)
    pE = Project("E", 170000)
    pF = Project("F", 100000)

    budget = 1000000

    instance = Instance([pA, pB, pC, pD, pE, pF], budget)

    profile = ApprovalProfile([ApprovalBallot({pA}), ApprovalBallot({pA, pB, pC, pE}), ApprovalBallot({pA, pB, pC}),
                               ApprovalBallot({pA, pB, pC}), ApprovalBallot({pA, pB, pC}), ApprovalBallot({pA, pB, pF}),
                               ApprovalBallot({pD, pE}), ApprovalBallot({pD, pE}), ApprovalBallot({pD, pE, pF}),
                               ApprovalBallot({pC, pD, pF})])

    assert bos_equal_shares(instance, profile) == [pA, pC, pD, pF]


def test_random():
    random.seed(42)
    budget = random.randint(5000, 50000)
    num_projects = 100

    projects = [Project(str(i), random.randint(500, 10000)) for i in range(num_projects)]

    instance = Instance(projects, budget)

    num_voters = 5000
    ballots = []
    for _ in range(num_voters):
        num_approvals = min(random.randint(1, 100), len(projects))
        voter_selection = set(random.sample(projects, num_approvals))
        ballots.append(ApprovalBallot(voter_selection))

    profile = ApprovalProfile(ballots)

    mes_result = method_of_equal_shares(instance, profile, sat_class=Cost_Sat)
    bos_result = bos_equal_shares(instance, profile)

    mes_spending = sum(p.cost for p in mes_result)
    bos_spending = sum(p.cost for p in bos_result)
    assert bos_spending >= mes_spending
