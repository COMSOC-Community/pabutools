"""
Approval profiles, i.e., collections of approval ballots.
"""

from __future__ import annotations

from abc import ABC
from collections import defaultdict
from collections.abc import Iterable, Generator
from itertools import product

from pabutools.utils import Numeric

from pabutools.election.ballot.approvalballot import AbstractApprovalBallot
from pabutools.election.ballot.ballot import AbstractBallot

from pabutools.election.ballot import (
    ApprovalBallot,
    FrozenBallot,
    FrozenApprovalBallot,
    get_random_approval_ballot,
)
from pabutools.election.profile.profile import Profile, MultiProfile, AbstractProfile
from pabutools.election.instance import Instance, Project
from pabutools.utils import powerset


class AbstractApprovalProfile(AbstractProfile, ABC, Iterable[AbstractApprovalBallot]):
    """
    Abstract class for approval profiles. Stores the metadata and the methods specific to approval profiles.

    Parameters
    ----------
        legal_min_length : int, optional
            The minimum length of an approval ballot per the rules of the election.
            Defaults to `None`.
        legal_max_length : int, optional
            The maximum length of an approval ballot per the rules of the election.
            Defaults to `None`.
        legal_min_cost : Numeric, optional
            The minimum total cost of an approval ballot per the rules of the election.
            Defaults to `None`.
        legal_max_cost : Numeric, optional
            The maximum total cost of an approval ballot per the rules of the election.
            Defaults to `None`.

    Attributes
    ----------
        legal_min_length : int
            The minimum length of an approval ballot per the rules of the election.
        legal_max_length : int
            The maximum length of an approval ballot per the rules of the election.
        legal_min_cost : Numeric
            The minimum total cost of an approval ballot per the rules of the election.
        legal_max_cost : Numeric
            The maximum total cost of an approval ballot per the rules of the election.
    """

    def __init__(
        self,
        legal_min_length: int | None = None,
        legal_max_length: int | None = None,
        legal_min_cost: Numeric | None = None,
        legal_max_cost: Numeric | None = None,
    ):
        AbstractProfile.__init__(self)
        ABC.__init__(self)
        self.legal_min_length = legal_min_length
        self.legal_max_length = legal_max_length
        self.legal_min_cost = legal_min_cost
        self.legal_max_cost = legal_max_cost

    def approval_scores(self) -> dict[Project, int]:
        """
        Returns the approval score of all the projects as a dictionary. The approval score of a project is the number of
        voters who approves of it.

        Returns
        -------
            int
                The approval score.
        """
        approval_scores = defaultdict(int)
        for ballot in self:
            for project in ballot:
                approval_scores[project] += self.multiplicity(ballot)
        return dict(approval_scores)

    def approval_score(self, project: Project) -> int:
        """
        Returns the approval score of a project, that is, the number of voters who approves of it.

        Parameters
        ----------
            project : :py:class:`~pabutools.election.instance.Project`
                The project.
        Returns
        -------
            int
                The approval score.
        """
        approval_score = 0
        for ballot in self:
            if project in ballot:
                approval_score += self.multiplicity(ballot)
        return approval_score

    def approved_projects(self) -> set[Project]:
        """
        Returns the set of all the projects approved by at least one voter.

        Returns
        -------
            set[:py:class:`~pabutools.election.instance.Project`]
                The set of projects with at least one supporter.
        """
        approved_projects = set()
        for ballot in self:
            approved_projects.update(ballot)
        return approved_projects

    def is_trivial(self) -> bool:
        """
        Tests if the profile is trivial, meaning that all projects that are approved by at least one voter have a cost
        that exceeds the budget limit.

        Returns
        -------
            bool
                `True` if the profile is trivial, and `False` otherwise.
        """
        return all(
            project.cost > self.instance.budget_limit
            for project in self.approved_projects()
        )

    def is_party_list(self) -> bool:
        """
        Checks whether the profile is a party-list profile.
        In a party-list profile all approval sets are either disjoint or equal.

        Returns
        -------
            bool
                `True` if the profile is party-list and `False` otherwise.
        """
        return all(len(b1 & b2) in (0, len(b1)) for b1 in self for b2 in self)


