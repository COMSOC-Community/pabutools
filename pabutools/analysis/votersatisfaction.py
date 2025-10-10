from collections.abc import Collection

from pabutools.utils import Numeric

import numpy as np
import math

from pabutools.election.instance import Instance, Project
from pabutools.election.profile.profile import MultiProfile, AbstractProfile
from pabutools.election.satisfaction import (
    SatisfactionMeasure,
    CC_Sat,
    SatisfactionMultiProfile,
)
from pabutools.fractions import frac

from pabutools.utils import gini_coefficient, mean_generator


def avg_satisfaction(
    instance: Instance,
    profile: AbstractProfile,
    budget_allocation: Collection[Project],
    sat_class: type[SatisfactionMeasure],
) -> Numeric:
    """
    Computes the average satisfaction for a given instance, profile and satisfaction measure.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        budget_allocation : Iterable[:py:class:`~pabutools.election.instance.Project`]
            Collection of projects.
        sat_class: type[:py:class:`~pabutools.election.satisfaction.satisfactionmeasure.SatisfactionMeasure`]
            The satisfaction measure used to do the comparison.

    Returns
    -------
        Numeric
            The average satisfaction of a voter for the budget allocation.
    """

    return mean_generator(
        (
            sat_class(instance, profile, ballot).sat(budget_allocation),
            profile.multiplicity(ballot),
        )
        for ballot in profile
    )


def percent_non_empty_handed(
    instance: Instance, profile: AbstractProfile, budget_allocation: Collection[Project]
) -> Numeric:
    """
    Computes the percentage of voter for which at least one project from the budget allocation also appears in their
    ballot.

    It mostly makes sense for approval ballots, though any profile of ballots supporting the `in` operator can be used.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        budget_allocation : Iterable[:py:class:`~pabutools.election.instance.Project`]
            Collection of projects.

    Returns
    -------
        Numeric
            The percentage of non-empty handed voters.
    """
    return avg_satisfaction(instance, profile, budget_allocation, CC_Sat)


def percent_positive_satisfaction(
    profile: AbstractProfile,
    budget_allocation: Collection[Project],
    sat_class: type[SatisfactionMeasure],
) -> Numeric:
    """
    Computes the percentage of voter who enjoy a positive (thus non-zero) satisfaction.

    Parameters
    ----------
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        budget_allocation : Iterable[:py:class:`~pabutools.election.instance.Project`]
            Collection of projects.
        sat_class : type[:py:class:`~pabutools.election.satisfaction.satisfactionmeasure.SatisfactionMeasure`]
            The class defining the satisfaction function used to measure the social welfare. It should be a class
            inheriting from :py:class:`~pabutools.election.satisfaction.satisfactionmeasure.SatisfactionMeasure`.

    Returns
    -------
        Numeric
            The percentage of non-empty handed voters.
    """
    sat_profile = profile.as_sat_profile(sat_class)
    num_pos_sat = 0
    for sat in sat_profile:
        if sat.sat(budget_allocation) > 0:
            num_pos_sat += 1
    return frac(num_pos_sat, profile.num_ballots())


def gini_coefficient_of_satisfaction(
    instance: Instance,
    profile: AbstractProfile,
    budget_allocation: Collection[Project],
    sat_class: type[SatisfactionMeasure],
    invert: bool = False,
) -> Numeric:
    """
    Computes the Gini coefficient of the satisfaction of the voters.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        budget_allocation : Iterable[:py:class:`~pabutools.election.instance.Project`]
            Collection of projects.
        sat_class: type[:py:class:`~pabutools.election.satisfaction.satisfactionmeasure.SatisfactionMeasure`]
            The satisfaction measure used to do the comparison.
        invert: bool, optional
            Set to `True` to return 1 minus the Gini coefficient. Defaults to `False`.

    Returns
    -------
        Numeric
            The Gini coefficient of the satisfaction of the voters.
    """
    voter_satisfactions = []
    for ballot in profile:
        voter_satisfaction = frac(
            sat_class(instance, profile, ballot).sat(budget_allocation)
        )
        for i in range(profile.multiplicity(ballot)):
            voter_satisfactions.append(voter_satisfaction)

    if invert:
        return 1 - gini_coefficient(np.array(voter_satisfactions))
    return gini_coefficient(np.array(voter_satisfactions))


def satisfaction_histogram(
    instance: Instance,
    profile: AbstractProfile,
    budget_allocation: Collection[Project],
    sat_class: type[SatisfactionMeasure],
    max_satisfaction: Numeric,
    num_bins: int = 21,
) -> list[Numeric]:
    """
    Computes the data necessary to plot a histogram of the satisfaction of the voters. Each bin contains the percentage
    of voters whose satisfaction corresponds to the bin.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        budget_allocation : Iterable[:py:class:`~pabutools.election.instance.Project`]
            Collection of projects.
        sat_class: type[:py:class:`~pabutools.election.satisfaction.satisfactionmeasure.SatisfactionMeasure`]
            The satisfaction measure used to do the comparison.
        max_satisfaction: Numeric
            The normaliser for the satisfaction.
        num_bins: int, optional
            The number of bins of the histogram. Defaults to `20`.

    Returns
    -------
        list[Numeric]
            A list of values, one per bin of the histogram.
    """

    if isinstance(profile, MultiProfile):
        sat_profile = SatisfactionMultiProfile(
            instance=instance, multiprofile=profile, sat_class=sat_class
        )
    else:
        sat_profile = SatisfactionMultiProfile(
            instance=instance, profile=profile, sat_class=sat_class
        )

    hist_data = [0.0 for _ in range(num_bins)]
    for ballot in sat_profile:
        satisfaction = ballot.sat(budget_allocation)
        if satisfaction >= max_satisfaction:
            hist_data[-1] += sat_profile.multiplicity(ballot)
        else:
            hist_data[
                math.ceil(satisfaction * (num_bins - 1) / max_satisfaction)
            ] += sat_profile.multiplicity(ballot)
    for i in range(len(hist_data)):
        hist_data[i] /= profile.num_ballots()
    return hist_data
