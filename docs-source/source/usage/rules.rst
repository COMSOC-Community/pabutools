
Rules
=====

For reference, see the module :py:mod:`~pabutools.rules`.

We provide the implementation of the most celebrated rules for participatory budgeting.

Budget Allocation
-----------------

All rules return a :py:class:`~pabutools.rules.budgetallocation.BudgetAllocation` object.
The :py:class:`~pabutools.rules.budgetallocation.BudgetAllocation` class inherits from
:code:`list` and behaves similarly. It is used to store additional information about the
outcome (for visualisation/explanation purposes).

Additive Utilitarian Welfare Maximiser
--------------------------------------

:py:func:`~pabutools.rules.maxwelfare.max_additive_utilitarian_welfare`

The first rule provided is the Additive Utilitarian Welfare Maximiser. It aims to return
budget allocations that maximize the utilitarian social welfare when the satisfaction
measure is additive.

.. code-block:: python

    from pabutools.election import Instance, Project, ApprovalProfile, ApprovalBallot, Cost_Sat
    from pabutools.rules import max_additive_utilitarian_welfare, MaxAddUtilWelfareAlgo

    p = [Project("p" + str(i), 1) for i in range(10)]
    instance = Instance(p, budget_limit=5)
    profile = ApprovalProfile([
        ApprovalBallot(p),
        ApprovalBallot(p[:4]),
        ApprovalBallot({p[0], p[8]})
    ])

    # By passing a sat_class, the profile is automatically converted to a satisfaction profile
    outcome = max_additive_utilitarian_welfare(
        instance,
        profile,
        sat_class=Cost_Sat
    )

    # Or we can directly pass the satisfaction profile
    outcome = max_additive_utilitarian_welfare(
        instance,
        profile,
        sat_profile=profile.as_sat_profile(Cost_Sat)
    )

    # An initial budget allocation can be given
    outcome = max_additive_utilitarian_welfare(
        instance,
        profile,
        sat_profile=profile.as_sat_profile(Cost_Sat),
        initial_budget_allocation=[p[1], p[2]]
    )

    # We can get the irresolute outcome, i.e., a set of tied budget allocations
    irresolute_outcome = max_additive_utilitarian_welfare(
        instance,
        profile,
        sat_class=Cost_Sat,
        resoluteness=False
    )

    # We can force the use of the ILP solver
    irresolute_outcome = max_additive_utilitarian_welfare(
        instance,
        profile,
        sat_class=Cost_Sat,
        resoluteness=False,
        inner_algo=MaxAddUtilWelfareAlgo.ILP_SOLVER
    )

The outcome of the utilitarian welfare maximiser can be computed either using a integer linear
program (ILP) solver (through the  `mip package <https://www.python-mip.com/>`_) or using the
primal/dual approach for solving knapsack problems.

Only the ILP solver supports irresolute outcomes. Irresolute outcomes are
computed by iteratively adding constraints excluding previously returned budget
allocations. Note that because the computation is handled via a linear program solver, we
have no control as to how ties are broken.

Note that this can only be used for additive satisfaction measures. There is no general solution
for non-additive satisfaction measures.

Greedy Approximation of the Welfare Maximiser
---------------------------------------------

:py:func:`~pabutools.rules.greedywelfare.greedy_utilitarian_welfare`

The library also implements standard greedy rules. The primary rule used in this
context is the Greedy Utilitarian Welfare. It behaves similarly to the
Utilitarian Welfare Maximiser but offers additional functionalities: it is not limited
to additive satisfaction measures (and runs faster).

