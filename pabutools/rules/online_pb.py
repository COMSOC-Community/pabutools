"""Rules for online participatory budgeting."""
from collections.abc import Iterable

import networkx as nx

from pabutools.election import Instance, AbstractApprovalProfile, Project, SatisfactionMeasure, total_cost
from pabutools.fractions import frac
from pabutools.rules import BudgetAllocation
from pabutools.rules.mes.mes_rule import MESVoter, MESProject, affordability_poor_rich
from pabutools.utils import Numeric


def greedy_budgeting(instance: Instance, profile: AbstractApprovalProfile, online_order: list[Project],
    sat_class: type[SatisfactionMeasure], initial_budget_allocation=None, resoluteness=True) -> BudgetAllocation:
    nb_voters = profile.num_ballots()

    if initial_budget_allocation is not None:
        res = BudgetAllocation(initial_budget_allocation)
    else:
        res = BudgetAllocation()

    available_budget = instance.budget_limit - total_cost(res)
    initial_budget_per_voter = frac(available_budget, nb_voters)

    voters = []
    sat_profile = profile.as_sat_profile(sat_class)
    for index, sat in enumerate(sat_profile):
        voters.append(
            MESVoter(
                index,
                sat.ballot,
                sat,
                initial_budget_per_voter,
                sat_profile.multiplicity(sat),
            )
        )
        index += 1

    projects = set()
    mes_projects_ordered = []
    for p in online_order:
        mes_p = MESProject(p)
        total_sat = 0
        for i, v in enumerate(voters):
            voter_sat = v.total_sat_project(p)
            if voter_sat > 0:
                total_sat += voter_sat
                mes_p.supporter_indices.append(i)
                mes_p.sat_supporter_map[v] = voter_sat
        if total_sat > 0:
            if p.cost > 0:
                mes_p.total_sat = total_sat
                afford = frac(p.cost, total_sat)
                mes_p.initial_affordability = afford
                mes_p.affordability = afford
                projects.add(mes_p)
        mes_projects_ordered.append(mes_p)

    for project in mes_projects_ordered:
        if (
                sum(voters[i].total_budget() for i in project.supporter_indices)
                >= project.cost
        ):
            q = affordability_poor_rich(voters, project)
            for i in project.supporter_indices:
                voters[i].budget -= min(
                    voters[i].budget, q * voters[i].sat.sat_project(project)
                )
            res.append(project.project)
    return res

def contribution_flow_network(projects: Iterable[Project], profile: AbstractApprovalProfile, voter_budget: Numeric):
    G = nx.DiGraph()

    # Define source and sink
    source = "source"
    sink = "sink"

    # Add project nodes and edges from source to project
    for p in projects:
        G.add_node(p.name, type='project')
        G.add_edge(source, p.name, capacity=p.cost)

    # Add ballot nodes and edges ballot to sink
    for i, ballot in enumerate(profile):
        for j in range(profile.multiplicity(ballot)):
            G.add_node(f"ballot_{i}_{j}", type='ballot')
            G.add_edge(f"ballot_{i}_{j}", sink, capacity=voter_budget)

            # Add edges from project to ballot
            for project in ballot:
                if project in projects:
                    G.add_edge(project.name, f"ballot_{i}_{j}", capacity=float('inf'))

    return G, source, sink


def efficient_greedy_budgeting(instance: Instance, profile: AbstractApprovalProfile, online_order: list[Project], initial_budget_allocation=None, resoluteness=True) -> BudgetAllocation:
    if initial_budget_allocation is not None:
        res = BudgetAllocation(initial_budget_allocation)
    else:
        res = BudgetAllocation()

    current_cost = total_cost(res)
    voters_budget = frac(instance.budget_limit - current_cost, profile.num_ballots())
    for project in online_order:
        if project.cost + current_cost <= instance.budget_limit:
            network, source, sink = contribution_flow_network(list(res) + [project], profile, voters_budget)
            flow_value = nx.maximum_flow_value(network, source, sink)
            if flow_value >= project.cost + current_cost:
                res.append(project)
                current_cost += project.cost

    return res
