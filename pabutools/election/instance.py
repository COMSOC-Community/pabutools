"""
Module defining the basic classes used to represent a participatory budgeting election.
The :py:class:`~pabutools.election.instance.Project` and the
:py:class:`~pabutools.election.instance.Instance` classes are defined here.
"""

from __future__ import annotations

from collections.abc import Collection, Generator

from pulp import LpProblem, LpMaximize, LpVariable, LpBinary, lpSum, PULP_CBC_CMD, LpStatusOptimal, value

from pabutools.utils import Numeric

from pabutools.fractions import frac
from pabutools.utils import powerset

from math import ceil

import random


class Project:
    """
    Represents a project, that is, the entity that is voted upon in a participatory budgeting election.

    Parameters
    ----------
        name : str, optional
            The name of the project. This is used as the identifier of a project. It should be unique with a collection
            of projects, though this is not enforced.
            Defaults to `""`.
        cost : Numeric, optional
            The cost of the project.
            Defaults to `0`.
        categories: set[str], optional
            The categories that the project is a member of. These categories can  "Urban greenery" or "Public
            transport" for instance.
            Defaults to `{}`.
        targets: set[str], optional
            The target groups that the project is targeting. These can be "Citizens above 60 years old" or
            "Residents of district A" for instance.
            Defaults to `{}`.

    Attributes
    ----------
        name : str
            The name of the project. This is used as the identifier of a project. It should be unique with a collection
            of projects, though this is not enforced.
        cost : Numeric
            The cost of the project.
        categories: set[str]
            The categories that the project is a member of. These categories can  "Urban greenery" or "Public
            transport" for instance.
        targets: set[str]
            The target groups that the project is targeting. These can be "Citizens above 60 years old" or
            "Residents of district A" for instance.
    """

    def __str__(self) -> str:
        return str(self.name)

    def __repr__(self) -> str:
        return self.__str__()

    def __init__(
        self, name: str = "", cost: Numeric = 0, categories=None, targets=None
    ) -> None:
        if targets is None:
            targets = {}
        if categories is None:
            categories = {}
        self.name = name
        if not int(cost) == cost:
            cost = frac(cost)  # float costs do not work, enforce fractions
        else:
            cost = int(cost)
        self.cost = cost
        self.categories = categories
        self.targets = targets

    def __eq__(self, other) -> bool:
        if isinstance(other, Project):
            return self.name == other.name
        if isinstance(other, str):
            return self.name == other
        return False

    def __le__(self, other) -> bool:
        if isinstance(other, Project):
            return self.name.__le__(other.name)
        if isinstance(other, str):
            return self.name.__le__(other)
        return False

    def __lt__(self, other) -> bool:
        if isinstance(other, Project):
            return self.name.__lt__(other.name)
        if isinstance(other, str):
            return self.name.__lt__(other)
        return False

    def __hash__(self) -> int:
        return hash(self.name)


def total_cost(projects: Collection[Project]) -> Numeric:
    """
    Returns the total cost of a collection of projects, summing the cost of the projects.

    Parameters
    ----------
        projects : iterable[:py:class:`~pabutools.election.instance.Project`]
            An iterable of projects.

    Returns
    -------
        Numeric
            The total cost
    """
    return sum(p.cost for p in projects)


def max_budget_allocation_cardinality(
    projects: Collection[Project], budget_limit: Numeric
) -> int:
    """
    Returns the maximum number of projects that can be chosen with respect to the budget limit.

    Parameters
    ----------
        projects : iterable[:py:class:`~pabutools.election.instance.Project`]
            An iterable of projects.
        budget_limit : Numeric
            the budget limit

    Returns
    -------
        int
            The maximum number of projects that can be chosen with respect to the budget limit.

    """
    projects_sorted = sorted(projects, key=lambda proj: proj.cost)
    cost = 0
    selected = 0
    for p in projects_sorted:
        new_total_cost = p.cost + cost
        if new_total_cost > budget_limit:
            break
        cost = new_total_cost
        selected += 1
    return selected


def max_budget_allocation_cost(
    projects: Collection[Project], budget_limit: Numeric
) -> Numeric:
    """
    Returns the maximum total cost over all subsets of projects with respect to the budget limit.

    Parameters
    ----------
        projects : iterable[:py:class:`~pabutools.election.instance.Project`]
            An iterable of projects.
        budget_limit : Numeric
            the budget limit

    Returns
    -------
        int
            The maximum total cost over all subsets of projects with respect to the budget limit.

    """
    mip_model = LpProblem("MaxCostAllocation", LpMaximize)

    p_vars = {p: LpVariable(f"x_{p}", cat=LpBinary) for p in projects}

    if not p_vars:
        return 0

    # Objective: maximize total cost of selected projects
    mip_model += lpSum(p_vars[p] * p.cost for p in projects)

    # Budget constraint
    mip_model += lpSum(p_vars[p] * p.cost for p in projects) <= budget_limit

    # Solve the model
    mip_model.solve(PULP_CBC_CMD(msg=False))

    if mip_model.status == LpStatusOptimal:
        max_cost = value(mip_model.objective)
        return frac(float(max_cost))


