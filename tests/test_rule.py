from unittest import TestCase
from parameterized import parameterized

from pabutools.fractions import frac
from pabutools.rules.budgetallocation import BudgetAllocation
from pabutools.election.profile import ApprovalProfile
from pabutools.election.ballot import ApprovalBallot
from pabutools.election.satisfaction import (
    Cost_Sat,
    Cardinality_Sat,
    Effort_Sat,
    Cost_Log_Sat,
    Cost_Sqrt_Sat,
    CC_Sat,
    SatisfactionProfile,
    SatisfactionMultiProfile,
    Additive_Cost_Sqrt_Sat,
    Additive_Cost_Log_Sat,
)
from pabutools.election.instance import Project, Instance, total_cost
from pabutools.rules.budgetallocation import BudgetAllocation
from pabutools.rules.phragmen import sequential_phragmen
from pabutools.rules.exhaustion import (
    completion_by_rule_combination,
    exhaustion_by_budget_increase,
)
from pabutools.rules.greedywelfare import greedy_utilitarian_welfare
from pabutools.rules.maxwelfare import max_additive_utilitarian_welfare
from pabutools.rules.mes import method_of_equal_shares


def mes_iterated(
    instance,
    profile,
    sat_class=None,
    sat_profile=None,
    initial_budget_allocation=None,
    resoluteness=False,
):
    return method_of_equal_shares(
        instance,
        profile,
        sat_class,
        sat_profile,
        initial_budget_allocation=initial_budget_allocation,
        voter_budget_increment=frac(1, 10),
        resoluteness=resoluteness,
    )


ALL_SAT_RULES = [
    greedy_utilitarian_welfare,
    max_additive_utilitarian_welfare,
    method_of_equal_shares,
    mes_iterated,
]
ALL_NON_SAT_RULES = [sequential_phragmen]
ALL_SAT = [
    Cost_Sat,
    Cardinality_Sat,
    Effort_Sat,
    Cost_Log_Sat,
    Cost_Sqrt_Sat,
    CC_Sat,
    Additive_Cost_Sqrt_Sat,
    Additive_Cost_Log_Sat,
]


class DummyElection:
    def __init__(
        self, name="", projects=None, instance=None, profile=None, initial_alloc=None
    ):
        self.name = name
        self.projects = projects
        self.instance = instance
        self.profile = profile
        self.initial_alloc = initial_alloc
        self.irr_results_sat = dict()
        for rule in ALL_SAT_RULES:
            self.irr_results_sat[rule] = dict()
            for sat in ALL_SAT:
                self.irr_results_sat[rule][sat] = None
        self.irr_results_non_sat = dict()
        for rule in ALL_NON_SAT_RULES:
            self.irr_results_non_sat[rule] = None


