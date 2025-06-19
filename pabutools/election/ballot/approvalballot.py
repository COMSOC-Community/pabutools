"""
Approval ballots, i.e., ballots in which the voters indicate which projects they approve of.
"""

from __future__ import annotations

import random
from abc import ABC

from collections.abc import Iterable

from pabutools.election.instance import Project
from pabutools.election.ballot.ballot import Ballot, FrozenBallot, AbstractBallot


class AbstractApprovalBallot(AbstractBallot, ABC):
    """
    Abstract class for approval ballots. Essentially used for typing purposes.
    """


class FrozenApprovalBallot(tuple[Project], FrozenBallot, AbstractApprovalBallot):
    """
    Frozen approval ballot, that is, a ballot in which the voter expressed their preferences by simply selecting
    some projects they approve of. It derives from the Python class `tuple` and can be used as one.

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
                meta = dict
        FrozenBallot.__init__(self, name, meta)
        AbstractApprovalBallot.__init__(self)

    def __new__(
        cls,
        approved: Iterable[Project] = (),
        name: str = "",
        meta: dict | None = None,
    ):
        return tuple.__new__(cls, tuple(approved))

    def __hash__(self):
        return tuple.__hash__(self)


class ApprovalBallot(set[Project], Ballot, AbstractApprovalBallot):
    """
    An approval ballot, that is, a ballot in which the voter has indicated the projects that they approve of. It
    is a subclass of the Python class `set` and can be used as one.

    Parameters
    ----------
        init: Iterable[:py:class:`~pabutools.election.instance.Project`], optional
            Collection of :py:class:`~pabutools.election.instance.Project` used to initialise the set. In case an
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
        init: Iterable[Project] = (),
        name: str | None = None,
        meta: dict | None = None,
    ) -> None:
        set.__init__(self, init)
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
        Ballot.__init__(self, name, meta)
        AbstractApprovalBallot.__init__(self)

    def frozen(self) -> FrozenApprovalBallot:
        """
        Returns the frozen approval ballot (that is hashable) corresponding to the ballot.

        Returns
        -------
            FrozenApprovalBallot
                The frozen approval ballot.
        """
        return FrozenApprovalBallot(self, name=self.name, meta=self.meta)

    # Ensures that methods returning copies of sets cast back into ApprovalBallot
    @classmethod
    def _wrap_methods(cls, methods):
        def wrap_method_closure(method):
            def inner_method(self, *args):
                result = getattr(super(cls, self), method)(*args)
                if isinstance(result, set) and not isinstance(result, cls):
                    result = cls(init=result, name=self.name, meta=self.meta)
                return result

            inner_method.fn_name = method
            setattr(cls, method, inner_method)

        for m in methods:
            wrap_method_closure(m)


ApprovalBallot._wrap_methods(
    [
        "__ror__",
        "difference_update",
        "__isub__",
        "symmetric_difference",
        "__rsub__",
        "__and__",
        "__rand__",
        "intersection",
        "difference",
        "__iand__",
        "union",
        "__ixor__",
        "symmetric_difference_update",
        "__or__",
        "copy",
        "__rxor__",
        "intersection_update",
        "__xor__",
        "__ior__",
        "__sub__",
    ]
)


def get_random_approval_ballot(
    projects: Iterable[Project], name: str = "RandomAppBallot"
) -> ApprovalBallot:
    """
    Generates a random approval ballot in which each project is approved with probability 0.5.

    Parameters
    ----------
        projects : Iterable[:py:class:`~pabutools.election.instance.Project`]
            An iterable of projects.
        name : str, optional
            The identifier of the ballot.
            Defaults to `"RandomAppBallot"`.
    Returns
    -------
        ApprovalBallot
            The randomly-generated approval ballot.
    """
    ballot = ApprovalBallot(name=name)
    for p in projects:
        if random.random() > 0.5:
            ballot.add(p)
    return ballot
