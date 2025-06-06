"""
Welfare-maximizing rules.
"""

from __future__ import annotations

from collections.abc import Collection, Iterable


import math

from pulp import LpProblem, LpMaximize, LpVariable, LpBinary, lpSum, PULP_CBC_CMD, value, LpStatusOptimal

from pabutools.election import (
    Instance,
    SatisfactionMeasure,
    Project,
    total_cost,
    GroupSatisfactionMeasure,
    AbstractProfile,
)
from pabutools.rules.budgetallocation import BudgetAllocation
from pabutools.utils import DocEnum


class MaxAddUtilWelfareAlgo(DocEnum):
    """
    Constants use to represent different algorithms that can be used to compute budget allocations
    maximising the additive utilitarian welfare.
    """

    ILP_SOLVER = (
        1,
        "Converts the instance into a integer linear program (ILP) and uses an ILP "
        "solver to compute the outcome.",
    )

    PRIMAL_DUAL = (
        2,
        "Uses state-of-the-art primal/dual solvers for knapsack problems to compute "
        "the outcome.",
    )


def max_additive_utilitarian_welfare_ilp_scheme(
    instance: Instance,
    sat_profile: GroupSatisfactionMeasure,
    initial_budget_allocation: Collection[Project],
    resoluteness: bool = True,
) -> BudgetAllocation | list[BudgetAllocation]:
    """
    The inner algorithm for the welfare maximizing rule. It generates the corresponding budget allocations using a
    linear program solver. Note that there is no control over the way ties are broken.

    Parameters
    ----------
        instance: :py:class:`~pabutools.election.instance.Instance`
            The instance.
        sat_profile : :py:class:`~pabutools.election.satisfaction.satisfactionmeasure.GroupSatisfactionMeasure`
            The profile of satisfaction functions.
        initial_budget_allocation : Iterable[:py:class:`~pabutools.election.instance.Project`]
            An initial budget allocation, typically empty.
        resoluteness : bool, optional
            Set to `False` to obtain an irresolute outcome, where all tied budget allocations are returned.
            Defaults to True.
    Returns
    -------
        :py:class:`~pabutools.rules.budgetallocation.BudgetAllocation` | list[:py:class:`~pabutools.rules.budgetallocation.BudgetAllocation`]
            The selected projects if resolute (:code:`resoluteness == True`), or the set of selected projects if irresolute
            (:code:`resoluteness == False`).
    """
    score = {p: sat_profile.total_satisfaction_project(p) for p in instance}

    mip_model = LpProblem("MaxWelfare", LpMaximize)
    p_vars = {
        p: LpVariable("x_{}".format(p), cat=LpBinary)
        for p in instance
        if p not in initial_budget_allocation
    }

    mip_model += lpSum(p_vars[p] * score[p] for p in p_vars)

    available_budget = instance.budget_limit - total_cost(initial_budget_allocation)
    mip_model += lpSum(p_vars[p] * p.cost for p in p_vars) <= available_budget

    mip_model.solve(PULP_CBC_CMD(msg=False))
    opt_value = value(mip_model.objective)

    # First allocation
    if resoluteness:
        return BudgetAllocation(
            [p for p in p_vars if p_vars[p].varValue is not None and p_vars[p].varValue >= 0.99] + list(initial_budget_allocation)
        )

    if mip_model.status != LpStatusOptimal:
        raise ValueError("Solver did not find an optimal solution.")

    previous_partial_alloc = [p for p in p_vars if p_vars[p].varValue is not None and p_vars[p].varValue >= 0.99]
    all_partial_allocs = [previous_partial_alloc]

    # Add constraint to enforce same objective value
    mip_model += lpSum(score[p] * p_vars[p] for p in p_vars) == opt_value

    while True:
        # See http://yetanothermathprogrammingconsultant.blogspot.com/2011/10/integer-cuts.html
        mip_model += (
                        lpSum((1 - p_vars[p]) for p in previous_partial_alloc) +
                        lpSum(p_vars[p] for p in p_vars if p not in previous_partial_alloc)
                ) >= 1

        mip_model += (
                        lpSum(p_vars[p] for p in previous_partial_alloc) -
                        lpSum(p_vars[p] for p in p_vars if p not in previous_partial_alloc)
                ) <= len(previous_partial_alloc) - 1

        mip_model.solve(PULP_CBC_CMD(msg=False))

        if mip_model.status != LpStatusOptimal:
            break

        previous_partial_alloc = [p for p in p_vars if p_vars[p].varValue is not None and p_vars[p].varValue >= 0.99]
        if previous_partial_alloc not in all_partial_allocs:
            all_partial_allocs.append(previous_partial_alloc)

    return [
        BudgetAllocation(partial_alloc + list(initial_budget_allocation))
        for partial_alloc in all_partial_allocs
    ]


