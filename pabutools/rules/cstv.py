"""
An implementation of the algorithms in:
"Participatory Budgeting with Cumulative Votes", by Piotr Skowron, Arkadii Slinko, Stanisaw Szufa,
Nimrod Talmon (2020), https://arxiv.org/pdf/2009.02690
Programmer: Achiya Ben Natan
Date: 2024/05/16.
"""

from __future__ import annotations

import math
import warnings

from collections.abc import Callable, Iterable
from enum import Enum

from pabutools.election.instance import Instance, Project
from pabutools.election.profile.cumulativeprofile import AbstractCumulativeProfile
from pabutools.fractions import frac
from pabutools.rules.budgetallocation import BudgetAllocation
from pabutools.tiebreaking import TieBreakingRule, lexico_tie_breaking
from pabutools.utils import Numeric

import pabutools.fractions
import logging

logger = logging.getLogger(__name__)

###################################################################
#                                                                 #
#                     Main algorithm                              #
#                                                                 #
###################################################################


class CSTV_Combination(Enum):
    EWT = 1
    """
    Project selection via greedy-by-excess; eligible projects selected via greedy-by-excess;
    elimination with transfer used if no eligible projects; and reverse elimination as post-processing method.
    """

    EWTC = 2
    """
    Project selection via greedy-by-support-over-cost; eligible projects selected via greedy-by-support-over-cost;
    elimination with transfer used if no eligible projects; and reverse elimination as post-processing method.
    """

    MT = 3
    """
    Project selection via greedy-by-excess; eligible projects selected via greedy-by-excess;
    minimal transfer used if no eligible projects; and acceptance of under-supported projects as post-processing method.
    """

    MTC = 4
    """
    Project selection via greedy-by-support-over-cost; eligible projects selected via greedy-by-support-over-cost
    minimal transfer used if no eligible projects; and acceptance of under-supported projects as post-processing method.
    """


