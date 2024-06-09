"""
An implementation of the algorithms in:
"Participatory Budgeting with Cumulative Votes", by Piotr Skowron, Arkadii Slinko, Stanisaw Szufa, Nimrod Talmon (2020), https://arxiv.org/pdf/2009.02690
Programmer: Achia Ben Natan
Date: 2024/05/16.
"""

from decimal import ROUND_UP, Decimal
import logging
from pabutools.election import Project, CumulativeBallot ,Instance
from typing import List
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


###################################################################
#                                                                 #
#                     Main algorithm                              #
#                                                                 #
###################################################################


def cstv_budgeting(donors: List[CumulativeBallot], projects: Instance, project_to_fund_selection_procedure: callable, eligible_fn: callable,
                    no_eligible_project_procedure: callable, inclusive_maximality_postprocedure: callable) -> Instance:
    """
    The CSTV (Cumulative Support Transfer Voting) budgeting algorithm to select projects based on donor ballots.

    Parameters
    ----------
    donors : List[CumulativeBallot]
        The list of donor ballots.
    projects : Instance
        The list of projects.
    project_to_fund_selection_procedure : callable
        The procedure to select a project for funding.
    eligible_fn : callable
        The function to determine eligible projects.
    no_eligible_project_procedure : callable
        The procedure when there are no eligible projects.
    inclusive_maximality_postprocedure : callable
        The post procedure to handle inclusive maximality.

    Returns
    -------
    Instance
        The list of selected projects.

    Examples
    --------
    >>> project_A = Project("Project A", 35)
    >>> project_B = Project("Project B", 30)
    >>> project_C = Project("Project C", 20)
    >>> donor1 = CumulativeBallot({"Project A": 5, "Project B": 10, "Project C": 5})
    >>> donor2 = CumulativeBallot({"Project A": 10, "Project B": 10, "Project C": 0})
    >>> donor3 = CumulativeBallot({"Project A": 0, "Project B": 15, "Project C": 5})
    >>> donor4 = CumulativeBallot({"Project A": 0, "Project B": 0, "Project C": 20})
    >>> donor5 = CumulativeBallot({"Project A": 15, "Project B": 5, "Project C": 0})
    >>> projects = [project_A, project_B, project_C]
    >>> donors = [donor1, donor2, donor3, donor4, donor5]
    >>> project_to_fund_selection_procedure = select_project_GE
    >>> eligible_fn = is_eligible_GE
    >>> no_eligible_project_procedure = elimination_with_transfers
    >>> inclusive_maximality_postprocedure = reverse_eliminations
    >>> len(cstv_budgeting(donors, projects, project_to_fund_selection_procedure, eligible_fn, no_eligible_project_procedure, inclusive_maximality_postprocedure))
    3
    """
    eliminated_projects = Instance([])
    if not len(set([sum(donor.values()) for donor in donors])) == 1:
        logger.warning("Not all donors donate the same amount. Change the donations and try again.")
        return
    S = Instance([])
    while True:
        budget = sum(sum(donor.values()) for donor in donors)
        logger.debug("Budget is: %s" , budget)
        if not projects:
            S = inclusive_maximality_postprocedure(donors, S, eliminated_projects, project_to_fund_selection_procedure, budget)
            logger.debug("Final selected projects: %s" , [project.name for project in S])
            return S
        eligible_projects = eligible_fn(donors, projects) # "If there are projects that are eligible for funding..."
        logger.debug("Eligible projects: %s" , [project.name for project in eligible_projects])
        
        for project in projects:
            donations = sum(donor[project.name] for donor in donors)
            logger.debug("Donors and total donations for %s: %s" , project.name, donations)
        
        while not eligible_projects:
            flag = no_eligible_project_procedure(donors, projects, eliminated_projects, project_to_fund_selection_procedure)
            if not flag:
                S = inclusive_maximality_postprocedure(donors, S, eliminated_projects, project_to_fund_selection_procedure, budget)
                logger.debug("Final selected projects: %s" , [project.name for project in S])
                return S
            eligible_projects = eligible_fn(donors, projects)
        p = project_to_fund_selection_procedure(donors, eligible_projects) # ...choose one such project p according to the “project-to-fund selection procedure”
        excess_support = sum(donor.get(p.name, 0) for donor in donors) - p.cost
        logger.debug("Excess support for %s: %s" , p.name, excess_support)

        if excess_support >= 0:
            if excess_support > 0.01:
                gama = p.cost / (excess_support + p.cost)
                projects = excess_redistribution_procedure(projects, p, donors, gama)
            else:
                logger.debug(f"Resetting donations for eliminated project: {p.name}")
                for donor in donors:
                    donor[p.name] = 0
            S.add(p)
            projects.remove(p)
            logger.debug("Updated selected projects: %s" , [project.name for project in S])
            budget -= p.cost
            continue
    



