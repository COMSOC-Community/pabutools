from pulp import LpProblem, LpMaximize, LpBinary, LpVariable, lpSum, PULP_CBC_CMD, value

from pabutools.election import Instance, AbstractApprovalProfile
from pabutools.fractions import frac
from pabutools.rules import BudgetAllocation
from pabutools.utils import Numeric


def average_distance_to_fair_share(instance: Instance, profile: AbstractApprovalProfile, budget_allocation: BudgetAllocation) -> Numeric:
    """
    Returns the average distance to fair share of the given budget allocation. The distance to fair
    share for a given ballot is defined as the absolute value of `fair share of the ballot - share of the ballot`.
    This is a measure in which 0 is the best and the lower, the better.

     Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        budget_allocation : Iterable[:py:class:`~pabutools.election.instance.Project`]
            Collection of projects.

    Returns
    -------
        Numeric
            The average normalised distance to fair share
    """
    approval_scores = profile.approval_scores()
    project_share = {p: frac(p.cost, approval_scores[p]) for p in instance}

    d = 0
    for ballot in profile:
        ballot_share = sum(project_share[p] for p in ballot if p in budget_allocation)
        ballot_fairshare = min(sum(project_share[p] for p in ballot), frac(instance.budget_limit, profile.num_ballots()))
        d += abs(ballot_share - ballot_fairshare) * profile.multiplicity(ballot)

    return frac(d, profile.num_ballots())


def min_distance_to_fair_share(instance: Instance, profile: AbstractApprovalProfile) -> Numeric:
    """
    Returns the minimum achievable distance to fair share for the given instance and profile. The distance to fair
    share for a given ballot is defined as the absolute value of `fair share of the ballot - share of the ballot`.
    This is a measure in which 0 is the best and the lower the better.

    Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.

    Returns
    -------
        Numeric
            The average normalised distance to fair share
    """
    mip_model = LpProblem("MaxBudgetAllocationScore", LpMaximize)

    p_vars = {p: LpVariable(f"p_{p}", cat=LpBinary) for p in instance}
    share_vars = {i: LpVariable(f"bs_{i}") for i, b in enumerate(profile)}
    share_abs_vars = {i: LpVariable(f"bsabs_{i}") for i, b in enumerate(profile)}

    mip_model += lpSum(share_abs_vars[i] * profile.multiplicity(b) for i, b in enumerate(profile))

    mip_model += lpSum(p_vars[p] * float(p.cost) for p in instance) <= instance.budget_limit

    approval_scores = profile.approval_scores()
    project_share = {p: frac(p.cost, approval_scores[p]) for p in instance}

    for i, ballot in enumerate(profile):
        ballot_fairshare = min(sum(project_share[p] for p in ballot), frac(instance.budget_limit, profile.num_ballots()))

        mip_model += share_vars[i] == lpSum(p_vars[p] * float(project_share[p]) for p in ballot)
        mip_model += share_abs_vars[i] >= share_vars[i] - float(ballot_fairshare)
        mip_model += share_abs_vars[i] >= float(ballot_fairshare) - share_vars[i]

    mip_model.solve(PULP_CBC_CMD(msg=False))

    return value(mip_model.objective)


def average_capped_fair_share_ratio(instance: Instance, profile: AbstractApprovalProfile, budget_allocation: BudgetAllocation) -> Numeric:
    """
    Returns the average capped fair share ratio of the given budget allocation. The capped fair share ratio is defined
    as the min between 1 and the ratio between the share of the ballot and the fair share of the ballot.
    This value is averaged up for all ballots in the profile .

     Parameters
    ----------
        instance : :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile : :py:class:`~pabutools.election.profile.profile.AbstractProfile`
            The profile.
        budget_allocation : Iterable[:py:class:`~pabutools.election.instance.Project`]
            Collection of projects.

    Returns
    -------
        Numeric
            The average capped fair share ratio
    """
    approval_scores = profile.approval_scores()
    project_share = {p: frac(p.cost, approval_scores[p]) for p in instance}

    r = 0
    for ballot in profile:
        ballot_share = sum(project_share[p] for p in ballot if p in budget_allocation)
        ballot_fairshare = min(sum(project_share[p] for p in ballot), frac(instance.budget_limit, profile.num_ballots()))
        r += min(frac(ballot_share, ballot_fairshare), 1) * profile.multiplicity(ballot)

    return frac(r, profile.num_ballots())