.. code-block:: python

    from pabutools.election import Instance, Project, ApprovalProfile, ApprovalBallot, Cost_Sat
    from pabutools.rules import greedy_utilitarian_welfare
    from pabutools.tiebreaking import app_score_tie_breaking

    p = [Project("p" + str(i), 1) for i in range(10)]
    instance = Instance(p, budget_limit=5)
    profile = ApprovalProfile([
        ApprovalBallot(p),
        ApprovalBallot(p[:4]),
        ApprovalBallot({p[0], p[8]})
    ])

    # By passing a sat_class, the profile is automatically converted to a satisfaction profile
    outcome = greedy_utilitarian_welfare(
        instance,
        profile,
        sat_class=Cost_Sat
    )

    # Or we can directly pass the satisfaction profile
    outcome = greedy_utilitarian_welfare(
        instance,
        profile,
        sat_profile=profile.as_sat_profile(Cost_Sat)
    )

    # If the satisfaction is known to be additive, we can say so to speed up computations
    # This is highly recommended
    outcome = greedy_utilitarian_welfare(
        instance,
        profile,
        sat_profile=profile.as_sat_profile(Cost_Sat),
        is_sat_additive=True
    )

    # An initial budget allocation can be given
    outcome = greedy_utilitarian_welfare(
        instance,
        profile,
        sat_profile=profile.as_sat_profile(Cost_Sat),
        initial_budget_allocation=[p[1], p[2]]
    )

    # The tie-breaking rule can be decided
    outcome = greedy_utilitarian_welfare(
        instance,
        profile,
        sat_profile=profile.as_sat_profile(Cost_Sat),
        tie_breaking=app_score_tie_breaking
    )

    # We can get the irresolute outcome, i.e., a set of tied budget allocations
    irresolute_outcome = greedy_utilitarian_welfare(
        instance,
        profile,
        sat_class=Cost_Sat,
        resoluteness=False
    )

Sequential Phragmén's Rule
--------------------------

:py:func:`~pabutools.rules.phragmen.sequential_phragmen`

Another rule provided is the Sequential Phragmén's Rule, which is different from the
previous two as it does not rely on a satisfaction measure.

.. code-block:: python

    from pabutools.election import Instance, Project, ApprovalProfile, ApprovalBallot
    from pabutools.rules import sequential_phragmen
    from pabutools.tiebreaking import app_score_tie_breaking

    p = [Project("p" + str(i), 1) for i in range(10)]
    instance = Instance(p, budget_limit=5)
    profile = ApprovalProfile([
        ApprovalBallot(p),
        ApprovalBallot(p[:4]),
        ApprovalBallot({p[0], p[8]})
    ])

    # The rule does not require a sat_class argument
    outcome = sequential_phragmen(
        instance,
        profile
    )

    # An initial budget allocation can be given
    outcome = sequential_phragmen(
        instance,
        profile,
        initial_budget_allocation=[p[1], p[2]]
    )

    # The tie-breaking rule can be indicated
    outcome = sequential_phragmen(
        instance,
        profile,
        tie_breaking=app_score_tie_breaking
    )

    # We can get the irresolute outcome, i.e., a set of tied budget allocations
    irresolute_outcome = sequential_phragmen(
        instance,
        profile,
        resoluteness=False
    )

Maximin Support Rule
--------------------

:py:func:`~pabutools.rules.maximin_support.maximin_support`

We also provide the Maximin Support rule. For the latter, we use the PuLP solver to compute the optimal load
distribution at each round.

.. code-block:: python

    from pabutools.election import Instance, Project, ApprovalProfile, ApprovalBallot, Cost_Sat
    from pabutools.rules import maximin_support
    from pabutools.tiebreaking import app_score_tie_breaking

    p = [Project("p" + str(i), 1) for i in range(10)]
    instance = Instance(p, budget_limit=5)
    profile = ApprovalProfile([
        ApprovalBallot(p),
        ApprovalBallot(p[:4]),
        ApprovalBallot({p[0], p[8]})
    ])

    # The rule does not require a sat_class argument
    outcome = maximin_support(
        instance,
        profile
    )

    # An initial budget allocation can be given
    outcome = maximin_support(
        instance,
        profile,
        initial_budget_allocation=[p[1], p[2]]
    )

    # The tie-breaking rule can be indicated
    outcome = maximin_support(
        instance,
        profile,
        tie_breaking=app_score_tie_breaking
    )

