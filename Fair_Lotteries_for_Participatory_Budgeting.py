"""
An implentation of the algorithms in:
"Fair Lotteries for Participatory Budgeting" 
by Haris Aziz, Xinhang Lu, Mashbat Suzuki, Jeremy Vollen, Toby Walsh (2024) 
https://ojs.aaai.org/index.php/AAAI/article/view/28801
Programmers: Dotan Danino, Naama Yahav.
Date: 19/4/2026
"""

import random
from pabutools.rules.mes import method_of_equal_shares
from pabutools.election.instance import Instance, Project
from pabutools.election.profile import Profile
from pabutools.election.ballot.approvalballot import ApprovalBallot
from pabutools.election.ballot import ApprovalBallot
from pabutools.election.satisfaction import AdditiveSatisfaction
from pabutools.election.profile.approvalprofile import ApprovalProfile
from pabutools.rules.greedywelfare.greedywelfare_rule import greedy_utilitarian_welfare
from pabutools.election.satisfaction import AdditiveSatisfaction


class BinarySatisfaction(AdditiveSatisfaction):
    def __init__(self, *args, **kwargs):
        kwargs['func'] = lambda *a, **k: 1
        super().__init__(*args, **kwargs)

def dependent_rounding_bb1(p_vec: dict, cost: dict) -> set:
    """
    Performs Dependent Randomized Rounding to convert a fractional
    probability vector into a discrete set of projects (0 or 1),
    ensuring ex-post Budget Balanced up to 1 project (BB1).
    """
    # Create a copy of the probabilities to modify
    p = p_vec.copy()
    
    while True:
        # Find all projects with fractional probabilities (not exactly 0.0 or 1.0)
        fractional = [c for c, prob in p.items() if 0.0001 < prob < 0.9999]
        
        # If no fractional probabilities remain, the rounding is complete
        if len(fractional) == 0:
            break
            
        # If exactly one fractional project remains, round it independently.
        # This single independent rounding step is what causes the BB1 deviation.
        if len(fractional) == 1:
            c = fractional[0]
            if random.random() < p[c]:
                p[c] = 1.0
            else:
                p[c] = 0.0
            break
            
        # Select two fractional projects for the dependent rounding step
        i = fractional[0]
        j = fractional[1]
        
        # We want to either increase p[i] and decrease p[j] (Option A),
        # or decrease p[i] and increase p[j] (Option B),
        # such that the expected overall budget remains exactly the same.
        
        # Option A: Increase i, decrease j
        max_alpha_i = 1.0 - p[i]  # Max amount i can increase until reaching 1.0
        max_alpha_j = p[j] * (cost[j] / cost[i])  # Max amount i can increase before j hits 0.0
        alpha = min(max_alpha_i, max_alpha_j)
        beta = alpha * (cost[i] / cost[j])
        
        # Option B: Decrease i, increase j
        max_gamma_i = p[i]  # Max amount i can decrease until reaching 0.0
        max_gamma_j = (1.0 - p[j]) * (cost[j] / cost[i])  # Max amount i can decrease before j hits 1.0
        gamma = min(max_gamma_i, max_gamma_j)
        delta = gamma * (cost[i] / cost[j])
        
        # Calculate the probability (q) of choosing Option A 
        # to ensure the expected value remains unchanged (keeping the lottery fair)
        q = gamma / (alpha + gamma)
        
        # Flip a biased coin based on probability q
        if random.random() < q:
            p[i] += alpha
            p[j] -= beta
        else:
            p[i] -= gamma
            p[j] += delta

    # Return the final set of selected projects (where probability reached 1.0)
    W = {c for c, prob in p.items() if prob >= 0.9999}
    return W