def max_additive_utilitarian_welfare_primal_dual_scheme(
    instance: Instance,
    sat_profile: GroupSatisfactionMeasure,
    initial_budget_allocation: Collection[Project],
) -> BudgetAllocation:
    budget_allocation = BudgetAllocation(initial_budget_allocation)

    items = []
    for p in instance:
        if p not in budget_allocation:
            profit = sat_profile.total_satisfaction_project(p)
            if p.cost == 0:
                if profit > 0:
                    budget_allocation.append(p)
            else:
                items.append(KnapsackItem(p, p.cost, profit))

    current_budget_limit = instance.budget_limit - total_cost(budget_allocation)
    result = primal_dual_branch(items, current_budget_limit)
    budget_allocation.extend(p.project for p in result)
    return budget_allocation


class KnapsackItem:
    def __init__(self, project, weight, profit):
        self.project = project
        self.weight = weight
        self.profit = profit

    @property
    def efficiency(self):
        return self.profit / self.weight if self.weight != 0 else 0

    def __repr__(self):
        return self.project.__repr__()

    def __str__(self):
        return self.project.__str__()


def primal_dual_branch(items: list[KnapsackItem], capacity: float):
    items.sort(key=lambda x: x.efficiency, reverse=True)

    tmp_capacity = capacity
    split_idx = -1
    split_weight = 0
    split_profit = 0
    for i, item in enumerate(items):
        tmp_capacity -= item.weight
        split_idx = i
        if split_idx == len(items) - 1 and tmp_capacity >= 0:
            split_idx += 1

        if tmp_capacity < 0:
            break

        split_weight += item.weight
        split_profit += item.profit

    solution = [0 for _ in range(len(items))]
    lower_bound = [0]
    a_star = [-1]
    b_star = [-1]
    primal_dual_branch_impl(
        split_idx - 1,
        split_idx,
        split_profit,
        split_weight,
        items,
        capacity,
        solution,
        lower_bound,
        a_star,
        b_star,
    )

    result = []
    for i in range(len(items)):
        if i < len(items) and i < b_star[0]:
            if i < a_star[0] + 1:
                solution[i] = 1

            if solution[i] == 1:
                result.append(items[i])

    return result


def primal_dual_branch_impl(
    a, b, profit_sum, weight_sum, items, capacity, x, lower_bound, a_star, b_star
):
    improved = False

    if weight_sum <= capacity:
        if profit_sum > lower_bound[0]:
            lower_bound[0] = profit_sum
            a_star[0] = a
            b_star[0] = b
            improved = True

        if b > len(items) - 1:
            return improved

        upper_bound = math.floor((capacity - weight_sum) * items[b].efficiency)
        if profit_sum + upper_bound <= lower_bound[0]:
            return improved

        pb = items[b].profit
        wb = items[b].weight
        if primal_dual_branch_impl(
            a,
            b + 1,
            profit_sum + pb,
            weight_sum + wb,
            items,
            capacity,
            x,
            lower_bound,
            a_star,
            b_star,
        ):
            x[b] = 1
            improved = True

        if primal_dual_branch_impl(
            a,
            b + 1,
            profit_sum,
            weight_sum,
            items,
            capacity,
            x,
            lower_bound,
            a_star,
            b_star,
        ):
            x[b] = 0
            improved = True
    else:
        if a < 0:
            return False

        upper_bound = math.floor((capacity - weight_sum) * items[a].efficiency)
        if profit_sum + upper_bound <= lower_bound[0]:
            return False

        pa = items[a].profit
        wa = items[a].weight
        if primal_dual_branch_impl(
            a - 1,
            b,
            profit_sum - pa,
            weight_sum - wa,
            items,
            capacity,
            x,
            lower_bound,
            a_star,
            b_star,
        ):
            x[a] = 0
            improved = True

        if primal_dual_branch_impl(
            a - 1,
            b,
            profit_sum,
            weight_sum,
            items,
            capacity,
            x,
            lower_bound,
            a_star,
            b_star,
        ):
            x[a] = 1
            improved = True

    return improved