Method of Equal Shares (MES)
----------------------------

:py:func:`~pabutools.rules.mes.method_of_equal_shares`

The Method of Equal Shares is another rule that returns budget allocations based on the satisfaction
measure provided. For more details, see the `equalshares.net <https://equalshares.net/>`_ website.

.. code-block:: python

    from pabutools.election import Instance, Project, ApprovalProfile, ApprovalBallot, Cost_Sat
    from pabutools.rules import method_of_equal_shares
    from pabutools.tiebreaking import app_score_tie_breaking

    p = [Project("p" + str(i), 1) for i in range(10)]
    instance = Instance(p, budget_limit=5)
    profile = ApprovalProfile([
        ApprovalBallot(p),
        ApprovalBallot(p[:4]),
        ApprovalBallot({p[0], p[8]})
    ])

    # By passing a sat_class, the profile is automatically converted to a satisfaction profile
    outcome = method_of_equal_shares(
        instance,
        profile,
        sat_class=Cost_Sat
    )

    # Or we can directly pass the satisfaction profile
    outcome = method_of_equal_shares(
        instance,
        profile,
        sat_profile=profile.as_sat_profile(Cost_Sat)
    )

    # An initial budget allocation can be given
    outcome = method_of_equal_shares(
        instance,
        profile,
        sat_profile=profile.as_sat_profile(Cost_Sat),
        initial_budget_allocation=[p[1], p[2]]
    )

    # The tie-breaking rule can be decided
    outcome = method_of_equal_shares(
        instance,
        profile,
        sat_profile=profile.as_sat_profile(Cost_Sat),
        tie_breaking=app_score_tie_breaking
    )

    # We can get the irresolute outcome, i.e., a set of tied budget allocations
    irresolute_outcome = method_of_equal_shares(
        instance,
        profile,
        sat_class=Cost_Sat,
        resoluteness=False
    )

MES can significantly under-use the budget. The idea of running the rule for different
initial budget for the voters has been proposed in the scientific literature as a fix
for that problem. General exhaustion methods are presented further down this page. For
improved performances, one should use the following:

.. code-block:: python

    outcome = method_of_equal_shares(
        instance,
        profile.as_multiprofile(), # Faster in general (typically if ballots repeat a lot)
        sat_class=Cost_Sat,
        voter_budget_increment=1 # As soon as not-None, mes iterated is used
    )


Cumulative Support Transfer Voting Rule
---------------------------------------

:py:func:`~pabutools.rules.cstv.cstv`

The `cstv` function implements the Cost-Sensitive Approval Voting algorithm for participatory budgeting. This rules takes as input cumulative profiles that are interpreted as donation in favour of the projects.

The rule uses a combination of inner functions that need to be provided as arguments. Alternatively, pre-defined
combinations can be used via the :py:class:`~pabutools.rules.cstv.CSTV_Combination`.

.. code-block:: python

    from pabutools.election import Instance, Project, CumulativeProfile, CumulativeBallot
    from pabutools.rules import cstv

    p1 = Project("A", 27)
    p2 = Project("B", 30)
    p3 = Project("C", 40)
    instance = Instance([p1, p2, p3])
    donors = CumulativeProfile(
        [
            CumulativeBallot({p1: 5, p2: 10, p3: 5}),
            CumulativeBallot({p1: 10, p2: 10, p3: 0}),
            CumulativeBallot({p1: 0, p2: 15, p3: 5}),
            CumulativeBallot({p1: 0, p2: 0, p3: 20}),
            CumulativeBallot({p1: 15, p2: 5, p3: 0}),
        ]
    )

    # Using of the pre-defined combination:
    from pabutools.rules import CSTV_Combination
    cstv(instance, donors, CSTV_Combination.EWT)
    cstv(instance, donors, CSTV_Combination.EWTC)
    cstv(instance, donors, CSTV_Combination.EWT)
    cstv(instance, donors, CSTV_Combination.MTC)

    # Passing all the functions (this combination is EWT):
    from pabutools.rules.cstv import (
        select_project_ge, is_eligible_ge,
        elimination_with_transfers, reverse_eliminations
    )
    cstv(
        instance,
        donors,
        select_project_to_fund_func = select_project_ge,
        eligible_projects_func = is_eligible_ge,
        no_eligible_project_func = elimination_with_transfers,
        exhaustiveness_postprocess_func = reverse_eliminations
    )

    # You can also specify the usual parameters:
    from pabutools.rules import BudgetAllocation
    from pabutools.tiebreaking import lexico_tie_breaking
    cstv(
        instance,
        donors,
        CSTV_Combination.EWT,
        initial_budget_allocation = BudgetAllocation([Project("D", 10)]),
        tie_breaking = lexico_tie_breaking,
        resoluteness = True,  # Value 'False' is not yet supported
        verbose = True
    )

