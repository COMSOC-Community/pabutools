"""
Module with tools for analysis of the priceability / stable-priceability property of budget allocation.
"""

from __future__ import annotations

import collections
from collections.abc import Collection
import logging

logger = logging.getLogger(__name__)

from pabutools.analysis.priceability_relaxation import Relaxation
from pabutools.election import (
    Instance,
    AbstractApprovalProfile,
    Project,
    total_cost,
)
from pabutools.utils import Numeric, round_cmp


import pulp

CHECK_ROUND_PRECISION = 2
ROUND_PRECISION = 6


def validate_price_system(
    instance: Instance,
    profile: AbstractApprovalProfile,
    budget_allocation: Collection[Project],
    voter_budget: Numeric,
    payment_functions: list[dict[Project, Numeric]],
    stable: bool = False,
    exhaustive: bool = True,
    relaxation: Relaxation | None = None,
    *,
    verbose: bool = False,
) -> bool:
    """
    Given a price system (`voter_budget`, `payment_functions`),
    verifies whether `budget_allocation` is priceable / stable-priceable.

    :py:func:`~pabutools.utils.round_cmp`: is used across the implementation to ensure no rounding errors.

    Reference paper: https://www.cs.utoronto.ca/~nisarg/papers/priceability.pdf

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        budget_allocation : Collection[:py:class:`~pabutools.election.instance.Project`]
            The selected collection of projects.
        voter_budget : Numeric
            Voter initial endowment.
        payment_functions : list[dict[:py:class:`~pabutools.election.instance.Project`, Numeric]]
            Collection of payment functions for each voter.
            A payment function indicates the amounts paid for each project by a voter.
        stable : bool, optional
            Verify for stable-priceable allocation.
            Defaults to `False`.
        exhaustive : bool, optional
            Verify for exhaustiveness of the allocation.
            Defaults to `True`.
        relaxation : :py:class:`~pabutools.analysis.priceability_relaxation.Relaxation`, optional
            Relaxation method to the stable-priceability condition.
            Defaults to `None`.
        **verbose : bool, optional
            Display additional information.
            Defaults to `False`.

    Returns
    -------
        bool
            Boolean value specifying whether `budget_allocation` is priceable / stable-priceable.

    """
    C = instance
    N = profile
    W = budget_allocation
    NW = [c for c in C if c not in W]
    b = voter_budget
    pf = payment_functions
    total = total_cost(W)
    spent = [sum(pf[idx][c] for c in C) for idx, _ in enumerate(N)]
    leftover = [(b - spent[idx]) for idx, _ in enumerate(N)]
    max_payment = [max((pf[idx][c] for c in C), default=0) for idx, _ in enumerate(N)]

    errors = collections.defaultdict(list)

    # equivalent of `instance.is_feasible(W)`
    if total > instance.budget_limit:
        errors["C0a"].append(
            f"total price for allocation is equal {total} > {instance.budget_limit}"
        )

    if exhaustive:
        # equivalent of `instance.is_exhaustive(W)`
        for c in NW:
            if total + c.cost <= instance.budget_limit:
                errors["C0b"].append(
                    f"allocation is not exhaustive {total} + {c.cost} = {total + c.cost} <= {instance.budget_limit}"
                )

    if round_cmp(b * profile.num_ballots(), instance.budget_limit, CHECK_ROUND_PRECISION) < 0:
        errors["C0c"].append(
            f"voters total money is less than instance budget {b * profile.num_ballots()} < {instance.budget_limit}"
        )

    for idx, i in enumerate(N):
        for c in C:
            if c not in i and pf[idx][c] != 0:
                errors["C1"].append(
                    f"voter {idx} paid {pf[idx][c]} for unapproved project {c}"
                )

    for idx, _ in enumerate(N):
        if round_cmp(spent[idx], b, CHECK_ROUND_PRECISION) > 0:
            errors["C2"].append(f"payments of voter {idx} are equal {spent[idx]} > {b}")

    for c in W:
        s = sum(pf[idx][c] for idx, _ in enumerate(N))
        if round_cmp(s, c.cost, CHECK_ROUND_PRECISION) != 0:
            errors["C3"].append(
                f"payments for selected project {c} are equal {s} != {c.cost}"
            )

    for c in NW:
        s = sum(pf[idx][c] for idx, _ in enumerate(N))
        if round_cmp(s, 0, CHECK_ROUND_PRECISION) != 0:
            errors["C4"].append(
                f"payments for not selected project {c} are equal {s} != 0"
            )

    if not stable:
        for c in NW:
            s = sum(leftover[idx] for idx, i in enumerate(N) if c in i)
            if round_cmp(s, c.cost, CHECK_ROUND_PRECISION) > 0:
                errors["C5"].append(
                    f"voters' leftover money for not selected project {c} are equal {s} > {c.cost}"
                )
    else:
        for c in NW:
            s = sum(
                max(max_payment[idx], leftover[idx])
                for idx, i in enumerate(N)
                if c in i
            )

            cost = c.cost if relaxation is None else relaxation.get_relaxed_cost(c)
            if round_cmp(s, cost, CHECK_ROUND_PRECISION) > 0:
                errors["S5"].append(
                    f"voters' leftover money (or the most they've spent for a project) for not selected project {c} are equal {s} > {cost}"
                )

    if verbose:
        for condition, error in errors.items():
            logger.info("(%s) %s", condition, error)

    return not errors


