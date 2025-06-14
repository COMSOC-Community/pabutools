from unittest import TestCase
import tempfile
import os

from pabutools.election import Cost_Sat
from pabutools import election
from pabutools.visualisation.visualisation import MESVisualiser
from pabutools.rules.mes.mes_rule import method_of_equal_shares


class TestUtils(TestCase):
    def test_mes_visualisation(self):
        file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "PaBuLib",
            "All_10",
            "poland_czestochowa_2020_grabowka.pb",
        )
        instance, profile = election.parse_pabulib(file_path)
        outcome = method_of_equal_shares(
            instance, profile, sat_class=Cost_Sat, analytics=True
        )
        vis = MESVisualiser(profile, instance, outcome)
        with tempfile.TemporaryDirectory() as temp_dir:
            vis.render(temp_dir, name="test")
            summary_file_path = os.path.join(temp_dir, "test_summary.html")
            round_analysis_file_path = os.path.join(
                temp_dir, "test_round_analysis.html"
            )
            assert os.path.isfile(summary_file_path)
            assert os.path.isfile(round_analysis_file_path)
            with open(summary_file_path, "r") as summary_file:
                assert "<!DOCTYPE html>" in summary_file.read()
            with open(round_analysis_file_path, "r") as round_analysis_file:
                assert "<!DOCTYPE html>" in round_analysis_file.read()
        assert len(vis.rounds) == 4 == len(outcome.details.iterations) - 1
