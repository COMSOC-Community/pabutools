"""
An implentation of the algorithms in:
"Fair Lotteries for Participatory Budgeting" 
by Haris Aziz, Xinhang Lu, Mashbat Suzuki, Jeremy Vollen, Toby Walsh (2024) 
https://ojs.aaai.org/index.php/AAAI/article/view/28801
Programmers: Dotan Danino, Naama Yahav.
Date: 19/4/2026
"""
import logging
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

logger = logging.getLogger("Algos")

class BinarySatisfaction(AdditiveSatisfaction):
    def __init__(self, *args, **kwargs):
        kwargs['func'] = lambda *a, **k: 1
        super().__init__(*args, **kwargs)

def dependent_rounding_bb1(p_vec_list: list, C: list, cost: dict) -> set:
    """
    Performs Dependent Randomized Rounding to convert a fractional
    probability vector into a discrete set of projects (0 or 1).
    This guarantees ex-post Budget Balance up to 1 project (BB1).
    
    Args:
        p_vec_list: A list of fractional probabilities corresponding to C.
        C: A list of project identifiers.
        cost: A dictionary mapping projects to their costs.
        
    Returns:
        set: The final selected discrete set of projects (W).
    """
    logger.info("Starting dependent_rounding_bb1 (BB1) with %d projects.", len(C))
    # Create a dictionary internally for easier tracking by project name
    logger.debug("Mapping probability list to project names.")
    p = {C[i]: p_vec_list[i] for i in range(len(C))}
    round_iteration = 1
    while True:
        # Find all projects with fractional probabilities (not exactly 0.0 or 1.0)
        fractional = [c for c, prob in p.items() if 0.0001 < prob < 0.9999]
        
        # If no fractional probabilities remain, the rounding is complete
        if len(fractional) == 0:
            logger.info("No fractional probabilities remain. Dependent rounding complete in %d iterations.", round_iteration)
            break
            
        # If exactly one fractional project remains, round it independently.
        if len(fractional) == 1:
            c = fractional[0]
            logger.info("Only 1 fractional project left (%s) with prob %.4f. Rounding independently.", c, p[c])
            if random.random() < p[c]:
                p[c] = 1.0
                logger.debug("Independent flip: Project %s rounded UP to 1.0.", c)
            else:
                p[c] = 0.0
                logger.debug("Independent flip: Project %s rounded DOWN to 0.0.", c)
            break
            
        # Select two fractional projects for the dependent rounding step
        i = fractional[0]
        j = fractional[1]
        logger.debug("Iteration %d: Selected pair for dependent rounding -> %s (prob %.4f) and %s (prob %.4f).", round_iteration, i, p[i], j, p[j])

        # Option A: Increase i, decrease j
        max_alpha_i = 1.0 - p[i]  
        max_alpha_j = p[j] * (cost[j] / cost[i])  
        alpha = min(max_alpha_i, max_alpha_j)
        beta = alpha * (cost[i] / cost[j])
        
        # Option B: Decrease i, increase j
        max_gamma_i = p[i]  
        max_gamma_j = (1.0 - p[j]) * (cost[j] / cost[i])  
        gamma = min(max_gamma_i, max_gamma_j)
        delta = gamma * (cost[i] / cost[j])
        
        # Calculate the probability (q) of choosing Option A 
        # (added a small safety check for zero division)
        if (alpha + gamma) > 0:
            q = gamma / (alpha + gamma)
        else:
            logger.warning("alpha + gamma is 0 for projects %s and %s. Setting q to 0.", i, j)
            q = 0.0
            
        # Flip a biased coin based on probability q
        if random.random() < q:
            p[i] += alpha
            p[j] -= beta
            logger.debug("Coin flip (%.4f < %.4f): Option A. %s increased by %.4f, %s decreased by %.4f.", rand_val, q, i, alpha, j, beta)
        else:
            p[i] -= gamma
            p[j] += delta
            logger.debug("Coin flip (%.4f >= %.4f): Option B. %s decreased by %.4f, %s increased by %.4f.", rand_val, q, i, gamma, j, delta)
        
        round_iteration += 1

    # Return the final set of selected projects
    W = {c for c, prob in p.items() if prob >= 0.9999}
    logger.info("BB1 dependent rounding finished. Final set contains %d projects.", len(W))
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
    # variable for the amount of voters
    n = len(N)
    logger.info("Starting BW_GCR_PB (Algorithm 1) with %d citizens and %d projects.", len(N), len(C))
    logger.debug("Total budget available: %f", B)
    # fixed the data types to make sure 
    # its will match the GCR algorithm.
    logger.debug("Converting basic types into pabutools Project and Instance objects.")
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
        logger.info("Calling the greedy_utilitarian_welfare algorithm from pabutools.")
        # calling for the GCR algo.
        gcr_allocation = greedy_utilitarian_welfare(
            instance=instance, 
            profile=profile,
            sat_class=BinarySatisfaction
        )
        
        selected_projects = {proj.name for proj in gcr_allocation}
        logger.info("GCR algorithm successfully selected %d projects.", len(selected_projects))
        logger.debug("Projects selected by GCR: %s", selected_projects)

    except Exception as e:
        logger.error("Error running Greedy rule from library: %s", e)
        selected_projects = set()

    """
    Finished the data structures fix and call for GCR ALGO and 
    """
    # Line 2:
    # Initialize the probability vector.
    # Projects selected by GCR get probability 1.
    # All other projects start with probability 0.
    p_vec = {c: 0.0 for c in C}
    for proj in selected_projects:
        p_vec[proj] = 1.0

    #line 3 initilaize N_tilde as an empty set
    N_tilde = set() 
    # line 4 bi <- 0 for all i in N
    b = {str(i): 0.0 for i in N} 
    
    # Line 5: Let {N^1, ..., N^eta} be the unanimous groups of N
    logger.debug("Grouping citizens into unanimous groups based on identical preferences.")
    groups_dict = {}
    for i in N:
        voter_str = str(i)
        # The key will be the project they want, if 2 or more wants the same projects
        # they will have the same key
        v_ui = ui.get(voter_str, {})
        approved = tuple(sorted([c for c, val in v_ui.items() if val == 1]))
        if approved not in groups_dict:
            groups_dict[approved] = []
        groups_dict[approved].append(voter_str)
    
    # Convert to a list of groups so we can safely iterate and
    # process each group's budget.
    unanimous_groups = list(groups_dict.values())
    logger.info("Identified %d unanimous groups among the citizens.", len(unanimous_groups))

    # Line 6: foreach unanimous group z do
    for idx, Nz in enumerate(unanimous_groups):
        logger.debug("Processing unanimous group %d (size: %d).", idx + 1, len(Nz))
        # Since everyone in Nz wants the same projects,
        # we just look at the first citizen's preferences 
        ui_NZ = ui.get(Nz[0], {})
        A_Nz = [c for c, val in ui_NZ.items() if val == 1]
        
        # sort py price to see how mant they can buy.(G_NZ)
        A_Nz_sorted = sorted(A_Nz, key=lambda x: cost[x])
        group_budget_limit = len(Nz) * (B / len(N))
        # calculate G_Nz
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
            logger.debug("Group %d meets the intersection condition. Allocating fractional probabilities.", idx + 1)
            # Line 8: N_tilde <- N_tilde U N^z
            N_tilde.update(Nz)
            
            # Line 9: Assign budgets bi <-B/n - (1/N_z) * cost(G_Nz)
            cost_G_Nz = sum(cost[c] for c in G_Nz)
            for i in Nz:
                b[i] = (B / n) - (1 / len(Nz)) * cost_G_Nz
                
            # Line 10: Let voters N^z spend their total budget on the cheapest project...
            total_group_budget = len(Nz) * (B / n) - cost_G_Nz
            logger.debug("Group %d has a leftover budget of %f to spend.", idx + 1, total_group_budget)

            for c in A_Nz_sorted:
                #searching for the cheapest available project
                if p_vec[c] < 1.0 and total_group_budget > 0:
                    max_prob_increase = 1.0 - p_vec[c]
                    prob_to_buy = total_group_budget / cost[c]
                    
                    actual_increase = min(max_prob_increase, prob_to_buy)
                    p_vec[c] += actual_increase
                    total_group_budget -= (actual_increase * cost[c])
                    logger.debug("Increased probability of project %s by %f.", c, actual_increase)

    # Line 11: Increase p arbitrarily such that cost(p) = B
    current_expected_cost = sum(p_vec[c] * cost[c] for c in C)
    remaining_budget = B - current_expected_cost
    logger.info("Finished processing groups. Current expected cost is %f. Remaining budget: %f.", current_expected_cost, remaining_budget)
    
    if remaining_budget < -0.0001:
        logger.warning("Warning: Remaining budget is negative (%f)! Expected cost exceeded total budget B.", remaining_budget)

    for c in C:
        if remaining_budget <= 0.0001: # small diffrence to avoid numerical issues
            break
        if p_vec[c] < 1.0:
            max_increase = 1.0 - p_vec[c]
            cost_for_max = max_increase * cost[c]
            
            if remaining_budget >= cost_for_max:
                p_vec[c] = 1.0
                remaining_budget -= cost_for_max
                logger.debug("Arbitrarily maxed out project %s to probability 1.0.", c)
            else:
                p_vec[c] += remaining_budget / cost[c]
                remaining_budget = 0
                logger.debug("Arbitrarily increased project %s probability. Budget is now fully exhausted.", c)

    p_vec_list = [p_vec[c] for c in C]
    logger.info("BW_GCR_PB execution completed successfully.")
    
    return p_vec_list

