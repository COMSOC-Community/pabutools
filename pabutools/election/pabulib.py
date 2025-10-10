"""
Tools to work with PaBuLib.
"""

from natsort import natsorted
from copy import deepcopy

from pabutools.fractions import str_as_frac
from pabutools.election.instance import Instance, Project
from pabutools.election.ballot import (
    ApprovalBallot,
    CardinalBallot,
    OrdinalBallot,
    CumulativeBallot,
    AbstractCardinalBallot,
)
from pabutools.election.profile import (
    AbstractProfile,
    Profile,
    ApprovalProfile,
    AbstractApprovalProfile,
    CardinalProfile,
    AbstractCardinalProfile,
    CumulativeProfile,
    AbstractCumulativeProfile,
    OrdinalProfile,
    AbstractOrdinalProfile,
)

import urllib.request
import csv
import os


def parse_pabulib_from_string(file_content: str) -> tuple[Instance, Profile]:
    """
    Parses a PaBuLib file given as a string and returns the corresponding instance and profile. The
    returned profile will be of the correct type depending on the metadata in the file.

    Parameters
    ----------
        file_content : str
            String containing the contents of the PaBuLib file to be parsed.

    Returns
    -------
        tuple[:py:class:`~pabutools.election.instance.Instance`, :py:class:`~pabutools.election.profile.profile.Profile`]
            The instance and the profile corresponding to the file.
    """
    instance = Instance()
    ballots = []
    optional_sets = {"categories": set(), "targets": set()}

    lines = file_content.splitlines()
    section = ""
    header = []
    reader = csv.reader(lines, delimiter=";")
    for row in reader:
        if len(row) == 0 or (len(row) == 1 and len(row[0].strip()) == 0):
            continue
        if str(row[0]).strip().lower() in ["meta", "projects", "votes"]:
            section = str(row[0]).strip().lower()
            header = next(reader)
        elif section == "meta":
            instance.meta[row[0].strip()] = row[1].strip()
        elif section == "projects":
            p = Project()
            project_meta = dict()
            for i in range(len(row)):
                key = header[i].strip()
                p.name = row[0].strip()
                if row[i].strip().lower() != "none":
                    if key in ["category", "categories"]:
                        project_meta["categories"] = {
                            entry.strip() for entry in row[i].split(",")
                        }
                        p.categories = set(project_meta["categories"])
                        optional_sets["categories"].update(project_meta["categories"])
                    elif key in ["target", "targets"]:
                        project_meta["targets"] = {
                            entry.strip() for entry in row[i].split(",")
                        }
                        p.targets = set(project_meta["targets"])
                        optional_sets["targets"].update(project_meta["targets"])
                    else:
                        project_meta[key] = row[i].strip()
            p.cost = str_as_frac(project_meta["cost"].replace(",", "."))
            instance.add(p)
            instance.project_meta[p] = project_meta
        elif section == "votes":
            ballot_meta = dict()
            for i in range(len(row)):
                if row[i].strip().lower() != "none":
                    ballot_meta[header[i].strip()] = row[i].strip()
            vote_type = instance.meta["vote_type"]
            if vote_type in ["approval", "choose-1"]:
                ballot = ApprovalBallot()
                for project_name in ballot_meta["vote"].split(","):
                    if project_name:
                        ballot.add(instance.get_project(project_name))
                ballot_meta.pop("vote")
            elif vote_type in ["scoring", "cumulative"]:
                if vote_type == "scoring":
                    ballot = CardinalBallot()
                else:
                    ballot = CumulativeBallot()
                if "points" in ballot_meta:  # if not, the ballot should be empty
                    points = ballot_meta["points"].split(",")
                    for index, project_name in enumerate(
                        ballot_meta["vote"].split(",")
                    ):
                        ballot[instance.get_project(project_name)] = str_as_frac(
                            points[index].strip()
                        )
                    ballot_meta.pop("vote")
                    ballot_meta.pop("points")
            elif vote_type == "ordinal":
                ballot = OrdinalBallot()
                for project_name in ballot_meta["vote"].split(","):
                    if project_name:
                        ballot.append(instance.get_project(project_name))
                ballot_meta.pop("vote")
            else:
                raise NotImplementedError(
                    "The PaBuLib parser cannot parse {} profiles for now.".format(
                        instance.meta["vote_type"]
                    )
                )
            ballot.meta = ballot_meta
            ballots.append(ballot)

    legal_min_length = instance.meta.get("min_length", None)
    if legal_min_length is not None:
        legal_min_length = int(legal_min_length)
        if legal_min_length == 1:
            legal_min_length = None
    legal_max_length = instance.meta.get("max_length", None)
    if legal_max_length is not None:
        legal_max_length = int(legal_max_length)
        if legal_max_length >= len(instance):
            legal_max_length = None
    legal_min_cost = instance.meta.get("min_sum_cost", None)
    if legal_min_cost is not None:
        legal_min_cost = str_as_frac(legal_min_cost)
        if legal_min_cost == 0:
            legal_min_cost = None
    legal_max_cost = instance.meta.get("max_sum_cost", None)
    if legal_max_cost is not None:
        legal_max_cost = str_as_frac(legal_max_cost)
        if legal_max_cost >= instance.budget_limit:
            legal_max_cost = None
    legal_min_total_score = instance.meta.get("min_sum_points", None)
    if legal_min_total_score is not None:
        legal_min_total_score = str_as_frac(legal_min_total_score)
        if legal_min_total_score == 0:
            legal_min_total_score = None
    legal_max_total_score = instance.meta.get("max_sum_points", None)
    if legal_max_total_score is not None:
        legal_max_total_score = str_as_frac(legal_max_total_score)
    legal_min_score = instance.meta.get("min_points", None)
    if legal_min_score is not None:
        legal_min_score = str_as_frac(legal_min_score)
        if legal_min_score == 0:
            legal_min_score = None
    legal_max_score = instance.meta.get("max_points", None)
    if legal_max_score is not None:
        legal_max_score = str_as_frac(legal_max_score)
        if legal_max_score == legal_max_total_score:
            legal_max_score = None

    profile = None
    if instance.meta["vote_type"] in ["approval", "choose-1"]:
        profile = ApprovalProfile(
            deepcopy(ballots),
            legal_min_length=legal_min_length,
            legal_max_length=legal_max_length,
            legal_min_cost=legal_min_cost,
            legal_max_cost=legal_max_cost,
        )
    elif instance.meta["vote_type"] == "scoring":
        profile = CardinalProfile(
            deepcopy(ballots),
            legal_min_length=legal_min_length,
            legal_max_length=legal_max_length,
            legal_min_score=legal_min_score,
            legal_max_score=legal_max_score,
        )
    elif instance.meta["vote_type"] == "cumulative":
        profile = CumulativeProfile(
            deepcopy(ballots),
            legal_min_length=legal_min_length,
            legal_max_length=legal_max_length,
            legal_min_score=legal_min_score,
            legal_max_score=legal_max_score,
            legal_min_total_score=legal_min_total_score,
            legal_max_total_score=legal_max_total_score,
        )
    elif instance.meta["vote_type"] == "ordinal":
        profile = OrdinalProfile(
            deepcopy(ballots),
            legal_min_length=legal_min_length,
            legal_max_length=legal_max_length,
        )

    # We retrieve the budget limit from the meta information
    instance.budget_limit = str_as_frac(instance.meta["budget"].replace(",", "."))

    # We add the category and target information that we collected from the projects
    instance.categories = optional_sets["categories"]
    instance.targets = optional_sets["targets"]

    return instance, profile