class ApprovalProfile(Profile, AbstractApprovalProfile):
    """
    A profile of approval ballots, that is, a list of approval ballots per voters. See the class
    :py:class:`~pabutools.election.ballot.approvalballot.ApprovalBallot` for more details on approval ballots.
    This class inherits from the Python `list` class and can thus be used as one.

    Parameters
    ----------
        init : Iterable[:py:class:`~pabutools.election.ballot.approvalballot.ApprovalBallot`], optional
            An iterable of :py:class:`~pabutools.election.ballot.approvalballot.ApprovalBallot` that is used an
            initializer for the list. If activated, the types of the ballots are validated. In case an
            :py:class:`~pabutools.election.profile.profile.AbstractProfile` object is passed, the
            additional attributes are also copied (except if the corresponding keyword arguments have been given).
        instance : :py:class:`~pabutools.election.instance.Instance`, optional
            The instance related to the profile.
            Defaults to `Instance()`.
        ballot_validation : bool, optional
            Boolean indicating whether ballots should be validated before being added to the profile.
            Defaults to `True`.
        ballot_type : type[:py:class:`~pabutools.election.ballot.ballot.AbstractBallot`], optional
            The type that the ballots are validated against. If `ballot_validation` is `True` and a ballot of a type
            that is not a subclass of `ballot_type` is added, an exception will be raised.
            Defaults to `ApprovalBallot`.
        legal_min_length : int, optional
            The minimum length of an approval ballot per the rules of the election.
            Defaults to `None`.
        legal_max_length : int, optional
            The maximum length of an approval ballot per the rules of the election.
            Defaults to `None`.
        legal_min_cost : Numeric, optional
            The minimum total cost of an approval ballot per the rules of the election.
            Defaults to `None`.
        legal_max_cost : Numeric, optional
            The maximum total cost of an approval ballot per the rules of the election.
            Defaults to `None`.

    Attributes
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance related to the profile.
        ballot_validation : bool
            Boolean indicating whether ballots should be validated before being added to the profile.
        ballot_type : type[:py:class:`~pabutools.election.ballot.ballot.AbstractBallot`]
            The type that the ballots are validated against. If `ballot_validation` is `True` and a ballot of a type
            that is not a subclass of `ballot_type` is added, an exception will be raised.
        legal_min_length : int
            The minimum length of an approval ballot per the rules of the election.
        legal_max_length : int
            The maximum length of an approval ballot per the rules of the election.
        legal_min_cost : Numeric
            The minimum total cost of an approval ballot per the rules of the election.
        legal_max_cost : Numeric
            The maximum total cost of an approval ballot per the rules of the election.
    """

    def __init__(
        self,
        init: Iterable[ApprovalBallot] = (),
        instance: Instance | None = None,
        ballot_validation: bool | None = None,
        ballot_type: type[AbstractBallot] | None = None,
        legal_min_length: int | None = None,
        legal_max_length: int | None = None,
        legal_min_cost: Numeric | None = None,
        legal_max_cost: Numeric | None = None,
    ) -> None:
        if legal_min_length is None and isinstance(init, AbstractApprovalProfile):
            legal_min_length = init.legal_min_length
        if legal_max_length is None and isinstance(init, AbstractApprovalProfile):
            legal_max_length = init.legal_max_length
        if legal_min_cost is None and isinstance(init, AbstractApprovalProfile):
            legal_min_cost = init.legal_min_cost
        if legal_max_cost is None and isinstance(init, AbstractApprovalProfile):
            legal_max_cost = init.legal_max_cost
        AbstractApprovalProfile.__init__(
            self,
            legal_min_length=legal_min_length,
            legal_max_length=legal_max_length,
            legal_min_cost=legal_min_cost,
            legal_max_cost=legal_max_cost,
        )
        if ballot_validation is None:
            if isinstance(init, AbstractProfile):
                ballot_validation = init.ballot_validation
            else:
                ballot_validation = True
        if ballot_type is None:
            if isinstance(init, AbstractProfile):
                ballot_type = init.ballot_type
            else:
                ballot_type = ApprovalBallot
        if instance is None and isinstance(init, AbstractApprovalProfile):
            instance = init.instance
        Profile.__init__(
            self,
            init=init,
            instance=instance,
            ballot_validation=ballot_validation,
            ballot_type=ballot_type,
        )

    def as_multiprofile(self):
        """
        Converts the profile into a :py:class:`~pabutools.election.profile.approvalprofile.ApprovalMultiProfile`.

        Returns
        -------
            :py:class:`~pabutools.election.profile.approvalprofile.ApprovalMultiProfile`
                The multiprofile corresponding to the profile.
        """

        return ApprovalMultiProfile(
            instance=self.instance,
            profile=self,
            ballot_validation=self.ballot_validation,
            ballot_type=FrozenApprovalBallot,
            legal_min_length=self.legal_min_length,
            legal_max_length=self.legal_max_length,
            legal_min_cost=self.legal_min_cost,
            legal_max_cost=self.legal_max_cost,
        )

    @classmethod
    def _wrap_methods(cls, names):
        def wrap_method_closure(name):
            def inner(self, *args):
                result = getattr(super(cls, self), name)(*args)
                if isinstance(result, list) and not isinstance(result, cls):
                    result = cls(
                        result,
                        instance=self.instance,
                        ballot_validation=self.ballot_validation,
                        ballot_type=self.ballot_type,
                        legal_min_length=self.legal_min_length,
                        legal_max_length=self.legal_max_length,
                        legal_min_cost=self.legal_min_cost,
                        legal_max_cost=self.legal_max_cost,
                    )
                return result

            inner.fn_name = name
            setattr(cls, name, inner)

        for n in names:
            wrap_method_closure(n)