def cstv(
    instance: Instance,
    profile: AbstractCumulativeProfile,
    combination: CSTV_Combination = None,
    select_project_to_fund_func: Callable = None,
    eligible_projects_func: Callable = None,
    no_eligible_project_func: Callable = None,
    exhaustiveness_postprocess_func: Callable = None,
    initial_budget_allocation: Iterable[Project] | None = None,
    tie_breaking: TieBreakingRule | None = None,
    resoluteness: bool = True,
    verbose: bool = False,
) -> BudgetAllocation | list[BudgetAllocation]:
    """
    The CSTV (Cumulative Support Transfer Voting) budgeting algorithm determines project funding
    based on cumulative support from donor ballots.
    This function evaluates a list of projects and donor profiles, selecting projects for funding
    according to the CSTV methodology.
    It employs various procedures for project selection, eligibility determination, and handling of
    scenarios where no eligible projects exist or to ensure inclusive maximality.
    You can read more about the algorithm in sections 4 and 5 in the paper here:
    https://arxiv.org/pdf/2009.02690 in sections 4 and 5.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The list of projects.
        profile : :py:class:`~pabutools.election.profile.cumulativeprofile.AbstractCumulativeProfile`
            The list of donor ballots.
        combination : :py:class:`~pabutools.rules.cstv.CSTV_Combination`
            Shortcut to use pre-defined sets of parameters (all the different procedures).
        select_project_to_fund_func : Callable
            The procedure to select a project for funding.
        eligible_projects_func : Callable
            The function to determine eligible projects.
        no_eligible_project_func : Callable
            The procedure when there are no eligible projects.
        exhaustiveness_postprocess_func : Callable
            The post procedure to handle inclusive maximality.
        initial_budget_allocation : Iterable[:py:class:`~pabutools.election.instance.Project`]
            An initial budget allocation, typically empty.
        tie_breaking : :py:class:`~pabutools.tiebreaking.TieBreakingRule`, optional
            The tie-breaking rule to use, defaults to lexico_tie_breaking.
        resoluteness : bool, optional
            Set to `False` to obtain an irresolute outcome, where all tied budget allocations are
            returned. Defaults to True.
        verbose : bool, optional
            (De)Activate the display of additional information.
            Defaults to `False`.

    Returns
    -------
        BudgetAllocation
            The list of selected projects.
    """

    if tie_breaking is None:
        tie_breaking = lexico_tie_breaking

    if combination is not None:
        if combination == CSTV_Combination.EWT:
            select_project_to_fund_func = select_project_ge
            eligible_projects_func = is_eligible_ge
            no_eligible_project_func = elimination_with_transfers
            exhaustiveness_postprocess_func = reverse_eliminations
        elif combination == CSTV_Combination.EWTC:
            select_project_to_fund_func = select_project_gsc
            eligible_projects_func = is_eligible_gsc
            no_eligible_project_func = elimination_with_transfers
            exhaustiveness_postprocess_func = reverse_eliminations
        elif CSTV_Combination.MT:
            select_project_to_fund_func = select_project_ge
            eligible_projects_func = is_eligible_ge
            no_eligible_project_func = minimal_transfer
            exhaustiveness_postprocess_func = acceptance_of_under_supported_projects
        elif CSTV_Combination.MTC:
            select_project_to_fund_func = select_project_gsc
            eligible_projects_func = is_eligible_gsc
            no_eligible_project_func = minimal_transfer
            exhaustiveness_postprocess_func = acceptance_of_under_supported_projects
        else:
            raise ValueError(
                f"Invalid combination {combination}. Please select an element of the "
                f"CSTV_Combination enumeration."
            )
    else:
        if select_project_to_fund_func is None:
            raise ValueError(
                "If no combination is passed, the select_project_to_fund_func "
                "argument needs to be used"
            )
        if eligible_projects_func is None:
            raise ValueError(
                "If no combination is passed, the eligible_projects_func "
                "argument needs to be used"
            )
        if no_eligible_project_func is None:
            raise ValueError(
                "If no combination is passed, the no_eligible_project_func "
                "argument needs to be used"
            )
        if exhaustiveness_postprocess_func is None:
            raise ValueError(
                "If no combination is passed, the exhaustiveness_postprocess_func "
                "argument needs to be used"
            )

    if not resoluteness:
        raise NotImplementedError(
            'The "resoluteness = False" feature is not yet implemented'
        )

    # Check if all donors donate the same amount
    if not len(set([sum(donor.values()) for donor in profile])) == 1:
        raise ValueError(
            "Not all donors donate the same amount. Change the donations and try again."
        )

    if initial_budget_allocation is None:
        initial_budget_allocation = BudgetAllocation()
    else:
        initial_budget_allocation = BudgetAllocation(initial_budget_allocation)

    # Initialize the set of selected projects and eliminated projects
    selected_projects = initial_budget_allocation
    eliminated_projects = set()

    # The donations to avoid to mutate the profile passed as argument
    donations = [
        {p: ballot[p] * profile.multiplicity(ballot) for p in instance}
        for ballot in profile
    ]

    current_projects = set(instance)
    # Loop until a halting condition is met
    while True:
        # Calculate the total budget
        budget = sum(sum(donor.values()) for donor in donations)
        if verbose:
            logger.info(f"Budget is: {budget}")

        # Halting condition: if there are no more projects to consider
        if not current_projects:
            # Perform the inclusive maximality postprocedure
            exhaustiveness_postprocess_func(
                selected_projects,
                donations,
                eliminated_projects,
                select_project_to_fund_func,
                budget,
                tie_breaking,
            )
            if verbose:
                logger.info(f"Final selected projects: {selected_projects}")
            return selected_projects

        # Log donations for each project
        if verbose:
            for project in current_projects:
                total_donation = sum(donor[project] for donor in donations)
                logger.info(
                    f"Donors and total donations for {project}: {total_donation}. Price: {project.cost}"
                )

        # Determine eligible projects for funding
        eligible_projects = eligible_projects_func(current_projects, donations)
        if verbose:
            logger.info(
                f"Eligible projects: {eligible_projects}",
            )

        # If no eligible projects, execute the no-eligible-project procedure
        while not eligible_projects:
            flag = no_eligible_project_func(
                current_projects,
                donations,
                eliminated_projects,
                select_project_to_fund_func,
                tie_breaking
            )
            if not flag:
                # Perform the inclusive maximality postprocedure
                exhaustiveness_postprocess_func(
                    selected_projects,
                    donations,
                    eliminated_projects,
                    select_project_to_fund_func,
                    budget,
                    tie_breaking,
                )
                if verbose:
                    logger.info(f"Final selected projects: {selected_projects}")
                return selected_projects
            eligible_projects = eligible_projects_func(current_projects, donations)

        # Choose one project to fund according to the project-to-fund selection procedure
        tied_projects = select_project_to_fund_func(
            eligible_projects, donations
        )
        if len(tied_projects) > 1:
            p = tie_breaking.untie(current_projects, profile, tied_projects)
        else:
            p = tied_projects[0]
        excess_support = sum(donor.get(p.name, 0) for donor in donations) - p.cost
        if verbose:
            logger.info(f"Excess support for {p}: {excess_support}")

        # If the project has enough or excess support
        if excess_support >= 0:
            if excess_support > 0.01:
                # Perform the excess redistribution procedure
                gama = frac(p.cost, excess_support + p.cost)
                excess_redistribution_procedure(donations, p, gama)
            else:
                # Reset donations for the eliminated project
                if verbose:
                    logger.info(f"Resetting donations for eliminated project: {p}")
                for donor in donations:
                    donor[p] = 0

            # Add the project to the selected set and remove it from further consideration
            selected_projects.append(p)
            current_projects.remove(p)
            if verbose:
                logger.info(f"Updated selected projects: {selected_projects}")
            budget -= p.cost
            continue