def dummy_elections():
    res = []

    # Approval example 1
    p = [Project("p0", 1), Project("p1", 3), Project("p2", 2), Project("p3", 1)]
    inst = Instance(p, budget_limit=3)
    prof = ApprovalProfile(
        [
            ApprovalBallot((p[0], p[1], p[2], p[3])),
            ApprovalBallot((p[0], p[1], p[2], p[3])),
        ],
        instance=inst,
    )
    test_election = DummyElection("AppEx_1", p, inst, prof)
    test_election.irr_results_sat[greedy_utilitarian_welfare][Cost_Sat] = sorted(
        [[p[0], p[2]], [p[0], p[3]], [p[1]], [p[2], p[3]]]
    )
    test_election.irr_results_sat[greedy_utilitarian_welfare][Cardinality_Sat] = sorted(
        [[p[0], p[3]]]
    )
    test_election.irr_results_sat[max_additive_utilitarian_welfare][Cost_Sat] = sorted(
        [[p[0], p[2]], [p[1]], [p[2], p[3]]]
    )
    test_election.irr_results_sat[max_additive_utilitarian_welfare][Cardinality_Sat] = (
        sorted([[p[0], p[3]], [p[0], p[2]], [p[2], p[3]]])
    )
    res.append(test_election)

    # Approval example 2
    p = [Project("p0", 1), Project("p1", 0.9), Project("p2", 2), Project("p3", 1.09)]
    inst = Instance(p, budget_limit=4)
    prof = ApprovalProfile(
        [
            ApprovalBallot({p[0]}),
            ApprovalBallot({p[1], p[2], p[3]}),
            ApprovalBallot({p[1], p[2], p[3]}),
            ApprovalBallot({p[2]}),
        ],
        instance=inst,
    )
    test_election = DummyElection("AppEx_2", p, inst, prof)
    test_election.irr_results_sat[method_of_equal_shares][Cardinality_Sat] = sorted(
        [[p[0], p[1], p[3]]]
    )
    test_election.irr_results_sat[mes_iterated][Cardinality_Sat] = sorted(
        [[p[0], p[1], p[3]]]
    )
    test_election.irr_results_sat[method_of_equal_shares][Cost_Sat] = sorted(
        [[p[0], p[2]]]
    )
    test_election.irr_results_sat[mes_iterated][Cost_Sat] = sorted([[p[0], p[1], p[2]]])
    res.append(test_election)

    # Approval example 3 - With app score 0
    p = [
        Project("p0", 1),
        Project("p1", 0.9),
        Project("p2", 2),
        Project("p3", 1.09),
        Project("p4", 1.09),
        Project("p5", 1.09),
    ]
    inst = Instance(p, budget_limit=4)
    prof = ApprovalProfile(
        [
            ApprovalBallot({p[0]}),
            ApprovalBallot({p[1], p[2], p[3]}),
            ApprovalBallot({p[1], p[2], p[3]}),
            ApprovalBallot({p[2]}),
        ],
        instance=inst,
    )
    test_election = DummyElection("AppEx_3", p, inst, prof)
    test_election.irr_results_sat[method_of_equal_shares][Cardinality_Sat] = sorted(
        [[p[0], p[1], p[3]]]
    )
    test_election.irr_results_sat[method_of_equal_shares][Cost_Sat] = sorted(
        [[p[0], p[2]]]
    )
    test_election.irr_results_sat[mes_iterated][Cost_Sat] = sorted([[p[0], p[1], p[2]]])
    res.append(test_election)

    # Approval example 4 - With project with cost 0
    p = [
        Project("p0", 0),
        Project("p1", 1),
        Project("p2", 2),
    ]
    inst = Instance(p, budget_limit=2)
    prof = ApprovalProfile(
        [
            ApprovalBallot({p[0]}),
            ApprovalBallot({p[0], p[1], p[2]}),
            ApprovalBallot({p[2]}),
        ],
        instance=inst,
    )
    test_election = DummyElection("AppEx_4", p, inst, prof)
    test_election.irr_results_sat[greedy_utilitarian_welfare][Cost_Sat] = sorted(
        [[p[0], p[2]]]
    )
    test_election.irr_results_sat[greedy_utilitarian_welfare][Cardinality_Sat] = sorted(
        [[p[0], p[1]], [p[0], p[2]]]
    )
    test_election.irr_results_sat[max_additive_utilitarian_welfare][Cost_Sat] = sorted(
        [[p[0], p[2]], [p[2]]]
    )
    test_election.irr_results_sat[max_additive_utilitarian_welfare][Cardinality_Sat] = (
        sorted([[p[0], p[2]]])
    )
    test_election.irr_results_sat[method_of_equal_shares][Cost_Sat] = sorted([[]])
    test_election.irr_results_sat[mes_iterated][Cost_Sat] = sorted([[p[2]]])
    test_election.irr_results_sat[method_of_equal_shares][Cardinality_Sat] = sorted(
        [[p[0]]]
    )
    test_election.irr_results_sat[mes_iterated][Cardinality_Sat] = sorted(
        [[p[0], p[1]], [p[0], p[2]]]
    )
    res.append(test_election)

    # Empty profile
    p = [Project("p0", 1), Project("p1", 3), Project("p2", 2), Project("p3", 1)]
    inst = Instance(p, budget_limit=3)
    prof = ApprovalProfile([ApprovalBallot()], instance=inst)
    test_election = DummyElection("EmptyProfile", p, inst, prof)
    for sat_class in ALL_SAT:
        test_election.irr_results_sat[max_additive_utilitarian_welfare][sat_class] = (
            sorted([sorted(list(b)) for b in inst.budget_allocations()])
        )
        test_election.irr_results_sat[greedy_utilitarian_welfare][sat_class] = sorted(
            [
                sorted(list(b))
                for b in inst.budget_allocations()
                if inst.is_exhaustive(b)
            ]
        )
        test_election.irr_results_sat[method_of_equal_shares][sat_class] = [[]]
        test_election.irr_results_sat[mes_iterated][sat_class] = [[]]
    test_election.irr_results_non_sat[sequential_phragmen] = [
        [p[0]],
        [p[1]],
        [p[2]],
        [p[3]],
    ]
    res.append(test_election)

    # Empty profile with initial alloc
    p = [Project("p0", 1), Project("p1", 3), Project("p2", 2), Project("p3", 1)]
    inst = Instance(p, budget_limit=3)
    prof = ApprovalProfile([ApprovalBallot()], instance=inst)
    initial_alloc = p[:1]
    test_election = DummyElection("EmptyProfile_Initial", p, inst, prof, initial_alloc)
    for sat_class in ALL_SAT:
        test_election.irr_results_sat[max_additive_utilitarian_welfare][sat_class] = (
            sorted([sorted(list(b)) for b in inst.budget_allocations() if p[0] in b])
        )
        test_election.irr_results_sat[greedy_utilitarian_welfare][sat_class] = sorted(
            [
                sorted(list(b))
                for b in inst.budget_allocations()
                if p[0] in b and inst.is_exhaustive(b)
            ]
        )
        test_election.irr_results_sat[method_of_equal_shares][sat_class] = [
            initial_alloc
        ]
        test_election.irr_results_sat[mes_iterated][sat_class] = [initial_alloc]
    test_election.irr_results_non_sat[sequential_phragmen] = [initial_alloc]
    res.append(test_election)

    # All affordable
    p = [Project("p0", 1), Project("p1", 3), Project("p2", 2), Project("p3", 1)]
    inst = Instance(p, budget_limit=7)
    prof = ApprovalProfile([ApprovalBallot(p)], instance=inst)
    test_election = DummyElection("AllAfford", p, inst, prof)
    for rule in ALL_SAT_RULES:
        for sat_class in ALL_SAT:
            if sat_class != Cost_Log_Sat:
                test_election.irr_results_sat[rule][sat_class] = sorted([p])
    for rule in ALL_NON_SAT_RULES:
        test_election.irr_results_non_sat[rule] = sorted([p])
    res.append(test_election)

    # Running example from Lackner & Skowron 2023
    p = [
        Project("a", 1),
        Project("b", 1),
        Project("c", 1),
        Project("d", 1),
        Project("e", 1),
        Project("f", 1),
        Project("g", 1),
    ]
    inst = Instance(p, budget_limit=4)
    prof = ApprovalProfile(
        [
            ApprovalBallot({p[0], p[1]}),
            ApprovalBallot({p[0], p[1]}),
            ApprovalBallot({p[0], p[1]}),
            ApprovalBallot({p[0], p[2]}),
            ApprovalBallot({p[0], p[2]}),
            ApprovalBallot({p[0], p[2]}),
            ApprovalBallot({p[0], p[3]}),
            ApprovalBallot({p[0], p[3]}),
            ApprovalBallot({p[1], p[2], p[5]}),
            ApprovalBallot({p[4]}),
            ApprovalBallot({p[5]}),
            ApprovalBallot({p[6]}),
        ],
        instance=inst,
    )
    test_election = DummyElection("RunningEx LackSkow23", p, inst, prof)
    test_election.irr_results_non_sat[sequential_phragmen] = sorted([p[:4]])
    for sat_class in [Cost_Sat, Cardinality_Sat, Cost_Sqrt_Sat, Cost_Log_Sat]:
        test_election.irr_results_sat[method_of_equal_shares][sat_class] = sorted(
            [[p[0]]]
        )
    res.append(test_election)

    return res