class Instance(set[Project]):
    """
    Participatory budgeting instances.
    An instance contains the projects that are voted on, together with other information about the election such as the
    budget limit.
    Importantly, the ballots submitted by the voters is not part of the instance.
    See the module :py:mod:`~pabutools.election.profile` for how to handle the voters.
    Note that `Instance` is a subclass of the Python class `set`, and can be used as a set is.

    Parameters
    ----------
        init: Iterable[:py:class:`~pabutools.election.instance.Project`], optional
            An iterable of :py:class:`~pabutools.election.instance.Project` that constitutes the initial set of projects
            for the instance. In case an :py:class:`~pabutools.election.instance.Instance` object is passed, the
            additional attributes are also copied (except if the corresponding keyword arguments have been given).
        budget_limit : Numeric, optional
            The budget limit of the instance, that is, the maximum amount of money a set of projects can use to be
            feasible.
        categories: set[str], optional
            The set of categories that the projects can be assigned to. These can be "Urban greenery" or "Public
            transport" for instance.
            Defaults to `{}`.
        targets: set[str], optional
            The set of target groups that the project can be targeting. These can be "Citizens above 60 years old" or
            "Residents of district A" for instance.
            Defaults to `{}`.
        file_path : str, optional
            If the instance has been parsed from a file, the path to the file.
            Defaults to `""`.
        file_name : str, optional
            If the instance has been parsed from a file, the name of the file.
            Defaults to `""`.
        parsing_errors : bool, optional
            Boolean indicating if errors were encountered when parsing the file.
            Defaults to `None`.
        meta : dict, optional
            All kinds of relevant information for the instance, stored in a dictionary. Keys and values are
            typically strings.
            Defaults to `dict()`.
        project_meta : dict[:py:class:`~pabutools.election.instance.Project`, dict], optional
            All kinds of relevant information about the projects, stored in a dictionary. Keys are
            :py:class:`~pabutools.election.instance.Project` and values are dictionaries.
            Defaults to `dict()`.


    Attributes
    ----------
        budget_limit : Numeric
            The budget limit of the instance, that is, the maximum amount of money a set of projects can use to be
            feasible.
        categories: set[str]
            The set of categories that the projects can be assigned to. These can be "Urban greenery" or "Public
            transport" for instance.
        targets: set[str]
            The set of target groups that the project can be targeting. These can be "Citizens above 60 years old" or
            "Residents of district A" for instance.
        file_path : str
            If the instance has been parsed from a file, the path to the file.
        file_name : str
            If the instance has been parsed from a file, the name of the file.
        parsing_errors : bool
            Boolean indicating if errors were encountered when parsing the file.
        meta : dict
            All kinds of relevant information for the instance, stored in a dictionary. Keys and values are
            typically strings.
        project_meta : dict[:py:class:`~pabutools.election.instance.Project`: dict]
            All kinds of relevant information about the projects, stored in a dictionary. Keys are
            :py:class:`~pabutools.election.instance.Project` and values are dictionaries.
    """

    def __init__(
        self,
        init: Collection[Project] = (),
        budget_limit: Numeric | None = None,
        categories: set[str] | None = None,
        targets: set[str] | None = None,
        file_path: str | None = None,
        file_name: str | None = None,
        parsing_errors: bool | None = None,
        meta: dict | None = None,
        project_meta: dict | None = None,
    ) -> None:
        set.__init__(self, init)

        self.budget_limit: Numeric = (
            0  # Only for type checking, so that init.budget_limit does not fail
        )
        if budget_limit is None:
            if isinstance(init, Instance):
                budget_limit = init.budget_limit
            else:
                budget_limit = 0
        self.budget_limit = budget_limit

        self.categories = (
            None  # Only for type checking, so that init.categories does not fail
        )
        if categories is None:
            if isinstance(init, Instance):
                categories = init.categories
            else:
                categories = set()
        self.categories = categories

        self.targets = (
            None  # Only for type checking, so that init.targets does not fail
        )
        if targets is None:
            if isinstance(init, Instance):
                targets = init.targets
            else:
                targets = set()
        self.targets = targets

        self.file_path = (
            None  # Only for type checking, so that init.file_path does not fail
        )
        if file_path is None:
            if isinstance(init, Instance):
                file_path = init.file_path
            else:
                file_path = ""
        self.file_path = file_path

        self.file_name = (
            None  # Only for type checking, so that init.file_name does not fail
        )
        if file_name is None:
            if isinstance(init, Instance):
                file_name = init.file_name
            else:
                file_name = ""
        self.file_name = file_name

        self.parsing_errors = (
            None  # Only for type checking, so that init.parsing_errors does not fail
        )
        if parsing_errors is None:
            if isinstance(init, Instance):
                parsing_errors = init.parsing_errors
            else:
                parsing_errors = False
        self.parsing_errors = parsing_errors

        self.meta = None  # Only for type checking, so that init.meta does not fail
        if meta is None:
            if isinstance(init, Instance):
                meta = init.meta
            else:
                meta = dict()
        self.meta = meta

        self.project_meta = (
            None  # Only for type checking, so that init.projet_meta does not fail
        )
        if project_meta is None:
            if isinstance(init, Instance):
                project_meta = init.project_meta
            else:
                project_meta = dict()
        self.project_meta = project_meta

    def get_project(self, project_name: str) -> Project:
        """
        Iterates over the instance to find a project with the given name. If found, the project is returned, otherwise
        a `KeyError` exception is raised.

        Returns
        -------
            :py:class:`~pabutools.election.instance.Project`
                The project.
        """
        for p in self:
            if p.name == project_name:
                return p
        raise KeyError(
            "No project with name {} found in the instance.".format(project_name)
        )

    def budget_allocations(self) -> Generator[Collection[Project]]:
        """
        Returns a generator for all the feasible budget allocations of the instance.

        Returns
        -------
            Generator[Iterable[:py:class:`~pabutools.election.instance.Project`]
                The generator.

        """
        for b in powerset(self):
            if self.is_feasible(b):
                yield b

    def is_trivial(self) -> bool:
        """
        Tests if the instance is trivial, meaning that either all projects can be selected without
        exceeding the budget limit, or that no project can be selected.

        Returns
        -------
            bool
                `True` if the instance is trivial, `False` otherwise.
        """
        return (total_cost(self) <= self.budget_limit) or (
            self.budget_limit <= min(p.cost for p in self)
        )

    def is_feasible(self, projects: Collection[Project]) -> bool:
        """
        Tests if a given collection of projects is feasible for the instance, meaning that the total cost of the
        projects does not exceed the budget limit of the instance.

        Parameters
        ----------
            projects : Iterable[:py:class:`~pabutools.election.instance.Project`]
                The collection of projects.
        Returns
        -------
            bool
                `True` if the collection of project cost less than the budget limit, `False` otherwise.
        """
        return total_cost(projects) <= self.budget_limit

    def is_exhaustive(
        self,
        projects: Collection[Project],
        available_projects: Collection[Project] | None = None,
    ) -> bool:
        """
        Tests if a given collection of projects is exhaustive. A collection of projects is said to be exhaustive if no
        additional project could be added without violating the budget limit.
        Note that a collection of projects can be exhaustive, but not feasibility.

        Parameters
        ----------
            projects : Iterable[:py:class:`~pabutools.election.instance.Project`]
                The collection of projects.
            available_projects : Iterable[:py:class:`~pabutools.election.instance.Project`], optional
                Only these projects are considered when testing for exhaustiveness. Defaults to None, i.e., considering
                all projects.
        Returns
        -------
            bool
                `True` if the collection of project is exhaustive, `False` otherwise.
        """
        if available_projects is None:
            available_projects = self
        cost = total_cost(projects)
        for p in available_projects:
            if p not in projects and (p.cost + cost <= self.budget_limit):
                return False
        return True

    def __str__(self) -> str:
        res = "Instance "
        if self.file_name:
            res += "({}) ".format(self.file_name)
        res += "with budget limit {} and {} projects:\n".format(
            self.budget_limit, len(self)
        )
        for p in self:
            res += "\tc({}) = {}\n".format(p, p.cost)
        return res[:-1]

    def __repr__(self) -> str:
        return self.__str__()

    # This allows set method returning copies of a set to work with PBInstances
    @classmethod
    def _wrap_methods(cls, names):
        def wrap_method_closure(name):
            def inner(self, *args):
                result = getattr(super(cls, self), name)(*args)
                if isinstance(result, set) and not isinstance(result, cls):
                    result = cls(
                        result,
                        budget_limit=self.budget_limit,
                        categories=self.categories,
                        targets=self.targets,
                        file_name=self.file_name,
                        file_path=self.file_path,
                        parsing_errors=self.parsing_errors,
                        meta=self.meta,
                        project_meta=self.project_meta,
                    )
                return result

            inner.fn_name = name
            setattr(cls, name, inner)

        for n in names:
            wrap_method_closure(n)


Instance._wrap_methods(
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


def get_random_instance(num_projects: int, min_cost: int, max_cost: int) -> Instance:
    """
    Generates a random instance. Costs and budget limit are integers. The costs are selected uniformly at random between
    `min_cost` and `max_cost`. The budget limit is sample form a uniform between the minimum cost of a project
    and the total cost of all the projects.
    The parameters are rounded up to the closest int.

    Parameters
    ----------
        num_projects : int
            The number of projects in the instance.
        min_cost : int
            The minimum cost of a project.
        max_cost : int
            The maximum cost of a project.
    Returns
    -------
        pabutools.election.instance.Instance
            The randomly-generated instance.
    """
    inst = Instance()
    inst.update(
        Project(
            name=str(p),
            cost=random.randint(round(min_cost), round(max_cost)),
        )
        for p in range(round(num_projects))
    )
    inst.budget_limit = random.randint(
        ceil(min(p.cost for p in inst)), ceil(sum(p.cost for p in inst))
    )
    return inst
