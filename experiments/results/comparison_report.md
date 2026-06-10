# Section A – Performance Comparison

## Experiment Description

This experiment compares the performance of the algorithms from the paper
**"Streamlining Equal Shares"** (Kraiczy, Robinson, Elkind, 2024)
against other Participatory Budgeting rules from the `pabutools` library.

### Algorithms Tested

| Algorithm | Description | Source |
|-----------|-------------|--------|
| **EES** | Exact Equal Shares (Algorithm 1) – selects projects by bang-per-buck ratio, splitting costs equally among supporters | Paper, `ees_addopt.py` |
| **EES_AddOpt** | EES + Add-Opt Completion (Corollary 4.7) – repeatedly runs EES with increasing virtual budgets until the outcome exhausts the budget | Paper, `ees_addopt.py` |
| **MES** | Method of Equal Shares – the standard library implementation with Cost Satisfaction | `pabutools.rules.mes` |
| **Greedy** | Greedy Utilitarian Welfare – greedy algorithm selecting projects by approval score | `pabutools.rules.greedywelfare` |

### Metrics Measured

1. **runtime** – execution time in seconds
2. **remaining_budget** – unused budget (budget_limit − total_cost)
3. **total_cost** – total cost of selected projects
4. **social_welfare** – sum of approval scores for selected projects
5. **num_selected** – number of selected projects

### Experiment Parameters

All 4 algorithms run on **exactly the same inputs**:

- **Number of projects**: 10, 30, 60, 100
- **Number of voters**: 50
- **Repetitions**: 3 runs (seeds: 1, 2, 3) – averages shown in plots
- **Input generation**: random costs between 0 and 100, budget = 40%–80% of total cost, approval probability = 0.4

### Tools

- `experiments-csv` library for experiment definition and CSV output
- `matplotlib` for plotting

---

## Results

### Runtime

![Runtime](runtime_voters_50.png)

| Algorithm | 10 projects | 30 projects | 60 projects | 100 projects |
|-----------|------------|------------|------------|-------------|
| **EES** | 0.002s | 0.03s | 0.07s | 0.18s |
| **EES_AddOpt** | 0.12s | 1.50s | 9.83s | **49.87s** |
| **MES** | 0.004s | 0.01s | 0.02s | 0.05s |
| **Greedy** | 0.001s | 0.002s | 0.006s | 0.01s |

**Findings:**
- **Greedy** is the fastest, followed by **MES**
- **EES** (Algorithm 1 alone) is relatively fast – 0.18s at 100 projects
- **EES_AddOpt** is significantly slower: ~50 seconds at 100 projects, because it runs EES + add_opt multiple times with increasing virtual budgets

### Remaining Budget

![Remaining Budget](remaining_budget_voters_50.png)

| Algorithm | 10 projects | 30 projects | 60 projects | 100 projects |
|-----------|------------|------------|------------|-------------|
| **EES** | 152 | 279 | 339 | 246 |
| **EES_AddOpt** | **23** | **21** | **14** | **39** |
| **MES** | 102 | 123 | 103 | 82 |
| **Greedy** | 19 | 7 | 4 | 5 |

**Findings:**
- **EES** leaves the most budget unused – it stops as soon as no project can be funded equally among supporters
- **EES_AddOpt** dramatically improves budget utilization: only 14–39 remaining, compared to 152–339 for plain EES
- **MES** is in between: 82–123 remaining
- **Greedy** has the best budget utilization (4–19) but does not guarantee fairness

### Social Welfare

![Social Welfare](social_welfare_voters_50.png)

| Algorithm | 10 projects | 30 projects | 60 projects | 100 projects |
|-----------|------------|------------|------------|-------------|
| **EES** | 115 | 448 | 897 | 1505 |
| **EES_AddOpt** | **152** | **514** | **979** | **1555** |
| **MES** | 129 | 472 | 924 | 1453 |
| **Greedy** | 150 | 490 | 899 | 1402 |

**Findings:**
- **EES_AddOpt** achieves the highest social welfare at every input size
- At 100 projects: EES_AddOpt (1555) > EES (1505) > MES (1453) > Greedy (1402)
- The gap between EES_AddOpt and MES grows with input size

### Total Cost and Number of Selected Projects

![Total Cost](total_cost_voters_50.png)
![Num Selected](num_selected_voters_50.png)

---

## Conclusions

| | Runtime | Budget Utilization | Social Welfare | Fairness |
|---|---|---|---|---|
| **EES** | Fast | Low | Medium | ✓ |
| **EES_AddOpt** | **Very slow** | **High** | **Highest** | ✓ |
| **MES** | Fast | Medium | Medium-High | ✓ |
| **Greedy** | **Fastest** | **Highest** | Relatively low | ✗ |

1. **EES_AddOpt** achieves the best outcomes (social welfare + budget utilization) while maintaining fairness – but at a very high runtime cost (~50s at 100 projects)
2. **EES** alone is fast but does not exhaust the budget – suitable as an intermediate step
3. **MES** is a good compromise: fast, fair, and produces reasonable results
4. **Greedy** is the fastest and best at budget utilization, but does not guarantee fair allocation

---

## How to Run

```bash
# Run experiment and generate plots
py experiments/experiment_comparison.py

# Generate plots only (from existing CSV data)
py experiments/experiment_comparison.py plot
```

### Files

| File | Description |
|------|-------------|
| `experiment_comparison.py` | Main experiment script |
| `comparison.csv` | Raw experiment data |
| `runtime_voters_50.png` | Runtime plot |
| `remaining_budget_voters_50.png` | Remaining budget plot |
| `total_cost_voters_50.png` | Total cost plot |
| `social_welfare_voters_50.png` | Social welfare plot |
| `num_selected_voters_50.png` | Number of selected projects plot |