def BW_GCR_PB_wrapped(N: list, C: list, cost: dict, B: float, ui: dict) -> tuple[list, set]:
    logger.info("Starting BW_GCR_PB_wrapped. Validating input parameters.")
    # Check whether one of the parameters is None, and raise a ValueError
    if(N is None or C is None or cost is None or B is None or ui is None):
        logger.critical("Critical Validation Failure: One or more parameters are None.")
        raise ValueError("One or more of the parameters is null")
    # Check whether one of the parameters is empty, and raise a ValueError
    if(len(N)==0 or len(C)==0 or len(cost)==0 or B==0 or len(ui)==0):
        logger.critical("Critical Validation Failure: One or more parameters are empty.")
        raise ValueError("One or more of the parameters is empty")
    
    # Check whether the parameters are the same as the annotations 
    logger.debug("Validating parameter types against function annotations.")
    annotations= BW_GCR_PB_wrapped.__annotations__
    local_vars= locals()
    for x in annotations.keys():
        if x == "return":
            continue
        if(type(local_vars[x]) != annotations[x]):
            logger.error("Type mismatch: Parameter %s expected %s but got %s.", x, annotations[x], type(local_vars[x]))
            raise ValueError(f"Parameter {x} is not of the expected type {annotations[x]}")
    #lines 1-11 the explanation is in the function
    p_vec = BW_GCR_PB(N,C,cost,B,ui)
    # line 12: ObtainanoutcomeWsampledfromthelottery
    # implementingpbyapplyingTheorem3.2.
    logger.info("Applying BB1 dependent rounding to generate the final discrete set of projects.")
    final_proj = dependent_rounding_bb1(p_vec,C,cost)
    # line 13: return P and W
    logger.info("BW_GCR_PB_wrapped finished. Returning probability vector and %d selected projects.", len(final_proj))
    return p_vec,final_proj


