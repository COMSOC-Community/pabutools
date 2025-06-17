from __future__ import annotations

from collections import defaultdict
from abc import ABC, abstractmethod
from numbers import Real

from pabutools.election import Instance, Profile, Project

from pulp import LpProblem, LpVariable, lpSum, LpContinuous, value


class Relaxation(ABC):
    """
    Base class for stable-priceability condition relaxation methods.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            An instance the relaxation is operating on.
        profile : :py:class:`~pabutools.election.profile.profile.Profile`
            A profile the relaxation is operating on.
        variables : dict
            A dictionary with variables of the mip model.

    Attributes
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            An instance the relaxation is operating on.
        profile : :py:class:`~pabutools.election.profile.profile.Profile`
            A profile the relaxation is operating on.
        variables : dict
            A dictionary with variables of the mip model.

    """

    def __init__(self, instance: Instance, profile: Profile, variables: dict | None = None):
        self.instance = self.C = instance
        self.profile = self.N = profile
        self.INF = instance.budget_limit * 10
        self._saved_beta = None
        if variables is None:
            self.variables = dict()
        else:
            self.variables = dict(variables)

    @abstractmethod
    def add_beta(self, model: LpProblem) -> None:
        """
        Add beta variable to the model.

        Parameters
        ----------
            model : LpProblem
                The stable-priceability MIP model.
        """

    @abstractmethod
    def add_objective(self, model: LpProblem) -> None:
        """
        Add objective function to the model.

        Parameters
        ----------
            model : LpProblem
                The stable-priceability MIP model.
        """

    @abstractmethod
    def add_stability_constraint(self, model: LpProblem) -> None:
        """
        Add relaxed stability constraint to the model.

        Parameters
        ----------
            model : LpProblem
                The stable-priceability MIP model.
        """

    @abstractmethod
    def get_beta(self) -> Real | dict:
        """
        Get the value of beta from the model.
        This method implicitly saves internally the value of beta variable.

        Returns
        -------
            Real | dict
                The value of beta from the model.

        """

    @abstractmethod
    def get_relaxed_cost(self, project: Project) -> float:
        """
        Get relaxed cost of a project.

        Parameters
        ----------
            project : :py:class:`~pabutools.election.instance.Project`
                The project to get the relaxed cost for.

        Returns
        -------
            float
                Relaxed cost of the project.

        """


class MinMul(Relaxation):
    """
    The right-hand side of the condition is multiplied by a beta in [0, inf).
    The objective function minimizes beta.
    """

    def add_beta(self, model: LpProblem) -> None:
        self.variables["beta"] = LpVariable("beta", lowBound=0, cat=LpContinuous)

    def add_objective(self, model: LpProblem) -> None:
        model += -self.variables["beta"]  # PuLP does not allow for changing optimization sense

    def add_stability_constraint(self, model: LpProblem) -> None:
        x_vars = {c: self.variables[f"x_{c.name}"] for c in self.C}
        m_vars = [
            self.variables[f"m_{idx}"] for idx, _ in enumerate(self.N)
        ]
        beta = self.variables["beta"]

        for c in self.C:
            model += lpSum(m_vars[idx] for idx, i in enumerate(self.N) if c in i) \
                     <= c.cost * beta + x_vars[c] * self.INF

    def get_beta(self) -> Real:
        self._saved_beta = value(self.variables["beta"])
        return self._saved_beta

    def get_relaxed_cost(self, project: Project) -> float:
        return project.cost * self._saved_beta


class MinAdd(Relaxation):
    def add_beta(self, model: LpProblem) -> None:
        self.variables["beta"] = LpVariable("beta", lowBound=-self.INF, cat=LpContinuous)

    def add_objective(self, model: LpProblem) -> None:
        model += -self.variables["beta"]  # PuLP does not allow for changing optimization sense

    def add_stability_constraint(self, model: LpProblem) -> None:
        for c in self.C:
            model += lpSum(self.variables[f"m_{idx}"] for idx, i in enumerate(self.N) if c in i) \
                     <= c.cost + self.variables["beta"] + self.variables[f"x_{c.name}"] * self.INF

    def get_beta(self) -> Real:
        self._saved_beta = value(self.variables["beta"])
        return self._saved_beta

    def get_relaxed_cost(self, project: Project) -> float:
        return project.cost + self._saved_beta


