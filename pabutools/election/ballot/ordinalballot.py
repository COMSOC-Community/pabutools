"""
Ordinal ballots, i.e., ballots in which the voters order the projects given their preferences.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Collection, Iterable

from pabutools.election.ballot.ballot import FrozenBallot, Ballot, AbstractBallot
from pabutools.election.instance import Project


class AbstractOrdinalBallot(AbstractBallot, ABC, Collection[Project]):
    """
    Abstract class for ordinal ballots. Essentially used for typing purposes.
    """

    @abstractmethod
    def position(self, project: Project) -> int:
        """
        Returns the position of a project in the ordinal ballot.

        Parameters
        ----------
            project : :py:class:`~pabutools.election.instance.Project`
                The project.

        Returns
        -------
            int
                The position of the project.
        """


class FrozenOrdinalBallot(tuple[Project], FrozenBallot, AbstractOrdinalBallot):
    """
    Frozen ordinal ballot, that is, a ballot in which the voter has ordered some projects according to their
    preferences. It derives from the Python class `tuple` and can be used as one.

    Parameters
    ----------
        init: Iterable[:py:class:`~pabutools.election.instance.Project`], optional
            Iterable of :py:class:`~pabutools.election.instance.Project` used to initialise the tuple. In case an
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

    def position(self, project: Project) -> int:
        return self.index(project)

    def __init__(
        self,
        init: Iterable[Project] = (),
        name: str | None = None,
        meta: dict | None = None,
    ) -> None:
        tuple.__init__(self)
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
        FrozenBallot.__init__(self, name, meta)
        AbstractOrdinalBallot.__init__(self)

    def __new__(
        cls,
        iterable: Collection[Project] = (),
        name: str = "",
        meta: dict | None = None,
    ):
        if len(set(iterable)) != len(iterable):
            raise ValueError(
                "Some projects are repeated in {}, this is not a valid ordinal ballot.".format(
                    iterable
                )
            )
        return tuple.__new__(cls, tuple(iterable))

    def __hash__(self):
        return tuple.__hash__(self)


class OrdinalBallot(dict, Ballot, AbstractOrdinalBallot):
    """
    Ordinal ballot, that is, a ballot in which the voter has ordered some projects according to their
    preferences. It behaves as an ordered set (implemented using Python `dict` for technical reasons).
    The convention is that the elements are presented from the most preferred one to the least preferred one.

    Parameters
    ----------
        init: Iterable[:py:class:`~pabutools.election.instance.Project`], optional
            Iterable of :py:class:`~pabutools.election.instance.Project` used to initialise the ballot. In case an
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

    def position(self, project: Project) -> int:
        return self.index(project)

    def __init__(
        self,
        init: Iterable[Project] = (),
        name: str | None = None,
        meta: dict | None = None,
    ) -> None:
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
        dict.__init__(self, {e: None for e in init})
        Ballot.__init__(self, name=name, meta=meta)
        AbstractOrdinalBallot.__init__(self)

    def append(self, project: Project) -> None:
        """
        Appends a project to the order. If the project is already present, its position does not change.

        Parameters
        ----------
            project : :py:class:`~pabutools.election.instance.Project`
                The project to append.
        """
        self[project] = None

    def __add__(self, other):
        if not isinstance(other, OrdinalBallot):
            raise TypeError("Only ordinal ballots can be added to ordinal ballots")
        result = OrdinalBallot(self, name=self.name, meta=self.meta)
        for e in other:
            result[e] = None
        return result

    def __reversed__(self):
        rev_generator = dict.__reversed__(self)
        res = OrdinalBallot(name=self.name, meta=self.meta)
        for key in rev_generator:
            res.append(key)
        return res

    def index(self, project: Project) -> int:
        """
        Returns the index of the project given as argument by looping through all the projects until finding it.
        If the required project is not found, a `ValueError` is raised.

        Parameters
        ----------
            project : :py:class:`~pabutools.election.instance.Project`
                The project to append.

        Returns
        -------
            int
                The index of the project in the order.
        """
        i = 0
        for e in self:
            if e == project:
                return i
            i += 1
        raise ValueError("{} is not in the ballot".format(project))

    def at_index(self, index: int) -> Project:
        """
        Returns the project at index `index`, or None . A `ValueError` is raised if the index is invalid.

        Parameters
        ----------
            index : int
                The index.

        Returns
        -------
            :py:class:`~pabutools.election.instance.Project`
                The project at position `index`.
        """
        i = 0
        for e in self:
            if i == index:
                return e
            i += 1
        raise ValueError(
            "Index {} invalid for ordinal ballot of length {}.".format(
                index, len(self)
            )
        )

    def frozen(self) -> FrozenOrdinalBallot:
        """
        Returns the frozen ordinal ballot (that is hashable) corresponding to the ballot.

        Returns
        -------
            FrozenOrdinalBallot
                The frozen ordinal ballot.
        """
        return FrozenOrdinalBallot(self)

    def __eq__(self, other) -> bool:
        if not isinstance(other, OrdinalBallot):
            return False
        if len(self) != len(other):
            return False
        for e1, e2 in zip(self, other):
            if e1 != e2:
                return False
        return True

    def __ne__(self, other) -> bool:
        return not self.__eq__(other)

    def __lt__(self, other) -> bool:
        if not isinstance(other, OrdinalBallot):
            raise TypeError("'<' can only be used between two ordinal ballots")
        for e1, e2 in zip(self, other):
            if e1 < e2:
                return True
            elif e2 < e1:
                return False
        return len(self) < len(other)

    def __le__(self, other) -> bool:
        if not isinstance(other, OrdinalBallot):
            raise TypeError("'<' can only be used between two ordinal ballots")
        for e1, e2 in zip(self, other):
            if e1 < e2:
                return True
            elif e2 < e1:
                return False
        return len(self) <= len(other)

    def __repr__(self) -> str:
        return list(self.keys()).__repr__()

    def __str__(self) -> str:
        return list(self.keys()).__str__()

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


OrdinalBallot._wrap_methods(["copy", "__ior__", "__or__", "__ror__"])