class PriceableResult:
    """
    Result of :py:func:`~pabutools.analysis.priceability.priceable`.
    Contains information about the optimization status of LP outcome.
    If the status is valid (i.e. `Optimal` / `Feasible`), the class contains
    the budget allocation, as well as the price system (`voter_budget`, `payment_functions`)
    that satisfies the priceable / stable-priceable property.

    Parameters
    ----------
        status : str
            Optimization status from PuLP (e.g., 'Optimal', 'Infeasible', etc.).
        allocation : list[:py:class:`~pabutools.election.instance.Project`], optional
            The selected collection of projects.
            Defaults to `None`.
        relaxation_beta : float or dict, optional
            Relaxation parameter beta, if used.
            Defaults to `None`.
        voter_budget : float, optional
            Voter initial endowment.
            Defaults to `None`.
        payment_functions : list[dict[:py:class:`~pabutools.election.instance.Project`, float]], optional
            List of payment functions for each voter.
            A payment function indicates the amounts paid for each project by a voter.
            Defaults to `None`.

    Attributes
    ----------
        status : str
            Optimization status from PuLP.
        allocation : list[:py:class:`~pabutools.election.instance.Project`] or None
            The selected collection of projects.
            `None` if the optimization status is not `Optimal` / `Feasible`.
        relaxation_beta : float or dict or None
            Relaxation parameter beta, if applicable.
        voter_budget : float or None
            Voter initial endowment.
            `None` if the optimization status is not `Optimal` / `Feasible`.
        payment_functions : list[dict[:py:class:`~pabutools.election.instance.Project`, float]] or None
            List of payment functions for each voter.
            A payment function indicates the amounts paid for each project by a voter.
            `None` if the optimization status is not `Optimal` / `Feasible`.
    """

    def __init__(
        self,
        status: str,
        allocation: list[Project] | None = None,
        relaxation_beta: float | dict = None,
        voter_budget: float | None = None,
        payment_functions: list[dict[Project, float]] | None = None,
    ) -> None:
        self.status = status
        self.allocation = allocation
        self.relaxation_beta = relaxation_beta
        self.voter_budget = voter_budget
        self.payment_functions = payment_functions

    def validate(self) -> bool | None:
        """
        Checks if the optimization status is 'Optimal' / 'Feasible'.

        Returns
        -------
            bool or None
                `True` if optimization succeeded,
                `False` if failed,
                `None` if status is unknown.
        """
        if self.status == pulp.LpStatusNotSolved:
            return None
        return self.status in [pulp.LpStatusOptimal]

    def __repr__(self):
        return f"PriceableResult[{self.status}]"