ApprovalProfile._wrap_methods(
    [
        "__add__",
        "__iadd__",
        "__imul__",
        "__mul__",
        "__reversed__",
        "__rmul__",
        "copy",
        "reverse",
        "__getitem__",
    ]
)


def get_random_approval_profile(instance: Instance, num_agents: int) -> ApprovalProfile:
    """
    Generates a random approval profile in which approval ballots are such that each project is approved with
    probability 0.5.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance the profile is defined with respect to.
        num_agents : int
            The length of the profile, i.e., the number of agents.

    Returns
    -------
        :py:class:`~pabutools.election.profile.approvalprofile.ApprovalProfile`
            The randomly generated profile.
    """
    profile = ApprovalProfile(instance=instance)
    sorted_instance: list[Project] = sorted(instance)
    for i in range(num_agents):
        profile.append(
            get_random_approval_ballot(sorted_instance, name="RandomAppBallot {}".format(i))
        )
    return profile


def get_all_approval_profiles(
    instance: Instance, num_agents: int
) -> Generator[ApprovalProfile]:
    """
    Returns a generator over all the possible profile for a given instance of a given length.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance the profile is defined with respect to.
        num_agents : int
            The length of the profile, i.e., the number of agents.

    Returns
    -------
        Generator[Iterable[:py:class:`~pabutools.election.instance.Project`]]
            Generator over subsets of projects.
    """
    for p in product(powerset(instance), repeat=num_agents):
        yield ApprovalProfile([ApprovalBallot(b) for b in p], instance=instance)


