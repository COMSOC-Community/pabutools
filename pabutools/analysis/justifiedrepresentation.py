from __future__ import annotations

from collections.abc import Collection, Callable, Iterable
import gurobipy as gp

from pabutools.utils import Numeric

from pabutools.analysis.cohesiveness import cohesive_groups, is_large_enough
from pabutools.election import (
    Instance,
    AbstractApprovalProfile,
    Project,
    SatisfactionMeasure,
    Additive_Cardinal_Sat,
    AbstractCardinalProfile,
    ApprovalBallot,
    total_cost,
    AbstractProfile,
)
from pabutools.utils import powerset


def is_in_core(
    instance: Instance,
    profile: AbstractProfile,
    sat_class: type[SatisfactionMeasure],
    budget_allocation: Collection[Project],
    up_to_func: Callable[[Iterable[Numeric]], Numeric] | None = None,
) -> bool:
    """
    Test if a given budget allocation is in the core of the instance.
    """
    for group in powerset(profile):
        if len(group) > 0:
            for project_set in powerset(instance):
                if is_large_enough(
                    len(group),
                    profile.num_ballots(),
                    total_cost(project_set),
                    instance.budget_limit,
                ):
                    all_better_alone = True
                    for ballot in group:
                        sat = sat_class(instance, profile, ballot)
                        surplus = 0
                        if up_to_func is not None:
                            surplus = up_to_func(
                                sat.sat_project(p)
                                for p in project_set
                                if p not in budget_allocation
                            )
                        if sat.sat(budget_allocation) + surplus >= sat.sat(project_set):
                            all_better_alone = False
                            break
                    if all_better_alone:
                        return False
    return True


def _find_coalition(
    instance: Instance,
    profile: AbstractProfile,
    sat_class: type[SatisfactionMeasure],
    budget_allocation: Collection[Project],
    x,
    y,
    env: gp.Env | None = None,
):
    promising_projects = [proj for proj in instance if x[proj].X > 0]
    promising_voters = [i for i in range(profile.num_ballots()) if y[i].X > 0]

    model = gp.Model("Find blocking coalition", env=env)
    model.setParam("OutputFlag", 0)

    x = {proj: model.addVar(vtype=gp.GRB.BINARY, name=f"x_{proj}") for proj in promising_projects}
    y = {i: model.addVar(vtype=gp.GRB.BINARY, name=f"y_{i}") for i in promising_voters}

    model.setObjective(0, gp.GRB.MAXIMIZE)

    # V is non-empty
    model.addConstr(gp.quicksum(y.values()) >= 1)

    # cost(T) * n ≤ |V| * k
    model.addConstr(gp.quicksum(x[proj] * proj.cost for proj in promising_projects) * profile.num_ballots() <= gp.quicksum(y.values()) * instance.budget_limit)

    # ∀ i ∈ V u_i(T) > u_i(W)
    for i, ballot in enumerate(profile):
        if i not in promising_voters:
            continue
        sat = sat_class(instance, profile, ballot)
        model.addConstr(gp.quicksum(x[proj] * proj.cost for proj in ballot if proj in promising_projects) >= y[i] * (sat.sat(budget_allocation) + 1))

    model.optimize()

    if model.Status == gp.GRB.OPTIMAL:
        blocking_projects = set(proj for proj in promising_projects if x[proj].X > 0)
        blocking_voters = [i for i in promising_voters if y[i].X > 0]
        return False, (blocking_projects, blocking_voters)
    return None, None


