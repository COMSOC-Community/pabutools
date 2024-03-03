from typing import Dict
import numpy as np

from pabutools.utils import Numeric

from pabutools.election import (
    AbstractApprovalProfile,
    AbstractCardinalProfile,
    AbstractProfile,
)
from pabutools.election import Instance, total_cost

from pabutools.fractions import frac
from pabutools.utils import mean_generator


def avg_ballot_length(instance: Instance, profile: AbstractProfile) -> Numeric:
    """
    Returns the average length of the ballots in the profile.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.

    Returns
    -------
        Numeric
            The average length of the ballots in the profile.

    """
    return mean_generator(
        (len(ballot), profile.multiplicity(ballot)) for ballot in profile
    )


def median_ballot_length(instance: Instance, profile: AbstractProfile) -> int:
    """
    Returns the median length of the ballots in the profile.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.

    Returns
    -------
        Numeric
            The median length of the ballots in the profile.

    """
    if profile.num_ballots() == 0:
        return 0
    ballot_lengths = np.zeros(profile.num_ballots())
    index = 0
    for ballot in profile:
        for j in range(profile.multiplicity(ballot)):
            ballot_lengths[index] = len(ballot)
            index += 1
    return int(np.median(ballot_lengths))


def avg_ballot_cost(instance: Instance, profile: AbstractProfile) -> Numeric:
    """
    Returns the average cost of the ballots in the profile.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.

    Returns
    -------
        Numeric
            The average cost of the ballots in the profile.

    """
    return mean_generator(
        (total_cost(ballot), profile.multiplicity(ballot)) for ballot in profile
    )


def median_ballot_cost(instance: Instance, profile: AbstractProfile) -> Numeric:
    """
    Returns the median cost of the ballots in the profile.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.

    Returns
    -------
        Numeric
            The median cost of the ballots in the profile.

    """
    if profile.num_ballots() == 0:
        return 0
    ballot_costs = np.zeros(profile.num_ballots())
    index = 0
    for ballot in profile:
        for j in range(profile.multiplicity(ballot)):
            ballot_costs[index] = total_cost(ballot)
            index += 1
    return np.median(ballot_costs)


def avg_approval_score(instance: Instance, profile: AbstractApprovalProfile) -> Numeric:
    """
    Returns the average approval score of projects.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.approvalprofile.AbstractApprovalProfile`
            The profile.

    Returns
    -------
        Numeric
            The average approval score of projects.

    """
    return mean_generator([profile.approval_score(project) for project in instance])


def median_approval_score(
    instance: Instance, profile: AbstractApprovalProfile
) -> Numeric:
    """
    Returns the median approval score of projects.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.approvalprofile.AbstractApprovalProfile`
            The profile.

    Returns
    -------
        Numeric
            The median approval score of projects.

    """
    if len(instance) == 0:
        return 0
    return float(
        np.median([frac(profile.approval_score(project)) for project in instance])
    )


def avg_total_score(instance: Instance, profile: AbstractCardinalProfile) -> Numeric:
    """
    Returns the average score assigned to a project by the voters.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.cardinalprofile.AbstractCardinalProfile`
            The profile.

    Returns
    -------
        Numeric
            The average score assigned to a project.

    """
    return mean_generator(profile.total_score(project) for project in instance)


def median_total_score(instance: Instance, profile: AbstractCardinalProfile) -> Numeric:
    """
    Returns the median score assigned to a project by the voters.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.cardinalprofile.AbstractCardinalProfile`
            The profile.

    Returns
    -------
        Numeric
            The median score assigned to a project.

    """
    if len(instance) == 0:
        return 0
    return float(
        np.median([frac(profile.total_score(project)) for project in instance])
    )


def votes_count_by_project(profile: AbstractCardinalProfile) -> Dict[str, int]:
    """
    Returns the number of votes for each project.

    Parameters
    ----------
        profile : :py:class:`~pabutools.election.profile.cardinalprofile.AbstractCardinalProfile`
            The profile.

    Returns
    -------
        Dict[str, int]
            The number of votes for each project.

    """
    project_votes = {}

    # Function to update the project_votes dictionary
    def update_votes(project_list):
        for project_id in project_list:
            if project_id in project_votes:
                project_votes[project_id] += 1
            else:
                project_votes[project_id] = 1

    for prof in profile:
        update_votes(list(prof))

    return project_votes

def voter_flow_matrix(instance: Instance, profile: AbstractCardinalProfile) -> Dict[str, Dict[str, int]]:
    """
    Returns the voter flow matrix. The voter flow matrix is a 2D dictionary where voter_flow[a][b] is the number of
    voters for 'a' who voted for 'b'

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.

    Returns
    -------
        Dict[str, Dict[str, int]]
            The voter flow matrix.

    """
    voter_flow = {}
    for project in instance:
        voter_flow[str(project)] = {}
        for other_project in instance:
            voter_flow[str(project)][str(other_project)] = 0

    def update_voter_flow(vote_list):
        for i in range(len(vote_list)):
            for j in range(i + 1, len(vote_list)):
                voter_flow[str(vote_list[i])][str(vote_list[j])] += 1
                voter_flow[str(vote_list[j])][str(vote_list[i])] += 1
        if len(vote_list) == 1:
            voter_flow[str(vote_list[0])][str(vote_list[0])] += 1

    for vote in profile:
        update_voter_flow(list(vote))

    return voter_flow