def BW_GCR_PB(N: list, C: list, cost: dict, B: float, ui: dict) -> list:
    """
    Algorithm 1: accepts an instance of PB and returns a probabilities vector and a set of projects that satisfy strong UFS and FJR.
    Args:
        N: A list of citizens.
        C: A list of projects.
        cost: A dictionary mapping each project to its cost.
        B: The total budget available.
        ui: A dictionary mapping each citizen to a dictionary of their utilities for each project.

        Example 1: Enough budget for all projects:
        >>> N = ['1', '2']
        >>> C = ['a', 'b', 'c']
        >>> cost = {'a': 21000, 'b': 10000, 'c': 2000}
        >>> B = 33000
        >>> ui = {
        ... '1': {'a': 1, 'b': 1, 'c': 0},
        ... '2': {'a': 0, 'b': 1, 'c': 1}
        ... }
        >>> BW_GCR_PB(N, C, cost, B, ui)
        [1.0, 1.0, 1.0]

        Example 2: Different output for each algorithm:
        >>> N = ['1', '2', '3']
        >>> C = ['a', 'b', 'c', 'd']
        >>> cost = {'a': 8000, 'b': 8000, 'c': 12000, 'd': 12000}
        >>> B = 30000
        >>> ui = {
        ... '1': {'a': 1, 'b': 0, 'c': 1, 'd': 0},
        ... '2': {'a': 0, 'b': 0, 'c': 1, 'd': 1},
        ... '3': {'a': 0, 'b': 1, 'c': 0, 'd': 1}
        ... }
        >>> BW_GCR_PB(N, C, cost, B, ui)
        [1.0, 1.0, 1.0, 0.16666666666666666]


        Example 3: "bad" output for the algorithm:
        >>> N = ['1', '2', '3', '4']
        >>> C = ['a', 'b']
        >>> cost = {'a': 1000, 'b': 5000}
        >>> B = 5000
        >>> ui = {
        ... '1': {'a': 1, 'b': 1},
        ... '2': {'a': 0, 'b': 1},
        ... '3': {'a': 0, 'b': 1},
        ... '4': {'a': 0, 'b': 1}
        ... }
        >>> BW_GCR_PB(N, C, cost, B, ui)
        [1.0, 0.8]

        
        Example 4: Many Projects, many Citizens:
        >>> N = ['1', '2', '3', '4', '5', '6', '7', '8']
        >>> C = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
        >>> cost = {'a': 8000, 'b': 15000, 'c': 10000, 'd': 10000, 'e': 6000, 'f': 12000, 'g': 9000, 'h': 9000, 'i': 5000, 'j': 5000}
        >>> B = 80000
        >>> ui = {
        ... '1': {'a': 1, 'b': 1, 'c': 1, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
        ... '2': {'a': 1, 'b': 1, 'c': 1, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
        ... '3': {'a': 1, 'b': 1, 'c': 0, 'd': 1, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
        ... '4': {'a': 1, 'b': 1, 'c': 0, 'd': 1, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
        ... '5': {'a': 1, 'b': 1, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
        ... '6': {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 1, 'f': 1, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
        ... '7': {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 1, 'h': 1, 'i': 0, 'j': 0},
        ... "8": {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 1, 'j': 1}
        ... }
        >>> BW_GCR_PB(N, C, cost, B, ui)
        [1.0, 0.4, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0]

        Example 5: not covering all code lines:
        >>> N = ['1', '2', '3']
        >>> C = ['a', 'b', 'c']
        >>> cost = {'a': 5000, 'b': 5000, 'c': 6000}
        >>> B = 15000
        >>> ui = {
        ... '1': {'a': 1, 'b': 1, 'c': 1},
        ... '2': {'a': 1, 'b': 1, 'c': 1},
        ... '3': {'a': 1, 'b': 1, 'c': 0}
        ... }
        >>> BW_GCR_PB(N, C, cost, B, ui)
        [1.0, 1.0, 0.8333333333333334]
    """

    # fixed the data types to make sure 
    # its will match the GCR alghoritm.
    n = len(N)
    projects_objects = [Project(name=c, cost=cost[c]) for c in C]
    
    instance = Instance(projects_objects)
    instance.budget_limit = B

    profile = ApprovalProfile()
    
    for voter_id in N:
        prefs = ui.get(str(voter_id), {}) 
        approved_projects = [proj for proj, val in prefs.items() if val == 1]
        ballot = ApprovalBallot(approved_projects)
        
        try:
            profile.add_voter(voter_id, ballot)
        except AttributeError:
            profile.append(ballot)

    try:
        # calling for the GCR algo.
        gcr_allocation = greedy_utilitarian_welfare(
            instance=instance, 
            profile=profile,
            sat_class=BinarySatisfaction
        )
        
        selected_projects = {proj.name for proj in gcr_allocation}
        
    except Exception as e:
        print(f"Error running Greedy rule from library: {e}")
        selected_projects = set()

    p_vec = {c: 0.0 for c in C}
    for proj in selected_projects:
        p_vec[proj] = 1.0

    N_tilde = set() #line 3
    b = {str(i): 0.0 for i in N} # line 4


    # Line 5: Let {N^1, ..., N^eta} be the unanimous groups of N
    groups_dict = {}
    for i in N:
        voter_str = str(i)
        # The key will be the project they want, if 2 or more wants the same projects
        # they will have the same key
        approved = tuple(sorted([c for c, val in ui[voter_str].items() if val == 1]))
        if approved not in groups_dict:
            groups_dict[approved] = []
        groups_dict[approved].append(voter_str)
    
    unanimous_groups = list(groups_dict.values())


    # Line 6: foreach unanimous group z do
    for Nz in unanimous_groups:
        # they all want the same projects
        A_Nz = [c for c, val in ui[Nz[0]].items() if val == 1]
        
        # sort py price to see how mant they can buy.   
        A_Nz_sorted = sorted(A_Nz, key=lambda x: cost[x])
        group_budget_limit = len(Nz) * (B / len(N))
        
        G_Nz = []
        current_cost = 0.0
        for c in A_Nz_sorted:
            if current_cost + cost[c] <= group_budget_limit:
                G_Nz.append(c)
                current_cost += cost[c]
            else:
                break
                
        # Line 7: if |A_Nz \cap W_GCR| == |G_Nz|
        A_Nz_intersect_W_GCR = [c for c in A_Nz if c in selected_projects]
        if len(A_Nz_intersect_W_GCR) == len(G_Nz):
            # Line 8: N_tilde <- N_tilde U N^z
            N_tilde.update(Nz)
            
            # Line 9: Assign budgets
            cost_G_Nz = sum(cost[c] for c in G_Nz)
            for i in Nz:
                b[i] = (B / n) - (1 / len(Nz)) * cost_G_Nz
                
            # Line 10: Let voters N^z spend their total budget on the cheapest project...
            total_group_budget = len(Nz) * (B / n) - cost_G_Nz
            
            for c in A_Nz_sorted:
                if p_vec[c] < 1.0 and total_group_budget > 0:
                    max_prob_increase = 1.0 - p_vec[c]
                    prob_to_buy = total_group_budget / cost[c]
                    
                    actual_increase = min(max_prob_increase, prob_to_buy)
                    p_vec[c] += actual_increase
                    total_group_budget -= (actual_increase * cost[c])

    # Line 11: Increase p arbitrarily such that cost(p) = B
    current_expected_cost = sum(p_vec[c] * cost[c] for c in C)
    remaining_budget = B - current_expected_cost
    for c in C:
        if remaining_budget <= 0.0001: # small diffrence to avoid numerical issues
            break
        if p_vec[c] < 1.0:
            max_increase = 1.0 - p_vec[c]
            cost_for_max = max_increase * cost[c]
            
            if remaining_budget >= cost_for_max:
                p_vec[c] = 1.0
                remaining_budget -= cost_for_max
            else:
                p_vec[c] += remaining_budget / cost[c]
                remaining_budget = 0

    p_vec_list = [p_vec[c] for c in C]
    W_sorted = [c for c in C if c in selected_projects]
    
    return p_vec_list

