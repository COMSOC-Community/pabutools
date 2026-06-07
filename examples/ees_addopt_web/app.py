"""A beginner-friendly web demo for the Method of Equal Shares (with add-opt completion).

You do not need to know how the algorithm works to use this site. You describe a
simple situation - some money to share, a few projects, and who voted for what -
and the site shows which projects get funded and explains, with real numbers, why
the result is fair.

The heavy lifting is done by the library function
``pabutools.rules.ees_addopt.ees_add_opt_completion``. This file only wraps it in
a friendly interface; it never changes the algorithm itself.
"""

from __future__ import annotations

import io
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flask import Flask, Response, render_template, request

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from pabutools.election.ballot import ApprovalBallot
from pabutools.election.instance import Instance, Project
from pabutools.election.profile import ApprovalProfile
from pabutools.fractions import frac, str_as_frac
from pabutools.rules.ees_addopt import (
    add_opt,
    exact_equal_shares,
    get_leftover_budgets,
    get_leximax_payment,
)

app = Flask(__name__)

ALGORITHM_LOGGER = logging.getLogger("pabutools.rules.ees_addopt")

# A ready-made, relatable example used for the "Load example" button and the
# first time the page is opened. Project indices in "voters" are 0-based and
# point into the "projects" list.
EXAMPLE: dict[str, Any] = {
    "budget": "10",
    "projects": [
        {"name": "New benches", "cost": "2"},
        {"name": "Bike lane", "cost": "3.2"},
        {"name": "Playground", "cost": "6"},
    ],
    "voters": [
        [0],
        [0, 2],
        [1, 2],
        [1, 2],
        [2],
    ],
}


@dataclass(frozen=True)
class ParsedElection:
    instance: Instance
    profile: ApprovalProfile
    projects: list[Project]
    project_names: list[str]
    ballots: list[list[str]]
    budget: Any


class InputError(ValueError):
    """Raised when the submitted election cannot be understood."""


def parse_number(raw_value: Any, field_name: str) -> Any:
    """Turn user text into a non-negative number, with a friendly error if it is not one."""
    text = str(raw_value).strip()
    if not text:
        raise InputError(f"{field_name} is missing a value.")
    try:
        value = str_as_frac(text)
    except Exception as exc:
        raise InputError(f'"{text}" is not a valid number for {field_name.lower()}.') from exc
    if value < 0:
        raise InputError(f"{field_name} cannot be negative.")
    return value


def parse_election_from_payload(payload: Any) -> ParsedElection:
    """Build an election from the structured data sent by the visual builder."""
    if not isinstance(payload, dict):
        raise InputError("The form could not be read. Please reload the page and try again.")

    budget = parse_number(payload.get("budget", ""), "The budget")

    raw_projects = payload.get("projects")
    if not isinstance(raw_projects, list) or not raw_projects:
        raise InputError("Add at least one project.")

    projects: list[Project] = []
    seen_names: set[str] = set()
    for position, item in enumerate(raw_projects, start=1):
        item = item or {}
        name = str(item.get("name", "")).strip()
        if not name:
            raise InputError(f"Project {position} needs a name.")
        if name in seen_names:
            raise InputError(f'Two projects are both called "{name}". Please give each project a different name.')
        cost = parse_number(item.get("cost", ""), f'The cost of "{name}"')
        seen_names.add(name)
        projects.append(Project(name, cost))

    raw_voters = payload.get("voters")
    if not isinstance(raw_voters, list) or not raw_voters:
        raise InputError("Add at least one voter.")

    ballots: list[ApprovalBallot] = []
    ballot_names: list[list[str]] = []
    for voter_position, approvals in enumerate(raw_voters, start=1):
        if approvals is None:
            approvals = []
        if not isinstance(approvals, list):
            raise InputError(f"Voter {voter_position}'s choices could not be read.")
        chosen_indices: list[int] = []
        for raw_index in approvals:
            try:
                index = int(raw_index)
            except (TypeError, ValueError):
                raise InputError(f"Voter {voter_position} has an invalid project choice.")
            if index < 0 or index >= len(projects):
                raise InputError(f"Voter {voter_position} voted for a project that does not exist.")
            chosen_indices.append(index)
        chosen_indices = sorted(set(chosen_indices))
        ballot_names.append([projects[index].name for index in chosen_indices])
        ballots.append(ApprovalBallot(projects[index] for index in chosen_indices))

    instance = Instance(projects, budget_limit=budget)
    profile = ApprovalProfile(ballots, instance=instance)
    return ParsedElection(
        instance=instance,
        profile=profile,
        projects=projects,
        project_names=[project.name for project in projects],
        ballots=ballot_names,
        budget=budget,
    )


def format_number(value: Any) -> str:
    """Show a number in the friendliest readable form (whole number, decimal, or fraction)."""
    if value == float("inf"):
        return "infinity"
    text = str(value)
    if "/" in text:
        try:
            as_float = float(value)
        except (TypeError, ValueError):
            return text
        if abs(as_float - round(as_float)) < 1e-10:
            return str(round(as_float))
        return f"{as_float:.4g}"
    return text