###################################################################
#                                                                 #
#                     Help functions                              #
#                                                                 #
###################################################################


def distribute_project_support(projects: Instance, eliminated_project: Project, donors: List[CumulativeBallot]) -> Instance:
    """
    Distributes the support of an eliminated project to the remaining projects.

    Parameters
    ----------
    projects : Instance
        The list of projects.
    eliminated_project : Project
        The project that has been eliminated.
    donors : List[CumulativeBallot]
        The list of donor ballots.

    Returns
    -------
    Instance
        The updated list of projects.

    Examples
    --------
    >>> project_A = Project("Project A", 35)
    
    >>> donor1 = CumulativeBallot({"Project A": 5, "Project B": 10, "Project C": 5})
    >>> donor2 = CumulativeBallot({"Project A": 10, "Project B": 0, "Project C": 5})
    >>> updated_projects = distribute_project_support(Instance[project_A, Project("Project B", 30), Project("Project C", 30)], project_A, [donor1, donor2])
    >>> updated_projects
    pabutools.election.instance.Instance[Project A, Project B, Project C]
    >>> for donor in [donor1, donor2]:
    ...     print({key: round(value, 2) for key, value in donor.items()})
    {'Project A': 0, 'Project B': 13.33, 'Project C': 6.67}
    {'Project A': 0, 'Project B': 0.0, 'Project C': 15.0}
    """
    
    eliminated_name = eliminated_project.name
    logger.debug(f"Distributing support of eliminated project: {eliminated_name}")
    for donor in donors:
        toDistribute = donor[eliminated_name]
        total = sum(donor.values()) - toDistribute
        if total == 0:
            continue
        
        for key, donation in donor.items():
            if key != eliminated_name:
                part = donation / total
                donor[key] = donation + toDistribute * part
                donor[eliminated_name] = 0 
    
    return projects

def excess_redistribution_procedure(projects: Instance, max_excess_project: Project, donors: List[CumulativeBallot], gama: float) -> Instance:
    """
    Distributes the excess support of a selected project to the remaining projects.

    Parameters
    ----------
    projects : Instance
        The list of projects.
    max_excess_project : Project
        The project with the maximum excess support.
    donors : List[CumulativeBallot]
        The list of donor ballots.
    gama : float
        The proportion to distribute.

    Returns
    -------
    Instance
        The updated list of projects.

    Examples
    --------
    >>> project_A = Project("Project A", 35)
    >>> project_B = Project("Project B", 30)
    >>> project_C = Project("Project C", 30)
    >>> donor1 = CumulativeBallot({"Project A": 5, "Project B": 10, "Project C": 5})
    >>> donor2 = CumulativeBallot({"Project A": 10, "Project B": 0, "Project C": 5})
    >>> updated_projects = excess_redistribution_procedure([project_A, project_B, project_C], project_A, [donor1, donor2], 0.5)
    >>> updated_projects
    [Project A, Project B, Project C]
    >>> for donor in [donor1, donor2]:
    ...     print({key: round(value, 2) for key, value in donor.items()})
    {'Project A': 0, 'Project B': 11.67, 'Project C': 5.83}
    {'Project A': 0, 'Project B': 0.0, 'Project C': 10.0}
    """
    max_project_name = max_excess_project.name
    logger.debug(f"Distributing excess support of selected project: {max_project_name}")
    for donor in donors:
        donor_copy = donor.copy()
        toDistribute = donor_copy[max_project_name] * (1 - gama)
        donor[max_project_name] = toDistribute
        donor_copy[max_project_name] = 0
        total = sum(donor_copy.values())
        for key, donation in donor_copy.items():
            if donation != max_project_name:
                if total != 0:
                    part = donation / total
                    donor[key] = donation + toDistribute * part
                    donor[max_project_name] = 0

    return projects