Exhaustion Methods
------------------

:py:func:`~pabutools.rules.exhaustion.completion_by_rule_combination`

:py:func:`~pabutools.rules.exhaustion.exhaustion_by_budget_increase`

Since not all rules return exhaustive budget allocations, the library offers standard
methods to render their outcome exhaustive.

Two methods are provided: the first applies a sequence of rules until achieving an
exhaustive budget allocation.

.. code-block:: python

    from pabutools.election import Instance, Project, ApprovalProfile, ApprovalBallot
    from pabutools.election import Cost_Sat, Cardinality_Sat
    from pabutools.rules import greedy_utilitarian_welfare, method_of_equal_shares
    from pabutools.rules import completion_by_rule_combination

    p = [Project("p" + str(i), 1) for i in range(10)]
    instance = Instance(p, budget_limit=5)
    profile = ApprovalProfile([
        ApprovalBallot(p),
        ApprovalBallot(p[:4]),
        ApprovalBallot({p[0], p[8]})
    ])

    # Here we apply two rules: first MES with the cost satisfaction,
    # and then the greedy rule with the cardinality satisfaction
    budget_allocation_mes_completed = completion_by_rule_combination(
        instance,
        profile,
        [method_of_equal_shares, greedy_utilitarian_welfare],
        [{"sat_class": Cost_Sat}, {"sat_class": Cardinality_Sat}],
    )

The second method consists of increasing the budget limit of the instance, in the hope that the
rule would then return a budget allocation that is exhaustive for the original instance. If at any
point the rule returns a budget allocation that is not feasible for the original budget limit, then
the previously returned budget allocation is returned.

.. code-block:: python

    from pabutools.election import Instance, Project, ApprovalProfile, ApprovalBallot, Cost_Sat
    from pabutools.rules import method_of_equal_shares, exhaustion_by_budget_increase
    from pabutools.fractions import frac

    p = [Project("p" + str(i), 1) for i in range(10)]
    instance = Instance(p, budget_limit=5)
    profile = ApprovalProfile([
        ApprovalBallot(p),
        ApprovalBallot(p[:4]),
        ApprovalBallot({p[0], p[8]})
    ])

    # Here we apply the MES rule with cost satisfaction until finding a suitable outcome
    budget_allocation_mes_iterated = exhaustion_by_budget_increase(
        instance,
        profile,
        method_of_equal_shares,
        {"sat_class": Cost_Sat},
        budget_step=instance.budget_limit * frac(1, 100), # Important for runtime, default is 1
    )

Note that since these two functions behave as rules, they can be combined. For instance, one
can first run MES with an increasing budget, and then complete the outcome with the greedy
method (which only does something if the outcome is not already exhaustive).

.. code-block:: python

    completion_by_rule_combination(
        instance,
        profile,
        [exhaustion_by_budget_increase, greedy_utilitarian_welfare],
        [
            {
                "rule": method_of_equal_shares,
                "rule_params": {"sat_class": Cost_Sat},
            },
            {"sat_class": Cost_Sat},
        ],
    )

