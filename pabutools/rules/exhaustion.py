from __future__ import annotations

from copy import deepcopy, copy
from collections.abc import Collection, Callable, Iterable

from pabutools.election.instance import Instance, Project
from pabutools.election.profile import AbstractProfile
from pabutools.fractions import frac
from pabutools.rules.budgetallocation import BudgetAllocation

from pabutools.utils import Numeric

def completion_by_rule_combination(
    instance: Instance,
    profile: AbstractProfile,
    rule_sequence: Collection[Callable],
    rule_params: Collection[dict] | None = None,
    initial_budget_allocation: Iterable[Project] | None = None,
    resoluteness: bool = True,
) -> BudgetAllocation | list[BudgetAllocation]:
    """
    Runs the given rules on the given instance and profile in sequence until an exhaustive budget
    allocation has been reached (or all rules have been applied). This is useful if the first rules
    are non-exhaustive. In the irresolute version, all outcomes are completed separately.

    Parameters
    ----------
        instance: :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        rule_sequence: Iterable[Callable]
            Iterable of the rule functions.
        rule_params: Iterable[dict], optional
            Iterable of dictionaries of additional parameters that are passed as keyword arguments
            to the rule functions. Defaults to `{}`.
        initial_budget_allocation : Iterable[:py:class:`~pabutools.election.instance.Project`], optional
            An initial budget allocation, typically empty. Defaults to `[]`.
        resoluteness : bool, optional
            Set to `False` to obtain an irresolute outcome, where all tied budget allocations are
            returned. Defaults to True.

    Returns
    -------
        :py:class:`~pabutools.rules.budgetallocation.BudgetAllocation` | list[:py:class:`~pabutools.rules.budgetallocation.BudgetAllocation`]
            The selected projects.
    """
    if rule_params is not None and len(rule_sequence) != len(rule_params):
        raise ValueError(
            "Parameters rule_sequence and rule_params must be of equal length."
        )
    if rule_params is None:
        rule_params = [{} for _ in rule_sequence]
    for i, params in enumerate(rule_params):
        if "resoluteness" in params and params["resoluteness"] != resoluteness:
            raise ValueError(
                f"The rule parameter at position {i} sets the resoluteness parameter to a different "
                "one that the resoluteness argument passed to completion_by_rule_combination."
            )

    exhaustive_allocations = []  # Only used for resoluteness = False
    if initial_budget_allocation is None:
        previous_allocations = [BudgetAllocation()]
    else:
        previous_allocations = [BudgetAllocation(initial_budget_allocation)]

    # Go through the rules
    for index, rule in enumerate(rule_sequence):
        # Complete each previous budget allocation
        new_budget_allocations = []
        irresolute_all_exhaustive = True
        for budget_allocation in previous_allocations:
            # Compute the rule
            outcome = rule(
                instance,
                profile,
                initial_budget_allocation=budget_allocation,
                resoluteness=resoluteness,
                **rule_params[index],
            )
            if resoluteness:
                # Check exhaustiveness, if so return, else continue with new outcome
                if instance.is_exhaustive(outcome):
                    return outcome
                else:
                    new_budget_allocations = [outcome]
            else:
                # Go through all the new outcomes, save the exhaustive ones and continue with the others
                for alloc in outcome:
                    if instance.is_exhaustive(alloc):
                        if alloc not in exhaustive_allocations:
                            exhaustive_allocations.append(alloc)
                    else:
                        irresolute_all_exhaustive = False
                        new_budget_allocations.append(alloc)

        if not resoluteness and irresolute_all_exhaustive:
            return exhaustive_allocations
        previous_allocations = new_budget_allocations

    if resoluteness:
        return previous_allocations[0]
    return exhaustive_allocations + previous_allocations


def exhaustion_by_budget_increase(
    instance: Instance,
    profile: AbstractProfile,
    rule: Callable,
    rule_params: dict | None = None,
    initial_budget_allocation: Iterable[Project] | None = None,
    resoluteness: bool = True,
    exhaustive_stop: bool = True,
    budget_step: Numeric | None = None,
    budget_bound: Numeric | None = None,
) -> BudgetAllocation | list[BudgetAllocation]:
    """
    Runs the given rule iteratively with increasing budget, until an exhaustive allocation is
    retrieved or the budget limit is exceeded by the rule with increased budget. In the irresolute
    version, as soon as one outcome is exhaustive or infeasible, the procedure stops.

    If you are interested to only stop when the returned budget allocation is not feasible
    (and thus not when it is exhaustive), set :code:`exhaustive_stop=False`.

    Parameters
    ----------
        instance: :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        rule:
            The rule function
        rule_params: dict, optional
            Dictionary of additional parameters that are passed as keyword arguments to the rule
            function. Defaults to `{}`.
        initial_budget_allocation: Collection[Project], optional
            An initial budget allocation, typically empty. Defaults to `[]`. Overrides the parameter
            in `rule_params`.
        resoluteness : bool, optional
            Set to `False` to obtain an irresolute outcome, where all tied budget allocations
            are returned. Defaults to True.
        exhaustive_stop: bool, optional
            Set to `False` to disable the exhaustive allocation stop condition, leaving only
            the non-feasibility as the stop condition of this rule. Defaults to True.
        budget_step: Numeric
            The step at which the budget is increased. Defaults to 1% of the budget limit.
        budget_bound: Numeric
            An upper bound on the budget limit. The method stops if this bound is exceeded. Defaults
            to the budget limit multiplied by the number of agents plus 1.

    Returns
    -------
        BudgetAllocation | Iterable[BudgetAllocation]
            The selected budget allocation if resolute (:code:`resoluteness == True`), or the set of
            budget allocations if irresolute (:code:`resoluteness == False`).
    """
    if rule_params is None:
        rule_params = {}
    current_instance = deepcopy(instance)
    if initial_budget_allocation is None:
        initial_budget_allocation = BudgetAllocation()
    else:
        initial_budget_allocation = BudgetAllocation(initial_budget_allocation)
    rule_params["initial_budget_allocation"] = initial_budget_allocation
    if resoluteness:
        previous_outcome = copy(initial_budget_allocation)
    else:
        previous_outcome = [copy(initial_budget_allocation)]
    if budget_step is None:
        budget_step = instance.budget_limit * frac(1, 100)
    if budget_bound is None:
        budget_bound = instance.budget_limit * (profile.num_ballots() + 1)
    rule_params["resoluteness"] = resoluteness
    while current_instance.budget_limit <= budget_bound:
        outcome = rule(current_instance, profile, **rule_params)
        if resoluteness:
            if not instance.is_feasible(outcome):
                return previous_outcome
            if exhaustive_stop and instance.is_exhaustive(outcome):
                return outcome
            current_instance.budget_limit += budget_step
            previous_outcome = outcome
        else:
            if any(not instance.is_feasible(o) for o in outcome):
                return previous_outcome
            if exhaustive_stop and any(instance.is_exhaustive(o) for o in outcome):
                return outcome
            current_instance.budget_limit += budget_step
            previous_outcome = outcome
    return previous_outcome
