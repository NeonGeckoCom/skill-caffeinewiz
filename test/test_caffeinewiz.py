# NEON AI (TM) SOFTWARE, Software Development Kit & Application Development System
#
# Copyright 2008-2021 Neongecko.com Inc. | All Rights Reserved
#
# Notice of License - Duplicating this Notice of License near the start of any file containing
# a derivative of this software is a condition of license for this software.
# Friendly Licensing:
# No charge, open source royalty free use of the Neon AI software source and object is offered for
# educational users, noncommercial enthusiasts, Public Benefit Corporations (and LLCs) and
# Social Purpose Corporations (and LLCs). Developers can contact developers@neon.ai
# For commercial licensing, distribution of derivative works or redistribution please contact licenses@neon.ai
# Distributed on an "AS IS” basis without warranties or conditions of any kind, either express or implied.
# Trademarks of Neongecko: Neon AI(TM), Neon Assist (TM), Neon Communicator(TM), Klat(TM)
# Authors: Guy Daniels, Daniel McKnight, Regina Bloomstine, Elon Gasper, Richard Leeds
#
# Specialized conversational reconveyance options from Conversation Processing Intelligence Corp.
# US Patents 2008-2021: US7424516, US20140161250, US20140177813, US8638908, US8068604, US8553852, US10530923, US10530924
# China Patent: CN102017585  -  Europe Patent: EU2156652  -  Patents Pending

import unittest

from copy import deepcopy
from os.path import dirname
from mock import Mock
from ovos_utils.messagebus import FakeBus
from mycroft_bus_client import Message

from mycroft.skills.skill_loader import SkillLoader


class TestSkill(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        bus = FakeBus()
        bus.run_in_thread()
        skill_loader = SkillLoader(bus, dirname(dirname(__file__)))
        skill_loader.load()
        cls.skill = skill_loader.instance

        # Override speak and speak_dialog to test passed arguments
        cls.skill.speak = Mock()
        cls.skill.speak_dialog = Mock()

    def test_00_skill_init(self):
        # Test any parameters expected to be set in init or initialize methods
        from neon_utils.skills.common_query_skill import CommonQuerySkill
        from datetime import datetime

        self.assertIsInstance(self.skill, CommonQuerySkill)
        self.assertIsInstance(self.skill.translate_drinks, dict)
        self.assertIsInstance(self.skill.last_updated, datetime)

        self.skill._get_new_info()
        self.assertIsNotNone(self.skill.from_caffeine_wiz)
        self.assertIsNotNone(self.skill.from_caffeine_informer)

    def test_CQS_match_query_phrase(self):
        from neon_utils.skills.common_query_skill import CQSMatchLevel

        null_response = self.skill.CQS_match_query_phrase("what time is it")
        self.assertIsNone(null_response)

        query_str = "what is in diet coke"
        general_match = self.skill.CQS_match_query_phrase(query_str)
        self.assertIsInstance(general_match, tuple)
        self.assertEqual(general_match[0], query_str)
        self.assertEqual(general_match[1], CQSMatchLevel.GENERAL)
        self.assertIsInstance(general_match[2], str)
        self.assertIsInstance(general_match[3], dict)

        query_str = "what is the caffeine content of diet coke"
        exact_match = self.skill.CQS_match_query_phrase(query_str)
        self.assertIsInstance(exact_match, tuple)
        self.assertEqual(exact_match[0], query_str)
        self.assertEqual(exact_match[1], CQSMatchLevel.EXACT)
        self.assertIsInstance(exact_match[2], str)
        self.assertIsInstance(exact_match[3], dict)

        query_str = "what is the caffeine content of software"
        non_match = self.skill.CQS_match_query_phrase(query_str)
        self.assertIsInstance(non_match, tuple)
        self.assertEqual(non_match[0], query_str)
        self.assertEqual(non_match[1], CQSMatchLevel.CATEGORY)
        self.assertIsInstance(non_match[2], str)
        self.assertIsInstance(non_match[3], dict)

    def test_handle_caffeine_intent(self):
        calls = deepcopy(self.skill.speak.call_count)
        message = Message("test_message", {"drink": "coke"}, {})
        self.skill.handle_caffeine_intent(message)
        self.assertEqual(self.skill.speak.call_count, calls + 1)

        message = Message("test_message", {}, {})
        self.skill.handle_caffeine_intent(message)
        self.skill.speak_dialog.assert_called_with("NoDrinkHeard")

        message = Message("test_message", {"drink": "software"}, {})
        self.skill.handle_caffeine_intent(message)
        self.skill.speak_dialog.assert_called_with("NotFound", {'drink': 'software'})


if __name__ == '__main__':
    unittest.main()