def is_eligible_GE(donors: List[CumulativeBallot], projects:Instance) -> Instance:
    """
    Determines the eligible projects based on the General Election (GE) rule.

    Parameters
    ----------
    donors : List[CumulativeBallot]
        The list of donor ballots.
    projects : Instance
        The list of projects.

    Returns
    -------
    Instance
        The list of eligible projects.

    Examples
    --------
    >>> project_A = Project("Project A", 35)
    >>> project_B = Project("Project B", 30)
    >>> donor1 = CumulativeBallot({"Project A": 5, "Project B": 30})
    >>> donor2 = CumulativeBallot({"Project A": 10, "Project B": 0})
    >>> is_eligible_GE([donor1, donor2], [project_A, project_B])
    [Project B]
    """
    return [project for project in projects if (sum(donor.get(project.name, 0) for donor in donors) - project.cost) >= 0]

def is_eligible_GSC(donors: List[CumulativeBallot], projects: Instance) -> Instance: 
    """
    Determines the eligible projects based on the Greatest Support to Cost (GSC) rule.

    Parameters
    ----------
    donors : List[CumulativeBallot]
        The list of donor ballots.
    projects : Instance
        The list of projects.

    Returns
    -------
    Instance
        The list of eligible projects.

    Examples
    --------
    >>> project_A = Project("Project A", 35)
    >>> project_B = Project("Project B", 30)
    >>> donor1 = CumulativeBallot({"Project A": 5, "Project B": 10})
    >>> donor2 = CumulativeBallot({"Project A": 30, "Project B": 0})
    >>> is_eligible_GSC([donor1, donor2], [project_A, project_B])
    [Project A]
    """
    return [project for project in projects if (sum(donor.get(project.name, 0) for donor in donors) / project.cost) >= 1]



def select_project_GE(donors: List[CumulativeBallot], projects: Instance) -> Project:
    """
    Selects the project with the maximum excess support using the General Election (GE) rule.

    Parameters
    ----------
    donors : List[CumulativeBallot]
        The list of donor ballots.
    projects : Instance
        The list of projects.

    Returns
    -------
    Project
        The selected project.

    Examples
    --------
    >>> project_A = Project("Project A", 36)
    >>> project_B = Project("Project B", 30)
    >>> donor1 = CumulativeBallot({"Project A": 5, "Project B": 10})
    >>> donor2 = CumulativeBallot({"Project A": 10, "Project B": 0})
    >>> select_project_GE([donor1, donor2], [project_A, project_B]).name
    'Project B'
    """
    
    excess_support = {project: sum(donor.get(project.name, 0) for donor in donors) - project.cost for project in projects}
    max_excess_project = max(excess_support, key=excess_support.get)
    logger.debug(f"Selected project by GE method: {max_excess_project.name}")
    return max_excess_project

def select_project_GSC(donors: List[CumulativeBallot], projects: Instance) -> Project:
    """
    Selects the project with the maximum ratio of support to cost using the Greatest Support to Cost (GSC) rule.

    Parameters
    ----------
    donors : List[CumulativeBallot]
        The list of donor ballots.
    projects : Instance
        The list of projects.

    Returns
    -------
    Project
        The selected project.

    Examples
    --------
    >>> project_A = Project("Project A", 34)
    >>> project_B = Project("Project B", 30)
    >>> donor1 = CumulativeBallot({"Project A": 5, "Project B": 10})
    >>> donor2 = CumulativeBallot({"Project A": 10, "Project B": 0})
    >>> select_project_GSC([donor1, donor2], [project_A, project_B]).name
    'Project A'
    """
    
    ratio_support = {project: sum(donor.get(project.name, 0) for donor in donors) / project.cost for project in projects}
    max_ratio_project = max(ratio_support, key=ratio_support.get)
    logger.debug(f"Selected project by GSC method: {max_ratio_project.name}")
    return max_ratio_project

def elimination_with_transfers(donors: List[CumulativeBallot], projects: Instance, eliminated_projects: Instance, _:callable) -> Instance:
    """
    Eliminates the project with the least excess support and redistributes its support to the remaining projects.

    Parameters
    ----------
    donors : List[CumulativeBallot]
        The list of donor ballots.
    projects : Instance
        The list of projects.
    eliminated_projects : Instance
        The list of eliminated projects.
    _ : callable
        A placeholder for a callable function.

    Returns
    -------
    Instance
        The updated list of projects.

    Examples
    --------
    >>> project_A = Project("Project A", 30)
    >>> project_B = Project("Project B", 30)
    >>> project_C = Project("Project C", 20)
    >>> donor1 = CumulativeBallot({"Project A": 5, "Project B": 10, "Project C": 5})
    >>> donor2 = CumulativeBallot({"Project A": 10, "Project B": 0, "Project C": 5})
    >>> elimination_with_transfers([donor1, donor2], [project_A, project_B, project_C], Instance([]), None)
    True
    >>> print(donor1["Project A"])
    10.0
    >>> print(donor1["Project B"])
    0
    >>> print(donor2["Project A"])
    10.0
    >>> print(donor2["Project B"])
    0
    >>> print(donor1["Project C"])
    10.0
    >>> print(donor2["Project C"])
    5.0
    """
    
    if len(projects) < 2:
        logger.debug("Not enough projects to eliminate.")
        if len(projects) == 1:
            eliminated_projects.add(projects.pop())
        return False
    min_project = min(projects, key=lambda p: sum(donor.get(p.name, 0) for donor in donors) - p.cost)
    logger.debug(f"Eliminating project with least excess support: {min_project.name}")
    projects = distribute_project_support(projects, min_project, donors)
    projects.remove(min_project)
    eliminated_projects.add(min_project)
    return True



