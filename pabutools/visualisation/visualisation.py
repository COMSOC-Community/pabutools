from __future__ import annotations
import os
import json
import logging

logger = logging.getLogger(__name__)


from pabutools.election import AbstractProfile

try:
    import jinja2
except ImportError:
    raise ImportError("You need to install jinja2 to use this visualisation module")

from pabutools.analysis.profileproperties import (
    votes_count_by_project,
    voter_flow_matrix,
)
from pabutools.election.instance import total_cost, Instance
from pabutools.rules.greedywelfare.greedywelfare_details import (
    GreedyWelfareAllocationDetails,
)
from pabutools.rules.mes.mes_details import MESAllocationDetails

ENV = jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(os.path.abspath(__file__)))
)


class Visualiser:
    pass


class MESVisualiser(Visualiser):
    """
    Class used to visualise the results of a MES election. The visualisation result consists of two
    pages: a summary page called 'summary.html' and a round by round analysis page called
    'round_analysis.html'.

    Parameters
    ----------
    profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
        The profile.
    instance : :py:class:`~pabutools.election.instance.Instance`
        The election instance.
    outcome : :py:class:`~pabutools.rules.budgetallocation.AllocationDetails`
            The outcome of the election.
    verbose : bool, optional
        Whether to print the results to the console. The default is False.

    Returns
    -------
        None
    """

    template = ENV.get_template("./templates/mes_round_analysis_template.html")
    page_summary_template = ENV.get_template(
        "./templates/mes_page_summary_template.html"
    )

    def __init__(self, profile, instance, outcome, verbose=False):
        self.profile = profile
        self.instance = instance
        self.verbose = verbose
        self.outcome = outcome
        self.details = outcome.details
        self.mes_iterations = [
            iteration
            for iteration in outcome.details.iterations
            if iteration.selected_project is not None
        ]
        self.were_projects_selected = True
        if not self.mes_iterations:
            self.were_projects_selected = False
        self.rounds = []

    def _calculate_rounds_dictinary(self):
        """
        Calculate the round by round dictionary that will be used to render the template.

        Parameters
        ----------
        None

        Returns
        -------
        None
        """
        initial_budget_per_voter = float(self.instance.meta["budget"]) / float(
            self.instance.meta["num_votes"]
        )
        budgetSpent = 0
        last_iteration = self.mes_iterations[-1]
        for i in range(len(self.mes_iterations) - 1):
            current_iteration = self.mes_iterations[i]
            next_iteration = self.mes_iterations[i + 1]
            round = dict()
            round["_current_iteration"] = current_iteration
            round["id"] = current_iteration.selected_project.name
            round["name"] = current_iteration.selected_project.name
            data = {
                p.name: float(1 / p.affordability)
                for p in current_iteration.get_all_projects()
            }
            round["effective_vote_count"] = dict(
                sorted(data.items(), key=lambda item: item[1], reverse=True)
            )
            round["effective_vote_count_reduction"] = {
                p.name: float(round["effective_vote_count"][p] - 1 / p.affordability)
                for p in next_iteration.get_all_projects()
            }

            # Statistics for Page Summary page
            round["cost"] = current_iteration.selected_project.cost
            round["totalvotes"] = len(
                current_iteration.selected_project.supporter_indices
            )
            round["initial_voter_funding"] = initial_budget_per_voter * len(
                current_iteration.selected_project.supporter_indices
            )
            unsorted_funding_lost_per_round = {
                r: (
                    float(
                        sum(
                            self.mes_iterations[r].voters_budget[p]
                            for p in current_iteration.selected_project.supporter_indices
                        )
                    )
                    - float(
                        sum(
                            self.mes_iterations[r + 1].voters_budget[p]
                            for p in current_iteration.selected_project.supporter_indices
                        )
                    )
                )
                for r in range(0, i)
            }
            round["funding_lost_per_round"] = dict(
                sorted(
                    unsorted_funding_lost_per_round.items(),
                    key=lambda x: x[1],
                    reverse=True,
                )
            )
            round["final_voter_funding"] = float(
                sum(
                    current_iteration.voters_budget[p]
                    for p in current_iteration.selected_project.supporter_indices
                )
            )

            # Get dropped projects
            dropped_projects = []
            for p in current_iteration:
                if p.discarded:
                    unsorted_funding_lost_per_round = {
                        r: (
                            float(
                                sum(
                                    self.mes_iterations[r].voters_budget[p]
                                    for p in p.project.supporter_indices
                                )
                            )
                            - float(
                                sum(
                                    self.mes_iterations[r + 1].voters_budget[p]
                                    for p in p.project.supporter_indices
                                )
                            )
                        )
                        for r in range(0, i)
                    }

                    rejected = {
                        "id": p.project.name,
                        "cost": p.project.cost,
                        "effective_vote_count": float(1 / p.project.affordability),
                        "totalvotes": len(p.project.supporter_indices),
                        "initial_voter_funding": initial_budget_per_voter
                        * len(p.project.supporter_indices),
                        "funding_lost_per_round": dict(
                            sorted(
                                unsorted_funding_lost_per_round.items(),
                                key=lambda x: x[1],
                                reverse=True,
                            )
                        ),
                        "final_voter_funding": float(
                            sum(
                                current_iteration.voters_budget[p]
                                for p in p.project.supporter_indices
                            )
                        ),
                    }
                    dropped_projects.append(rejected)
            round["dropped_projects"] = dropped_projects
            budgetSpent += current_iteration.selected_project.cost
            round["remaining_budget"] = (
                float(self.instance.meta["budget"]) - budgetSpent
            )
            self.rounds.append(round)

        # Final round
        unsorted_funding_lost_per_round = {
            r: (
                float(
                    sum(
                        self.mes_iterations[r].voters_budget[p]
                        for p in last_iteration.selected_project.supporter_indices
                    )
                )
                - float(
                    sum(
                        self.mes_iterations[r + 1].voters_budget[p]
                        for p in last_iteration.selected_project.supporter_indices
                    )
                )
            )
            for r in range(0, len(self.mes_iterations) - 1)
        }

        dropped_projects = []
        for p in last_iteration:
            if p.discarded:
                unsorted_funding_lost_per_round = {
                    r: (
                        float(
                            sum(
                                self.mes_iterations[r].voters_budget[p]
                                for p in p.project.supporter_indices
                            )
                        )
                        - float(
                            sum(
                                self.mes_iterations[r + 1].voters_budget[p]
                                for p in p.project.supporter_indices
                            )
                        )
                    )
                    for r in range(0, len(self.mes_iterations) - 1)
                }

                rejected = {
                    "id": p.project.name,
                    "cost": p.project.cost,
                    "effective_vote_count": float(1 / p.project.affordability),
                    "totalvotes": len(p.project.supporter_indices),
                    "initial_voter_funding": initial_budget_per_voter
                    * len(p.project.supporter_indices),
                    "funding_lost_per_round": dict(
                        sorted(
                            unsorted_funding_lost_per_round.items(),
                            key=lambda x: x[1],
                            reverse=True,
                        )
                    ),
                    "final_voter_funding": float(
                        sum(
                            last_iteration.voters_budget[p]
                            for p in p.project.supporter_indices
                        )
                    ),
                }
                dropped_projects.append(rejected)

        budgetSpent += last_iteration.selected_project.cost
        data = {
            p.name: float(1 / p.affordability)
            for p in last_iteration.get_all_projects()
        }
        self.rounds.append(
            {
                "name": last_iteration.selected_project.name,
                "_current_iteration": last_iteration,
                "effective_vote_count": dict(
                    sorted(data.items(), key=lambda item: item[1], reverse=True)
                ),
                "effective_vote_count_reduction": {
                    p.name: 0 for p in last_iteration.get_all_projects()
                },
                "cost": last_iteration.selected_project.cost,
                "totalvotes": len(last_iteration.selected_project.supporter_indices),
                "initial_voter_funding": initial_budget_per_voter
                * len(last_iteration.selected_project.supporter_indices),
                "funding_lost_per_round": dict(
                    sorted(
                        unsorted_funding_lost_per_round.items(),
                        key=lambda x: x[1],
                        reverse=True,
                    )
                ),
                "final_voter_funding": float(
                    sum(
                        last_iteration.voters_budget[p]
                        for p in last_iteration.selected_project.supporter_indices
                    )
                ),
                "dropped_projects": dropped_projects,
                "remaining_budget": float(self.instance.meta["budget"]) - budgetSpent,
            }
        )

    def _calculate_pie_charts(self, projectVotes):
        """
        Calculate the data necessary for the pie charts in the round by round analysis page.

        Parameters
        ----------
        projectVotes : dict
            A dictionary containing the number of votes for each project.

        Returns
        -------
        None
        """
        winners = []
        for round in self.rounds:
            pie_chart_items = []
            round["id"] = round["name"]
            selected = round["name"]
            winners.append(selected)
            num_projects = 0
            for project in projectVotes:
                if num_projects > 9:
                    break
                if project.name not in winners:
                    round_voters = round["voter_flow"][project.name][selected]
                    non_round_voters = projectVotes[project.name] - round_voters
                    reduction = self._calculate_avg_voter_budget(
                        round["_current_iteration"].voters_budget,
                        self._get_voters_for_project(project),
                    ) - self._calculate_avg_voter_budget(
                        round["_current_iteration"].voters_budget_after_selection,
                        self._get_voters_for_project(project),
                    )
                    pie_chart_item = {
                        "project": project.name,
                        "roundVoters": round_voters,
                        "nonRoundVoters": non_round_voters,
                        "reduction": reduction,
                    }
                    pie_chart_items.append(pie_chart_item)
                    num_projects += 1

            pie_chart_items = sorted(
                pie_chart_items, key=lambda x: x["roundVoters"], reverse=True
            )
            round["pie_chart_items"] = [pie_chart_items]
            round["pie_chart_triplet"] = [
                pie_chart_items[i : i + 3] for i in range(0, len(pie_chart_items), 3)
            ]

    def _calculate_avg_voter_budget(self, voters_budget, supporters):
        """
        Calculate the average budget of the supporters for a project.

        Parameters
        ----------
        voters_budget : dict
            A dictionary containing the budget of each voter.
        supporters : list
            A list of the supporters of the project.

        Returns
        -------
        float
            The average budget of the supporters for the project.

        """
        if not supporters:
            return 0
        return sum(voters_budget[s] for s in supporters) / len(supporters)

    def _get_voters_for_project(self, project):
        """
        Get the supporters of a project.

        Parameters
        ----------
        project : :py:class:`~pabutools.election.instance.Project`
            The project.

        """
        for project_details in self.details.get_all_project_details():
            if project_details.project == project:
                return project_details.project.supporter_indices

    def _calculate(self):
        """
        Calculate the data necessary for the visualisation.

        Parameters
        ----------
        None

        Returns
        -------
        None

        """
        self._calculate_rounds_dictinary()
        projectVotes = votes_count_by_project(self.profile)
        for round in self.rounds:
            round["voter_flow"] = voter_flow_matrix(self.instance, self.profile)
        self._calculate_pie_charts(projectVotes)

    def render(self, output_folder_path, name=""):
        """
        Render the visualisation.

        Parameters
        ----------
        output_folder_path : str
            The path to the folder where the visualisation will be saved.
        name : str, optional
            The prefix of the output files. The default is "".

        Returns
        -------
        None
        """
        if not self.were_projects_selected:
            logger.info(
                "No projects were selected in this election - therefore no visualisation will be created."
            )
            return
        self._calculate()
        for round in self.rounds:
            del round["_current_iteration"]
        if self.verbose:
            logger.info(self.rounds)

        # Round by Round
        round_analysis_page_output = MESVisualiser.template.render(
            election_name=(
                self.instance.meta["description"]
                if "description" in self.instance.meta
                else "No description provided."
            ),
            currency=(
                self.instance.meta["currency"]
                if "currency" in self.instance.meta
                else "CUR"
            ),
            rounds=self.rounds,
            projects=self.instance.project_meta,
            number_of_elected_projects=len(self.outcome),
            number_of_unelected_projects=len(self.instance) - len(self.outcome),
            spent=total_cost(p for p in self.instance if p.name in self.outcome),
            budget=self.instance.meta["budget"],
            total_votes=self.instance.meta["num_votes"],
            name=name,
        )

        # Page Summary
        summary_page_output = MESVisualiser.page_summary_template.render(
            election_name=(
                self.instance.meta["description"]
                if "description" in self.instance.meta
                else "No description provided."
            ),
            currency=(
                self.instance.meta["currency"]
                if "currency" in self.instance.meta
                else "CUR"
            ),
            rounds=self.rounds,
            projects=self.instance.project_meta,
            number_of_elected_projects=len(self.outcome),
            number_of_unelected_projects=len(self.instance) - len(self.outcome),
            spent=total_cost(p for p in self.instance if p.name in self.outcome),
            budget=self.instance.meta["budget"],
            total_votes=self.instance.meta["num_votes"],
            name=name,
        )
        if not os.path.exists(output_folder_path):
            os.makedirs(output_folder_path)
        with open(
            f"{output_folder_path}/{name}_round_analysis.html", "w", encoding="utf-8"
        ) as o:
            o.write(round_analysis_page_output)
        with open(
            f"{output_folder_path}/{name}_summary.html", "w", encoding="utf-8"
        ) as o:
            o.write(summary_page_output)