def _is_in_core_lp(
    instance: Instance,
    profile: AbstractProfile,
    sat_class: type[SatisfactionMeasure],
    budget_allocation: Collection[Project],
    env: gp.Env | None = None,
    timeout: float = float("inf"),
    relax_projects: bool = False,
    relax_voters: bool = False,
    branching_priority: bool = False,
    start_hint_vals: bool = False,
    voters_removal: bool = False,
):
    model = gp.Model("Is in Core", env=env)
    model.setParam("OutputFlag", 0)
    model.setParam("TimeLimit", timeout)

    x_vtype = gp.GRB.CONTINUOUS if relax_projects else gp.GRB.BINARY
    y_vtype = gp.GRB.CONTINUOUS if relax_voters else gp.GRB.BINARY

    # x_i ∈ T ⊆ C
    x = {proj: model.addVar(vtype=x_vtype, lb=0, ub=1, name=f"x_{proj}") for proj in instance}
    # y_i ∈ V ⊆ N
    y = {i: model.addVar(vtype=y_vtype, lb=0, ub=1, name=f"y_{i}") for i in range(profile.num_ballots())}

    approvers = {proj: 0 for proj in instance}
    for ballot in profile:
        for proj in ballot:
            approvers[proj] += 1

    # Set less probable projects to 0 at the beginning
    for proj in instance:
        if start_hint_vals and proj.cost * profile.num_ballots() > approvers[proj] * instance.budget_limit:
            x[proj].setAttr("Start", 0)
        # Give projects higher priority depending on approvers/cost score
        if branching_priority:
            x[proj].setAttr("BranchPriority", int(1000 * approvers[proj] / max(proj.cost, 1)))

    # Remove impossible voters
    for i, ballot in enumerate(profile):
        sat = sat_class(instance, profile, ballot)
        max_sat = sat.sat(ballot)
        current_sat = sat.sat(budget_allocation)
        if voters_removal and max_sat == current_sat:
            model.addLConstr(y[i] == 0)

        if start_hint_vals and current_sat == 0:
            y[i].setAttr("VarHintVal", 1)

        # Give voters higher priority depending on current utility
        priority = max_sat - current_sat
        if branching_priority:
            y[i].setAttr("BranchPriority", int(priority))

    model.setObjective(0, gp.GRB.MAXIMIZE)

    # V is non-empty
    model.addConstr(gp.quicksum(y.values()) >= 1)

    # cost(T) * n ≤ |V| * k
    model.addConstr(gp.quicksum(x[proj] * proj.cost for proj in instance) * profile.num_ballots() <= gp.quicksum(y.values()) * instance.budget_limit)

    # ∀ i ∈ V u_i(T) > u_i(W)
    for i, ballot in enumerate(profile):
        sat = sat_class(instance, profile, ballot)
        model.addConstr(gp.quicksum(x[proj] * proj.cost for proj in ballot) >= y[i] * (sat.sat(budget_allocation) + 1))

    model.optimize()

    if model.Status == gp.GRB.TIME_LIMIT:
        return None, model.Runtime, None

    if model.Status == gp.GRB.OPTIMAL:
        if relax_projects or relax_voters:
            res, blocking_coalition = _find_coalition(instance, profile, sat_class, budget_allocation, x, y, env)
            return res, model.Runtime, blocking_coalition
        return False, model.Runtime, None
    return True, model.Runtime, None


def is_in_core_lp(
    instance: Instance,
    profile: AbstractProfile,
    sat_class: type[SatisfactionMeasure],
    budget_allocation: Collection[Project],
    env: gp.Env | None = None,
    relaxations: bool = False,
    branching_priority: bool = False,
    start_hint_vals: bool = False,
    voters_removal: bool = False,
):
    if not relaxations:
        return _is_in_core_lp(
            instance,
            profile,
            sat_class,
            budget_allocation,
            env=env,
            timeout=60 * 30,
            branching_priority=branching_priority,
            start_hint_vals=start_hint_vals,
            voters_removal=voters_removal,
        )

    res1, exec_time1, blocking_coalition1 = _is_in_core_lp(instance, profile, sat_class, budget_allocation, env=env, relax_projects=True, relax_voters=True)

    res2, exec_time2, blocking_coalition2 = _is_in_core_lp(instance, profile, sat_class, budget_allocation, env=env, relax_projects=True, relax_voters=False)

    res3, exec_time3, blocking_coalition3 = _is_in_core_lp(instance, profile, sat_class, budget_allocation, env=env, relax_projects=False, relax_voters=True)

    exec_time = exec_time1 + exec_time2 + exec_time3

    if res1 or res2 or res3:
        return True, exec_time, None

    if not res1:
        return res1, exec_time, blocking_coalition1
    if not res2:
        return res2, exec_time, blocking_coalition2
    if not res3:
        return res3, exec_time, blocking_coalition3

    return None, exec_time, None