class ApprovalMultiProfile(MultiProfile, AbstractApprovalProfile):
    """
    A multiprofile of approval ballots, that is, a multiset of approval ballots together with their multiplicity.
    Ballots needs to be hashable, so the class
    :py:class:`~pabutools.election.ballot.approvalballot.FrozenApprovalBallot` should be used by default here.
    This class inherits from the Python `Counter` class and can thus be used as one.

    Parameters
    ----------
        init : Iterable[:py:class:`~pabutools.election.ballot.approvalballot.FrozenApprovalBallot`], optional
            An iterable of :py:class:`~pabutools.election.ballot.approvalballot.FrozenApprovalBallot` that is used an
            initializer for the counter. If activated, the types of the ballots are validated. In case an
            :py:class:`~pabutools.election.profile.profile.AbstractProfile` object is passed, the
            additional attributes are also copied (except if the corresponding keyword arguments have been given).
        instance : :py:class:`~pabutools.election.instance.Instance`, optional
            The instance related to the profile.
            Defaults to `Instance()`.
        ballot_validation : bool, optional
            Boolean indicating whether ballots should be validated before being added to the profile.
            Defaults to `True`.
        ballot_type : type[:py:class:`~pabutools.election.ballot.ballot.AbstractBallot`], optional
            The type that the ballots are validated against. If `ballot_validation` is `True` and a ballot of a type
            that is not a subclass of `ballot_type` is added, an exception will be raised.
            Defaults to `FrozenApprovalBallot`.
        profile: :py:class:`~pabutools.election.profile.approvalprofile.ApprovalProfile`, optional
            A profile used to initialise the multiprofile. Some metadata are taken from the profile if they are not
            specified in the constructor.
        legal_min_length : int, optional
            The minimum length of an approval ballot per the rules of the election.
            Defaults to `None`.
        legal_max_length : int, optional
            The maximum length of an approval ballot per the rules of the election.
            Defaults to `None`.
        legal_min_cost : Numeric, optional
            The minimum total cost of an approval ballot per the rules of the election.
            Defaults to `None`.
        legal_max_cost : Numeric, optional
            The maximum total cost of an approval ballot per the rules of the election.
            Defaults to `None`.

    Attributes
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance related to the profile.
        ballot_validation : bool
            Boolean indicating whether ballots should be validated before being added to the profile.
        ballot_type : type[:py:class:`~pabutools.election.ballot.ballot.AbstractBallot`]
            The type that the ballots are validated against. If `ballot_validation` is `True` and a ballot of a type
            that is not a subclass of `ballot_type` is added, an exception will be raised.
        legal_min_length : int
            The minimum length of an approval ballot per the rules of the election.
        legal_max_length : int
            The maximum length of an approval ballot per the rules of the election.
        legal_min_cost : Numeric
            The minimum total cost of an approval ballot per the rules of the election.
        legal_max_cost : Numeric
            The maximum total cost of an approval ballot per the rules of the election.
    """

    def __init__(
        self,
        init: Iterable[FrozenApprovalBallot] = (),
        instance: Instance | None = None,
        ballot_validation: bool | None = None,
        ballot_type: type[FrozenBallot] | None = None,
        profile: ApprovalProfile | None = None,
        legal_min_length: int | None = None,
        legal_max_length: int | None = None,
        legal_min_cost: Numeric | None = None,
        legal_max_cost: Numeric | None = None,
    ):
        if legal_min_length is None:
            if isinstance(init, AbstractApprovalProfile):
                legal_min_length = init.legal_min_length
            elif profile:
                legal_min_length = profile.legal_min_length
        if legal_max_length is None:
            if isinstance(init, AbstractApprovalProfile):
                legal_max_length = init.legal_max_length
            elif profile:
                legal_max_length = profile.legal_max_length
        if legal_min_cost is None:
            if isinstance(init, AbstractApprovalProfile):
                legal_min_cost = init.legal_min_cost
            elif profile:
                legal_min_cost = profile.legal_min_cost
        if legal_max_cost is None:
            if isinstance(init, AbstractApprovalProfile):
                legal_max_cost = init.legal_max_cost
            elif profile:
                legal_max_cost = profile.legal_max_cost
        AbstractApprovalProfile.__init__(
            self,
            legal_min_length=legal_min_length,
            legal_max_length=legal_max_length,
            legal_min_cost=legal_min_cost,
            legal_max_cost=legal_max_cost,
        )
        if ballot_validation is None:
            if isinstance(init, AbstractProfile):
                ballot_validation = init.ballot_validation
            else:
                ballot_validation = True
        if ballot_type is None:
            if isinstance(init, AbstractProfile):
                ballot_type = init.ballot_type
            else:
                ballot_type = FrozenApprovalBallot
        if instance is None:
            if isinstance(init, AbstractApprovalProfile):
                instance = init.instance
            elif profile:
                instance = profile.instance
        MultiProfile.__init__(
            self,
            init=init,
            instance=instance,
            ballot_validation=ballot_validation,
            ballot_type=ballot_type,
        )
        if profile is not None:
            self.extend(profile)

    @classmethod
    def _wrap_methods(cls, names):
        def wrap_method_closure(name):
            def inner(self, *args):
                result = getattr(super(cls, self), name)(*args)
                if isinstance(result, dict) and not isinstance(result, cls):
                    result = cls(
                        result,
                        instance=self.instance,
                        ballot_validation=self.ballot_validation,
                        ballot_type=self.ballot_type,
                        legal_min_length=self.legal_min_length,
                        legal_max_length=self.legal_max_length,
                        legal_min_cost=self.legal_min_cost,
                        legal_max_cost=self.legal_max_cost,
                    )
                return result

            inner.fn_name = name
            setattr(cls, name, inner)

        for n in names:
            wrap_method_closure(n)

    def __reduce__(self):
        return self.__class__, (
            dict(self),
            self.instance,
            self.ballot_validation,
            self.ballot_type,
            None,
            self.legal_min_length,
            self.legal_max_length,
            self.legal_min_cost,
            self.legal_max_cost,
        )


ApprovalMultiProfile._wrap_methods(
    [
        "__add__",
        "__and__",
        "__iadd__",
        "__iand__",
        "__ior__",
        "__isub__",
        "__imul__",
        "__mul__",
        "__or__",
        "__ror__",
        "__sub__",
        "copy",
    ]
)
