"""
Ballots, that is, the information submitted by the voters during the election.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Collection

from pabutools.election import Project


class AbstractBallot(ABC, Collection[Project]):
    """
    Abstract class representing the ballots, i.e., the information submitted by the voters. Essentially used for
    type-hint purposes.

    Parameters
    ----------
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
            strings. Could for instance store the gender of the voter, their location etc...
    """

    def __init__(self, name: str = "", meta: dict | None = None):
        if meta is None:
            meta = dict()
        self.meta = meta
        self.name = name

    def supports(self, c):
        raise NotImplementedError("This ballot does not support the notion of 'supporting' projects.")

    def utility(self, c):
        raise NotImplementedError("This ballot does not support the notion of 'utility' for projects.")


class FrozenBallot(AbstractBallot, ABC):
    """
    Abstract class representing frozen ballots, i.e., ballots that are hashable (and thus non-mutable). In general the
    :py:class:`~pabutools.election.ballot.ballot.Ballot` class should be preferred over this one but hashable ballots
    can be useful (typically for :py:class:`~pabutools.election.profile.profile.MultiProfile`).

    Parameters
    ----------
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
            strings. Could for instance store the gender of the voter, their location etc...
    """

    def __init__(self, name: str = "", meta: dict | None = None):
        if meta is None:
            meta = dict()
        AbstractBallot.__init__(self, name=name, meta=meta)
        self.meta = meta
        self.name = name


class Ballot(AbstractBallot):
    """
    Abstract class representing the ballots, i.e., the information submitted by the voters.

    Parameters
    ----------
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
            strings. Could for instance store the gender of the voter, their location etc...
    """

    def __init__(self, name: str = "", meta: dict | None = None):
        if meta is None:
            meta = dict()
        AbstractBallot.__init__(self, name=name, meta=meta)
        self.meta = meta
        self.name = name

    @abstractmethod
    def frozen(self) -> FrozenBallot:
        """
        Returns the ballot in its frozen form, that is, as a Frozen (hashable) ballot.

        Returns
        -------
            FrozenBallot
                The ballot in its frozen form.
        """