def minimal_transfer(donors: List[CumulativeBallot], projects: Instance, eliminated_projects: Instance, project_to_fund_selection_procedure:callable) -> Instance:
    """
    Performs minimal transfer of donations to reach the required support for a selected project.

    Parameters
    ----------
    donors : List[CumulativeBallot]
        The list of donor ballots.
    projects : Instance
        The list of projects.
    eliminated_projects : Instance
        The list of eliminated projects.
    project_to_fund_selection_procedure : callable
        The procedure to select a project for funding.

    Returns
    -------
    Instance
        The updated list of projects.

    Examples
    --------
    >>> project_A = Project("Project A", 35)
    >>> project_B = Project("Project B", 30)
    >>> donor1 = CumulativeBallot({"Project A": 5, "Project B": 10})
    >>> donor2 = CumulativeBallot({"Project A": 10, "Project B": 0})
    >>> minimal_transfer([donor1, donor2], [project_A, project_B], Instance([]), select_project_GE)
    False
    >>> print(donor1["Project A"])
    15.00000000000001
    >>> print(donor1["Project B"])
    0.0
    >>> print(donor2["Project A"])
    10
    >>> print(donor2["Project B"])
    0
    """
    chosen_project = project_to_fund_selection_procedure(donors, projects)
    logger.debug(f"Selected project for minimal transfer: {chosen_project.name}")
    r = sum(donor.get(chosen_project.name, 0) for donor in donors) / chosen_project.cost
    donors_of_selected_project = [donor for donor in donors if (donor.get(chosen_project.name, 0)) > 0]
    while r < 1:
        flag = True
        for donor in donors_of_selected_project:
            if float(Decimal(str(sum(donor.values()))).quantize(Decimal('1e-'+str(5)))) != float(Decimal(str(donor.get(chosen_project))).quantize(Decimal('1e-'+str(5)))):
                flag = False
                break
        if flag:
            eliminated_projects.add(chosen_project)
            return False
        for donor in donors_of_selected_project:
            total = sum(donor.values()) - donor.get(chosen_project.name)
            donation = donor.get(chosen_project.name)
            to_distribute = min(total, donation / r - donation)
            for project_name, donation in donor.items():
                if project_name != chosen_project.name and total > 0:
                    change = to_distribute * donation / total
                    donor[project_name] -= change
                    donor[chosen_project.name] += float(Decimal(str(change)).quantize(Decimal('1e-'+str(14)), rounding=ROUND_UP))
        r = sum(donor.get(chosen_project.name, 0) for donor in donors) / chosen_project.cost
    return True

def reverse_eliminations(__:List[CumulativeBallot], S: Instance, eliminated_projects: Instance, _:callable, budget: int) -> Instance:
    """
    Reverses eliminations of projects if the budget allows.

    Parameters
    ----------
    _ : List[CumulativeBallot]
        The list of donor ballots.
    selected_projects : Instance
        The list of selected projects.
    eliminated_projects : Instance
        The list of eliminated projects.
    _ : callable
        A placeholder for a callable function.
    budget : int
        The remaining budget.

    Returns
    -------
    Instance
        The updated list of selected projects.

    Examples
    --------
    >>> project_A = Project("Project A", 35)
    >>> project_B = Project("Project B", 30)
    >>> selected_projects = Instance([project_A])
    >>> eliminated_projects =  Instance([project_B])
    >>> len(reverse_eliminations([], selected_projects, eliminated_projects, None, 30))
    2
    """
    for project in eliminated_projects:
        if project.cost <= budget:
            S.add(project)
            budget -= project.cost
    return S

