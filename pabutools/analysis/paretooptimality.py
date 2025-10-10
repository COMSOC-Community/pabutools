from collections.abc import Collection
import gurobipy as gp

from pabutools.election import (
    Instance,
    Project,
    SatisfactionMeasure,
    AbstractProfile,
)

def is_pareto_optimal_lp(
    instance: Instance,
    profile: AbstractProfile,
    sat_class: type[SatisfactionMeasure],
    budget_allocation: Collection[Project],
    env: gp.Env | None = None,
    essential_projects: bool = False,
):
    model = gp.Model("Is Pareto Optimal", env=env)
    model.setParam("OutputFlag", 0)

    x = {proj: model.addVar(vtype=gp.GRB.BINARY, name=f"x_{proj}") for proj in instance}
    y = {i: model.addVar(vtype=gp.GRB.BINARY, name=f"y_{i}") for i in range(profile.num_ballots())}

    # Add essential projects
    for i, ballot in enumerate(profile):
        sat = sat_class(instance, profile, ballot)
        max_sat = sat.sat(ballot)
        current_sat = sat.sat(budget_allocation)
        if essential_projects and max_sat == current_sat:
            for proj in ballot:
                model.addLConstr(x[proj] == 1)

    model.setObjective(0, gp.GRB.MAXIMIZE)

    model.addConstr(
        gp.quicksum(x[proj] * proj.cost for proj in instance) <= instance.budget_limit,
    )

    model.addConstr(gp.quicksum(y.values()) == 1)

    for i, ballot in enumerate(profile):
        sat = sat_class(instance, profile, ballot)
        model.addConstr(gp.quicksum(x[proj] * proj.cost for proj in ballot) >= sat.sat(budget_allocation) + y[i])

    model.optimize()

    if model.Status == gp.GRB.OPTIMAL:
        dominant_projects = set(proj for proj in instance if x[proj].X > 0)
        return False, model.Runtime, dominant_projects
    return True, model.Runtime, None
