from __future__ import annotations


from pabutools.election.instance import Project
from pabutools.rules.budgetallocation import AllocationDetails
from pabutools.utils import Numeric


class MESAllocationDetails(AllocationDetails):
    """Class representing the details of MES rule.
    This class represents the MES details using an iteration approach: at each iteration of the MES rule some
    crucial information is saved which allow for reconstruction of the whole run. An iteration corresponds to one
    call to `mes_inner_algo`, and each iteration corresponds to one project being picked.

    Attributes
    ----------
        iterations: Iterable[:py:class:`~pabutools.rules.mes.MESIteration`]
            A list of all iterations of a MES rule run. It is progressively populated during a MES rule run.
    """

    def __init__(self, voter_multiplicity: list[int]):
        super().__init__()
        self.voter_multiplicity: list[int] = voter_multiplicity
        self.iterations: list[MESIteration] = []

    def get_all_project_details(self) -> list["MESProjectDetails"]:
        """
        Returns a list of all projects that were considered by MES.
        """
        res = []
        for iteration in self.iterations:
            for proj_detail in iteration:
                if proj_detail not in res:
                    res.append(proj_detail)
        return res

    def get_all_selected_projects(self) -> list[Project]:
        return [iteration.selected_project for iteration in self.iterations]

    def get_final_budget(self) -> Numeric:
        """
        Returns the budget limit used in the final feasible MES run.
        """
        budget_per_voter = self.iterations[0].voters_budget
        return sum(
            [
                budget_per_voter[i] * self.voter_multiplicity[i]
                for i in range(len(self.voter_multiplicity))
            ]
        )

    def __str__(self):
        return f"MESAllocationDetails[{self.iterations}]"

    def __repr__(self):
        return f"MESAllocationDetails[{self.iterations}]"


class MESProjectDetails:
    """Class representing a single iteration of a MES rule run, solely used in
    :py:class:`~pabutools.rules.mes.MESAllocationDetails`. Each iteration consist of information
    necessary for reconstructing a MES rule run. This includes the project the iteration is about, its supporters,
    whether it was picked or discarded, and the voters budgets after potential 'purchase' of the project.

    Parameters
    ----------
        project: :py:class:`~pabutools.election.instance.Project`
            The project that was considered by a MES iteration.
        iteration: :py:class:`~pabutools.rules.mes.MESIteration`
            The iteration this project belongs to.
        discarded: bool, optional
            Indicates whether the aforementioned project was discarded by MES. Defaults to `None`.
        effective_vote_count_reduced: bool, optional
            Indicates whether the effective vote count was reduced by the project. Defaults to `None`.

    Attributes
    ----------
        project: :py:class:`~pabutools.election.instance.Project`
            The project that was considered by a MES iteration.
        iteration: :py:class:`~pabutools.rules.mes.MESIteration`
            The iteration this project belongs to.
        discarded: bool, optional
            Indicates whether the aforementioned project was discarded by MES. Defaults to `None`. This
            is set within `MESIteration.update_project_details_as_discarded`
        effective_vote_count_reduced: bool, optional
            Indicates whether the effective vote count was reduced by the project. Defaults to `None`. This
            is set within `MESIteration.update_project_details_as_effective_vote_count_reduced`
    """

    def __init__(
        self,
        project: Project,
        iteration: "MESIteration",
        discarded: bool = None,
        effective_vote_count_reduced: bool = None,
    ):
        self.project: Project = project
        self.iteration: "MESIteration" = iteration
        self.discarded: bool = discarded
        self.effective_vote_count_reduced: bool = effective_vote_count_reduced

    def was_picked(self):
        """Returns whether the project was picked by MES during *this* iteration (Note: it could have been
        selected in a later iteration; use `MESAllocationDetails.get_all_selected_projects` instead to see
        if it was selected in any iteration). If no project has been picked yet, returns `None`.
        """
        if self.iteration.selected_project != None:
            return self.project == self.iteration.selected_project
        return None  # No project has been selected yet

    def __eq__(self, other):
        return self.project == other.project

    def __str__(self):
        return f"MESProjectDetails[Project: {self.project.name}]"

    def __repr__(self):
        return f"MESProjectDetails[Project: {self.project.name}]"


class MESIteration(list[MESProjectDetails]):
    """Class representing a single iteration of a MES rule run, solely used in
    :py:class:`~pabutools.rules.mes.MESAllocationDetails`. Each iteration consist of information
    necessary for reconstructing a MES rule run. This includes the list of projects that were considered
    in this iteration, the budget of all the voters and the project that was selected at the end of the iteration.

    Parameters
    ----------
        voters_budget: list[int], optional
            The budget of all voters at the start of the iteration. Defaults to `None`.
        voters_budget_after_selection: list[int], optional
            The budget of all voters after the selected project was covered. Defaults to `None`.
        selected_project: :py:class:`~pabutools.election.instance.Project`, optional
            The project that was selected at the end of the iteration. Defaults to `None`.

    Attributes
    ----------
        voters_budget: list[int], optional
            The budget of all voters at the start of the iteration. Defaults to `None`.
        voters_budget_after_selection: list[int], optional
            The budget of all voters after the selected project was covered. Defaults to `None`.
        selected_project: :py:class:`~pabutools.election.instance.Project`, optional
            The project that was selected at the end of the iteration. Defaults to `None`.
    """

    def __init__(
        self,
        voters_budget: list[Numeric] | None = None,
        voters_budget_after_selection: list[Numeric] | None = None,
        selected_project: Project | None = None,
    ):
        self.voters_budget: list[Numeric] | None = voters_budget
        self.voters_budget_after_selection: list[Numeric] | None = (
            voters_budget_after_selection
        )
        self.selected_project: Project | None = selected_project
        super().__init__()

    def update_project_details_as_discarded(self, project: Project):
        """Updates the project details of the given project as discarded during this iteration."""
        project_details = self[self.index(project)]
        project_details.discarded = True

    def update_project_details_as_effective_vote_count_reduced(self, project: Project):
        """Updates the project details of the given project as having its effective vote count reduced during this iteration."""
        project_details = self[self.index(project)]
        project_details.effective_vote_count_reduced = True

    def get_all_projects(self):
        return [project_details.project for project_details in self]

    def __str__(self):
        return f"MESIteration[{[project for project in self]}]"

    def __repr__(self):
        return f"MESIteration[{[project for project in self]}]"