def is_strong_EJR_approval(
    instance: Instance,
    profile: AbstractApprovalProfile,
    sat_class: type[SatisfactionMeasure],
    budget_allocation: Collection[Project],
) -> bool:
    """
    Test if a budget allocation satisfies strong EJR for the given instance and the given profile of
    approval ballots.
    """
    for group, project_set in cohesive_groups(instance, profile):
        all_agents_sat = True
        for ballot in group:
            sat = sat_class(instance, profile, ballot)
            if sat.sat(budget_allocation) < sat.sat(project_set):
                all_agents_sat = False
                break
        if not all_agents_sat:
            return False
    return True


def is_EJR_approval(
    instance: Instance,
    profile: AbstractApprovalProfile,
    sat_class: type[SatisfactionMeasure],
    budget_allocation: Collection[Project],
    up_to_func: Callable[[Iterable[Numeric]], Numeric] | None = None,
) -> bool:
    """
    Test if a budget allocation satisfies EJR for the given instance and the given profile of
    approval ballots.
    """
    for group, project_set in cohesive_groups(instance, profile):
        one_agent_sat = False
        for ballot in group:
            sat = sat_class(instance, profile, ballot)
            surplus = 0
            if up_to_func is not None:
                surplus = up_to_func(
                    sat.sat_project(p)
                    for p in project_set
                    if p not in budget_allocation
                )
            if sat.sat(budget_allocation) + surplus >= sat.sat(project_set):
                one_agent_sat = True
                break
        if not one_agent_sat:
            return False
    return True


def is_EJR_any_approval(
    instance: Instance,
    profile: AbstractApprovalProfile,
    sat_class: type[SatisfactionMeasure],
    budget_allocation: Collection[Project],
) -> bool:
    """
    Test if a budget allocation satisfies EJR up to any project for the given instance and the
    given profile of approval ballots.
    """
    return is_EJR_approval(
        instance,
        profile,
        sat_class,
        budget_allocation,
        up_to_func=lambda x: min(x, default=0),
    )


def is_EJR_one_approval(
    instance: Instance,
    profile: AbstractApprovalProfile,
    sat_class: type[SatisfactionMeasure],
    budget_allocation: Collection[Project],
) -> bool:
    """
    Test if a budget allocation satisfies EJR up to one project for the given instance and the given
    profile of approval ballots.
    """
    return is_EJR_approval(
        instance,
        profile,
        sat_class,
        budget_allocation,
        up_to_func=lambda x: max(x, default=0),
    )


def is_PJR_approval(
    instance: Instance,
    profile: AbstractApprovalProfile,
    sat_class: type[SatisfactionMeasure],
    budget_allocation: Collection[Project],
    up_to_func: Callable[[Iterable[Numeric]], Numeric] | None = None,
) -> bool:
    """
    Test if a budget allocation satisfies PJR for the given instance and the given profile of
    approval ballots.
    """
    for group, project_set in cohesive_groups(instance, profile):
        sat = sat_class(instance, profile, ApprovalBallot(instance))
        threshold = sat.sat(project_set)
        group_approved = {p for p in budget_allocation if any(p in b for b in group)}
        surplus = 0
        if up_to_func is not None:
            surplus = up_to_func(
                sat.sat_project(p) for p in project_set if p not in budget_allocation
            )
        group_sat = sat.sat(group_approved) + surplus
        if group_sat < threshold:
            return False
    return True


def is_PJR_any_approval(
    instance: Instance,
    profile: AbstractApprovalProfile,
    sat_class: type[SatisfactionMeasure],
    budget_allocation: Collection[Project],
) -> bool:
    """
    Test if a budget allocation satisfies PJR up to any project for the given instance and the given
    profile of approval ballots.
    """
    return is_PJR_approval(
        instance,
        profile,
        sat_class,
        budget_allocation,
        up_to_func=lambda x: min(x, default=0),
    )


def is_PJR_one_approval(
    instance: Instance,
    profile: AbstractApprovalProfile,
    sat_class: type[SatisfactionMeasure],
    budget_allocation: Collection[Project],
) -> bool:
    """
    Test if a budget allocation satisfies PJR up to one project for the given instance and the given
    profile of approval ballots.
    """
    return is_PJR_approval(
        instance,
        profile,
        sat_class,
        budget_allocation,
        up_to_func=lambda x: max(x, default=0),
    )


