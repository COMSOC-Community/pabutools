"""
An implentation of the algorithms in:
"Fair Lotteries for Participatory Budgeting" 
by Haris Aziz, Xinhang Lu, Mashbat Suzuki, Jeremy Vollen, Toby Walsh (2024) 

Programmers: Dotan Danino, Naama Yahav.
Date: 19/4/2026
"""

def BW_GCR_PB(N: list, C: list, cost: dict, B: float, ui: dict) -> tuple[list, set]:
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
            '1': {'a': 1, 'b': 1, 'c': 0},
            '2': {'a': 0, 'b': 1, 'c': 1}
        }
        >>> BW_GCR_PB(N, C, cost, B, ui)
        ([1.0, 1.0, 1.0], {'a', 'b', 'c'})

        Example 2: Different output for each algorithm:
        >>> N = ['1', '2', '3']
        >>> C = ['a', 'b', 'c', 'd']
        >>> cost = {'a': 8000, 'b': 8000, 'c': 12000, 'd': 12000}
        >>> B = 30000
        >>> ui = {
            '1': {'a': 1, 'b': 0, 'c': 1, 'd': 0},
            '2': {'a': 0, 'b': 0, 'c': 1, 'd': 1},
            '3': {'a': 0, 'b': 1, 'c': 0, 'd': 1}
        }
        >>> BW_GCR_PB(N, C, cost, B, ui)
        ([1,1,1,1/6], {'a', 'b', 'c'})


        Example 3: "bad" output for the algorithm:
        >>> N = ['1', '2', '3', '4']
        >>> C = ['a', 'b']
        >>> cost = {'a': 1000, 'b': 5000}
        >>> B = 5000
        >>> ui = {
            '1': {'a': 1, 'b': 1},
            '2': {'a': 0, 'b': 1},
            '3': {'a': 0, 'b': 1},
            '4': {'a': 0, 'b': 1}
        }
        >>> BW_GCR_PB(N, C, cost, B, ui)
        ([1.0, 0.8], {'a'})

        
        Example 4: Many Projects, many Citizens:
        >>> N = ['1', '2', '3', '4', '5', '6', '7', '8']
        >>> C = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
        >>> cost = {'a': 8000, 'b': 15000, 'c': 10000, 'd': 10000, 'e': 6000, 'f': 12000, 'g': 9000, 'h': 9000, 'i': 5000, 'j': 5000}
        >>> B = 80000
        >>> ui = {
            '1': {'a': 1, 'b': 1, 'c': 1, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
            '2': {'a': 1, 'b': 1, 'c': 1, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
            '3': {'a': 1, 'b': 1, 'c': 0, 'd': 1, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
            '4': {'a': 1, 'b': 1, 'c': 0, 'd': 1, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
            '5': {'a': 1, 'b': 1, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
            '6': {'a': 1, 'b': 1, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
            '7': {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 0, 'f': 1, 'g': 1, 'h': 1, 'i': 0, 'j': 0},
            "8": {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 1, 'j': 1}
        }
        >>> BW_GCR_PB(N, C, cost, B, ui)
        ([1.0, 0.4, 1.0, 1.0, 1.0, 1/3, 1.0, 1/9, 1.0, 1.0], {'a', 'c', 'd', 'e', 'g', 'i', 'j'})

        Example 5: not covering all code lines:
        >>> N = ['1', '2', '3']
        >>> C = ['a', 'b', 'c']
        >>> cost = {'a': 5000, 'b': 5000, 'c': 6000}
        >>> B = 15000
        >>> ui = {
            '1': {'a': 1, 'b': 1, 'c': 1},
            '2': {'a': 1, 'b': 1, 'c': 1},
            '3': {'a': 1, 'b': 1, 'c': 0}
        }
        >>> BW_GCR_PB(N, C, cost, B, ui)
        ([1.0, 1.0, 5/6], {'a', 'b'})
    """

def BW_MES_PB(N: list, C: list, cost: dict, B: float, ui: dict) -> tuple[list, set]:
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
            '1': {'a': 1, 'b': 1, 'c': 0},
            '2': {'a': 0, 'b': 1, 'c': 1}
        }
        >>> BW_GCR_PB(N, C, cost, B, ui)
        ([1.0, 1.0, 1.0], {'a', 'b', 'c'})

        Example 2: Different output for each algorithm:
        >>> N = ['1', '2', '3']
        >>> C = ['a', 'b', 'c', 'd']
        >>> cost = {'a': 8000, 'b': 8000, 'c': 12000, 'd': 12000}
        >>> B = 30000
        >>> ui = {
            '1': {'a': 1, 'b': 0, 'c': 1, 'd': 0},
            '2': {'a': 0, 'b': 0, 'c': 1, 'd': 1},
            '3': {'a': 0, 'b': 1, 'c': 0, 'd': 1}
        }
        >>> BW_GCR_PB(N, C, cost, B, ui)
        ([0.5,1,1.0,0.5], {'b', 'c'})


        Example 3: "bad" output for the algorithm:
        >>> N = ['1', '2', '3', '4']
        >>> C = ['a', 'b']
        >>> cost = {'a': 1000, 'b': 5000}
        >>> B = 5000
        >>> ui = {
            '1': {'a': 1, 'b': 1},
            '2': {'a': 0, 'b': 1},
            '3': {'a': 0, 'b': 1},
            '4': {'a': 0, 'b': 1}
        }
        >>> BW_GCR_PB(N, C, cost, B, ui)
        ([1.0, 0.8], {'a'})

        
        Example 4: Many Projects, many Citizens:
        >>> N = ['1', '2', '3', '4', '5', '6', '7', '8']
        >>> C = ['a', 'b', 'c', 'd', 'e', 'f', 'g', 'h', 'i', 'j']
        >>> cost = {'a': 8000, 'b': 15000, 'c': 10000, 'd': 10000, 'e': 6000, 'f': 12000, 'g': 9000, 'h': 9000, 'i': 5000, 'j': 5000}
        >>> B = 80000
        >>> ui = {
            '1': {'a': 1, 'b': 1, 'c': 1, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
            '2': {'a': 1, 'b': 1, 'c': 1, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
            '3': {'a': 1, 'b': 1, 'c': 0, 'd': 1, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
            '4': {'a': 1, 'b': 1, 'c': 0, 'd': 1, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
            '5': {'a': 1, 'b': 1, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
            '6': {'a': 1, 'b': 1, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 0, 'j': 0},
            '7': {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 0, 'f': 1, 'g': 1, 'h': 1, 'i': 0, 'j': 0},
            "8": {'a': 0, 'b': 0, 'c': 0, 'd': 0, 'e': 0, 'f': 0, 'g': 0, 'h': 0, 'i': 1, 'j': 1}
        }
        >>> BW_GCR_PB(N, C, cost, B, ui)
        ([1.0, 1.0, 1.0, 1.0, 1.0, 7/12, 1.0, 0.0, 1.0, 1.0], {'a', 'b', 'c', 'd', 'e', 'g', 'i', 'j'})

    """