# ==== Helper functions to convert the input into the relevant classes in pabutools,
# to be able to use the method_of_equal_shares function= MES implementation in pabutools. ====

def clean_number(x):
    """
    Convert a numeric value into a regular Python int or float.

    This helper is used because some numeric types, such as numpy numeric
    types, may not be accepted by pabutools' internal fraction utilities.
    If the value represents a whole number, it is converted to int.
    Otherwise, it is kept as float.

    Args:
        x: A numeric value.

    Returns:
        int | float: The cleaned numeric value.
    """
    x = float(x)

    if x.is_integer():
        return int(x)

    return x

def build_instance(C, cost, B):
    """
    Build a pabutools Instance object from the PB input.

    Each project name in C is converted into a pabutools Project object
    with its corresponding cost. The total budget B is stored as the
    budget limit of the instance.

    Args:
        C: A list of project identifiers.
        cost: A dictionary mapping each project to its cost.
        B: The total available budget.

    Returns:
        Instance: A pabutools instance containing the projects and budget limit.
    """
    projects = []

    for c in C:
        projects.append(Project(c, cost[c]))

    return Instance(projects, budget_limit=clean_number(B))

def build_profile(N, ui, instance):
    """
    Build a pabutools approval profile from the citizens' utility matrix.

    For each citizen, an ApprovalBallot is created containing exactly the
    projects that the citizen approves, meaning projects with utility 1.
    Project names are converted into pabutools Project objects using the
    given instance.

    Args:
        N: A list of citizens.
        ui: A dictionary mapping each citizen to utilities over projects.
        instance: The pabutools Instance containing the project objects.

    Returns:
        Profile: A pabutools approval profile.
    """
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
    """
    Define the approval-based satisfaction function used by MES.

    A citizen receives satisfaction 1 from a project if the project appears
    in their approval ballot, and 0 otherwise. This function is passed to
    pabutools' method_of_equal_shares as the satisfaction class.

    Args:
        instance: The pabutools Instance.
        profile: The pabutools Profile.
        ballot: The current citizen's approval ballot.

    Returns:
        AdditiveSatisfaction: The satisfaction measure for the given ballot.
    """
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
    Algorithm 2: accepts an instance of PB and returns a probabilities vector that satisfy strong UFS and EJR.
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
    logger.info("Starting BW_MES_PB (Algorithm 2) with %d citizens and %d projects.", len(N), len(C))
    logger.debug("Total budget available: %f", B)
    # Line 1:
    # Convert the input into pabutools objects and run MES.
    # The result of MES is the initial winning set W.
    logger.debug("Building pabutools Instance and Profile objects.")
    instance = build_instance(C, cost, B)
    profile = build_profile(N, ui, instance)
    try:
        logger.info("Calling method_of_equal_shares (MES) from pabutools.")
        allocation = method_of_equal_shares(
            instance,
            profile,
            sat_class=approval_sat
        )
        W = {p.name for p in allocation}
        logger.info("MES algorithm successfully selected %d projects deterministically.", len(W))
        logger.debug("Projects selected by MES: %s", W)
    except Exception as e:
        logger.error("Method of equal shares failed: %s", e)
        W = set()

    # Line 2:
    # Initialize the probability vector.
    # Projects selected by MES get probability 1.
    # All other projects start with probability 0.
    p_vec = {c: (1.0 if c in W else 0.0) for c in C}

    # Line 3:
    # Compute how much each citizen paid for the projects in W.
    # For each selected project, its cost is divided equally among its supporters.
    logger.debug("Calculating how much budget each citizen spent on the MES selected projects.")
    spent = {i: 0 for i in N}
    
    for c in W:
        supporters = [i for i in N if ui[i][c] == 1]
        if not supporters:
            continue
        share = cost[c] / len(supporters)
        for i in supporters:
            spent[i] += share
    
    # Line 4:
    # Compute the remaining budget of each citizen after paying for the MES projects.
    # Initially, each citizen receives an equal share of the total budget B / |N|.
    budget_per_voter = B / len(N)
    remaining = {i: budget_per_voter - spent[i] for i in N}

    # Line 5:
    # Build N_prime:
    # the set of citizens who still have remaining budget and still approve
    # at least one project that was not selected by MES.
    logger.debug("Identifying N_prime: Citizens with remaining budget who approve unselected projects.")
    N_prime = [
        i for i in N
        if remaining[i] > 0 and any(ui[i][c] == 1 for c in C if c not in W)
    ]
    logger.info("Found %d citizens in N_prime.", len(N_prime))
    # Lines 6-8:
    # Each citizen in N_prime spends their remaining budget only on projects
    # they approve and that are not already in W.
    # The projects are considered from cheapest to most expensive.
    # The citizen contributes as much as possible to each project until either
    # the project reaches probability 1 or the citizen has no money left.
    logger.debug("Allocating fractional probabilities for N_prime citizens based on their remaining budget.")
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
            logger.debug("Citizen %s contributed %f to project %s. Probability increased by %f.", i, payment, c, increase)

    # Lines 9-10:
    # Handle citizens that are not in N_prime.
    # These citizens either have no remaining approved projects or cannot
    # contribute to the previous step. Their remaining budget is assigned
    # to unselected projects according to the deterministic project order.
    logger.debug("Processing leftover budget for N_minus (citizens not in N_prime).")
    N_minus = [i for i in N if i not in N_prime]
    remaining_projects = [c for c in C if c not in W]

    if remaining_projects:
        c = remaining_projects[0]   # deterministic instead of random

        total_available = sum(remaining[i] for i in N_minus)

        if total_available > 0:
            needed = cost[c] * (1 - p_vec[c])

            if needed > 0:
                payment = min(total_available, needed)
                p_vec[c] += payment / cost[c]
                logger.debug("Aggregated leftover budget (%f) used to increase project %s probability by %f.", payment, c, increase)

                for i in N_minus:
                    remaining[i] = 0

    # Line 11:
    # Normalize probabilities that are numerically close to 1.
    # If a project reaches probability 1, it is treated as fully funded.
    logger.debug("Normalizing probabilities close to 1.0 to avoid floating point inaccuracies.")
    EPS = 1e-9
    for c in C:
        if p_vec[c] >= 1 - EPS:
            p_vec[c] = 1.0
            W.add(c)
    probabilities = [p_vec[c] for c in C]
    logger.info("BW_MES_PB execution completed successfully.")
    return probabilities

