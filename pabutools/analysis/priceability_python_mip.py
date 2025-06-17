"""
Module with tools for analysis of the priceability / stable-priceability property of budget allocation.
"""

from __future__ import annotations

import collections
import warnings
from collections.abc import Collection

from pabutools.analysis.priceability_relaxation import Relaxation
from pabutools.election import (
    Instance,
    AbstractApprovalProfile,
    Project,
    total_cost,
)
from pabutools.utils import Numeric, round_cmp


try:
    from mip import Model, xsum, minimize, OptimizationStatus, BINARY
except ImportError:
    raise ImportError(
        "The priceability functions need the python-mip package. This is no longer listed as a requirement as we are "
        "slowly moving to PuLP for Python 3.13 compatibility. If you are using Python < 3.13, install manually the "
        "python-mip package. If you are using Python 3.13, please help us translate this file to PuLP."
    )

CHECK_ROUND_PRECISION = 2
ROUND_PRECISION = 6

warnings.warn("The priceability modules based on python-mip are deprecated. Please use the new ones based "
              "on pulp.", DeprecationWarning)

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
            print(f"({condition}) {error}")

    return not errors


class PriceableResult:
    """
    Result of :py:func:`~pabutools.analysis.priceability.priceable`.
    Contains information about the optimization status of ILP outcome.
    If the status is valid (i.e. `OPTIMAL` / `FEASIBLE`), the class contains
    the budget allocation, as well as the price system (`voter_budget`, `payment_functions`)
    that satisfies the priceable / stable-priceable property.

    Parameters
    ----------
        status : OptimizationStatus
            Optimization status of the ILP outcome.
        allocation : Collection[:py:class:`~pabutools.election.instance.Project`], optional
            The selected collection of projects.
            Defaults to `None`.
        voter_budget : float, optional
            Voter initial endowment.
            Defaults to `None`.
        payment_functions : list[dict[:py:class:`~pabutools.election.instance.Project`, Numeric]], optional
            List of payment functions for each voter.
            A payment function indicates the amounts paid for each project by a voter.
            Defaults to `None`.

    Attributes
    ----------
        status : OptimizationStatus
            Optimization status of the ILP outcome.
        allocation : Collection[:py:class:`~pabutools.election.instance.Project`] or None
            The selected collection of projects.
            `None` if the optimization status is not `OPTIMAL` / `FEASIBLE`.
        voter_budget : bool or None
            Voter initial endowment.
            `None` if the optimization status is not `OPTIMAL` / `FEASIBLE`.
        payment_functions : list[dict[:py:class:`~pabutools.election.instance.Project`, Numeric]] or None
            List of payment functions for each voter.
            A payment function indicates the amounts paid for each project by a voter.
            `None` if the optimization status is not `OPTIMAL` / `FEASIBLE`.

    """

    def __init__(
        self,
        status: OptimizationStatus,
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
        Checks if the optimization status is `OPTIMAL` / `FEASIBLE`.
        Returns
        -------
            bool
                Validity of optimization status.

        """
        if self.status == OptimizationStatus.NO_SOLUTION_FOUND:
            return None
        return self.status in [OptimizationStatus.OPTIMAL, OptimizationStatus.FEASIBLE]


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
    mip_solver_name: str | None = None,
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
        **mip_solver_name : str, optional
            python-mip solver to use.
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

    mip_model = Model("stable-priceability" if stable else "priceability", solver_name=mip_solver_name)
    mip_model.verbose = verbose
    mip_model.integer_tol = 1e-8

    # voter budget
    b = mip_model.add_var(name="voter_budget")
    if voter_budget is not None:
        mip_model += b == voter_budget

    # prevent empty allocation as a result
    mip_model += b * profile.num_ballots() >= instance.budget_limit

    # payment functions
    p_vars = [
        {c: mip_model.add_var(name=f"p_{idx}_{c.name}") for c in C}
        for idx, i in enumerate(N)
    ]
    if payment_functions is not None:
        for idx, _ in enumerate(N):
            for c in C:
                mip_model += p_vars[idx][c] == payment_functions[idx][c]

    # winning allocation
    x_vars = {c: mip_model.add_var(var_type=BINARY, name=f"x_{c.name}") for c in C}
    if budget_allocation is not None:
        for c in C:
            if c in budget_allocation:
                mip_model += x_vars[c] == 1
            else:
                mip_model += x_vars[c] == 0

    cost_total = xsum(x_vars[c] * c.cost for c in C)

    # (C0a) the winning allocation is feasible
    mip_model += cost_total <= instance.budget_limit

    if exhaustive:
        # (C0b) the winning allocation is exhaustive
        for c in C:
            mip_model += (
                cost_total + c.cost + x_vars[c] * INF >= instance.budget_limit + 1
            )

    # (C1) voter can pay only for projects they approve of
    for idx, i in enumerate(N):
        for c in C:
            if c not in i:
                mip_model += p_vars[idx][c] == 0

    # (C2) voter will not spend more than their initial budget
    for idx, _ in enumerate(N):
        mip_model += xsum(p_vars[idx][c] for c in C) <= b

    # (C3) the sum of the payments for selected project equals its cost
    for c in C:
        payments_total = xsum(p_vars[idx][c] for idx, _ in enumerate(N))

        mip_model += payments_total <= c.cost
        mip_model += c.cost + (x_vars[c] - 1) * INF <= payments_total

    # (C4) voters do not pay for not selected projects
    for idx, _ in enumerate(N):
        for c in C:
            mip_model += 0 <= p_vars[idx][c]
            mip_model += p_vars[idx][c] <= x_vars[c] * INF

    if relaxation is not None:
        relaxation.add_beta(mip_model)

    if not stable:
        r_vars = [mip_model.add_var(name=f"r_{idx}") for idx, i in enumerate(N)]
        for idx, _ in enumerate(N):
            mip_model += r_vars[idx] == b - xsum(p_vars[idx][c] for c in C)

        # (C5) supporters of not selected project have no more money than its cost
        for c in C:
            mip_model += (
                xsum(r_vars[idx] for idx, i in enumerate(N) if c in i)
                <= c.cost + x_vars[c] * INF
            )
    else:
        m_vars = [mip_model.add_var(name=f"m_{idx}") for idx, i in enumerate(N)]
        for idx, _ in enumerate(N):
            for c in C:
                mip_model += m_vars[idx] >= p_vars[idx][c]
            mip_model += m_vars[idx] >= b - xsum(p_vars[idx][c] for c in C)

        # (S5) stability constraint
        if relaxation is None:
            for c in C:
                mip_model += (
                    xsum(m_vars[idx] for idx, i in enumerate(N) if c in i)
                    <= c.cost + x_vars[c] * INF
                )
        else:
            relaxation.add_stability_constraint(mip_model)

    if relaxation is not None:
        relaxation.add_objective(mip_model)

    if relaxation is None:
        status = mip_model.optimize(max_seconds=max_seconds, max_solutions=1)
    else:
        status = mip_model.optimize(max_seconds=max_seconds)

    if (
        hasattr(OptimizationStatus, "INF_OR_UNBD")
        and status == OptimizationStatus.INF_OR_UNBD
    ):
        # https://support.gurobi.com/hc/en-us/articles/4402704428177-How-do-I-resolve-the-error-Model-is-infeasible-or-unbounded
        # https://github.com/coin-or/python-mip/blob/1.15.0/mip/gurobi.py#L777
        # https://github.com/coin-or/python-mip/blob/1.16-pre/mip/gurobi.py#L778
        # This is not part of old python-mip version, hence the first test
        #
        mip_model.solver.set_int_param("DualReductions", 0)
        mip_model.reset()
        if relaxation is None:
            mip_model.optimize(max_seconds=max_seconds, max_solutions=1)
        else:
            mip_model.optimize(max_seconds=max_seconds)
        status = (
            OptimizationStatus.INFEASIBLE
            if mip_model.solver.get_int_attr("status") == 3
            else OptimizationStatus.UNBOUNDED
        )

    if status not in [OptimizationStatus.OPTIMAL, OptimizationStatus.FEASIBLE]:
        return PriceableResult(status=status)

    payment_functions = [collections.defaultdict(float) for _ in N]
    for idx, _ in enumerate(N):
        for c in C:
            if p_vars[idx][c].x > 1e-8:
                payment_functions[idx][c] = p_vars[idx][c].x

    return PriceableResult(
        status=status,
        allocation=list(sorted([c for c in C if x_vars[c].x >= 0.99])),
        voter_budget=b.x,
        relaxation_beta=(
            relaxation.get_beta(mip_model) if relaxation is not None else None
        ),
        payment_functions=payment_functions,
    )
