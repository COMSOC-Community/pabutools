import os

from unittest import TestCase

from pabutools.election import *
from pabutools.rules import *

ALL_SAT_RULES = [
    greedy_utilitarian_welfare,
    max_additive_utilitarian_welfare,
    method_of_equal_shares,
]

ALL_NON_SAT_RULES = [sequential_phragmen]


def profile_sat_map(prof):
    if isinstance(prof, AbstractApprovalProfile):
        return [
            CC_Sat,
            Cost_Sqrt_Sat,
            Cost_Log_Sat,
            Cardinality_Sat,
            Relative_Cardinality_Sat,
            Cost_Sat,
            Relative_Cost_Sat,
            Relative_Cost_Approx_Normaliser_Sat,
            Effort_Sat,
        ]
    if isinstance(prof, AbstractCardinalProfile):
        return [
            CC_Sat,
            Cardinality_Sat,
            Relative_Cardinality_Sat,
            Cost_Sat,
            Relative_Cost_Sat,
            Relative_Cost_Approx_Normaliser_Sat,
            Effort_Sat,
            Additive_Cardinal_Sat,
        ]
    if isinstance(prof, AbstractOrdinalProfile):
        return [
            Cardinality_Sat,
            Relative_Cardinality_Sat,
            Cost_Sat,
            Relative_Cost_Sat,
            Relative_Cost_Approx_Normaliser_Sat,
            Effort_Sat,
            Additive_Borda_Sat,
        ]


class TestPabulibData(TestCase):
    def test_files(self, source_dir="All_10"):
        max_num_instances = 10

        elections = []
        for file in os.listdir(os.path.join(source_dir)):
            if file.endswith(".pb"):
                instance, profile = parse_pabulib(os.path.join(source_dir, file))
                elections.append((instance, profile))

        for i, (instance, prof) in enumerate(elections):
            for rule in ALL_SAT_RULES:
                for profile in [prof, prof.as_multiprofile()]:
                    for sat_class in profile_sat_map(profile):
                        print(
                            "{}/{} {}[{}, {}] on {} (n={}, m={})".format(
                                i + 1,
                                len(elections),
                                rule.__name__,
                                type(profile).__name__,
                                sat_class.__name__,
                                instance.file_name,
                                profile.num_ballots(),
                                len(instance),
                            )
                        )
                        rule(instance, profile, sat_class=sat_class)
                        rule(
                            instance,
                            profile,
                            sat_profile=profile.as_sat_profile(sat_class),
                        )
            if i >= max_num_instances:
                break
