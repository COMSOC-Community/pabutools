"""
Cardinal ballots, i.e., ballots in which the voters map projects to scores.
"""

from __future__ import annotations

from abc import ABC
from collections.abc import Mapping, Iterable

from pabutools.election.ballot.ballot import FrozenBallot, Ballot, AbstractBallot
from pabutools.election.instance import Project

from pabutools.utils import Numeric


class AbstractCardinalBallot(AbstractBallot, ABC, Mapping[Project, Numeric]):
    """
    Abstract class for cardinal ballots. Essentially used for typing purposes.
    """


class FrozenCardinalBallot(
    dict[Project, Numeric], FrozenBallot, AbstractCardinalBallot
):
    """
    Frozen cardinal ballot, that is, a ballot in which the voter assigned scores to projects.
    Since there is no frozen dictionary implemented in Python, this class simply inherits from the Python class `dict`,
    overriding the `set_item` method to ensure that it is non-mutable (raising an exception if the method is used).

    Parameters
    ----------
        init: dict[:py:class:`~pabutools.election.instance.Project`], optional
            Dictionary of :py:class:`~pabutools.election.instance.Project` used to initialise the ballot. In case an
            :py:class:`~pabutools.election.ballot.ballot.AbstractBallot` object is passed, the
            additional attributes are also copied (except if the corresponding keyword arguments have been given).
            Defaults to `()`.
        name : str, optional
            The identifier of the ballot.
            Defaults to `""`.
        meta : dict, optional
            Additional information concerning the ballot, stored in a dictionary. Keys and values are typically
            strings. Could for instance store the gender of the voter, their location etc.
            Defaults to `dict()`.

    Attributes
    ----------
        name : str
            The identifier of the ballot.
        meta : dict
            Additional information concerning the ballot, stored in a dictionary. Keys and values are typically
            strings. Could for instance store the gender of the voter, their location etc.
    """

    def __init__(
        self,
        init: dict[Project, Numeric] = (),
        name: str | None = None,
        meta: dict | None = None,
    ):
        dict.__init__(self, init)
        if name is None:
            if isinstance(init, AbstractBallot):
                name = init.name
            else:
                name = ""
        if meta is None:
            if isinstance(init, AbstractBallot):
                meta = init.meta
            else:
                meta = dict()
        FrozenBallot.__init__(self, name=name, meta=meta)
        AbstractCardinalBallot.__init__(self)

    def __setitem__(self, key, value):
        raise ValueError("You cannot set values of a FrozenCardinalBallot")

    def __hash__(self):
        return tuple.__hash__(tuple(self.keys()))


class CardinalBallot(dict[Project, Numeric], Ballot, AbstractCardinalBallot):
    """
    A cardinal ballot, that is, a ballot in which the voter assigned scores to projects. This class inherits from the
    Python class `dict` and can be used as one.

    Parameters
    ----------
        init: dict[:py:class:`~pabutools.election.instance.Project`], optional
            Dictionary of :py:class:`~pabutools.election.instance.Project` used to initialise the ballot. In case an
            :py:class:`~pabutools.election.ballot.ballot.AbstractBallot` object is passed, the
            additional attributes are also copied (except if the corresponding keyword arguments have been given).
            Defaults to `()`.
        name : str, optional
            The identifier of the ballot.
            Defaults to `""`.
        meta : dict, optional
            Additional information concerning the ballot, stored in a dictionary. Keys and values are typically
            strings. Could for instance store the gender of the voter, their location etc.
            Defaults to `dict()`.

    Attributes
    ----------
        name : str
            The identifier of the ballot.
        meta : dict
            Additional information concerning the ballot, stored in a dictionary. Keys and values are typically
            strings. Could for instance store the gender of the voter, their location etc.
    """

    def __init__(
        self,
        init: dict[Project, Numeric] | None = None,
        name: str | None = None,
        meta: dict | None = None,
    ):
        if init is None:
            init = dict()
        dict.__init__(self, init)
        if name is None:
            if isinstance(init, AbstractBallot):
                name = init.name
            else:
                name = ""
        if meta is None:
            if isinstance(init, AbstractBallot):
                meta = init.meta
            else:
                meta = dict
        Ballot.__init__(self, name=name, meta=meta)
        AbstractCardinalBallot.__init__(self)

    def complete(self, projects: Iterable[Project], default_score: Numeric) -> None:
        """
        Completes the ballot by assigning the `default_score` to all projects from `projects` that have not been
        assigned a score yet.

        Parameters
        ----------
            projects : Iterable[:py:class:`~pabutools.election.instance.Project`]
                The set of all the projects to consider. This is typically the instance.
            default_score : Numeric
                The default score that will be assigned.
        """
        for project in projects:
            if project not in self:
                self[project] = default_score

    def frozen(self) -> FrozenCardinalBallot:
        """
        Returns the frozen cardinal ballot (that is hashable) corresponding to the ballot.

        Returns
        -------
            FrozenCardinalBallot
                The frozen cardinal ballot.
        """
        return FrozenCardinalBallot(self)

    # This allows dict method returning copies of a dict to work
    @classmethod
    def _wrap_methods(cls, names):
        def wrap_method_closure(name):
            def inner(self, *args):
                result = getattr(super(cls, self), name)(*args)
                if isinstance(result, dict) and not isinstance(result, cls):
                    result = cls(result, name=self.name, meta=self.meta)
                return result

            inner.fn_name = name
            setattr(cls, name, inner)

        for n in names:
            wrap_method_closure(n)


CardinalBallot._wrap_methods(["copy", "__ior__", "__or__", "__ror__"])