def BW_GCR_PB_wrapped(N: list, C: list, cost: dict, B: float, ui: dict) -> set:
    p_vec  = BW_GCR_PB(N,C,cost,B,ui)
    final_proj = dependent_rounding_bb1(p_vec,cost)
    return final_proj



def build_instance(C, cost, B):
    projects = []

    for c in C:
        projects.append(Project(c, cost[c]))

    return Instance(projects, budget_limit=B)

def build_profile(N, ui, instance):

    ballots = []

    for n in N:
        approved_projects = [
            instance.get_project(c)  
            for c in ui[n]
            if ui[n][c] == 1
        ]

        ballot = ApprovalBallot(approved_projects) 
        ballots.append(ballot)

    return Profile(ballots, instance=instance)
def approval_sat(instance, profile, ballot):
    def f(instance2, profile2, ballot2, project, *rest):
        return 1 if project in ballot else 0
    return AdditiveSatisfaction(
        instance,
        profile,
        ballot,
        func=f
    )

def BW_MES_PB(N: list, C: list, cost: dict, B: float, ui: dict) ->  list:
    """
    Algorithm 2: accepts an instance of PB and returns a probabilities vector and a set of projects that satisfy strong UFS and EJR.
    Args:
        N: A list of citizens.
        C: A list of projects.
        cost: A dictionary mapping each project to its cost.
        B: The total budget available.
        ui: A dictionary mapping each citizen to a dictionary of their utilities for each project.

        Example 1: Enough budget for all projects:
        >>> N = ['1', '2']
        >>> C = ['a', 'b', 'c']
        >>> cost = {'a': 21000, 'b': 10000, 'c': 2000}
        >>> B = 33000
        >>> ui = {
        ... '1': {'a': 1, 'b': 1, 'c': 0},
        ... '2': {'a': 0, 'b': 1, 'c': 1}
        ... }
        >>> BW_MES_PB(N, C, cost, B, ui)
        [1.0, 1.0, 1.0]

        Example 2: Different output for each algorithm:
        >>> N = ['1', '2', '3']
        >>> C = ['a', 'b', 'c', 'd']
        >>> cost = {'a': 8000, 'b': 8000, 'c': 12000, 'd': 12000}
        >>> B = 30000
        >>> ui = {
        ... '1': {'a': 1, 'b': 0, 'c': 1, 'd': 0},
        ... '2': {'a': 0, 'b': 0, 'c': 1, 'd': 1},
        ... '3': {'a': 0, 'b': 1, 'c': 0, 'd': 1}
        ... }
        >>> BW_MES_PB(N, C, cost, B, ui)
        [0.5, 1.0, 1.0, 0.5]


        Example 3: "bad" output for the algorithm:
        >>> N = ['1', '2', '3', '4']
        >>> C = ['a', 'b']
        >>> cost = {'a': 1000, 'b': 5000}
        >>> B = 5000
        >>> ui = {
        ... '1': {'a': 1, 'b': 1},
        ... '2': {'a': 0, 'b': 1},
        ... '3': {'a': 0, 'b': 1},
        ... '4': {'a': 0, 'b': 1}
        ... }
        >>> BW_MES_PB(N, C, cost, B, ui)
        [1.0, 0.8]

        
        Example 4: Many Projects, many Citizens:
        >>> N = ['1', '2', '3', '4', '5', '6', '7', '8']
        >>> C = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
        >>> cost = {'a': 8000, 'b': 15000, 'c': 10000, 'd': 10000, 'e': 6000, 'f': 12000, 'g': 9000, 'h': 9000, 'i': 5000, 'j': 5000}
        >>> B = 80000
        >>> ui = {
        ... '1': {'a': 1, 'b': 1, 'c': 1, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
        ... '2': {'a': 1, 'b': 1, 'c': 1, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
        ... '3': {'a': 1, 'b': 1, 'c': 0, 'd': 1, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
        ... '4': {'a': 1, 'b': 1, 'c': 0, 'd': 1, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
        ... '5': {'a': 1, 'b': 1, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
        ... '6': {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 1, 'f': 1, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
        ... '7': {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 1, 'h': 1, 'i': 0, 'j': 0},
        ... "8": {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 1, 'j': 1}
        ... }
        >>> BW_MES_PB(N, C, cost, B, ui)
        [1.0, 1.0, 1.0, 1.0, 1.0, 0.9166666666666667, 1.0, 0.1111111111111111, 1.0, 1.0]

    """

    # Casting the input to the relevant classes in pabutools, to be able to use the method_of_equal_shares function= MES implementation in pabutools.
    # ===== 1 =====
    instance = build_instance(C, cost, B)
    profile = build_profile(N, ui, instance)
    allocation = method_of_equal_shares(
        instance,
        profile,
        sat_class=approval_sat
    )
    W = {p.name for p in allocation}

    # ===== 2 =====
    p_vec = {c: (1.0 if c in W else 0.0) for c in C}

    # ===== 3 =====
    spent = {i: 0 for i in N}
    
    for c in W:
        supporters = [i for i in N if ui[i][c] == 1]
        if not supporters:
            continue
        share = cost[c] / len(supporters)
        for i in supporters:
            spent[i] += share
    
    # ===== 4 =====
    budget_per_voter = B / len(N)
    remaining = {i: budget_per_voter - spent[i] for i in N}

    # ===== 5 =====
    N_prime = [
        i for i in N
        if remaining[i] > 0 and any(ui[i][c] == 1 for c in C if c not in W)
    ]

    # ===== 6-8 =====
    for i in N_prime:
        liked_projects = sorted(
            [c for c in C if c not in W and ui[i][c] == 1],
            key=lambda c: cost[c]
        )
        for c in liked_projects:
            if remaining[i] <= 0:
                break
            needed = cost[c] * (1 - p_vec[c])
            if needed <= 0:
                continue
            payment = min(remaining[i], needed)
            remaining[i] -= payment
            p_vec[c] += payment / cost[c]

    # ===== 9-10 =====
    N_minus = [i for i in N if i not in N_prime]
    remaining_projects = [c for c in C if c not in W]

    if remaining_projects:
        c = remaining_projects[0]   # deterministic במקום random

        total_available = sum(remaining[i] for i in N_minus)

        if total_available > 0:
            needed = cost[c] * (1 - p_vec[c])

            if needed > 0:
                payment = min(total_available, needed)
                p_vec[c] += payment / cost[c]

                for i in N_minus:
                    remaining[i] = 0
    # ===== 11 =====
    EPS = 1e-9
    for c in C:
        if p_vec[c] >= 1 - EPS:
            p_vec[c] = 1.0
            W.add(c)
    probabilities = [p_vec[c] for c in C]
    W_sorted = [c for c in C if c in W]
    return probabilities

def BW_MES_PB_wrapped(N: list, C: list, cost: dict, B: float, ui: dict) -> list:
    p_vec = BW_MES_PB(N,C,cost,B,ui)
    final_proj = dependent_rounding_bb1(p_vec,cost)
    return final_proj

if __name__ == "__main__":
    import doctest
    doctest.testmod()
   