from __future__ import annotations

from pabutools.utils import Numeric
from pabutools.election.instance import Instance, Project
from pabutools.election.profile import Profile
from pabutools.rules.budgetallocation import BudgetAllocation, AllocationDetails
from pabutools.rules.mes.mes_rule import method_of_equal_shares


class ProjectLoss(Project):
    """
    Class used to represent the projects and how much budget they lost due to other projects being picked.
    This extends the :py:class:`~pabutools.election.instance.Project` and thus represents the project itself.

    Parameters
    ----------
        project: :py:class:`~pabutools.election.instance.Project`
            Project for which analytics is calculated.
        supporters_budget: :py:class:`~pabutools.utils.Numeric`
            The collective budget of the project supporters when project was considered by a rule.
        budget_lost: dict[:py:class:`~pabutools.election.instance.Project`, :py:class:`~pabutools.utils.Numeric`]
            Describes the amount of budget project supporters spent on other projects prior to this
            projects' consideration.

    Attributes
    ----------
        supporters_budget: :py:class:`~pabutools.utils.Numeric`
            The collective budget of the project supporters when project was considered by rule.
        budget_lost: dict[:py:class:`~pabutools.election.instance.Project`, :py:class:`~pabutools.utils.Numeric`]
            Describes the amount of budget project supporters spent on other projects prior to this
            projects' consideration.
    """

    def __init__(
        self,
        project: Project,
        supporters_budget: Numeric,
        budget_lost: dict[Project, Numeric],
    ):
        Project.__init__(
            self, project.name, project.cost, project.categories, project.targets
        )
        self.supporters_budget: Numeric = supporters_budget
        self.budget_lost: dict[Project, Numeric] = budget_lost

    def total_budget_lost(self) -> Numeric:
        """
        Returns the total budget spent by project supporters on prior projects.

        Returns
        -------
            :py:class:`~pabutools.utils.Numeric`
                The total budget spent.
        """
        return sum(self.budget_lost.values())

    def __str__(self):
        return f"ProjectLoss[{self.name}, {float(self.supporters_budget)}, {self.total_budget_lost()}]"

    def __repr__(self):
        return f"ProjectLoss[{self.name}, {float(self.supporters_budget)}, {self.total_budget_lost()}]"


def calculate_project_loss(
    allocation_details: AllocationDetails,
    verbose: bool = False,
) -> list[ProjectLoss]:
    """
    Returns a list of :py:class:`~pabutools.analysis.mesanalytics.ProjectLoss` objects for the projects.

    Parameters
    ----------
        allocation_details: :py:class:`~pabutools.rules.budgetallocation.AllocationDetails`
            The details of the budget allocation considered.
        verbose: bool, optional
            (De)Activate the display of additional information.
            Defaults to `False`.

    Returns
    -------
        list[:py:class:`~pabutools.analysis.mesanalytics.ProjectLoss`]
            List of :py:class:`~pabutools.analysis.mesanalytics.ProjectLoss` objects.

    """
    if not hasattr(allocation_details, "iterations"):
        raise ValueError(
            "Provided budget allocation details do not support calculating project loss. The allocation_details "
            "should have an 'iterations', and 'voter_multiplicity' attributes."
        )
    if len(allocation_details.iterations) == 0:
        if verbose:
            print(f"Rule did not have any iterations, returning empty list")
        return []

    project_losses = []
    voter_count = len(allocation_details.iterations[0].voters_budget)
    voter_multiplicity = allocation_details.voter_multiplicity
    iterations_count = len(allocation_details.iterations)
    voter_spendings: dict[int, list[tuple[Project, Numeric]]] = {}
    for idx in range(voter_count):
        voter_spendings[idx] = []

    for idx, iteration in enumerate(allocation_details.iterations):
        project_losses.append(
            _create_project_loss(
                iteration.selected_project,
                iteration.voters_budget,
                voter_spendings,
                voter_multiplicity,
                verbose,
            )
        )

        for supporter_idx in iteration.selected_project.supporter_indices:
            voter_spendings[supporter_idx].append(
                (
                    iteration.selected_project,
                    iteration.voters_budget[supporter_idx]
                    - iteration.voters_budget_after_selection[supporter_idx],
                )
            )

        for project_detail in iteration:
            if project_detail.discarded or (
                idx == iterations_count - 1
                and project_detail.project != iteration.selected_project
            ):
                project_losses.append(
                    _create_project_loss(
                        project_detail.project,
                        iteration.voters_budget_after_selection,
                        voter_spendings,
                        voter_multiplicity,
                        verbose,
                    )
                )

    return project_losses


