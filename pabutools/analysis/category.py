from collections.abc import Collection

from pabutools.utils import Numeric

import numpy as np

from pabutools.election import AbstractApprovalProfile, Instance, Project


def category_proportionality(
    instance: Instance,
    profile: AbstractApprovalProfile,
    budget_allocation: Collection[Project],
) -> Numeric:
    """
    Computes the difference between the cost allocated per category, and that existing in the profile. More
    specifically, for each category (an error is raised if not category are specified) we compute the amount of money
    dedicated to projects from the category in the budget allocation; together with the amount of money allocated to
    the category in the ballots of the voters. For each category, the average between these two scores is raised to the
    power 2, the global average over all categories is then considered, and we return the exponential of minus that
    value.

    It mostly makes sense for approval ballots, though any profile of ballots supporting the `in` operator can be used.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        budget_allocation : Iterable[:py:class:`~pabutools.election.instance.Project`]
            The selected collection of projects.

    Returns
    -------
        Numeric
            The score for the category proportionality.

    """
    categories = list(instance.categories)
    if len(categories) == 0:
        raise ValueError(
            "Category proportionality can only be computed for instances with categories."
        )
    if len(budget_allocation) == 0:
        return 0

    proportional_allocated_cost_per_category = {
        category: 0.0 for category in categories
    }
    allocated_cost_per_category = {category: 0.0 for category in categories}
    allocated_total_cost = 0.0
    for project in budget_allocation:
        allocated_total_cost += project.cost
        for category in project.categories:
            allocated_cost_per_category[category] += project.cost
    for category in categories:
        proportional_allocated_cost_per_category[category] = (
            allocated_cost_per_category[category] / allocated_total_cost
        )

    proportional_app_cost_per_category = {category: 0.0 for category in categories}
    for ballot in profile:
        app_cost_per_category = {category: 0.0 for category in categories}
        app_total_cost = 0.0
        for project in ballot:
            app_total_cost += project.cost
            for category in project.categories:
                app_cost_per_category[category] += project.cost
        if app_total_cost == 0:
            raise ValueError(
                "Category proportionality can only be computed for instances with at least one non-empty ballot."
            )
        for category in categories:
            proportional_app_cost_per_category[category] += (
                app_cost_per_category[category]
                / app_total_cost
                * profile.multiplicity(ballot)
            )
    for category in categories:
        proportional_app_cost_per_category[category] /= profile.num_ballots()

    mean_square_diff = 0.0
    for category in categories:
        mean_square_diff += (
            proportional_allocated_cost_per_category[category]
            - proportional_app_cost_per_category[category]
        ) ** 2
    mean_square_diff /= len(categories)

    return np.exp(-float(mean_square_diff))