ALL_TEST_ELECTIONS = dummy_elections()


def run_sat_rule(rule, verbose=False):
    for test_election in ALL_TEST_ELECTIONS:
        for sat_class in test_election.irr_results_sat[rule]:
            if test_election.irr_results_sat[rule][sat_class] is not None:
                for profile in [
                    test_election.profile,
                    test_election.profile.as_multiprofile(),
                ]:
                    for sat_profile in [None, profile.as_sat_profile(sat_class)]:
                        if verbose:
                            print(
                                f"\n=================== {rule.__name__} - {sat_class.__name__} ==================="
                            )
                            print(
                                f"Test `{test_election.name}`\nInst: {test_election.instance}\nProfile: {profile}"
                            )
                            print(f"Sat profile: {sat_profile}")
                            print(f"Initial alloc: {test_election.initial_alloc}")
                            print("------------------")

                        resolute_out = rule(
                            test_election.instance,
                            profile,
                            sat_class=sat_class,
                            sat_profile=sat_profile,
                            resoluteness=True,
                            initial_budget_allocation=test_election.initial_alloc,
                        )
                        if verbose:
                            print(
                                f"Res outcome:  {resolute_out} -- In irres: "
                                f"{sorted(resolute_out) in test_election.irr_results_sat[rule][sat_class]} "
                                f"({type(resolute_out)})"
                            )
                        irresolute_out = rule(
                            test_election.instance,
                            profile,
                            sat_class=sat_class,
                            sat_profile=sat_profile,
                            resoluteness=False,
                            initial_budget_allocation=test_election.initial_alloc,
                        )
                        if verbose:
                            print(
                                f"Irres outcome:  {irresolute_out} "
                                f"({tuple(type(out) for out in irresolute_out)})"
                            )
                            print(
                                f"Irres expected: {test_election.irr_results_sat[rule][sat_class]}"
                            )
                        resolute_out_sat_profile = rule(
                            test_election.instance,
                            test_election.profile,
                            resoluteness=True,
                            sat_profile=SatisfactionProfile(
                                profile=test_election.profile, sat_class=sat_class
                            ),
                            initial_budget_allocation=test_election.initial_alloc,
                        )
                        if verbose:
                            print(
                                f"Res outcome with sat_profile: {resolute_out_sat_profile} -- Same: "
                                f"{resolute_out == resolute_out_sat_profile} "
                                f"({type(resolute_out_sat_profile)})"
                            )

                        assert (
                            total_cost(resolute_out)
                            <= test_election.instance.budget_limit
                        )
                        assert (
                            total_cost(resolute_out_sat_profile)
                            <= test_election.instance.budget_limit
                        )
                        for res in irresolute_out:
                            assert (
                                total_cost(res) <= test_election.instance.budget_limit
                            )
                        assert (
                            sorted(resolute_out)
                            in test_election.irr_results_sat[rule][sat_class]
                        )
                        assert sorted(resolute_out) == sorted(resolute_out_sat_profile)
                        assert sorted(sorted(x) for x in irresolute_out) == sorted(
                            test_election.irr_results_sat[rule][sat_class]
                        )

                        assert isinstance(resolute_out, BudgetAllocation)
                        assert isinstance(resolute_out_sat_profile, BudgetAllocation)
                        assert isinstance(irresolute_out, list)
                        for out in irresolute_out:
                            assert isinstance(out, BudgetAllocation)


