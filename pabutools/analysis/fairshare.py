from pabutools.election import Instance, AbstractApprovalProfile
from pabutools.fractions import frac
from pabutools.rules import BudgetAllocation
from pabutools.utils import Numeric


def average_normalised_distance_to_fair_share(instance: Instance, profile: AbstractApprovalProfile, budget_allocation: BudgetAllocation) -> Numeric:
    """
    Returns the average normalised distance to fair share of the given budget allocation. The distance to fair
    share for a given ballot is defined as the absolute value of `fair share of the ballot - share of the ballot`.
    This is normalised by dividing by the fair share of the ballot. This value is averaged up for all ballots in the
    profile and 1 minus the resulting value is returned. This is a measure in which 1 is the best.

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
        d += frac(abs(ballot_share - ballot_fairshare), ballot_fairshare) * profile.multiplicity(ballot)

    return 1 - frac(d, profile.num_ballots())

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
