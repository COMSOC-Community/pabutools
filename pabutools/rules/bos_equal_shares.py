"""
An implementation of the algorithms found in:
"Method of Equal Shares with Bounded Overspending"
https://www.ac.tuwien.ac.at/comsoc2025/comsoc2025-papers/50.pdf

Programmer: Ivan Gorbachev
Date: 17/04/2026
"""
import doctest
import math

from scipy.optimize import root_scalar

from pabutools.election import Project, Instance, ApprovalBallot, ApprovalProfile, CardinalBallot


def get_utility(voter, project):
    if type(voter) == CardinalBallot:
        return voter.utility(project)
    return 1 if project in voter else 0


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
    voters = list(profile)
    selected_projects = list()
    cost_selected_projects = 0

    budget = instance.budget_limit
    num_voters = profile.num_ballots()

    virtual_budgets = [budget / num_voters for _ in voters]

    all_projects = list(instance)

    budget_for_project = {
        project: sum(virtual_budgets[i] * get_utility(voter, project) for i, voter in enumerate(voters)) for
        project in all_projects}

    available_projects = [project for project in all_projects if cost_selected_projects + project.cost <= budget and
                          budget_for_project[project] > 0 and project not in selected_projects]
    print(virtual_budgets)
    print(budget_for_project)
    while available_projects and cost_selected_projects <= budget:
        best_alpha = 1
        best_rho = math.inf
        best_project = None
        for project in available_projects:
            supporters = [(i, voter) for i, voter in enumerate(voters) if get_utility(voter, project) > 0]
            if not supporters:
                continue
            supporters_budgets = [virtual_budgets[i] for i, voter in supporters]
            supporters_utils = [get_utility(voter, project) for i, voter in supporters]
            if sum(supporters_budgets) < project.cost:
                lambda_prime = math.inf
            else:
                res = root_scalar(
                    lambda lmbda: sum(min(b, lmbda * project.cost * u) for b, u in
                                      zip(supporters_budgets, supporters_utils)) - project.cost,
                    bracket=[0, 1.0]
                )
                lambda_prime = res.root
            lambdas = [virtual_budgets[i] / (project.cost * u) for i, u in
                       zip([s[0] for s in supporters], supporters_utils)]
            lambdas.append(lambda_prime)
            for lamb in lambdas:
                total_collected = (sum(
                    min(virtual_budgets[i], lamb * project.cost * u) for i, u in
                    zip([s[0] for s in supporters], supporters_utils)))
                alpha = min(total_collected / project.cost, 1)
                if alpha <= 0:
                    continue
                rho = lamb / alpha
                print(project, alpha, rho)
                if rho / alpha < best_rho / best_alpha:
                    best_rho = rho
                    best_alpha = alpha
                    best_project = project

        if best_project is None:
            break
        print("selected", best_project)
        if best_project.cost + cost_selected_projects <= budget and best_project not in selected_projects:
            selected_projects.append(best_project)

        cost_selected_projects = sum(project.cost for project in selected_projects)

        for i, voter in enumerate(voters):
            u = get_utility(voter, best_project)
            if u > 0:
                virtual_budgets[i] = max(0, virtual_budgets[i] - best_rho * best_project.cost * u)

        budget_for_project = {
            project: sum(virtual_budgets[i] * get_utility(voter, project) for i, voter in enumerate(voters)) for
            project in all_projects}

        available_projects = [project for project in all_projects if
                              cost_selected_projects + project.cost <= budget and budget_for_project[
                                  project] > 0 and project not in selected_projects]
        print(budget_for_project)
        print(budget - cost_selected_projects)
        print(virtual_budgets)
    print(cost_selected_projects)
    return selected_projects


def fractional_equal_shares(instance, profile):
    """
    Algorithm "fractional equal shares" - The algorithm works much like equal shares with the exception that it
    allows players to purchase fractional shares in the projects they support for fractional cost. This Algorithm is
    used as a part of the BOS algorithm in order to select the projects before making the players paying the full
    price, thus leading to the overspending feature of BOS.
    """
    return []


if __name__ == '__main__':
    pA = Project("A", 300000)
    pB = Project("B", 400000)
    pC = Project("C", 300000)
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

    print(bos_equal_shares(instance, profile))
