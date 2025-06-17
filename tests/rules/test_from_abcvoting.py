import os
from unittest import TestCase

import yaml
from abcvoting.fileio import read_abcvoting_yaml_file

from pabutools.election import Cost_Sat, Cardinality_Sat, ApprovalBallot, ApprovalProfile, Project, Instance
from pabutools.fractions import frac
from pabutools.rules import max_additive_utilitarian_welfare, greedy_utilitarian_welfare, sequential_phragmen, \
    method_of_equal_shares, completion_by_rule_combination, exhaustion_by_budget_increase, maximin_support


def av_via_max_cost(instance, profile, resoluteness=True):
    return max_additive_utilitarian_welfare(instance, profile, sat_class=Cost_Sat, resoluteness=resoluteness)

def av_via_max_card(instance, profile, resoluteness=True):
    return max_additive_utilitarian_welfare(instance, profile, sat_class=Cardinality_Sat, resoluteness=resoluteness)

def av_via_greed_cost(instance, profile, resoluteness=True):
    return greedy_utilitarian_welfare(instance, profile, sat_class=Cost_Sat, resoluteness=resoluteness)

def av_via_greed_card(instance, profile, resoluteness=True):
    return greedy_utilitarian_welfare(instance, profile, sat_class=Cardinality_Sat, resoluteness=resoluteness)

def mes_card(instance, profile, resoluteness=True):
    return method_of_equal_shares(instance, profile, sat_class=Cardinality_Sat, resoluteness=resoluteness)

def mes_cost(instance, profile, resoluteness=True):
    return method_of_equal_shares(instance, profile, sat_class=Cost_Sat, resoluteness=resoluteness)

def mes_av_completion(instance, profile, resoluteness=True):
    return completion_by_rule_combination(
        instance,
        profile,
        [method_of_equal_shares, greedy_utilitarian_welfare],
        [{"sat_class": Cost_Sat}, {"sat_class": Cardinality_Sat}],
        resoluteness=resoluteness
    )

def mes_increment_completion(instance, profile, resoluteness=True):
    return exhaustion_by_budget_increase(
        instance,
        profile,
        method_of_equal_shares,
        {"sat_class": Cost_Sat},
        budget_step=instance.budget_limit * frac(1, 100),
        resoluteness=resoluteness
)

RULE_MAPPING = {
    "av": [av_via_max_card, av_via_greed_card, av_via_greed_cost, av_via_max_cost],
    "seqphragmen": [sequential_phragmen],
    # "equal-shares": [mes_card, mes_cost], -> This is actually the completion with phragmen with initial load
    "equal-shares-with-av-completion": [mes_av_completion],
    # "equal-shares-with-increment-completion": [mes_increment_completion], -> No irresolute outcomes
    "maximin-support": [maximin_support],
}

def abcvoting_to_pabutools(profile, committeesize: int):
    pb_instance = Instance()
    pb_instance.budget_limit = committeesize
    alt_to_project = {}
    for alt in profile.candidates:
        p = Project(alt, cost=1)
        pb_instance.add(p)
        alt_to_project[alt] = p
    pb_profile = ApprovalProfile()
    for voter in profile:
        pb_profile.append(ApprovalBallot([alt_to_project[a] for a in voter.approved]))
    return pb_instance, pb_profile

def read_abcvoting_file(file_path):
    abc_profile, budget_limit, _, _ = read_abcvoting_yaml_file(file_path)
    return abcvoting_to_pabutools(abc_profile, budget_limit)

def read_abcvoting_expected_result(file_path, instance, profile):
    with open(file_path) as f:
        data = yaml.safe_load(f)

    expected_results = dict()

    # Alternative that have support
    supported_alternatives = set()
    for alt in instance:
        if profile.approval_score(alt) > 0:
            supported_alternatives.add(int(alt.name))

    for entry in data["compute"]:
        if entry["rule_id"] in RULE_MAPPING and entry["resolute"] is False:
            potential_results = entry["result"]

            potential_results_representation = []
            for res in potential_results:
                res_representation = [a for a in res if a in supported_alternatives]
                res_representation.sort()
                if res_representation not in potential_results_representation:
                    potential_results_representation.append(res_representation)
            potential_results_representation.sort()

            expected_results[entry["rule_id"]] = potential_results_representation
    return expected_results

def resolute_res_representation(budget_allocation, instance, profile):
    # Alternative that have support
    supported_alternatives = set()
    for alt in instance:
        if profile.approval_score(alt) > 0:
            supported_alternatives.add(alt)
    return sorted([int(a.name) for a in budget_allocation if a in supported_alternatives])

def irresolute_res_representation(budget_allocations, instance, profile):
    res = []
    for alloc in budget_allocations:
        alloc_repr = resolute_res_representation(alloc, instance, profile)
        if alloc_repr not in res:
            res.append(alloc_repr)
    return sorted(res)

class TestRulesonABCVoting(TestCase):
    def test_rules_on_abcvoting(self):
        current_file_path = os.path.dirname(os.path.realpath(__file__))
        yaml_dir_path = os.path.join(current_file_path, "abcvoting_test_instances")
        all_yaml_files = os.listdir(yaml_dir_path)
        for yaml_file_index, yaml_file in enumerate(all_yaml_files):
            yaml_file_path = os.path.join(yaml_dir_path, yaml_file)

            instance, source_profile = read_abcvoting_file(yaml_file_path)

            print(f"{yaml_file_index + 1}/{len(all_yaml_files)} Testing on {yaml_file}: {len(instance)} projects and {source_profile.num_ballots()} voters")
            expected_result = read_abcvoting_expected_result(yaml_file_path, instance, source_profile)
            for abcvoting_rule, pb_rules in RULE_MAPPING.items():
                print(f"\t{abcvoting_rule}")
                potential_results_repr = expected_result[abcvoting_rule]
                for pb_rule in pb_rules:
                    for profile in [source_profile, source_profile.as_multiprofile()]:
                        try:
                            budget_allocation = pb_rule(instance, profile, resoluteness=True)
                            budget_allocation_repr = resolute_res_representation(budget_allocation, instance, profile)
                            self.assertIn(budget_allocation_repr, potential_results_repr)
                        except NotImplementedError:
                            pass

                        try:
                            budget_allocations = pb_rule(instance, profile, resoluteness=False)
                            budget_allocations_repr = irresolute_res_representation(budget_allocations, instance, profile)
                            self.assertEqual(budget_allocations_repr, potential_results_repr)
                        except NotImplementedError:
                            pass