def priceable(
    instance: Instance,
    profile: AbstractApprovalProfile,
    budget_allocation: Collection[Project] | None = None,
    voter_budget: Numeric | None = None,
    payment_functions: list[dict[Project, Numeric]] | None = None,
    stable: bool = False,
    exhaustive: bool = True,
    relaxation: Relaxation | None = None,
    *,
    max_seconds: int = 600,
    verbose: bool = False,
) -> PriceableResult:
    """
        Finds a priceable / stable-priceable budget allocation for approval profile
        using Linear Programming via `mip` Python package.

        Reference paper: https://www.cs.utoronto.ca/~nisarg/papers/priceability.pdf

        Parameters
        ----------
            instance : :py:class:`~pabutools.election.instance.Instance`
                The instance.
            profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
                The profile.
            budget_allocation : Collection[:py:class:`~pabutools.election.instance.Project`], optional
                The selected collection of projects.
                If specified, the allocation is hardcoded into the model.
                Defaults to `None`.
            voter_budget : Numeric
                Voter initial endowment.
                If specified, the voter budget is hardcoded into the model.
                Defaults to `None`.
            payment_functions : Collection[dict[:py:class:`~pabutools.election.instance.Project`, Numeric]]
                Collection of payment functions for each voter.
                If specified, the payment functions are hardcoded into the model.
                Defaults to `None`.
            stable : bool, optional
                Search stable-priceable allocation.
                Defaults to `False`.
            exhaustive : bool, optional
                Search exhaustive allocation.
                Defaults to `True`.
            relaxation : :py:class:`~pabutools.analysis.priceability_relaxation.Relaxation`, optional
                Relaxation method to the stable-priceability condition.
                Defaults to `None`.
            **max_seconds : int, optional
                Model's maximum runtime in seconds.
                Defaults to 600.
            **verbose : bool, optional
                Display additional information.
                Defaults to `False`.

        Returns
        -------
            :py:class:`~pabutools.analysis.priceability.PriceableResult`
                Dataclass containing priceable result details.

    """
    C = instance
    N = profile
    INF = instance.budget_limit * 10

    model = pulp.LpProblem("stable-priceability" if stable else "priceability", pulp.LpMaximize)

    # voter budget
    b = pulp.LpVariable("voter_budget", lowBound=0)
    if voter_budget is not None:
        model += b == voter_budget, "C_voter_budget"

    # prevent empty allocation as a result
    model += b * profile.num_ballots() >= instance.budget_limit, "C_no_empty"

    # payment functions
    p_vars = [
        {c: pulp.LpVariable(f"p_{idx}_{c.name}", lowBound=0) for c in C}
        for idx, i in enumerate(N)
    ]
    if payment_functions is not None:
        for idx, _ in enumerate(N):
            for c in C:
                model += p_vars[idx][c] == payment_functions[idx][c], f"C_pf_{idx}_{c.name}"

    # winning allocation
    x_vars = {c: pulp.LpVariable(f"x_{c.name}", cat="Binary") for c in C}
    if relaxation is not None:
        for c in C:
            relaxation.variables[f"x_{c.name}"] = x_vars[c]
    if budget_allocation is not None:
        for c in C:
            model += x_vars[c] == int(c in budget_allocation), f"C_init_alloc_{c.name}"

    cost_total = pulp.lpSum(x_vars[c] * c.cost for c in C)

    # (C0a) the winning allocation is feasible
    model += cost_total <= instance.budget_limit, "C_alloc_feas"

    if exhaustive:
        # (C0b) the winning allocation is exhaustive
        for c in C:
            model += cost_total + c.cost + x_vars[c] * INF >= instance.budget_limit + 1, f"C_alloc_exh_{c.name}"

    # (C1) voter can pay only for projects they approve of
    for idx, i in enumerate(N):
        for c in C:
            if c not in i:
                model += p_vars[idx][c] == 0, f"C_app_{idx}_{c.name}"

    # (C2) voter will not spend more than their initial budget
    for idx, _ in enumerate(N):
        model += pulp.lpSum(p_vars[idx][c] for c in C) <= b, f"C_no_overspend_{idx}"

    # (C3) the sum of the payments for selected project equals its cost
    for c in C:
        payments_total = pulp.lpSum(p_vars[idx][c] for idx, _ in enumerate(N))
        model += payments_total <= c.cost, f"C_pay_to_cost_{c.name}_nomore"
        model += c.cost + (x_vars[c] - 1) * INF <= payments_total,  f"C_pay_to_cost_{c.name}_selected"

    # (C4) voters do not pay for not selected projects
    for idx, _ in enumerate(N):
        for c in C:
            model += 0 <= p_vars[idx][c], f"C_nonselected_{idx}_{c.name}_lb"
            model += p_vars[idx][c] <= x_vars[c] * INF, f"C_nonselected_{idx}_{c.name}_ub"

    if relaxation is not None:
        relaxation.add_beta(model)

    if not stable:
        r_vars = [pulp.LpVariable(f"r_{idx}") for idx, _ in enumerate(N)]
        for idx, _ in enumerate(N):
            model += r_vars[idx] == b - pulp.lpSum(p_vars[idx][c] for c in C), f"C_rest_money_{idx}"

        # (C5) supporters of not selected project have no more money than its cost
        for c in C:
            model += (
                pulp.lpSum(r_vars[idx] for idx, i in enumerate(N) if c in i)
                <= c.cost + x_vars[c] * INF
            ), f"C_supp_notselected_noafford_{c.name}"
    else:
        m_vars = [pulp.LpVariable(f"m_{idx}") for idx, _ in enumerate(N)]
        # Add the vars to the relaxation
        if relaxation is not None:
            for idx, _ in enumerate(N):
                relaxation.variables[f"m_{idx}"] = m_vars[idx]
        for idx, _ in enumerate(N):
            for c in C:
                model += m_vars[idx] >= p_vars[idx][c]
            model += m_vars[idx] >= b - pulp.lpSum(p_vars[idx][c] for c in C)

        # (S5) stability constraint
        if relaxation is None:
            for c in C:
                model += (
                    pulp.lpSum(m_vars[idx] for idx, i in enumerate(N) if c in i)
                    <= c.cost + x_vars[c] * INF
                )
        else:
            relaxation.add_stability_constraint(model)

    if relaxation is not None:
        relaxation.add_objective(model)
    else:
        model += 0  # No-op objective if none is specified

    solver = pulp.PULP_CBC_CMD(msg=verbose, timeLimit=max_seconds)
    status = model.solve(solver)

    if status not in [pulp.LpStatusOptimal]:
        return PriceableResult(status=status)

    payment_functions = [collections.defaultdict(float) for _ in N]
    for idx, _ in enumerate(N):
        for c in C:
            val = pulp.value(p_vars[idx][c])
            if val is not None and val > 1e-8:
                payment_functions[idx][c] = val

    return PriceableResult(
        status=status,
        allocation=list(sorted([c for c in C if pulp.value(x_vars[c]) >= 0.99])),
        voter_budget=pulp.value(b),
        relaxation_beta=(
            relaxation.get_beta() if relaxation is not None else None
        ),
        payment_functions=payment_functions,
    )