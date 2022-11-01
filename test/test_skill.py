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
from os import mkdir
from os.path import dirname, join, exists
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

        # Define a directory to use for testing
        cls.test_fs = join(dirname(__file__), "skill_fs")
        if not exists(cls.test_fs):
            mkdir(cls.test_fs)

        # Override fs paths to use the test directory
        cls.skill.settings_write_path = cls.test_fs
        cls.skill.file_system.path = cls.test_fs
        cls.skill._init_settings()
        cls.skill.initialize()

        # Override speak and speak_dialog to test passed arguments
        cls.skill.speak = Mock()
        cls.skill.speak_dialog = Mock()

    def test_00_skill_init(self):
        # Test any parameters expected to be set in init or initialize methods
        from neon_utils.skills.common_query_skill import CommonQuerySkill

        self.assertIsInstance(self.skill, CommonQuerySkill)
        self.assertIsInstance(self.skill.translate_drinks, dict)

        self.skill._update_event.wait()

        self.skill._get_new_info()
        self.assertTrue(self.skill._update_event.is_set())
        self.assertIsNotNone(self.skill.from_caffeine_wiz)
        self.assertIsInstance(self.skill.from_caffeine_wiz, list)
        self.assertIsNotNone(self.skill.from_caffeine_informer)
        self.assertIsInstance(self.skill.from_caffeine_informer, list)
        self.assertTrue(all([d for d in self.skill.from_caffeine_informer
                             if d in self.skill.from_caffeine_wiz]))
        for d in self.skill.from_caffeine_wiz:
            self.assertIsInstance(d, list)
            self.assertIsInstance(d[0], str)
            self.assertIsInstance(float(d[1]), float)
            self.assertIsInstance(int(d[2]), int)

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

    def test_handle_caffeine_intent_valid(self):
        calls = deepcopy(self.skill.speak.call_count)
        message = Message("test_message", {"drink": "coke"}, {})
        self.skill.handle_caffeine_intent(message)
        self.assertEqual(self.skill.speak.call_count, calls + 1)

    def test_handle_caffeine_intent_no_drink(self):
        message = Message("test_message", {}, {})
        self.skill.handle_caffeine_intent(message)
        self.skill.speak_dialog.assert_called_with("no_drink_heard")

    def test_handle_caffeine_intent_invalid_drink(self):
        message = Message("test_message", {"drink": "software"}, {})
        self.skill.handle_caffeine_intent(message)
        self.skill.speak_dialog.assert_called_with("not_found",
                                                   {'drink': 'software'})

    def test_handle_caffeine_update(self):
        real_get_new_info = self.skill._get_new_info
        self.skill._get_new_info = Mock()
        self.skill.handle_caffeine_update(Message(""))
        self.skill.speak_dialog.assert_called_with("updating")
        self.skill._get_new_info.assert_called_once_with(reply=True)

        self.skill._get_new_info = real_get_new_info

    def test_CQS_action(self):
        phrase = 'test'
        data = {'results': ['one', 'two']}

        real_ask_yesno = self.skill.ask_yesno
        self.skill.ask_yesno = Mock()

        real_speak_alternate = self.skill._speak_alternate_results
        self.skill._speak_alternate_results = Mock()

        # No match
        self.skill.CQS_action(phrase, {})
        self.skill.speak_dialog.assert_not_called()
        self.skill.CQS_action(phrase, {'results': None})
        self.skill.speak_dialog.assert_not_called()
        self.skill.CQS_action(phrase, {'results': []})
        self.skill.speak_dialog.assert_not_called()

        # Single match
        self.skill.CQS_action(phrase, {'results': ['test']})
        self.skill.speak_dialog.assert_called_once_with("stay_caffeinated")
        self.skill.speak_dialog.reset_mock()

        # Multiple matches, no
        self.skill.ask_yesno.return_value = 'no'
        self.skill.CQS_action(phrase, data)
        self.skill.speak_dialog.assert_called_once_with("stay_caffeinated")
        self.skill.speak_dialog.reset_mock()

        # Multiple matches, no response
        self.skill.ask_yesno.return_value = None
        self.skill.CQS_action(phrase, data)
        self.skill.speak_dialog.assert_called_once_with("stay_caffeinated")
        self.skill.speak_dialog.reset_mock()

        # Multiple matches, yes response
        self.skill.ask_yesno.return_value = 'yes'
        self.skill.CQS_action(phrase, data)
        self.skill._speak_alternate_results.assert_called_once_with(
            None, data['results'])
        self.skill.speak_dialog.assert_called_once_with(
            "provided_by_caffeinewiz")
        self.skill.speak_dialog.reset_mock()

        self.skill.ask_yesno = real_ask_yesno
        self.skill._speak_alternate_results = real_speak_alternate

    def test_convert_metric(self):
        # ~30mg/250mL
        converted = self.skill.convert_metric(12, 34)
        self.assertEqual(converted, ('23', '250', 'word_milliliters'))
        converted = self.skill.convert_metric(24, 68)
        self.assertEqual(converted, ('47', '500', 'word_milliliters'))
        converted = self.skill.convert_metric(36, 102)
        self.assertEqual(converted, ('95', '1', 'word_liter'))

    def test_handle_goodbye_intent(self):
        message = Message("recognizer_loop:utterance",
                          {"goodbye_keyword": "good bye"})
        self.skill.handle_goodbye_intent(message)
        self.skill.speak_dialog.assert_called_with("stay_caffeinated")

    def test_get_drink_text(self):
        # TODO: Write this test DM
        pass

    def test_add_more_caffeine_data(self):
        real_data = self.skill.from_caffeine_wiz
        self.skill.from_caffeine_wiz = list()
        self.skill._add_more_caffeine_data()
        self.assertGreaterEqual(len(self.skill.from_caffeine_wiz), 1)
        invalid_entry = ["beverage", "quantity (oz)", "caffeine content (mg)"]
        self.skill.from_caffeine_wiz.append(invalid_entry)
        self.skill._add_more_caffeine_data()
        self.assertNotIn(invalid_entry, self.skill.from_caffeine_wiz)

        self.skill.from_caffeine_wiz = real_data

    def test_get_new_info(self):
        real_method = self.skill._add_more_caffeine_data
        self.skill._add_more_caffeine_data = Mock()
        self.skill.from_caffeine_wiz = None
        self.skill.from_caffeine_informer = None
        self.skill._get_new_info()
        self.assertIsInstance(self.skill.from_caffeine_wiz, list)
        self.assertIsInstance(self.skill.from_caffeine_informer, list)
        self.skill.speak_dialog.assert_not_called()
        self.skill._add_more_caffeine_data.assert_called_once()

        self.assertTrue(self.skill.file_system.exists(
            "drinkList_from_caffeine_wiz.txt"))
        # TODO: Replace after resolving update errors DM
        # self.assertTrue(self.skill.file_system.exists(
        #     "drinkList_from_caffeine_informer.txt"))

        self.assertTrue(self.skill._get_new_info(True))
        self.skill.speak_dialog.assert_called_once_with("update_complete")
        self.skill._add_more_caffeine_data = real_method

    def test_clean_drink_name(self):
        self.assertEqual("coffee", self.skill._clean_drink_name("a coffee"))
        self.assertEqual("coffee",
                         self.skill._clean_drink_name("a cup of coffee"))
        self.assertEqual("coffee",
                         self.skill._clean_drink_name("a glass of coffee"))
        self.assertEqual("coffee",
                         self.skill._clean_drink_name("a cup of coffee?"))
        self.assertEqual("coffee",
                         self.skill._clean_drink_name("a cup of coffee"))
        self.assertEqual("shot of espresso",
                         self.skill._clean_drink_name("a shot of espresso"))

        self.assertEqual("", self.skill._clean_drink_name("a cup of"))

        self.assertEqual("", self.skill._clean_drink_name("a "))

        for spoken, translated in self.skill.translate_drinks.items():
            self.assertEqual(translated, self.skill._clean_drink_name(spoken))

    def test_drink_in_database(self):
        self.assertTrue(self.skill._drink_in_database("coke"))
        self.assertTrue(self.skill._drink_in_database("coca-cola classic"))
        self.assertFalse(self.skill._drink_in_database("software"))

    def test_get_matching_drinks(self):
        self.assertIsInstance(self.skill._get_matching_drinks("coke"), list)
        self.assertIsInstance(
            self.skill._get_matching_drinks("coca-cola classic"), list)
        self.assertIsInstance(self.skill._get_matching_drinks("software"),
                              list)

    def test_generate_drink_dialog(self):
        # TODO: Write this test DM
        pass


if __name__ == '__main__':
    unittest.main()
