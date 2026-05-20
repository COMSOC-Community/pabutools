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

from pabutools.election import Project, Instance, ApprovalBallot, ApprovalProfile


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
    selected_projects = list()
    cost_selected_projects = 0

    budget = instance.budget_limit
    num_voters = profile.num_ballots()

    virtual_budgets = {voter.frozen(): budget / num_voters for voter in profile}

    all_projects = list(instance)
    budget_for_project = {project: sum(virtual_budgets[voter.frozen()] for voter in profile if project in voter) for
                          project in
                          all_projects}

    available_projects = [project for project in all_projects if
                          cost_selected_projects + project.cost <= budget and budget_for_project[
                              project] > 0 and project not in selected_projects]
    print(budget_for_project)

    while available_projects and cost_selected_projects <= budget:
        best_alpha = 1
        best_rho = math.inf
        best_project = None

        for project in available_projects:
            supporters = [voter for voter in profile if project in voter]
            if not supporters:
                continue
            supporters_budgets = [virtual_budgets[voter.frozen()] for voter in supporters]
            lambda_prime = math.inf if sum(supporters_budgets) < project.cost else root_scalar(
                lambda lmbda: sum(min(b, lmbda) for b in supporters_budgets) - project.cost,
                bracket=[0, max(supporters_budgets)]).root
            lambdas = [virtual_budgets[voter.frozen()] / project.cost for voter in supporters]
            lambdas.append(lambda_prime)
            for lamb in lambdas:
                alpha = min(
                    sum(min(virtual_budgets[supporter.frozen()], project.cost * lamb) for supporter in supporters), 1)
                rho = lamb / alpha
                if rho / alpha < best_rho / best_alpha:
                    best_rho = rho
                    best_alpha = alpha
                    best_project = project

        if best_project is None:
            break
        if best_project.cost + cost_selected_projects <= budget:
            selected_projects.append(best_project)
        print(selected_projects)
        cost_selected_projects = sum(project.cost for project in selected_projects)

        for voter in profile:
            if best_project in voter:
                virtual_budgets[voter.frozen()] = max(
                    0,
                    virtual_budgets[voter.frozen()] - best_rho
                )

        budget_for_project = {project: sum(virtual_budgets[voter.frozen()] for voter in profile if project in voter) for
                              project in
                              all_projects}

        available_projects = [project for project in all_projects if
                              cost_selected_projects + project.cost <= budget and budget_for_project[
                                  project] > 0 and project not in selected_projects]
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
    p1, p2 = Project("p1", 1000), Project("p2", 100)
    instance = Instance([p1, p2], 1000)
    profile = ApprovalProfile(
        [ApprovalBallot({p1}), ApprovalBallot({p1}), ApprovalBallot({p1}), ApprovalBallot({p1}), ApprovalBallot({p1}),
         ApprovalBallot({p2})])
    print(bos_equal_shares(instance, profile))
