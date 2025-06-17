"""
Module for relaxation of the stable-priceability constraint.
"""

from __future__ import annotations

import collections
import warnings
from abc import ABC, abstractmethod
from numbers import Real

from pabutools.election import (
    Instance,
    Profile,
    Project,
)

try:
    from mip import Model, xsum, minimize
except ImportError:
    raise ImportError(
        "The priceability functions need the python-mip package. This is no longer listed as a requirement as we are "
        "slowly moving to PuLP for Python 3.13 compatibility. If you are using Python < 3.13, install manually the "
        "python-mip package. If you are using Python 3.13, please help us translate this file to PuLP."
    )


warnings.warn("The priceability modules based on python-mip are deprecated. Please use the new ones based "
              "on pulp.", DeprecationWarning)

class Relaxation(ABC):
    """
    Base class for stable-priceability condition relaxation methods.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            An instance the relaxation is operating on.
        profile : :py:class:`~pabutools.election.profile.profile.Profile`
            A profile the relaxation is operating on.

    Attributes
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            An instance the relaxation is operating on.
        profile : :py:class:`~pabutools.election.profile.profile.Profile`
            A profile the relaxation is operating on.

    """

    def __init__(self, instance: Instance, profile: Profile):
        self.instance = self.C = instance
        self.profile = self.N = profile
        self.INF = instance.budget_limit * 10
        self._saved_beta = None

    @abstractmethod
    def add_beta(self, mip_model: Model) -> None:
        """
        Add beta variable to the model.

        Parameters
        ----------
            mip_model : Model
                The stable-priceability MIP model.
        """

    @abstractmethod
    def add_objective(self, mip_model: Model) -> None:
        """
        Add objective function to the model.

        Parameters
        ----------
            mip_model : Model
                The stable-priceability MIP model.
        """

    @abstractmethod
    def add_stability_constraint(self, mip_model: Model) -> None:
        """
        Add relaxed stability constraint to the model.

        Parameters
        ----------
            mip_model : Model
                The stable-priceability MIP model.
        """

    @abstractmethod
    def get_beta(self, mip_model: Model) -> Real | dict:
        """
        Get the value of beta from the model.
        This method implicitly saves internally the value of beta variable from `mip_model`.

        Parameters
        ----------
            mip_model : Model
                The stable-priceability MIP model.

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

    def add_beta(self, mip_model: Model) -> None:
        mip_model.add_var(name="beta")

    def add_objective(self, mip_model: Model) -> None:
        beta = mip_model.var_by_name(name="beta")
        mip_model.objective = minimize(beta)

    def add_stability_constraint(self, mip_model: Model) -> None:
        x_vars = {c: mip_model.var_by_name(name=f"x_{c.name}") for c in self.C}
        m_vars = [
            mip_model.var_by_name(name=f"m_{idx}") for idx, _ in enumerate(self.N)
        ]
        beta = mip_model.var_by_name(name="beta")
        for c in self.C:
            mip_model += (
                xsum(m_vars[idx] for idx, i in enumerate(self.N) if c in i)
                <= c.cost * beta + x_vars[c] * self.INF
            )

    def get_beta(self, mip_model: Model) -> Real | dict:
        beta = mip_model.var_by_name(name="beta")
        self._saved_beta = beta.x
        return self._saved_beta

    def get_relaxed_cost(self, project: Project) -> float:
        return project.cost * self._saved_beta


class MinAdd(Relaxation):
    """
    A beta in (-inf, inf) is added to the right-hand side of the condition.
    The objective function minimizes beta.
    """

    def add_beta(self, mip_model: Model) -> None:
        mip_model.add_var(name="beta", lb=-self.INF)

    def add_objective(self, mip_model: Model) -> None:
        beta = mip_model.var_by_name(name="beta")
        mip_model.objective = minimize(beta)

    def add_stability_constraint(self, mip_model: Model) -> None:
        x_vars = {c: mip_model.var_by_name(name=f"x_{c.name}") for c in self.C}
        m_vars = [
            mip_model.var_by_name(name=f"m_{idx}") for idx, _ in enumerate(self.N)
        ]
        beta = mip_model.var_by_name(name="beta")
        for c in self.C:
            mip_model += (
                xsum(m_vars[idx] for idx, i in enumerate(self.N) if c in i)
                <= c.cost + beta + x_vars[c] * self.INF
            )

    def get_beta(self, mip_model: Model) -> Real | dict:
        beta = mip_model.var_by_name(name="beta")
        self._saved_beta = beta.x
        return self._saved_beta

    def get_relaxed_cost(self, project: Project) -> float:
        return project.cost + self._saved_beta


class MinAddVector(Relaxation):
    """
    A separate beta[c] in (-inf, inf) for each project c is added to the right-hand side of the condition.
    The objective function minimizes the sum of beta[c] for each project c.
    """

    def add_beta(self, mip_model: Model) -> None:
        beta = {
            c: mip_model.add_var(name=f"beta_{c.name}", lb=-self.INF) for c in self.C
        }
        x_vars = {c: mip_model.var_by_name(name=f"x_{c.name}") for c in self.C}
        # beta[c] is zero for selected
        for c in self.C:
            mip_model += beta[c] <= (1 - x_vars[c]) * self.instance.budget_limit
            mip_model += (x_vars[c] - 1) * self.instance.budget_limit <= beta[c]

    def add_objective(self, mip_model: Model) -> None:
        beta = {c: mip_model.var_by_name(name=f"beta_{c.name}") for c in self.C}
        mip_model.objective = minimize(xsum(beta[c] for c in self.C))

    def add_stability_constraint(self, mip_model: Model) -> None:
        x_vars = {c: mip_model.var_by_name(name=f"x_{c.name}") for c in self.C}
        m_vars = [
            mip_model.var_by_name(name=f"m_{idx}") for idx, _ in enumerate(self.N)
        ]
        beta = {c: mip_model.var_by_name(name=f"beta_{c.name}") for c in self.C}
        for c in self.C:
            mip_model += (
                xsum(m_vars[idx] for idx, i in enumerate(self.N) if c in i)
                <= c.cost + beta[c] + x_vars[c] * self.INF
            )

    def get_beta(self, mip_model: Model) -> Real | dict:
        beta = {c: mip_model.var_by_name(name=f"beta_{c.name}") for c in self.C}
        return_beta = collections.defaultdict(int)
        for c in self.C:
            if beta[c].x:
                return_beta[c] = beta[c].x
        self._saved_beta = {"beta": return_beta, "sum": sum(return_beta.values())}
        return self._saved_beta

    def get_relaxed_cost(self, project: Project) -> float:
        return project.cost + self._saved_beta["beta"][project]


class MinAddVectorPositive(MinAddVector):
    """
    A separate beta[c] in [0, inf) for each project c is added to the right-hand side of the condition.
    The objective function minimizes the sum of beta[c] for each project c.
    """

    def add_beta(self, mip_model: Model) -> None:
        _beta = {c: mip_model.add_var(name=f"beta_{c.name}") for c in self.C}


class MinAddOffset(Relaxation):
    """
    A mixture of `MinAdd` and `MinAddVector` relaxation methods.
    A separate beta[c] in [0, inf) for each project c is added to the right-hand side of the condition.
    The sum of beta[c] for each project c is in [0, 0.025 * instance.budget_limit].
    Additionally, a global beta in (-inf, inf) is added to the right-hand side of the condition.
    The objective function minimizes the global beta.
    """

    BUDGET_FRACTION = 0.025

    def add_beta(self, mip_model: Model) -> None:
        _beta_global = mip_model.add_var(name="beta", lb=-self.INF)
        beta = {c: mip_model.add_var(name=f"beta_{c.name}") for c in self.C}
        mip_model += (
            xsum(beta[c] for c in self.C)
            <= self.BUDGET_FRACTION * self.instance.budget_limit
        )

    def add_objective(self, mip_model: Model) -> None:
        beta_global = mip_model.var_by_name(name="beta")
        mip_model.objective = minimize(beta_global)

    def add_stability_constraint(self, mip_model: Model) -> None:
        x_vars = {c: mip_model.var_by_name(name=f"x_{c.name}") for c in self.C}
        m_vars = [
            mip_model.var_by_name(name=f"m_{idx}") for idx, _ in enumerate(self.N)
        ]
        beta_global = mip_model.var_by_name(name="beta")
        beta = {c: mip_model.var_by_name(name=f"beta_{c.name}") for c in self.C}
        for c in self.C:
            mip_model += (
                xsum(m_vars[idx] for idx, i in enumerate(self.N) if c in i)
                <= c.cost + beta_global + beta[c] + x_vars[c] * self.INF
            )

    def get_beta(self, mip_model: Model) -> Real | dict:
        beta_global = mip_model.var_by_name(name="beta")
        beta = {c: mip_model.var_by_name(name=f"beta_{c.name}") for c in self.C}
        return_beta = collections.defaultdict(int)
        for c in self.C:
            if beta[c].x:
                return_beta[c] = beta[c].x
        self._saved_beta = {
            "beta": return_beta,
            "beta_global": beta_global.x,
            "sum": sum(return_beta.values()),
        }
        return self._saved_beta

    def get_relaxed_cost(self, project: Project) -> float:
        return (
            project.cost
            + self._saved_beta["beta_global"]
            + self._saved_beta["beta"][project]
        )