def parse_pabulib(file_path: str) -> tuple[Instance, Profile]:
    """
    Parses a PaBuLib files and returns the corresponding instance and profile. The returned profile will be of the
    correct type depending on the metadata in the file.

    Parameters
    ----------
        file_path : str
            Path to the PaBuLib file to be parsed.

    Returns
    -------
        tuple[:py:class:`~pabutools.election.instance.Instance`, :py:class:`~pabutools.election.profile.profile.Profile`]
            The instance and the profile corresponding to the file.
    """

    with open(file_path, "r", newline="", encoding="utf-8-sig") as csvfile:
        instance, profile = parse_pabulib_from_string(csvfile.read())

    instance.file_path = file_path
    instance.file_name = os.path.basename(file_path)

    return instance, profile


def parse_pabulib_from_url(url: str) -> tuple[Instance, Profile]:
    """
    Parses a PaBuLib files given a URL and returns the corresponding instance and profile. The returned profile will be
    of the correct type depending on the metadata in the file.

    Parameters
    ----------
        url : str
            URL to the PaBuLib file to be parsed.

    Returns
    -------
        tuple[:py:class:`~pabutools.election.instance.Instance`, :py:class:`~pabutools.election.profile.profile.Profile`]
            The instance and the profile corresponding to the file.
    """

    data = urllib.request.urlopen(url)
    lines = data.read().decode("utf-8-sig")
    data.close()

    instance, profile = parse_pabulib_from_string(lines)

    instance.file_path = url
    instance.file_name = url.split("/")[-1]

    return instance, profile


