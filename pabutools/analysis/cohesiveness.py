from __future__ import annotations

import random
from collections.abc import Collection

from pabutools.utils import Numeric

from pabutools.election import (
    Instance,
    AbstractApprovalProfile,
    Project,
    total_cost,
    AbstractCardinalProfile,
    AbstractCardinalBallot,
    AbstractApprovalBallot,
    AbstractProfile,
)
from pabutools.utils import powerset


def is_large_enough(
    group_size: int, num_voters: int, projects_cost: Numeric, budget_limit: Numeric
) -> bool:
    return projects_cost * num_voters <= group_size * budget_limit


def is_cohesive_approval(
    instance: Instance,
    profile: AbstractApprovalProfile,
    projects: Collection[Project],
    ballots: Collection[AbstractApprovalBallot],
) -> bool:
    if not is_large_enough(
        sum(profile.multiplicity(b) for b in ballots),
        profile.num_ballots(),
        total_cost(projects),
        instance.budget_limit,
    ):
        return False
    if len(ballots) == 0 or len(projects) == 0:
        return False
    for ballot in ballots:
        for p in projects:
            if p not in ballot:
                return False
    return True


def is_cohesive_cardinal(
    instance: Instance,
    profile: AbstractCardinalProfile,
    projects: Collection[Project],
    ballots: Collection[AbstractCardinalBallot],
    alpha: dict[Project, Numeric],
) -> bool:
    if not is_large_enough(
        sum(profile.multiplicity(b) for b in ballots),
        profile.num_ballots(),
        total_cost(projects),
        instance.budget_limit,
    ):
        return False
    if len(ballots) == 0 or len(projects) == 0:
        return False
    for ballot in ballots:
        for p in projects:
            if ballot[p] < alpha[p]:
                return False
    return True


def cohesive_groups(
    instance: Instance,
    profile: AbstractProfile,
    projects=None,
    sample_size: int | None = None,
):
    """
    Find (group, project_set) pairs that are cohesive.

    Parameters
    ----------
    instance : Instance
    profile : AbstractProfile
    projects : Collection[Project], optional
        Defaults to all projects in `instance`.
    sample_size : int, optional
        If `None` (default), exhaustively check every (group, project_set)
        pair via `powerset(profile) x powerset(projects)`. If set to an int,
        instead randomly sample that many (group, project_set) pairs — use
        this to keep runtime bounded on large instances, where the
        exhaustive enumeration is exponential in both the number of voters
        and the number of projects.
    """
    if projects is None:
        projects = instance
    projects = list(projects)
    ballots = list(profile)
    res = []

    if sample_size is None:
        group_project_pairs = (
            (group, project_set)
            for group in powerset(profile)
            for project_set in powerset(projects)
        )
    else:
        def _sampled_pairs():
            for _ in range(sample_size):
                group = (
                    random.sample(ballots, random.randint(1, len(ballots)))
                    if ballots
                    else []
                )
                project_set = (
                    random.sample(projects, random.randint(1, len(projects)))
                    if projects
                    else []
                )
                yield group, project_set

        group_project_pairs = _sampled_pairs()

    for group, project_set in group_project_pairs:
        if len(group) > 0 and len(project_set) > 0:
            # This fails for multiprofiles as the multiplicity is not taken into account
            if isinstance(profile, AbstractApprovalProfile):
                if is_cohesive_approval(instance, profile, project_set, group):
                    res.append((group, project_set))
            elif isinstance(profile, AbstractCardinalProfile):
                alpha_min = {p: min(b[p] for b in group) for p in project_set}
                if is_cohesive_cardinal(
                    instance, profile, project_set, group, alpha_min
                ):
                    res.append((group, project_set))
            else:
                raise NotImplementedError(
                    f"We cannot find cohesive groups in a profile of type {type(profile)}. "
                    f"Only approval and cardinal profiles are supported."
                )
    return res


def maximal_cohesive_for_projects_approval(
    instance: Instance, profile: AbstractApprovalProfile, projects: Collection[Project]
) -> list[AbstractApprovalBallot] | None:
    res = []
    for ballot in profile:
        all_in = True
        for p in projects:
            if p not in ballot:
                all_in = False
                break
        if all_in:
            res.append(ballot)
    if len(res) > 0 and is_large_enough(
        len(res), profile.num_ballots(), total_cost(projects), instance.budget_limit
    ):
        return res
    return None


def maximal_cohesive_groups(
    instance: Instance,
    profile: AbstractProfile,
    projects: Collection[Project] | None = None,
):
    if projects is None:
        projects = instance
    res = set()
    for project_set in powerset(projects):
        group = maximal_cohesive_for_projects_approval(instance, profile, project_set)
        if group:
            if isinstance(profile, AbstractApprovalProfile):
                if is_cohesive_approval(instance, profile, project_set, group):
                    res.add((group, project_set))
            else:
                raise NotImplementedError(
                    f"We cannot find maximal cohesive groups in a profile of type "
                    f"{type(profile)}. Only cardinal profiles are supported."
                )
    return res