def is_strong_EJR_cardinal(
    instance: Instance,
    profile: AbstractCardinalProfile,
    budget_allocation: Collection[Project],
    sat_class: type[SatisfactionMeasure] | None = None,
) -> bool:
    """
    Test if a budget allocation satisfies strong EJR for the given instance and the given profile
    of cardinal ballots.
    """
    if sat_class is None:
        sat_class = Additive_Cardinal_Sat
    for group, project_set in cohesive_groups(instance, profile):
        all_agents_sat = True
        threshold = sum(min(b[p] for b in group) for p in project_set)
        for ballot in group:
            sat = sat_class(instance, profile, ballot)
            if sat.sat(budget_allocation) < threshold:
                all_agents_sat = False
                break
        if not all_agents_sat:
            return False
    return True


def is_EJR_cardinal(
    instance: Instance,
    profile: AbstractCardinalProfile,
    budget_allocation: Collection[Project],
    sat_class: type[SatisfactionMeasure] | None = None,
    up_to_func: Callable[[Iterable[Numeric]], Numeric] | None = None,
) -> bool:
    """
    Test if a budget allocation satisfies EJR for the given instance and the given profile of
    cardinal ballots.
    """
    if sat_class is None:
        sat_class = Additive_Cardinal_Sat
    for group, project_set in cohesive_groups(instance, profile):
        one_agent_sat = False
        threshold = sum(min(b[p] for b in group) for p in project_set)
        for ballot in group:
            sat = sat_class(instance, profile, ballot)
            surplus = 0
            if up_to_func is not None:
                surplus = up_to_func(
                    sat.sat_project(p)
                    for p in project_set
                    if p not in budget_allocation
                )
            if sat.sat(budget_allocation) + surplus >= threshold:
                one_agent_sat = True
                break
        if not one_agent_sat:
            return False
    return True


def is_EJR_any_cardinal(
    instance: Instance,
    profile: AbstractCardinalProfile,
    budget_allocation: Collection[Project],
) -> bool:
    """
    Test if a budget allocation satisfies EJR up to any project for the given instance and
    the  given profile of cardinal ballots.
    """
    return is_EJR_cardinal(
        instance, profile, budget_allocation, up_to_func=lambda x: min(x, default=0)
    )


def is_EJR_one_cardinal(
    instance: Instance,
    profile: AbstractCardinalProfile,
    budget_allocation: Collection[Project],
) -> bool:
    """
    Test if a budget allocation satisfies EJR up to one project for the given instance and
    the given profile of cardinal ballots.
    """
    return is_EJR_cardinal(
        instance, profile, budget_allocation, up_to_func=lambda x: max(x, default=0)
    )


def is_PJR_cardinal(
    instance: Instance,
    profile: AbstractCardinalProfile,
    budget_allocation: Iterable[Project],
    up_to_func: Callable[[Iterable[Numeric]], Numeric] | None = None,
) -> bool:
    """
    Test if a budget allocation satisfies PJR for the given instance and the given profile of
    cardinal ballots.
    """
    for group, project_set in cohesive_groups(instance, profile):
        threshold = sum(min(b[p] for b in group) for p in project_set)
        group_sat = sum(max(b[p] for b in group) for p in budget_allocation)
        surplus = 0
        if up_to_func is not None:
            surplus = up_to_func(
                max(b[p] for b in group)
                for p in project_set
                if p not in budget_allocation
            )
        if group_sat + surplus < threshold:
            return False
    return True


def is_PJR_any_cardinal(
    instance: Instance,
    profile: AbstractCardinalProfile,
    budget_allocation: Iterable[Project],
) -> bool:
    """
    Test if a budget allocation satisfies PJR up to any project for the given instance and
    the given profile of cardinal ballots.
    """
    return is_PJR_cardinal(
        instance, profile, budget_allocation, up_to_func=lambda x: min(x, default=0)
    )


def is_PJR_one_cardinal(
    instance: Instance,
    profile: AbstractCardinalProfile,
    budget_allocation: Iterable[Project],
) -> bool:
    """
    Test if a budget allocation satisfies PJR up to one project for the given instance and
    the given profile of cardinal ballots.
    """
    return is_PJR_cardinal(
        instance, profile, budget_allocation, up_to_func=lambda x: max(x, default=0)
    )