def max_additive_utilitarian_welfare(
    instance: Instance,
    profile: AbstractProfile,
    sat_class: type[SatisfactionMeasure] | None = None,
    sat_profile: GroupSatisfactionMeasure | None = None,
    resoluteness: bool = True,
    initial_budget_allocation: Collection[Project] | None = None,
    inner_algo: MaxAddUtilWelfareAlgo | None = None,
) -> BudgetAllocation | list[BudgetAllocation]:
    """
    Rule returning the budget allocation(s) maximizing the utilitarian social welfare. The
    utilitarian social welfare is defined as the sum of the satisfaction of the voters, where the
    satisfaction is computed using the satisfaction measure given as a parameter. The satisfaction
    measure is assumed to be additive.

    The outcome can be computed either via an integer linear program solver or with a primal/dual
    approach. Note that depending on the selected algorithm, not all functionalities are supported
    (with the ILP solver ties cannot be handled while the primal/dual approach does not support
    irresolute outcomes).

    Parameters
    ----------
        instance: :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        sat_class : type[:py:class:`~pabutools.election.satisfaction.satisfactionmeasure.SatisfactionMeasure`]
            The class defining the satisfaction function used to measure the social welfare. It should be a class
            inheriting from pabutools.election.satisfaction.satisfactionmeasure.SatisfactionMeasure.
            If no satisfaction is provided, a satisfaction profile needs to be provided. If a satisfaction profile is
            provided, the satisfaction argument is disregarded.
        sat_profile : :py:class:`~pabutools.election.satisfaction.satisfactionmeasure.GroupSatisfactionMeasure`
            The satisfaction profile corresponding to the instance and the profile. If no satisfaction profile is
            provided, but a satisfaction function is, the former is computed from the latter.
        initial_budget_allocation : Iterable[:py:class:`~pabutools.election.instance.Project`]
            An initial budget allocation, typically empty.
        resoluteness : bool, optional
            Set to `False` to obtain an irresolute outcome, where all tied budget allocations are returned.
            Defaults to True.
        inner_algo: :py:class:`~pabutools.rules.maxwelfare.MaxAddUtilWelfareAlgo`, optional
            The inner algorithm used. See :py:class:`~pabutools.rules.maxwelfare.MaxAddUtilWelfareAlgo`
            for the available choices.
            Defaults to :py:enum:mem:`~pabutools.rules.maxwelfare.MaxAddUtilWelfareAlgo.PRIMAL_DUAL`
            if :code:`resoluteness == True`, otherwise defaults to
            :py:enum:mem:`~pabutools.rules.maxwelfare.MaxAddUtilWelfareAlgo.ILP_SOLVER`.

    Returns
    -------
        :py:class:`~pabutools.rules.budgetallocation.BudgetAllocation` | list[:py:class:`~pabutools.rules.budgetallocation.BudgetAllocation`]
            The selected projects if resolute (:code:`resoluteness == True`), or the set of selected projects if irresolute
            (:code:`resoluteness == False`).
    """
    if initial_budget_allocation is not None:
        budget_allocation = BudgetAllocation(initial_budget_allocation)
    else:
        budget_allocation = BudgetAllocation()

    if sat_class is None:
        if sat_profile is None:
            raise ValueError("Satisfaction and sat_profile cannot both be None.")
    else:
        if sat_profile is None:
            sat_profile = profile.as_sat_profile(sat_class=sat_class)
    if inner_algo:
        if inner_algo == MaxAddUtilWelfareAlgo.PRIMAL_DUAL and not resoluteness:
            raise ValueError(
                "The primal/dual algorithm does not support irresolute outcomes."
            )
    else:
        if resoluteness:
            inner_algo = MaxAddUtilWelfareAlgo.PRIMAL_DUAL
        else:
            inner_algo = MaxAddUtilWelfareAlgo.ILP_SOLVER
    if inner_algo == MaxAddUtilWelfareAlgo.PRIMAL_DUAL:
        return max_additive_utilitarian_welfare_primal_dual_scheme(
            instance, sat_profile, budget_allocation
        )
    elif inner_algo == MaxAddUtilWelfareAlgo.ILP_SOLVER:
        return max_additive_utilitarian_welfare_ilp_scheme(
            instance, sat_profile, budget_allocation, resoluteness
        )
    else:
        raise ValueError(
            "The parameter 'inner_algo' needs to be a member of the "
            "MaxAddUtilWelfareAlgo enumeration."
        )
