from unittest import TestCase
import tempfile

from pabutools.election import Cost_Sat
from pabutools import election
from pabutools.visualisation.visualisation import MESVisualiser
from pabutools.rules.mes.mes_rule import method_of_equal_shares


class TestUtils(TestCase):
    def test_mes_visualisation(self):
        instance, profile = election.parse_pabulib("tests/PaBuLib/All_10/poland_czestochowa_2020_grabowka.pb")
        outcome = method_of_equal_shares(instance, profile, sat_class=Cost_Sat, analytics=True)
        vis = MESVisualiser(profile, instance, outcome.details)
        with tempfile.NamedTemporaryFile(suffix=".html", mode='w+t', delete=False) as temp_file:
            vis.render(outcome, temp_file.name)
            temp_file.seek(0)
            assert '<!DOCTYPE html>' in temp_file.read()
        assert len(vis.rounds) == 4 == len(outcome.details.iterations)