def election_as_pabulib_string(instance: Instance, profile: AbstractProfile) -> str:
    """
    Creates a string representing the instance and the profile according to the Pabulib standard
    (as specified in https://arxiv.org/pdf/2305.11035.pdf).


    Parameters
    ----------
        instance: :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile: :py:class:`~pabutools.election.profile.profile.Profile`
            The profile.

    Returns
    -------
        str
            The instance and profile represented as a Pabulib string
    """

    def update_meta_value(meta_dict, inst_meta, field, mandatory=False):
        if field in inst_meta:
            meta_dict[field] = inst_meta[field]
        elif mandatory:
            meta_dict[field] = "Auto-filled " + str(field)

    meta = {}
    update_meta_value(meta, instance.meta, "description", mandatory=True)
    update_meta_value(meta, instance.meta, "country", mandatory=True)
    update_meta_value(meta, instance.meta, "unit", mandatory=True)
    update_meta_value(meta, instance.meta, "subunit")
    update_meta_value(meta, instance.meta, "instance", mandatory=True)
    meta["num_projects"] = len(instance)
    meta["num_votes"] = profile.num_ballots()
    meta["budget"] = instance.budget_limit
    if isinstance(profile, AbstractApprovalProfile):
        meta["vote_type"] = "approval"
    elif isinstance(profile, AbstractCumulativeProfile):
        meta["vote_type"] = "cumulative"
    elif isinstance(profile, AbstractCardinalProfile):
        meta["vote_type"] = "scoring"
    elif isinstance(profile, AbstractOrdinalProfile):
        meta["vote_type"] = "ordinal"
    update_meta_value(meta, instance.meta, "rule", mandatory=True)
    update_meta_value(meta, instance.meta, "date_begin", mandatory=False)
    update_meta_value(meta, instance.meta, "date_end", mandatory=False)
    update_meta_value(meta, instance.meta, "date_language", mandatory=False)
    update_meta_value(meta, instance.meta, "date_edition", mandatory=False)
    update_meta_value(meta, instance.meta, "date_district", mandatory=False)
    update_meta_value(meta, instance.meta, "date_comment", mandatory=False)
    if profile.legal_min_length:
        meta["min_length"] = str(profile.legal_min_length)
    if profile.legal_max_length:
        meta["max_length"] = str(profile.legal_max_length)
    if isinstance(profile, AbstractApprovalProfile):
        if profile.legal_min_cost:
            meta["min_sum_cost"] = str(profile.legal_min_cost)
        if profile.legal_max_cost:
            meta["max_sum_cost"] = str(profile.legal_max_cost)
    elif isinstance(profile, AbstractCumulativeProfile):
        if profile.legal_min_score:
            meta["min_points"] = str(profile.legal_min_score)
        if profile.legal_max_score:
            meta["max_points"] = str(profile.legal_max_score)
        if profile.legal_min_total_score:
            meta["min_sum_points"] = str(profile.legal_min_total_score)
        if profile.legal_max_total_score:
            meta["max_sum_points"] = str(profile.legal_max_total_score)
        else:
            meta["max_sum_points"] = "Auto-filled max_sum_points"
    elif isinstance(profile, AbstractCardinalProfile):
        if profile.legal_min_score:
            meta["min_points"] = str(profile.legal_min_score)
        if profile.legal_max_score:
            meta["max_points"] = str(profile.legal_max_score)
        update_meta_value(meta, instance.meta, "default_score", mandatory=False)
    elif isinstance(profile, AbstractOrdinalProfile):
        update_meta_value(meta, instance.meta, "scoring_fn", mandatory=False)
    for key, value in instance.meta.items():
        if key not in meta:
            meta[key] = value

    project_dicts = []
    project_keys = ["project_id", "cost"]
    for project in instance:
        project_meta = {"project_id": project.name, "cost": project.cost}
        if "name" in instance.project_meta.get(project, {}):
            project_meta["name"] = instance.project_meta[project]["name"]
            if "name" not in project_keys:
                project_keys.append("name")
        if project.categories:
            project_meta["category"] = ",".join(project.categories)
            if "category" not in project_keys:
                project_keys.append("category")
        if project.targets:
            project_meta["target"] = ",".join(project.targets)
            if "target" not in project_keys:
                project_keys.append("target")
        for key, value in instance.project_meta.get(project, {}).items():
            if key not in project_meta and key not in ["categories", "targets"]:
                project_meta[key] = value
                if key not in project_keys:
                    project_keys.append(key)
        project_dicts.append(project_meta)
    project_dicts = natsorted(project_dicts, key=lambda d: d["project_id"])

    vote_dicts = []
    vote_keys = ["voter_id"]
    voter_ids = set()
    for index, ballot in enumerate(profile):
        if "voter_id" in ballot.meta:
            voter_id = str(ballot.meta["voter_id"])
        else:
            voter_id = index
        counter = 1
        base_id = voter_id
        while voter_id in voter_ids:
            voter_id = base_id + "__" + str(counter)
        vote_meta = {"voter_id": voter_id}
        if "age" in ballot.meta:
            vote_meta["age"] = ballot.meta["age"]
            if "age" not in vote_keys:
                vote_keys.append("age")
        if "sex" in ballot.meta:
            vote_meta["sex"] = ballot.meta["sex"]
            if "sex" not in vote_keys:
                vote_keys.append("sex")
        if "voting_method" in ballot.meta:
            vote_meta["voting_method"] = ballot.meta["voting_method"]
            if "voting_method" not in vote_keys:
                vote_keys.append("voting_method")
        vote_meta["vote"] = ",".join([str(p.name) for p in ballot])
        if "vote" not in vote_keys:
            vote_keys.append("vote")
        if isinstance(ballot, AbstractCardinalBallot):
            vote_meta["points"] = ",".join([str(float(ballot[p])) for p in ballot])
            if "points" not in vote_keys:
                vote_keys.append("points")
        for key, value in ballot.meta.items():
            if key not in vote_meta:
                vote_meta[key] = value
                if key not in vote_keys:
                    project_keys.append(key)
        for mul in range(profile.multiplicity(ballot)):
            vote_dicts.append(vote_meta)
    vote_dicts = natsorted(vote_dicts, key=lambda d: d["voter_id"])

    file_str = "META\nkey;value\n"
    for key, value in meta.items():
        file_str += f"{key};{value}\n"
    file_str += "PROJECTS\n" + ";".join(project_keys) + "\n"
    for project_dict in project_dicts:
        file_str += (
            ";".join([str(project_dict.get(key, "None")) for key in project_keys])
            + "\n"
        )
    file_str += "VOTES\n" + ";".join(vote_keys) + "\n"
    for vote_dict in vote_dicts:
        file_str += (
            ";".join([str(vote_dict.get(key, "None")) for key in vote_keys]) + "\n"
        )
    return file_str


def write_pabulib(instance: Instance, profile: AbstractProfile, file_path: str) -> None:
    """Writes an instance and a profile to a file using the pabulib format (as specified in
    https://arxiv.org/pdf/2305.11035.pdf).

    Parameters
    ----------
        instance: :py:class:`~pabutools.election.instance.Instance`
            The instance.
        profile: :py:class:`~pabutools.election.profile.profile.Profile`
            The profile.
        file_path: str
            The path to the output file. Defaults to :code:`None`.
    """

    with open(file_path, "w", encoding="utf-8-sig") as f:
        f.write(election_as_pabulib_string(instance, profile))