###################################################################
#                                                                 #
#                     Help functions                              #
#                                                                 #
###################################################################


def excess_redistribution_procedure(
    donors: list[dict[Project, Numeric]],
    selected_project: Project,
    gama: Numeric,
) -> None:
    """
    Distributes the excess support of a selected project to the remaining projects.

    Parameters
    ----------
        donors : list[dict[Project, Numeric]]
            The list of donors.
        selected_project : Project
            The project with the maximum excess support.
        gama : Numeric
            The proportion to distribute.

    Returns
    -------
        None
    """
    for donor in donors:
        donor_copy = donor.copy()
        to_distribute = donor_copy[selected_project] * (1 - gama)
        donor[selected_project] = to_distribute
        donor_copy[selected_project] = 0
        total = sum(donor_copy.values())
        for key, donation in donor_copy.items():
            if donation != selected_project:
                if total != 0:
                    part = frac(donation, total)
                    donor[key] = donation + to_distribute * part
                donor[selected_project] = 0


def is_eligible_ge(
    projects: Iterable[Project], donors: list[dict[Project, Numeric]]
) -> list[Project]:
    """
    Determines the eligible projects based on the General Election (GE) rule.

    Parameters
    ----------
        projects : Iterable[Project]
            The list of projects.
        donors : list[dict[Project, Numeric]]
            The list of donor ballots.

    Returns
    -------
        list[Project]
            The list of eligible projects.
    """
    return [
        project
        for project in projects
        if (sum(donor.get(project, 0) for donor in donors) - project.cost) >= 0
    ]


def is_eligible_gsc(
    projects: Iterable[Project], donors: list[dict[Project, Numeric]]
) -> list[Project]:
    """
    Determines the eligible projects based on the Greatest Support to Cost (GSC) rule.

    Parameters
    ----------
        projects : Iterable[Project]
            The list of projects.
        donors : list[dict[Project, Numeric]]
            The list of donor ballots.

    Returns
    -------
        list[Project]
            The list of eligible projects.
    """
    return [
        project
        for project in projects
        if frac(sum(donor.get(project, 0) for donor in donors), project.cost) >= 1
    ]


def select_project_ge(
    projects: Iterable[Project],
    donors: list[dict[Project, Numeric]],
) -> list[Project]:
    """
    Selects the project with the maximum excess support using the General Election (GE) rule.

    Parameters
    ----------
        projects : Iterable[Project]
            The list of projects.
        donors : list[dict[Project, Numeric]]
            The list of donor ballots.

    Returns
    -------
        list[Project]
            The tied selected projects.
    """
    excess_support = {
        project: sum(donor.get(project, 0) for donor in donors) - project.cost
        for project in projects
    }
    max_excess_value = max(excess_support.values())
    max_excess_projects = [
        project
        for project, excess in excess_support.items()
        if excess == max_excess_value
    ]
    return max_excess_projects


