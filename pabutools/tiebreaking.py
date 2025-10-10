from __future__ import annotations

from collections.abc import Callable, Iterable, Collection

from pabutools.utils import Numeric

from pabutools.election.profile import AbstractProfile
from pabutools.election.instance import Instance, Project


class TieBreakingException(Exception):
    """Raised when a tie occurs and no tie-breaking rule is provided."""


class TieBreakingRule:
    """
    Implements a tie-breaking rule.

    Parameters
    ----------
        func : Callable[[Collection[Project], Profile, Project], Numeric]
            A function taking as input an instance, a profile and a project and returning the value on which the
            project will be sorted.

    Attributes
    ----------
        func : Callable[[Collection[Project], Profile, Project], Numeric]
            A function taking as input an instance, a profile and a project and returning the value on which the
            project will be sorted.
    """

    def __init__(self, func: Callable[[Collection[Project], AbstractProfile, Project], Numeric]):
        self.func = func

    def order(
        self,
        instance: Collection[Project],
        profile: AbstractProfile,
        projects: Collection[Project],
        key: Callable[..., Project] | None = None,
    ) -> list[Project]:
        """
        Break the ties among all the projects provided in input and returns them ordered. The tie-breaking can be
        based on the instance or/and on the profile.

        Parameters
        ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.Profile`
            The profile.
        projects : Iterable[:py:class:`~pabutools.election.instance.Project`]
            The set of projects between which ties are to be broken.
        key : Callable[..., :py:class:`~pabutools.election.instance.Project`], optional
            A key function to select the project from the input. Defaults to `lambda x: x`.

        Returns
        -------
            list[:py:class:`~pabutools.election.instance.Project`]
                The projects, ordered by the tie-breaking.
        """

        def default_key(p):
            return p

        if key is None:
            key = default_key
        return sorted(
            projects,
            key=lambda project: self.func(instance, profile, key(project)),
        )

    def untie(
        self,
        instance: Collection[Project],
        profile: AbstractProfile,
        projects: Collection[Project],
        key: Callable[..., Project] | None = None,
    ) -> Project:
        """
        Break the ties among all the projects provided in input and returns a single project. Orders the
        projects according to the tie-breaking rule and return the first project of the order.


        Parameters
        ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.Profile`
            The profile.
        projects : Iterable[:py:class:`~pabutools.election.instance.Project`]
            The set of projects between which ties are to be broken.
        key : Callable[..., :py:class:`~pabutools.election.instance.Project`], optional
            A key function to select the project from the input. Defaults to `lambda x: x`.

        Returns
        -------
            :py:class:`~pabutools.election.instance.Project`
                The first project according to the tie-breaking.
        """

        def default_key(p):
            return p

        if key is None:
            key = default_key
        return self.order(instance, profile, projects, key)[0]


lexico_tie_breaking = TieBreakingRule(lambda inst, prof, proj: proj.name)
"""
Implements lexicographic tie breaking, i.e., tie-breaking based on the name of the projects.
"""

app_score_tie_breaking = TieBreakingRule(
    lambda inst, prof, proj: -prof.approval_score(proj)
)
"""
Implements tie breaking based on the approval score where the projects with the highest number of supporters in the 
profile is selected. Can only be applied to approval profiles.
"""

min_cost_tie_breaking = TieBreakingRule(lambda inst, prof, proj: proj.cost)
"""
Implements lexicographic tie breaking based on the cost where ties are broken in favour of the project with the lowest 
cost.
"""

max_cost_tie_breaking = TieBreakingRule(lambda inst, prof, proj: -proj.cost)
"""
Implements lexicographic tie breaking based on the cost where ties are broken in favour of the project with the highest
cost.
"""


def refuse_to_break_ties(
    instance: Instance, profile: AbstractProfile, project: Project
):
    raise TieBreakingException("A tie occurred, but no tie-breaking rule was provided.")


refuse_tie_breaking = TieBreakingRule(refuse_to_break_ties)
"""
Special tie-breaking function that simply raises an error when a tie needs to be broken.
"""