class MinAddVector(Relaxation):
    """
    A separate beta[c] in (-inf, inf) for each project c is added to the right-hand side of the condition.
    The objective function minimizes the sum of beta[c] for each project c.
    """
    def add_beta(self, model: LpProblem) -> None:
        for c in self.C:
            self.variables[f"beta_{c.name}"] = LpVariable(f"beta_{c.name}", lowBound=-self.INF, cat=LpContinuous)
        # beta[c] is zero for selected
        for c in self.C:
            model += self.variables[f"beta_{c.name}"] <= (1 - self.variables[f"x_{c.name}"]) * self.instance.budget_limit
            model += (self.variables[f"x_{c.name}"] - 1) * self.instance.budget_limit <= self.variables["beta"][c]

    def add_objective(self, model: LpProblem) -> None:
        model += -lpSum(self.variables[f"beta_{c.name}"] for c in self.C)

    def add_stability_constraint(self, model: LpProblem) -> None:
        for c in self.C:
            model += lpSum(self.variables[f"m_{idx}"] for idx, i in enumerate(self.N) if c in i) \
                     <= c.cost + self.variables[f"beta_{c.name}"] + self.variables[f"x_{c.name}"] * self.INF

    def get_beta(self) -> dict:
        return_beta = defaultdict(int)
        for c in self.C:
            val = value(self.variables[f"beta_{c.name}"])
            if val:
                return_beta[c] = val
        self._saved_beta = {"beta": return_beta, "sum": sum(return_beta.values())}
        return self._saved_beta

    def get_relaxed_cost(self, project: Project) -> float:
        return project.cost + self._saved_beta["beta"][project]


class MinAddVectorPositive(MinAddVector):
    """
    A separate beta[c] in [0, inf) for each project c is added to the right-hand side of the condition.
    The objective function minimizes the sum of beta[c] for each project c.
    """

    def add_beta(self, model: LpProblem) -> None:
        for c in self.C:
            self.variables[f"beta_{c.name}"] = LpVariable(f"beta_{c.name}", lowBound=0, cat=LpContinuous)


class MinAddOffset(Relaxation):
    BUDGET_FRACTION = 0.025

    def add_beta(self, model: LpProblem) -> None:
        self.variables["beta"] = LpVariable("beta", lowBound=-self.INF, cat=LpContinuous)
        for c in self.C:
            self.variables[f"beta_{c.name}"] = LpVariable(f"beta_{c.name}", lowBound=0, cat=LpContinuous)
        model += lpSum(self.variables[f"beta_{c.name}"] for c in self.C) <= self.BUDGET_FRACTION * self.instance.budget_limit

    def add_objective(self, model: LpProblem) -> None:
        model += -self.variables["beta"]

    def add_stability_constraint(self, model: LpProblem) -> None:
        for c in self.C:
            model += lpSum(self.variables[f"m_{idx}"] for idx, i in enumerate(self.N) if c in i) \
                     <= c.cost + self.variables["beta"] + self.variables[f"beta_{c.name}"] + self.variables[f"x_{c.name}"] * self.INF

    def get_beta(self) -> dict:
        return_beta = defaultdict(int)
        for c in self.C:
            val = value(self.variables[f"beta_{c.name}"])
            if val:
                return_beta[c] = val
        self._saved_beta = {
            "beta": return_beta,
            "beta_global": value(self.variables["beta"]),
            "sum": sum(return_beta.values()),
        }
        return self._saved_beta

    def get_relaxed_cost(self, project: Project) -> float:
        return (
            project.cost
            + self._saved_beta["beta_global"]
            + self._saved_beta["beta"][project]
        )