def total_cost(projects: list[Project]) -> Any:
    total = frac(0)
    for project in projects:
        total += frac(project.cost)
    return total


def supporters_by_project(parsed: ParsedElection) -> dict[str, int]:
    counts = {project.name: 0 for project in parsed.projects}
    for ballot in parsed.ballots:
        for project_name in ballot:
            counts[project_name] += 1
    return counts


def summarize_allocation(parsed: ParsedElection, allocation: list[Project]) -> dict[str, Any]:
    """Describe one outcome: which projects, who paid, and how much each voter kept."""
    selected_projects = list(allocation)
    selected_names = [project.name for project in selected_projects]
    details = getattr(allocation, "details", None)
    payments = getattr(details, "payments", {}) if details is not None else {}
    number_of_voters = len(parsed.profile)
    voter_budget = frac(parsed.instance.budget_limit) / number_of_voters if number_of_voters else frac(0)
    cost_value = total_cost(selected_projects)

    project_payments = []
    for project in selected_projects:
        paid = frac(0)
        payers = []
        for voter_index in range(number_of_voters):
            amount = payments.get(voter_index, {}).get(project, frac(0))
            if amount:
                payers.append({"voter": voter_index + 1, "amount": format_number(amount)})
                paid += amount
        project_payments.append(
            {
                "name": project.name,
                "cost": format_number(project.cost),
                "paid": format_number(paid),
                "is_fully_paid": paid == frac(project.cost),
                "payers": payers,
            }
        )

    voter_rows = []
    for voter_index in range(number_of_voters):
        paid_total = frac(0)
        paid_entries = []
        for project in selected_projects:
            amount = payments.get(voter_index, {}).get(project, frac(0))
            if amount:
                paid_entries.append(f"{project.name}: {format_number(amount)}")
                paid_total += amount
        voter_rows.append(
            {
                "number": voter_index + 1,
                "approvals": ", ".join(parsed.ballots[voter_index]) or "nothing",
                "payments": ", ".join(paid_entries) or "-",
                "paid_total": format_number(paid_total),
                "leftover": format_number(voter_budget - paid_total),
                "within_budget": paid_total <= voter_budget,
            }
        )

    return {
        "selected_names": selected_names,
        "selected_display": ", ".join(selected_names) if selected_names else "no projects",
        "count": len(selected_names),
        "is_empty": len(selected_names) == 0,
        "total_cost": format_number(cost_value),
        "total_cost_num": cost_value,
        "is_budget_feasible": cost_value <= parsed.instance.budget_limit,
        "project_payments": project_payments,
        "voter_rows": voter_rows,
    }


def percent_of_budget(used: Any, budget: Any) -> float:
    budget_value = frac(budget)
    if budget_value <= 0:
        return 0.0
    fraction = float(frac(used) / budget_value) * 100.0
    return max(0.0, min(100.0, round(fraction, 1)))


def run_completion_with_steps(parsed: ParsedElection) -> tuple[list[dict[str, Any]], list[Project], int]:
    """Reproduce the add-opt completion loop, recording every round as a visible step.

    This mirrors ``ees_add_opt_completion`` exactly - it only calls the same public
    functions - so the page can show each round without changing the algorithm.
    """
    instance = parsed.instance
    profile = parsed.profile
    number_of_voters = len(profile)
    original_budget = frac(instance.budget_limit)
    projects = list(instance)

    rounds: list[dict[str, Any]] = []
    virtual_budget = original_budget
    best_index = -1
    best_cost = frac(-1)

    while True:
        virtual_instance = Instance(projects, budget_limit=virtual_budget)
        allocation = exact_equal_shares(virtual_instance, profile)
        cost = total_cost(list(allocation))
        fits = cost <= original_budget
        delta = add_opt(virtual_instance, profile, allocation)
        rounds.append(
            {
                "allocation": allocation,
                "virtual_budget": virtual_budget,
                "share": virtual_budget / number_of_voters if number_of_voters else frac(0),
                "selected": [project.name for project in allocation],
                "total_cost": cost,
                "fits": fits,
                "delta": delta,
            }
        )
        if fits and cost > best_cost:
            best_cost = cost
            best_index = len(rounds) - 1
        if delta == float("inf") or delta <= 0 or len(rounds) >= 60:
            break
        virtual_budget = virtual_budget + number_of_voters * frac(delta)

    if best_index < 0:
        best_index = 0
    return rounds, rounds[best_index]["allocation"], best_index