def acceptance_of_undersupported_projects(donors: List[CumulativeBallot], S: Instance, eliminated_projects:Instance, project_to_fund_selection_procedure: callable, budget: int) ->Instance:
    """
    Accepts undersupported projects if the budget allows.

    Parameters
    ----------
    donors : List[CumulativeBallot]
        The list of donor ballots.
    selected_projects : Instance
        The list of selected projects.
    eliminated_projects : Instance
        The list of eliminated projects.
    project_to_fund_selection_procedure : callable
        The procedure to select a project for funding.
    budget : int
        The remaining budget.

    Returns
    -------
    Instance
        The updated list of selected projects.

    Examples
    --------
    >>> project_A = Project("Project A", 35)
    >>> project_B = Project("Project B", 30)
    >>> project_C = Project("Project C", 20)
    >>> selected_projects = Instance(init=[project_A])
    >>> eliminated_projects = Instance(init=[project_B, project_C])
    >>> print(len(acceptance_of_undersupported_projects([], selected_projects, eliminated_projects, select_project_GE, 25)))
    2
    """
    while len(eliminated_projects) != 0:
        selected_project = project_to_fund_selection_procedure(donors, eliminated_projects)
        if selected_project.cost <= budget:
            S.add(selected_project)
            eliminated_projects.remove(selected_project)
            budget -= selected_project.cost
        else:
            eliminated_projects.remove(selected_project)
    return S



def cstv_budgeting_combination(donors: List[CumulativeBallot], projects: Instance, combination: str) -> Instance:
    """
    Runs the CSTV test based on the combination of functions provided.

    Parameters
    ----------
    combination : str
        The combination of CSTV functions to run.

    Returns
    -------
    Instance
        The selected projects.

    Examples
    --------
    >>> project_A = Project("Project A", 35)
    >>> project_B = Project("Project B", 30)
    >>> project_C = Project("Project C", 25)
    >>> instance = Instance([project_A, project_B, project_C])
    >>> donor1 = CumulativeBallot({"Project A": 5, "Project B": 10, "Project C": 5})
    >>> donor2 = CumulativeBallot({"Project A": 10, "Project B": 10, "Project C": 0})
    >>> donor3 = CumulativeBallot({"Project A": 0, "Project B": 15, "Project C": 5})
    >>> donor4 = CumulativeBallot({"Project A": 0, "Project B": 0, "Project C": 20})
    >>> donor5 = CumulativeBallot({"Project A": 15, "Project B": 5, "Project C": 0})
    >>> donors = [donor1, donor2, donor3, donor4, donor5]
    >>> combination = "ewt"
    >>> print(len(cstv_budgeting_combination(donors, instance, combination)))
    3
    """
    combination = combination.lower()
    if combination =="ewt":
        return cstv_budgeting(donors, projects, select_project_GE, is_eligible_GE, elimination_with_transfers, reverse_eliminations)
    elif combination =="ewtc":
        return cstv_budgeting(donors, projects, select_project_GSC, is_eligible_GSC, elimination_with_transfers, reverse_eliminations)
    elif combination =="mt":
        return cstv_budgeting(donors, projects, select_project_GE, is_eligible_GE, minimal_transfer, acceptance_of_undersupported_projects)
    elif combination =="mtc":
        return cstv_budgeting(donors, projects, select_project_GSC, is_eligible_GSC, minimal_transfer, acceptance_of_undersupported_projects)
    else:
        raise KeyError(f"Invalid combination algorithm: {combination}. Please insert an existing combination algorithm.")

def main():
    instance = Instance(init=[Project("Project A", 35), Project("Project B", 30), Project("Project C", 30), Project("Project D", 30)])
    donors = [CumulativeBallot({"Project A": 5, "Project B": 10, "Project C": 5, "Project D": 5}), CumulativeBallot({"Project A": 10, "Project B": 10, "Project C": 0, "Project D": 5}), CumulativeBallot({"Project A": 0, "Project B": 15, "Project C": 5, "Project D": 5}), CumulativeBallot({"Project A": 0, "Project B": 0, "Project C": 20, "Project D": 5}), CumulativeBallot({"Project A": 15, "Project B": 5, "Project C": 0, "Project D": 5})]
    selected_projects = cstv_budgeting_combination(donors, instance,"ewt")
    if selected_projects:
        logger.info(f"Selected projects: {[project.name for project in selected_projects]}")
    
if __name__ == "__main__":
    import doctest
    doctest.testmod()
    main()
    