def select_project_gsc(
    projects: Iterable[Project],
    donors: list[dict[Project, Numeric]],
) -> list[Project]:
    """
    Selects the project with the maximum excess support using the General Election (GSC) rule.

    Parameters
    ----------
        projects : Instance
            The list of projects.
        donors : list[dict[Project, Numeric]]
            The list of donor ballots.

    Returns
    -------
        list[Project]
            The tied selected projects.
    """
    excess_support = {
        project: frac(sum(donor.get(project, 0) for donor in donors), project.cost)
        for project in projects
    }
    max_excess_value = max(excess_support.values())
    max_excess_projects = [
        project
        for project, excess in excess_support.items()
        if excess == max_excess_value
    ]
    return max_excess_projects


def elimination_with_transfers(
    projects: list[Project],
    donors: list[dict[Project, Numeric]],
    eliminated_projects: set[Project],
    project_to_fund_selection_procedure: Callable,
    tie_breaking: TieBreakingRule,
) -> bool:
    """
    Eliminates the project with the least excess support and redistributes its support to the
    remaining projects.

    Parameters
    ----------
        projects : list[Project]
            The list of projects.
        donors : list[dict[Project, Numeric]]
            The list of donor ballots.
        eliminated_projects : set[Project]
            The set of eliminated projects
        project_to_fund_selection_procedure : callable
            The procedure to select a project for funding, not used in this function.
        tie_breaking : TieBreakingRule, optional
            The tie-breaking rule to use, defaults to lexico_tie_breaking.

    Returns
    -------
        bool
            True if the elimination with transfers was successful, False otherwise.
    """

    def distribute_project_support(
        all_donors: list[dict[Project, Numeric]],
        eliminated_project: Project,
    ) -> None:
        """
        Distributes the support of an eliminated project to the remaining projects.
        """
        for donor in all_donors:
            to_distribute = donor[eliminated_project]
            total = sum(donor.values()) - to_distribute
            if total == 0:
                continue
            for key, donation in donor.items():
                if key != eliminated_project:
                    part = frac(donation, total)
                    donor[key] = donation + to_distribute * part
            donor[eliminated_project] = 0

    if len(projects) < 2:
        if len(projects) == 1:
            eliminated_projects.add(projects.pop())
        return False
    min_project = min(
        projects, key=lambda p: sum(donor.get(p.name, 0) for donor in donors) - p.cost
    )
    distribute_project_support(donors, min_project)
    projects.remove(min_project)
    eliminated_projects.add(min_project)
    return True