Remember that for MES specifically, it is much faster to use the `voter_budget_increment`
parameter directly to obtain the iterated version.

Rule Composition
----------------

:py:func:`~pabutools.rules.composition.popularity_comparison`

:py:func:`~pabutools.rules.composition.social_welfare_comparison`

The library also provides ways to compose rules, such as selecting the outcome that is
preferred by the largest number of voters for a given satisfaction measure.

.. code-block:: python

    from pabutools.election import Instance, Project, ApprovalProfile, ApprovalBallot
    from pabutools.election import Cost_Sat, Cardinality_Sat
    from pabutools.rules import greedy_utilitarian_welfare, method_of_equal_shares
    from pabutools.rules import popularity_comparison

    p = [Project("p" + str(i), 1) for i in range(10)]
    instance = Instance(p, budget_limit=5)
    profile = ApprovalProfile([
        ApprovalBallot(p),
        ApprovalBallot(p[:4]),
        ApprovalBallot({p[0], p[8]})
    ])

    # Here we apply two rules: MES and greedy with the cost satisfaction,
    # and return the most preferred outcome based on Cardinality_Sat
    outcome = popularity_comparison(
        instance,
        profile,
        Cardinality_Sat,
        [method_of_equal_shares, greedy_utilitarian_welfare],
        [{"sat_class": Cost_Sat}, {"sat_class": Cost_Sat}],
    )

To run the rule as it was implemented in Wieliczka and Świece, for instance, one would run
the following:

.. code-block:: python

    from pabutools.election import Instance, Project, ApprovalProfile, ApprovalBallot
    from pabutools.election import Cost_Sat, Cardinality_Sat
    from pabutools.rules import greedy_utilitarian_welfare, method_of_equal_shares
    from pabutools.rules import completion_by_rule_combination, popularity_comparison

    p = [Project("p" + str(i), 1) for i in range(10)]
    instance = Instance(p, budget_limit=5)
    profile = ApprovalProfile([
        ApprovalBallot(p),
        ApprovalBallot(p[:4]),
        ApprovalBallot({p[0], p[8]})
    ])

    # First define MES iterated and completed (to simplify)
    def mes_full(instance, profile, initial_budget_allocation=None):
        return completion_by_rule_combination(
            instance,
            profile,
            [method_of_equal_shares, greedy_utilitarian_welfare],
            [
                {
                    "sat_class": Cost_Sat,
                    "voter_budget_increment": 1,
                },
                {"sat_class": Cost_Sat},
            ],
        )

    # Then run a popularity comparison between MES in full and Greedy Cardinality
    popularity_comparison(
        instance,
        profile,
        Cardinality_Sat,
        [mes_full, greedy_utilitarian_welfare],
        [{}, {"sat_class": Cardinality_Sat}]
    )

We also provide a similar comparison using utilitarian social welfare through the function
:py:func:`~pabutools.rules.composition.social_welfare_comparison`.

Details for the Budget Allocation Rule
--------------------------------------

Some rules, for instance :py:func:`~pabutools.rules.greedywelfare.greedy_utilitarian_welfare` or
:py:func:`~pabutools.rules.mes.method_of_equal_shares`, accept a
:code:`analytics` boolean argument to activate the storage of additional information
regarding the budget allocations output by the rule. When :code:`analytics = True`,
the rule populate the :code:`details` member of the
:py:class:`~pabutools.rules.budgetallocation.BudgetAllocation` object it returns.
The stored information can then be used for analytical purposes.

.. list-table::
   :widths: 50 50
   :header-rows: 1

   * - Rule
     - Details class
   * - :py:func:`~pabutools.rules.greedywelfare.greedy_utilitarian_welfare`
     - :py:class:`~pabutools.rules.greedywelfare.GreedyWelfareAllocationDetails`
   * - :py:func:`~pabutools.rules.mes.method_of_equal_shares`
     - :py:class:`~pabutools.rules.mes.MESAllocationDetails`

See the :ref:`outcome-visualisation` page for more details.