def run_non_sat_rule(rule):
    for test_election in ALL_TEST_ELECTIONS:
        if test_election.irr_results_non_sat[rule] is not None:
            for profile in [
                test_election.profile,
                test_election.profile.as_multiprofile(),
            ]:
                # print("\n===================== {} =====================".format(rule.__name__))
                # print("Test `{}`\nInst: {}\n Profile: {}".format(test_election.name, test_election.instance,
                #                                                  test_election.profile))
                resolute_out = sorted(
                    rule(
                        test_election.instance,
                        profile,
                        resoluteness=True,
                        initial_budget_allocation=test_election.initial_alloc,
                    )
                )
                irresolute_out = sorted(
                    rule(
                        test_election.instance,
                        profile,
                        resoluteness=False,
                        initial_budget_allocation=test_election.initial_alloc,
                    )
                )
                # print("Res outcome:  {}".format(resolute_out))
                # print("Irres outcome:  {}".format(irresolute_out))
                # print("Irres expected: {}".format(test_election.irr_results_non_sat[rule]))
                assert resolute_out in test_election.irr_results_non_sat[rule]
                assert irresolute_out == test_election.irr_results_non_sat[rule]


class TestRule(TestCase):
    def test_greedy_welfare(self):
        run_sat_rule(greedy_utilitarian_welfare, verbose=False)
        with self.assertRaises(ValueError):
            greedy_utilitarian_welfare(Instance(), ApprovalProfile())

    def test_greedy_multiprofile(self):
        for test_election in ALL_TEST_ELECTIONS:
            outcome1 = greedy_utilitarian_welfare(
                test_election.instance,
                test_election.profile,
                resoluteness=True,
                initial_budget_allocation=test_election.initial_alloc,
                sat_class=Cost_Sat,
            )
            multiprofile = test_election.profile.as_multiprofile()
            outcome2 = greedy_utilitarian_welfare(
                test_election.instance,
                multiprofile,
                sat_class=Cost_Sat,
                resoluteness=True,
                initial_budget_allocation=test_election.initial_alloc,
            )
            assert outcome1 == outcome2

    def test_greedy_multisat(self):
        for test_election in ALL_TEST_ELECTIONS:
            for add_sat in [True, False]:
                sat_profile = SatisfactionProfile(
                    profile=test_election.profile, sat_class=Cost_Sat
                )
                outcome1 = greedy_utilitarian_welfare(
                    test_election.instance,
                    test_election.profile,
                    sat_profile=sat_profile,
                    resoluteness=True,
                    initial_budget_allocation=test_election.initial_alloc,
                    is_sat_additive=add_sat,
                )
                sat_multiprofile = SatisfactionMultiProfile(
                    profile=test_election.profile, sat_class=Cost_Sat
                )
                outcome2 = greedy_utilitarian_welfare(
                    test_election.instance,
                    test_election.profile,
                    sat_profile=sat_multiprofile,
                    resoluteness=True,
                    initial_budget_allocation=test_election.initial_alloc,
                    is_sat_additive=add_sat,
                )
                assert outcome1 == outcome2

    def test_max_welfare(self):
        run_sat_rule(max_additive_utilitarian_welfare, verbose=False)
        with self.assertRaises(ValueError):
            max_additive_utilitarian_welfare(Instance(), ApprovalProfile())

    def test_phragmen(self):
        run_non_sat_rule(sequential_phragmen)

    def test_mes_approval(self):
        run_sat_rule(method_of_equal_shares, verbose=False)
        run_sat_rule(mes_iterated, verbose=False)
        with self.assertRaises(ValueError):
            method_of_equal_shares(Instance(), ApprovalProfile())

    def test_iterated_exhaustion(self):
        projects = [
            Project("a", 1),
            Project("b", 1),
            Project("c", 1),
            Project("d", 1),
            Project("e", 1),
            Project("f", 1),
            Project("g", 1),
        ]
        instance = Instance(projects, budget_limit=4)
        profile = ApprovalProfile(
            [
                ApprovalBallot({projects[0], projects[1]}),
                ApprovalBallot({projects[0], projects[1]}),
                ApprovalBallot({projects[0], projects[1]}),
                ApprovalBallot({projects[0], projects[2]}),
                ApprovalBallot({projects[0], projects[2]}),
                ApprovalBallot({projects[0], projects[2]}),
                ApprovalBallot({projects[0], projects[3]}),
                ApprovalBallot({projects[0], projects[3]}),
                ApprovalBallot({projects[1], projects[2], projects[5]}),
                ApprovalBallot({projects[4]}),
                ApprovalBallot({projects[5]}),
                ApprovalBallot({projects[6]}),
            ]
        )
        budget_allocation_mes = method_of_equal_shares(instance, profile, Cost_Sat)
        assert budget_allocation_mes == [projects[0]]

        budget_allocation_mes_iterated = exhaustion_by_budget_increase(
            instance,
            profile,
            method_of_equal_shares,
            {"sat_class": Cost_Sat},
            budget_step=frac(1, 24),
        )
        assert sorted(budget_allocation_mes_iterated) == [
            projects[0],
            projects[1],
            projects[2],
            projects[3],
        ]

        budget_allocation_mes_iterated = exhaustion_by_budget_increase(
            instance,
            profile,
            method_of_equal_shares,
            {"sat_class": Cost_Sat},
            budget_step=frac(1, 24),
            initial_budget_allocation=[projects[6]],
        )
        assert sorted(budget_allocation_mes_iterated) == [
            projects[0],
            projects[1],
            projects[2],
            projects[6],
        ]

        budget_allocation_mes_iterated_big_steps = exhaustion_by_budget_increase(
            instance,
            profile,
            method_of_equal_shares,
            {"sat_class": Cost_Sat},
            budget_step=5,
        )
        assert budget_allocation_mes_iterated_big_steps == [projects[0]]

        with self.assertRaises(ValueError):
            exhaustion_by_budget_increase(instance, profile, method_of_equal_shares)

    def test_completion(self):
        projects = [
            Project("a", 1),
            Project("b", 2),
            Project("c", 2),
            Project("d", 1),
            Project("e", 1),
            Project("f", 1),
        ]
        instance = Instance(projects, budget_limit=5)
        profile = ApprovalProfile(
            [
                ApprovalBallot({projects[0], projects[1]}),
                ApprovalBallot({projects[0], projects[1]}),
                ApprovalBallot({projects[0]}),
                ApprovalBallot({projects[0], projects[2]}),
                ApprovalBallot({projects[0], projects[2]}),
                ApprovalBallot({projects[0], projects[2]}),
                ApprovalBallot({projects[0], projects[3]}),
                ApprovalBallot({projects[0], projects[3]}),
                ApprovalBallot({projects[5]}),
                ApprovalBallot({projects[4]}),
            ]
        )
        budget_allocation_mes = method_of_equal_shares(instance, profile, Cost_Sat)
        assert budget_allocation_mes == [projects[0]]

        budget_allocation_mes_iterated = completion_by_rule_combination(
            instance,
            profile,
            [method_of_equal_shares, greedy_utilitarian_welfare],
            [{"sat_class": Cost_Sat}, {"sat_class": Cost_Sat}],
        )
        assert sorted(budget_allocation_mes_iterated) == [
            projects[0],
            projects[1],
            projects[2],
        ]
        budget_allocation_mes_iterated = completion_by_rule_combination(
            instance,
            profile,
            [method_of_equal_shares, greedy_utilitarian_welfare],
            [{"sat_class": Cost_Sat}, {"sat_class": Cost_Sat}],
            initial_budget_allocation=[projects[5]],
        )
        assert sorted(budget_allocation_mes_iterated) == [
            projects[0],
            projects[2],
            projects[3],
            projects[5],
        ]

        with self.assertRaises(ValueError):
            completion_by_rule_combination(
                instance,
                profile,
                [method_of_equal_shares, greedy_utilitarian_welfare],
                [{"sat_class": Cost_Sat}],
            )

        with self.assertRaises(ValueError):
            completion_by_rule_combination(
                instance, profile, [method_of_equal_shares, greedy_utilitarian_welfare]
            )

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

        p1 = Project("p1", 2)
        p2 = Project("p2", 2)
        p3 = Project("p3", 3)
        instance = Instance([p1, p2, p3], budget_limit=4)
        profile = ApprovalProfile(
            [
                ApprovalBallot([p1]),
                ApprovalBallot([p1]),
                ApprovalBallot([p1]),
                ApprovalBallot([p1]),
                ApprovalBallot([p1]),
                ApprovalBallot([p2]),
                ApprovalBallot([p3]),
                ApprovalBallot([p3]),
            ]
        )

        def mes_phragmen(instance, profile, resoluteness=True):
            return completion_by_rule_combination(
                instance,
                profile,
                [method_of_equal_shares, sequential_phragmen],
                [{"sat_class": Cost_Sat}, {}],
                resoluteness=resoluteness,
            )

        assert method_of_equal_shares(instance, profile, Cost_Sat) == [p1]
        assert mes_phragmen(instance, profile) == [p1]
        assert mes_phragmen(instance, profile, resoluteness=False) == [[p1]]

    @parameterized.expand(
        [
            (
                [1, 1, 2, 1, 2],
                [0, 2],
                [0, 2],
                [0],
                [
                    [frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2)],
                ],
            ),
            (
                [1, 1, 2, 1, 2],
                [0, 1, 2],
                [0],
                [0, 1],
                [
                    [frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2)],
                    [frac(3, 8), frac(3, 8), frac(3, 8), frac(3, 8), frac(3, 8), frac(3, 8), frac(3, 8), frac(3, 8), frac(1, 2), frac(1, 2)],
                ],
            ),
            (
                [1, 1, 2, 1, 2],
                [0, 1, 2],
                [0, 1, 2],
                [0, 1],
                [
                    [frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2)],
                    [frac(3, 8), frac(3, 8), frac(3, 8), frac(3, 8), frac(3, 8), frac(3, 8), frac(3, 8), frac(3, 8), frac(1, 2), frac(1, 2)],
                ],
            ),
            (
                [5, 1, 2, 1, 2],
                [0, 1, 2],
                [0, 1, 2],
                [1, 3],
                [
                    [frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2),  frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2)],
                    [frac(1, 4), frac(1, 4), frac(1, 2), frac(1, 4),  frac(1, 4), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2)] 
                ],
            ),
            (
                [5, 5, 5, 5, 5],
                [0, 1, 2],
                [0, 1, 2],
                [],
                []
            ),
            (
                [5, 1, 2, 1, 2],
                [0, 1, 2],
                [0, 1, 2],
                [1, 3],
                [
                    [frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2)],
                    [frac(1, 4), frac(1, 2), frac(1, 4), frac(1, 2), frac(1, 2), frac(1, 2)],
                ],
                True,
                [2, 1, 2, 1, 2, 2],
            ),
            (
                [5, 1, 2, 1, 2],
                [0, 1, 2],
                [0, 1, 2],
                [1, 3],
                [
                    [frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2)],
                    [frac(1, 4), frac(1, 2), frac(1, 4), frac(1, 2), frac(1, 2), frac(1, 2)],
                ],
                True,
                [2, 1, 2, 1, 2, 2],
            ),
            (
                [5, 1, 2, 1, 2],
                [0, 1, 2],
                [0, 1, 2],
                [1, 3],
                [
                    [frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2), frac(1, 2)],
                    [frac(1, 4), frac(1, 2), frac(1, 4), frac(1, 2), frac(1, 2), frac(1, 2)],
                ],
                True,
                [2, 1, 2, 1, 2, 2],
            ),
        ]
    )
    def test_mes_analytics(
        self,
        costs,
        third_voter_approval_idxs,
        fourth_voter_approval_idxs,
        picked_projects_idxs,
        expected_voter_budgets,
        multiprofile=False,
        expected_multiplicity=[1 for _ in range(10)],
    ):
        projects = [Project(chr(ord("a") + idx), costs[idx]) for idx in range(0, 5)]
        instance = Instance(projects, budget_limit=5)
        profile = ApprovalProfile(
            [
                ApprovalBallot({projects[0], projects[1]}),
                ApprovalBallot({projects[0], projects[1]}),
                ApprovalBallot({projects[0]}),
                ApprovalBallot([projects[idx] for idx in third_voter_approval_idxs]),
                ApprovalBallot([projects[idx] for idx in fourth_voter_approval_idxs]),
                ApprovalBallot({projects[0], projects[2]}),
                ApprovalBallot({projects[0], projects[3]}),
                ApprovalBallot({projects[0], projects[3]}),
                ApprovalBallot({projects[4]}),
                ApprovalBallot({projects[4]}),
            ]
        )
        if multiprofile:
            profile = profile.as_multiprofile()
        result = method_of_equal_shares(instance, profile, Cost_Sat, analytics=True)
        assert sorted(list(result), key=lambda proj: proj.name) == [
            projects[idx] for idx in picked_projects_idxs
        ]

        if len(result.details.iterations) > 0:
            assert result.details.iterations[0].voters_budget[0] == frac(1, 2)
        assert result.details.voter_multiplicity == expected_multiplicity
        for idx, anl in enumerate(
            sorted(result.details.get_all_project_details(), key=lambda proj_details: proj_details.project.name)
        ):
            assert anl.project.name == projects[idx].name
            assert not anl.was_picked() or anl.project in result

        for idx, it in enumerate(result.details.iterations):
            print(it.voters_budget)
            print(expected_voter_budgets[idx])
            assert it.voters_budget == expected_voter_budgets[idx]
        
    def test_mes_analytics_irresolute(self):
        projects = [Project(chr(ord("a") + idx), 3) for idx in range(0, 3)]
        instance = Instance(projects, budget_limit=6)
        profile = ApprovalProfile(
            [
                ApprovalBallot({projects[1], projects[2]}),
                ApprovalBallot({projects[0], projects[2]}),
                ApprovalBallot({projects[0], projects[1]}),
            ]
        )
        result = method_of_equal_shares(
            instance, profile, Cost_Sat, resoluteness=False, analytics=True
        )
        #TODO: Support for analytics in non-resolute case
        assert True
        # assert all(elem in result for elem in [[proj] for proj in projects])
        # assert len(result) == 3

        # for idxs, alloc in enumerate(result):
        #     assert alloc.details.initial_budget_per_voter == frac(2, 1)
        #     assert alloc.details.iterations[0].was_picked == True
        #     assert all([not iter.was_picked for iter in alloc.details.iterations[1:]])
        #     assert alloc.details.iterations[0].project.name == projects[idxs]
        #     for iter in alloc.details.iterations:
        #         assert iter.voters_budget == [
        #             2 if idxs == idx else frac(1, 2) for idx in range(3)
        #         ]

    def test_iterated_exhaustion_analytics(self):
        projects = [Project(chr(ord("a") + idx), 1) for idx in range(0, 8)]
        instance = Instance(projects, budget_limit=4)
        profile = ApprovalProfile(
            [
                ApprovalBallot({projects[0], projects[1]}),
                ApprovalBallot({projects[0], projects[1]}),
                ApprovalBallot({projects[0], projects[2]}),
                ApprovalBallot({projects[0], projects[2]}),
                ApprovalBallot({projects[0], projects[3]}),
                ApprovalBallot({projects[0], projects[3]}),
                ApprovalBallot({projects[1], projects[2], projects[5]}),
                ApprovalBallot({projects[4]}),
                ApprovalBallot({projects[5]}),
                ApprovalBallot({projects[6]}),
            ]
        )
        budget_allocation_mes_iterated = exhaustion_by_budget_increase(
            instance,
            profile,
            method_of_equal_shares,
            {"sat_class": Cost_Sat, "analytics": True},
            budget_step=frac(1, 24),
        )
        expected_voter_budgets = [
            [frac(2, 3)] * 10,
            [frac(1, 2)] * 6 + [frac(2, 3)] * 4,
            [frac(1, 6)] * 2 + [frac(1, 2)] * 4 + [frac(1, 3)] + [frac(2, 3)] * 3,
            [frac(1, 6)] * 4 + [frac(1, 2)] * 2 + [0] + [frac(2, 3)] * 3
        ]

        assert sorted(
            list(budget_allocation_mes_iterated), key=lambda proj: proj.name
        ) == [projects[idx] for idx in range(4)]

        assert len(budget_allocation_mes_iterated.details.get_all_project_details()) == 7
        assert budget_allocation_mes_iterated.details.iterations[0].voters_budget[0] == frac(
            2, 3
        )
        assert budget_allocation_mes_iterated.details.get_all_selected_projects() == list(budget_allocation_mes_iterated)
        for idx, iteration in enumerate(budget_allocation_mes_iterated.details.iterations):
            assert iteration.voters_budget == expected_voter_budgets[idx]