def BW_MES_PB_wrapped(N: list, C: list, cost: dict, B: float, ui: dict) -> tuple[list, set]:
    """
    Final wrapper for Algorithm 2:
    Validate the input, run BW_MES_PB, and apply dependent rounding.

    This wrapper checks that the input is not None, not empty, and has the
    expected basic types. It then computes the probability vector using
    BW_MES_PB and applies dependent_rounding_bb1 in order to obtain a final
    feasible set of selected projects.

    Args:
        N: A list of citizens.
        C: A list of projects.
        cost: A dictionary mapping each project to its cost.
        B: The total available budget.
        ui: A dictionary mapping each citizen to binary utilities over projects.

    Returns:
        tuple[list, set]:
            The probability vector returned by BW_MES_PB and the final set
            of selected projects returned by dependent rounding.

    Raises:
        ValueError: If one of the parameters is None, empty, or has an
        unexpected type.
    """
    # Check whether one of the parameters is None, and raise a ValueError
    if(N is None or C is None or cost is None or B is None or ui is None):
        logger.critical("Critical Validation Failure: One or more parameters are None.")
        raise ValueError("One or more of the parameters is null")
    # Check whether one of the parameters is empty, and raise a ValueError
    if(len(N)==0 or len(C)==0 or len(cost)==0 or B==0 or len(ui)==0):
        logger.critical("Critical Validation Failure: One or more parameters are empty.")
        raise ValueError("One or more of the parameters is empty")
    
    # Check whether the parameters are the same as the annotations
    logger.debug("Validating parameter types against function annotations.") 
    annotations= BW_MES_PB_wrapped.__annotations__
    local_vars= locals()
    for x in annotations.keys():
        if x == "return":
            continue
        if(type(local_vars[x]) != annotations[x]):
            logger.error("Type mismatch: Parameter %s expected %s but got %s.", x, annotations[x], type(local_vars[x]))
            raise ValueError(f"Parameter {x} is not of the expected type {annotations[x]}")
    
    p_vec = BW_MES_PB(N,C,cost,B,ui)
    # Line 12:
    # Send the probability vector to the BB1 dependent rounding mechanism.
    # BB1 converts the fractional probabilities into a final feasible set of selected projects.
    logger.info("Applying BB1 dependent rounding to generate the final discrete set of projects.")
    final_proj = dependent_rounding_bb1(p_vec,C,cost)

    logger.info("BW_MES_PB_wrapped finished. Returning probability vector and %d selected projects.", len(final_proj))#Line 13: Return the probability vector and the final set of selected projects.
    return p_vec,final_proj



if __name__ == "__main__":
    import doctest
    doctest.testmod()
   