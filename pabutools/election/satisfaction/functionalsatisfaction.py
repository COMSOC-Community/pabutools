"""
Functional satisfaction measures.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable, Collection

from pabutools.utils import Numeric

import numpy as np

from pabutools.election.satisfaction.satisfactionmeasure import SatisfactionMeasure
from pabutools.election.ballot import (
    AbstractBallot,
    AbstractApprovalBallot,
    AbstractCardinalBallot,
)
from pabutools.election.instance import Instance, Project, total_cost

from typing import TYPE_CHECKING

from pabutools.fractions import frac

# To avoid circular import that is only needed for type checking
if TYPE_CHECKING:
    from pabutools.election.profile import AbstractProfile


class FunctionalSatisfaction(SatisfactionMeasure):
    """
    Class representing satisfaction measures that are simply defined via functions of the ballot and a subset of
    projects.


    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        ballot : :py:class:`~pabutools.election.ballot.ballot.AbstractBallot`
            The ballot.
        func : Callable[[:py:class:`~pabutools.election.instance.Instance`, :py:class:`~pabutools.election.profile.profile.AbstractProfile`, :py:class:`~pabutools.election.ballot.ballot.AbstractBallot`, Iterable[:py:class:`~pabutools.election.instance.Project`], Numeric]
            The actual satisfaction function, i.e., a function returning the satisfaction for a given collection of
            projects, given the instance, the profile and the ballot under consideration.

    Attributes
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        ballot : :py:class:`~pabutools.election.ballot.ballot.AbstractBallot`
            The ballot.
        func : Callable[[:py:class:`~pabutools.election.instance.Instance`, :py:class:`~pabutools.election.profile.profile.AbstractProfile`, :py:class:`~pabutools.election.ballot.ballot.AbstractBallot`, Iterable[:py:class:`~pabutools.election.instance.Project`], Numeric]
            The actual satisfaction function, i.e., a function returning the satisfaction for a given collection of
            projects, given the instance, the profile and the ballot under consideration.
    """

    def __init__(
        self,
        instance: Instance,
        profile: AbstractProfile,
        ballot: AbstractBallot,
        func: Callable[
            [Instance, AbstractProfile, AbstractBallot, Collection[Project]], Numeric
        ],
    ):
        SatisfactionMeasure.__init__(self, instance, profile, ballot)
        self.func = func

    def sat(self, projects: Collection[Project]) -> Numeric:
        return self.func(self.instance, self.profile, self.ballot, projects)

    def sat_project(self, project: Project) -> Numeric:
        return self.sat([project])


def cc_sat_func_app(
    instance: Instance,
    profile: AbstractProfile,
    ballot: AbstractApprovalBallot,
    projects: Collection[Project],
) -> int:
    """
    Computes the Chamberlin-Courant satisfaction for approval ballots. It is equal to 1 if at least one approved project
    has been selected, and 0 otherwise.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        ballot : :py:class:`~pabutools.election.ballot.approvalballot.AbstractApprovalBallot`
            The ballot.
        projects : Iterable[:py:class:`~pabutools.election.instance.Project`]
            The selected collection of projects.

    Returns
    -------
        int
            The Chamberlin-Courant satisfaction.

    """
    return int(any(p in ballot for p in projects))


def cc_sat_func_card(
    instance: Instance,
    profile: AbstractProfile,
    ballot: AbstractCardinalBallot,
    projects: Collection[Project],
) -> Numeric:
    """
    Computes the Chamberlin-Courant satisfaction for approval ballots. It is equal to the maximum score assigned to
    a selected project in the ballot, and 0 if no selected project has been assigned a score.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        ballot : :py:class:`~pabutools.election.ballot.cardinalballot.AbstractCardinalBallot`
            The ballot.
        projects : Iterable[:py:class:`~pabutools.election.instance.Project`]
            The selected collection of projects.

    Returns
    -------
        Numeric
            The Chamberlin-Courant satisfaction.

    """
    res = 0
    for p in projects:
        if p in ballot and ballot[p] > res:
            res = ballot[p]
    return res


class CC_Sat(FunctionalSatisfaction):
    """
    Chamberlin-Courant satisfaction. It can only be applied to approval or cardinal ballots.

    In the case of approval ballots, it is equal to 1 if at least one selected project is approved, and 0 otherwise.

    In the case of cardinal ballots, it is equal to the maximum score assigned to a selected project in the ballot,
    and 0 if no selected project has been assigned a score.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        ballot : :py:class:`~pabutools.election.ballot.ballot.AbstractBallot`
            The ballot.
    """

    def __init__(
        self, instance: Instance, profile: AbstractProfile, ballot: AbstractBallot
    ):
        if isinstance(ballot, AbstractApprovalBallot):
            FunctionalSatisfaction.__init__(
                self, instance, profile, ballot, cc_sat_func_app
            )
        elif isinstance(ballot, AbstractCardinalBallot):
            FunctionalSatisfaction.__init__(
                self, instance, profile, ballot, cc_sat_func_card
            )
        else:
            raise ValueError(
                "The Chamberlin-Courant satisfaction cannot be used for ballots of type {}".format(
                    type(ballot)
                )
            )


def cost_sqrt_sat_func(
    instance: Instance,
    profile: AbstractProfile,
    ballot: AbstractApprovalBallot,
    projects: Collection[Project],
) -> Numeric:
    """
    Computes the cost square root satisfaction for approval ballots. It is equal to the square root of the total cost of
    the approved and selected projects.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        ballot : :py:class:`~pabutools.election.ballot.approvalballot.AbstractApprovalBallot`
            The ballot.
        projects : Iterable[:py:class:`~pabutools.election.instance.Project`]
            The selected collection of projects.

    Returns
    -------
        Numeric
            The cost square root satisfaction.

    """
    return frac(np.sqrt(float(total_cost(tuple(p for p in projects if p in ballot)))))


class Cost_Sqrt_Sat(FunctionalSatisfaction):
    """
    Cost square root satisfaction. It can only be applied to approval ballots. It is equal to the square root of
    the total cost of the approved and selected projects.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        ballot : :py:class:`~pabutools.election.ballot.ballot.AbstractBallot`
            The ballot.
    """

    def __init__(
        self, instance: Instance, profile: AbstractProfile, ballot: AbstractBallot
    ):
        if isinstance(ballot, AbstractApprovalBallot):
            FunctionalSatisfaction.__init__(
                self, instance, profile, ballot, cost_sqrt_sat_func
            )
        else:
            raise ValueError(
                "The cost square root satisfaction cannot be used with ballot types {}".format(
                    type(ballot)
                )
            )


def cost_log_sat_func(
    instance: Instance,
    profile: AbstractProfile,
    ballot: AbstractApprovalBallot,
    projects: Collection[Project],
) -> Numeric:
    """
    Computes the cost log satisfaction for approval ballots. It is equal to the log of 1 plus the total cost of
    the approved and selected projects.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        ballot : :py:class:`~pabutools.election.ballot.approvalballot.AbstractApprovalBallot`
            The ballot.
        projects : Iterable[:py:class:`~pabutools.election.instance.Project`]
            The selected collection of projects.

    Returns
    -------
        Numeric
            The log cost satisfaction.

    """
    return frac(np.log(float(1 + total_cost(p for p in projects if p in ballot))))


class Cost_Log_Sat(FunctionalSatisfaction):
    """
    Cost log satisfaction. It can only be applied to approval ballots. It is equal to the log of 1 plus the total cost
    of the approved and selected projects.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        ballot : :py:class:`~pabutools.election.ballot.ballot.AbstractBallot`
            The ballot.
    """

    def __init__(
        self, instance: Instance, profile: AbstractProfile, ballot: AbstractBallot
    ):
        if isinstance(ballot, AbstractApprovalBallot):
            FunctionalSatisfaction.__init__(
                self, instance, profile, ballot, cost_log_sat_func
            )
        else:
            raise ValueError(
                "The cost log satisfaction cannot be used with ballot types {}".format(
                    type(ballot)
                )
            )