class GreedyWelfareVisualiser(Visualiser):
    """
    Class used to visualise the results of a Greedy Welfare election. The visualisation result
    consists of a round by round analysis page called 'round_analysis.html'.

    Parameters
    ----------
    profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
        The profile.
    instance : :py:class:`~pabutools.election.instance.Instance`
        The election instance.
    outcome : :py:class:`~pabutools.rules.budgetallocation.AllocationDetails`
            The outcome of the election.
    verbose : bool, optional
        Whether to print the results to the console. The default is False.

    Returns
    -------
    None

    """

    template = ENV.get_template("./templates/greedy_round_analysis_template.html")

    def __init__(self, profile, instance, outcome, verbose=False):
        self.profile = profile
        self.instance = instance
        self.verbose = verbose
        self.outcome = outcome
        self.details = outcome.details
        self.rounds = []
        project_votes = outcome.details.projects
        project_votes = {
            project_votes[k].project.name: float(project_votes[k].score)
            for k in range(len(project_votes))
        }
        self.project_votes = {
            k: project_votes[k]
            for k in sorted(project_votes, key=project_votes.get, reverse=True)
        }

    def _calculate(self):
        """
        Calculate the data necessary for the visualisation.
        """

        self.rounds = []
        current_round = {}
        rejected_projects = []
        projects = sorted(
            self.details.projects, key=lambda x: float(x.score), reverse=True
        )
        for project in projects:
            if project.discarded:
                rejected_projects.append(
                    {
                        "id": project.project.name,
                        "name": project.project.name,
                        "cost": int(project.project.cost),
                        "votes": self.project_votes[project.project.name],
                    }
                )
            else:
                current_round["selected_project"] = {
                    "id": project.project.name,
                    "name": project.project.name,
                    "cost": int(project.project.cost),
                    "votes": self.project_votes[project.project.name],
                }
                current_round["rejected_projects"] = rejected_projects[:]
                current_round["remaining_budget"] = int(project.remaining_budget) + int(
                    project.project.cost
                )
                rejected_cost = [int(p["cost"]) for p in rejected_projects]
                current_round["max_cost"] = (
                    max(max(rejected_cost), current_round["remaining_budget"])
                    if rejected_cost
                    else current_round["remaining_budget"]
                )
                self.rounds.append(current_round)
                current_round = {}
                rejected_projects = []

        self.rounds = sorted(
            self.rounds, key=lambda x: x["remaining_budget"], reverse=True
        )
        for i, round in enumerate(self.rounds):
            round["id"] = i + 1

    def render(self, output_folder_path, name=""):
        """
        Render the visualisation.

        Parameters
        ----------
        output_folder_path : str
            The path to the folder where the visualisation will be saved.
        name : str, optional
            The prefix of the output files. The default is "".
        Returns
        -------
            None

        """
        self._calculate()
        if self.verbose:
            logger.info(self.rounds)

        # Round by Round
        round_analysis_page_output = GreedyWelfareVisualiser.template.render(
            election_name=(
                self.instance.meta["description"]
                if "description" in self.instance.meta
                else "No description provided."
            ),
            currency=(
                self.instance.meta["currency"]
                if "currency" in self.instance.meta
                else "CUR"
            ),
            projects_selected_or_rejected=json.dumps(
                {str(p): (p in self.outcome) for p in self.project_votes.keys()}
            ),
            project_votes=self.project_votes,
            rounds=self.rounds,
            projects=self.instance.project_meta,
            number_of_elected_projects=len(self.outcome),
            number_of_unelected_projects=len(self.instance) - len(self.outcome),
            spent=total_cost(p for p in self.instance if p.name in self.outcome),
            budget=self.instance.meta["budget"],
            total_votes=self.instance.meta["num_votes"],
            name=name,
        )
        if not os.path.exists(output_folder_path):
            os.makedirs(output_folder_path)
        with open(
            f"{output_folder_path}/{name}_round_analysis.html", "w", encoding="utf-8"
        ) as o:
            o.write(round_analysis_page_output)
