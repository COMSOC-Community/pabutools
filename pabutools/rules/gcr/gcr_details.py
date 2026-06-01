from __future__ import annotations

from dataclasses import dataclass, field

from pabutools.election.instance import Project
from pabutools.rules.budgetallocation import AllocationDetails


@dataclass
class GCRIteration:
    """
    Stores information about a single iteration of the Greedy Cohesive Rule.

    Attributes
    ----------
    beta : int
        The β value of the cohesive group selected in this iteration.
    selected_projects : list[Project]
        The set T of projects added to W in this iteration.
    deactivated_voters : list[int]
        Indices of the voters in N' that were deactivated in this iteration.
    active_voters_remaining : int
        Number of still-active voters after this iteration.
    """

    beta: int
    selected_projects: list[Project]
    deactivated_voters: list[int]
    active_voters_remaining: int


@dataclass
class GCRAllocationDetails(AllocationDetails):
    """
    Stores the full execution trace of the Greedy Cohesive Rule.

    Attributes
    ----------
    iterations : list[GCRIteration]
        One entry per GCR iteration, in order of execution.
    """

    iterations: list[GCRIteration] = field(default_factory=list)