def analyze(parsed: ParsedElection) -> dict[str, Any]:
    """Run the algorithm and assemble everything the results page needs to explain it."""
    log_stream = io.StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
    previous_level = ALGORITHM_LOGGER.level
    previous_propagate = ALGORITHM_LOGGER.propagate
    ALGORITHM_LOGGER.setLevel(logging.DEBUG)
    ALGORITHM_LOGGER.propagate = False
    ALGORITHM_LOGGER.addHandler(handler)
    try:
        rounds, completed_allocation, best_index = run_completion_with_steps(parsed)
        base_allocation = rounds[0]["allocation"]
        leftover_budgets = get_leftover_budgets(parsed.instance, parsed.profile, base_allocation)
        leximax_payments = get_leximax_payment(base_allocation, len(parsed.profile), parsed.instance)
        next_delta = rounds[0]["delta"]
    finally:
        ALGORITHM_LOGGER.removeHandler(handler)
        ALGORITHM_LOGGER.setLevel(previous_level)
        ALGORITHM_LOGGER.propagate = previous_propagate

    number_of_voters = len(parsed.profile)
    budget_value = frac(parsed.budget)
    share_value = budget_value / number_of_voters if number_of_voters else frac(0)

    base = summarize_allocation(parsed, base_allocation)
    completed = summarize_allocation(parsed, completed_allocation)

    supporter_counts = supporters_by_project(parsed)
    base_selected_names = set(base["selected_names"])
    completed_selected_names = set(completed["selected_names"])
    project_rows = [
        {
            "name": project.name,
            "cost": format_number(project.cost),
            "supporters": supporter_counts[project.name],
            "in_base": project.name in base_selected_names,
            "in_completed": project.name in completed_selected_names,
        }
        for project in parsed.projects
    ]

    leftover_rows = [
        {
            "voter": voter_index + 1,
            "leftover": format_number(leftover_budgets[voter_index]),
            "leximax": ", ".join(
                f"{project_name}: {format_number(amount)}"
                for amount, project_name in leximax_payments[voter_index]
            ),
        }
        for voter_index in range(number_of_voters)
    ]

    completion_rounds = []
    for index, round_data in enumerate(rounds):
        delta_value = round_data["delta"]
        if delta_value == float("inf") or delta_value <= 0:
            delta_display = None
        else:
            delta_display = format_number(delta_value)
        completion_rounds.append(
            {
                "number": index + 1,
                "share": format_number(round_data["share"]),
                "selected_display": ", ".join(round_data["selected"]) if round_data["selected"] else "no projects",
                "total_cost": format_number(round_data["total_cost"]),
                "fits": round_data["fits"],
                "delta": delta_display,
                "is_chosen": index == best_index,
            }
        )

    return {
        "budget": format_number(parsed.budget),
        "voter_count": number_of_voters,
        "share_per_voter": format_number(share_value),
        "project_count": len(parsed.projects),
        "project_rows": project_rows,
        "base": base,
        "completed": completed,
        "base_leftover": format_number(budget_value - base["total_cost_num"]),
        "completed_leftover": format_number(budget_value - completed["total_cost_num"]),
        "completed_used_percent": percent_of_budget(completed["total_cost_num"], parsed.budget),
        "same_as_base": base_selected_names == completed_selected_names,
        "completion_rounds": completion_rounds,
        "completion_multistep": len(completion_rounds) > 1,
        "chosen_round": best_index + 1,
        "next_delta": format_number(next_delta),
        "leftover_rows": leftover_rows,
        "logs": [line for line in log_stream.getvalue().splitlines() if line.strip()],
    }


@app.get("/")
def index():
    return render_template("index.html", initial_data=EXAMPLE, example_data=EXAMPLE, error=None)


@app.post("/run")
def run_algorithm():
    raw_payload = request.form.get("payload", "")
    try:
        payload = json.loads(raw_payload) if raw_payload else {}
    except json.JSONDecodeError:
        payload = {}

    fallback = payload if isinstance(payload, dict) and payload else EXAMPLE
    try:
        parsed = parse_election_from_payload(payload)
        result = analyze(parsed)
    except InputError as exc:
        return (
            render_template("index.html", initial_data=fallback, example_data=EXAMPLE, error=str(exc)),
            400,
        )
    except Exception as exc:  # noqa: BLE001 - surface any unexpected failure to the user.
        return (
            render_template(
                "index.html",
                initial_data=fallback,
                example_data=EXAMPLE,
                error=f"Something went wrong while running the election: {exc}",
            ),
            400,
        )
    return render_template("result.html", result=result)


@app.get("/about")
def about():
    return render_template("about.html")


# A tiny inline icon so browsers do not get a 404 when they ask for /favicon.ico.
FAVICON_SVG = (
    "<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'>"
    "<rect width='32' height='32' rx='7' fill='#1f7a70'/>"
    "<path d='M8 16.5l5 5 11-12' fill='none' stroke='#ffffff' stroke-width='3.5' "
    "stroke-linecap='round' stroke-linejoin='round'/></svg>"
)


@app.get("/favicon.ico")
def favicon():
    return Response(FAVICON_SVG, mimetype="image/svg+xml")


if __name__ == "__main__":
    app.run(debug=True)