def minimal_transfer(
    projects: Iterable[Project],
    donors: list[dict[Project, Numeric]],
    eliminated_projects: set[Project],
    project_to_fund_selection_procedure: Callable,
    tie_breaking: TieBreakingRule = lexico_tie_breaking,
) -> bool:
    """
    Performs minimal transfer of donations to reach the required support for a selected project.

    Parameters
    ----------
        projects : Iterable[Project]
            The list of projects.
        donors : list[dict[Project, Numeric]]
            The list of donor ballots.
        eliminated_projects : set[Project]
            The list of eliminated projects.
        project_to_fund_selection_procedure : callable
            The procedure to select a project for funding.
        tie_breaking : TieBreakingRule, optional
            The tie-breaking rule to use, defaults to lexico_tie_breaking.

    Returns
    -------
        bool
            True if the minimal transfer was successful, False if the project was added to
            eliminated_projects.

    """
    if pabutools.fractions.FRACTION != pabutools.fractions.FLOAT_FRAC:
        warnings.warn("You are using minimal transfers with exact fractions, this may never end...")
    projects_with_chance = []
    for project in projects:
        donors_of_selected_project = [
            donor.values()
            for _, donor in enumerate(donors)
            if donor.get(project, 0) > 0
        ]
        sum_of_don = 0
        for d in donors_of_selected_project:
            sum_of_don += sum(d)
        if sum_of_don >= project.cost:
            projects_with_chance.append(project)
    if not projects_with_chance:
        return False
    chosen_project = project_to_fund_selection_procedure(projects_with_chance, donors)[
        0
    ]  # TODO: there should be a tie-breaking here
    donors_of_selected_project = [
        i for i, donor in enumerate(donors) if donor.get(chosen_project.name, 0) > 0
    ]

    project_cost = chosen_project.cost

    # Calculate initial support ratio
    total_support = sum(donor.get(chosen_project, 0) for donor in donors)
    r = frac(total_support, project_cost)

    # Loop until the required support is achieved
    num_loop_run = 0
    while r < 1:
        num_loop_run += 1
        # Check if all donors have their entire donation on the chosen project
        all_on_chosen_project = all(
            sum(donors[i].values()) == donors[i].get(chosen_project, 0)
            for i in donors_of_selected_project
        )
        if all_on_chosen_project:
            for project in projects:
                eliminated_projects.add(project)
            return False

        for i in donors_of_selected_project:
            donor = donors[i]
            donation = donor.get(chosen_project, 0)
            total = sum(donor.values()) - donation
            if total > 0:
                to_distribute = min(total, frac(donation, r) - donation)
                for proj_name, proj_donation in donor.items():
                    if proj_name != chosen_project and proj_donation > 0:
                        change = frac(to_distribute * proj_donation, total)
                        if 1 - change < 1e-14:
                            change = 1
                        donor[proj_name] -= change
                        donor[chosen_project] += frac(math.ceil(change * 100000000000000), 100000000000000)

        # Recalculate the support ratio
        total_support = sum(donor.get(chosen_project, 0) for donor in donors)
        r = frac(total_support, project_cost)

        if num_loop_run > 10000:
            raise RuntimeError("The while loop of the minimal_transfer function ran for too long. This can be due to"
                               " issues with floating point arithmetic.")
    return True


def reverse_eliminations(
    selected_projects: BudgetAllocation,
    donors: list[dict[Project, Numeric]],
    eliminated_projects: set[Project],
    project_to_fund_selection_procedure: Callable,
    budget: Numeric,
    tie_breaking: TieBreakingRule = lexico_tie_breaking,
) -> None:
    """
    Reverses elimination of projects if the budget allows.

    Parameters
    ----------
        selected_projects : BudgetAllocation
            The list of selected projects.
        donors : list[dict[Project, Numeric]]
            The list of donor ballots, not used in this function.
        eliminated_projects : Instance
            The list of eliminated projects.
        project_to_fund_selection_procedure : callable
            The procedure to select a project for funding, not used in this function.
        budget : Numeric
            The remaining budget.
        tie_breaking : TieBreakingRule, optional
            The tie-breaking rule to use, defaults to lexico_tie_breaking.

    Returns
    -------
        None
    """
    for project in eliminated_projects:
        if project.cost <= budget:
            selected_projects.append(project)
            budget -= project.cost


def acceptance_of_under_supported_projects(
    selected_projects: BudgetAllocation,
    donors: list[dict[Project, Numeric]],
    eliminated_projects: Instance,
    project_to_fund_selection_procedure: Callable,
    budget: Numeric,
    tie_breaking: TieBreakingRule = lexico_tie_breaking,
) -> None:
    """
    Accepts under-supported projects if the budget allows.

    Parameters
    ----------
        selected_projects : BudgetAllocation
            The list of selected projects.
        donors : list[dict[Project, Numeric]]
            The list of donor ballots.
        eliminated_projects : Instance
            The list of eliminated projects.
        project_to_fund_selection_procedure : callable
            The procedure to select a project for funding.
        budget : Numeric
            The remaining budget.
        tie_breaking : TieBreakingRule, optional
            The tie-breaking rule to use, defaults to lexico_tie_breaking.

    Returns
    -------
        None
    """
    while len(eliminated_projects) != 0:
        selected_project = project_to_fund_selection_procedure(
            eliminated_projects, donors, tie_breaking, True
        )[
            0
        ]  # TODO: tie-breaking here
        if selected_project.cost <= budget:
            selected_projects.append(selected_project)
            eliminated_projects.remove(selected_project)
            budget -= selected_project.cost
        else:
            eliminated_projects.remove(selected_project)
