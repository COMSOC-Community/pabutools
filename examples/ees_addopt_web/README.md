# EES add-opt Flask demo

This small Flask app demonstrates `exact_equal_shares`, `add_opt`, and `ees_add_opt_completion` from `pabutools.rules.ees_addopt`.

## Run

From the repository root:

```powershell
python -m pip install -r examples/ees_addopt_web/requirements.txt
python examples/ees_addopt_web/app.py
```

Then open <http://127.0.0.1:5000>.

## Input format

```text
Budget: 10

Projects:
p1, 2
p2, 3.2
p3, 6

Ballots:
p1
p1, p3
p2, p3
```

Use `-` for a voter who approves no projects.