def calculate_effective_supports(
    instance: Instance,
    profile: Profile,
    allocation: BudgetAllocation,
    mes_params: dict | None = None,
    final_budget: Numeric | None = None,
) -> dict[Project, int]:
    """
    Returns a dictionary of :py:class:`~pabutools.election.instance.Project` and their effective support
    in a given instance, profile and mes election. Effective support for a project is an analytical metric
    which allows to measure the ratio of initial budget received to minimal budget required to win.
    Effective support is represented in percentages.

    Parameters
    ----------
        instance: :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile: :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        allocation: :py:class:`~pabutools.rules.budgetallocation.BudgetAllocation`
            Resulting allocation of the above instance & profile.
        mes_params: dict, optional
            Dictionary of additional parameters that are passed as keyword arguments to the MES rule.
            Defaults to None.
        final_budget: Numeric, optional
            Numeric value of the final budget which will replace the instance budget. Allows for simulating
            exhaustive MES.

    Returns
    -------
        dict[:py:class:`~pabutools.election.instance.Project`, int]
            Dictionary of pairs (:py:class:`~pabutools.election.instance.Project`, effective support).
    """
    if mes_params is None:
        mes_params = {}
    effective_supports: dict[Project, int] = {}
    if final_budget:
        instance.budget_limit = final_budget
    for project in instance:
        effective_supports[project] = calculate_effective_support(
            instance, profile, project, project in allocation, mes_params
        )

    return effective_supports


def calculate_effective_support(
    instance: Instance,
    profile: Profile,
    project: Project,
    was_picked: bool,
    mes_params: dict | None = None,
) -> int:
    """
    Calculates the effective support of a given project in a given instance, profile and mes election.
    Effective support for a project is an analytical metric which allows to measure the ratio of
    initial budget received to minimal budget required to win. Effective support is represented in percentages.

    Parameters
    ----------
        instance: :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        project: :py:class:`~pabutools.election.instance.Project`
            Project for which effective support is calculated. Must be a part of the instance.
        was_picked: bool
            Whether the considerd project was picked as a winner in the allocation.
        mes_params: dict, optional
            Dictionary of additional parameters that are passed as keyword arguments to the MES rule.
            Defaults to `{}`.

    Returns
    -------
        int
            The effective support value in percentages for project.
    """
    if project not in instance:
        raise RuntimeError("Provided instance does not match the allocation details")
    if mes_params is None:
        mes_params = {}
    mes_params["analytics"] = True
    mes_params["skipped_project"] = project
    mes_params["resoluteness"] = True
    details = method_of_equal_shares(instance, profile, **mes_params).details
    effective_support = details.skipped_project_eff_support
    if was_picked:
        effective_support = max(effective_support, 100)
    return effective_support


def _create_project_loss(
    project: Project,
    current_voters_budget: list[Numeric],
    voter_spendings: dict[int, list[tuple[Project, Numeric]]],
    voter_multiplicity: list[int],
    verbose: bool = False,
) -> ProjectLoss:
    if verbose:
        print(f"Considering: {project.name}")
    budget_lost = {}
    for idx in project.supporter_indices:
        spending = voter_spendings[idx]
        for prev_project, spent in spending:
            if prev_project not in budget_lost.keys():
                budget_lost[prev_project] = 0
            budget_lost[prev_project] = (
                budget_lost[prev_project] + spent * voter_multiplicity[idx]
            )
    return ProjectLoss(
        project,
        sum(
            current_voters_budget[i] * voter_multiplicity[i]
            for i in project.supporter_indices
        ),
        budget_lost,
    )
