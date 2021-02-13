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

import ast
import datetime
import difflib
import multiprocessing
import pathlib
import pickle
import urllib.request
from os.path import join, abspath, dirname
from adapt.intent import IntentBuilder
from bs4 import BeautifulSoup
# from NGI.utilities import beautifulSoupHelper as bU
from mycroft.skills import CQSMatchLevel
from mycroft.skills import CommonQuerySkill
from time import sleep
# from mycroft.util import create_signal, check_for_signal
from mycroft.util.log import LOG
from mycroft.util.parse import normalize
from neon_utils import stub_missing_parameters, skill_needs_patching, web_utils

TIME_TO_CHECK = 3600


class CaffeineWizSkill(CommonQuerySkill):
    def __init__(self):
        super(CaffeineWizSkill, self).__init__(name="CaffeineWizSkill")
        if skill_needs_patching(self):
            LOG.warning("Patching Neon skill for non-neon core")
            stub_missing_parameters(self)

        self.results = None  # TODO: Should be dict for multi-user support DM
        self.translate_drinks = {
            'pepsi': 'pepsi cola',
            # 'coke 0': 'coke zero',
            'coke': 'coca-cola classic',
            'coca-cola': 'coca-cola classic',
            'coca cola': 'coca-cola classic',
            'starbucks blonde': 'starbucks coffee blonde roast',
            'starbucks blond': 'starbucks coffee blonde roast',
            'diet cherry coke': 'diet cherry coca-cola',
            "a and w root beer": "a&w root beer",
            "mcdonald's coffee": "mcdonalds coffee",
            "okay energy drink": "ok energy drink",
            "vitamin water energy drink": "vitaminwater energy drink",
            # "7 11 energy shot": "7-eleven energy shot",
            # "7 up": "7-up",
            # "amp energy 0": "amp energy zero",
            "all day energy shot": "allday energy shot",
            "blue energy drinks": "blu energy drinks",
            "blue frog energy drink": "blu frog energy drink"
            }

        self.last_updated = None
        try:
            if self.settings.get("lastUpdate"):
                self.last_updated = datetime.datetime.strptime(self.settings["lastUpdate"], '%Y-%m-%d %H:%M:%S.%f')
        except Exception as e:
            LOG.info(e)
        LOG.debug(self.last_updated)
        self.from_caffeine_wiz = None
        self.from_caffeine_informer = None

    def initialize(self):
        caffeine_intent = IntentBuilder("CaffeineContentIntent").require("CaffeineKeyword").require("drink").build()
        self.register_intent(caffeine_intent, self.handle_caffeine_intent)

        goodbye_intent = IntentBuilder("CaffeineContentGoodbyeIntent").require("GoodbyeKeyword").build()
        self.register_intent(goodbye_intent, self.handle_goodbye_intent)

        update_caffeine = IntentBuilder("Caffeine_update").require("UpdateCaffeine").build()
        self.register_intent(update_caffeine, self.handle_caffeine_update)

        self.disable_intent('CaffeineContentGoodbyeIntent')

        tdelta = datetime.datetime.now() - self.last_updated if self.last_updated else datetime.timedelta(hours=1.1)
        LOG.info(tdelta)
        # if more than one hour, calculate and fetch new data again:
        if tdelta.total_seconds() > TIME_TO_CHECK \
                or not pathlib.Path(join(abspath(dirname(__file__)), 'drinkList_from_caffeine_informer.txt')).exists() \
                or not pathlib.Path(join(abspath(dirname(__file__)), 'drinkList_from_caffeine_wiz.txt')).exists():
            self.create_signal("WIZ_getting_new_content")
            # starting a separate process because websites might take a while to respond
            t = multiprocessing.Process(target=self._get_new_info())
            t.start()
        else:
            # if less than 1 hour, unpickle saved results from the appropriate files:
            with self.file_system.open('drinkList_from_caffeine_wiz.txt',
                                       'rb') as from_caffeine_wiz_file:
                self.from_caffeine_wiz = pickle.load(from_caffeine_wiz_file)

            with self.file_system.open('drinkList_from_caffeine_informer.txt',
                                       'rb') as from_caffeine_informer_file:
                self.from_caffeine_informer = pickle.load(from_caffeine_informer_file)
                # combine them as in get_new_info and add rocket chocolate:
                self._add_more_caffeine_data()

    def handle_caffeine_update(self, message):
        LOG.debug(message)
        self.speak_dialog("Updating")
        t = multiprocessing.Process(target=self._get_new_info(reply=True))
        t.start()

    # def handle_no_intent(self):
    #     self.speak("Say how about caffeine content of another drink or say goodbye.", True) if \
    #         not self.check_for_signal("CORE_skipWakeWord", -1) else self.speak("Stay caffeinated!")
    #     self.enable_intent('CaffeineContentGoodbyeIntent')
    #     self.request_check_timeout(self.default_intent_timeout, 'CaffeineContentGoodbyeIntent')
    #     self.disable_intent('CaffeineYesIDoIntent')
    #     self.disable_intent('Caffeine_no_intent')
    #
    # def handle_yes_i_do_intent(self, message):
    #     LOG.info(self.results)
    #     self._get_drink_text(message)
    #     # self.speak(self._get_drink_text())
    #     # self.speak("Provided by CaffeineWiz.")
    #     self.speak("Provided by CaffeineWiz. Say how about caffeine content of another drink or say goodbye.", True) \
    #         if not self.check_for_signal("CORE_skipWakeWord", -1) else \
    #         self.speak("Provided by CaffeineWiz. Stay caffeinated!")
    #     self.enable_intent('CaffeineContentGoodbyeIntent')
    #     self.request_check_timeout(self.default_intent_timeout, 'CaffeineContentGoodbyeIntent')
    #     self.disable_intent('CaffeineYesIDoIntent')
    #     self.disable_intent('Caffeine_no_intent')

    def CQS_match_query_phrase(self, utt, message=None):
        if " of " in utt:
            drink = utt.split(" of ", 1)[1]
        elif " in " in utt:
            drink = utt.split(" in ", 1)[1]
        else:
            drink = utt
        drink = self._clean_drink_name(drink)
        if not drink:
            return None
        if self._drink_in_database(drink):
            try:
                to_speak = self._generate_drink_dialog(drink, message)
                if self.voc_match(utt, "caffeine"):
                    conf = CQSMatchLevel.EXACT
                elif drink.lower() in to_speak.lower().split():
                    # If the exact drink name was matched, but caffeine not requested, consider this a general match
                    conf = CQSMatchLevel.GENERAL
                else:
                    # We didn't match "caffeine" or an exact drink name, this request isn't for this skill
                    return None
            except Exception as e:
                LOG.error(e)
                LOG.error(drink)
                return None
        else:
            to_speak = self.dialog_renderer.render("NotFound", {"drink": drink})
            if self.voc_match(utt, "caffeine"):
                conf = CQSMatchLevel.CATEGORY
            else:
                return None
        return utt, conf, to_speak, {"user": self.get_utterance_user(message)}

    def CQS_action(self, phrase, data):
        if self.neon_core:
            self.make_active()
            if len(self.results) == 1:
                if not self.check_for_signal("CORE_skipWakeWord", -1):
                    self.speak_dialog("HowAboutMore", expect_response=True)
                    self.enable_intent('CaffeineContentGoodbyeIntent')
                    self.request_check_timeout(self.default_intent_timeout, 'CaffeineContentGoodbyeIntent')
                else:
                    self.speak_dialog("StayCaffeinated")
            else:
                self.speak_dialog("MoreDrinks", expect_response=True)
                self.await_confirmation(data.get("user", "local"), "more")

    def handle_caffeine_intent(self, message):
        # flac_filename = message.data.get("flac_filename")
        drink = self._clean_drink_name(message.data.get("drink", None))
        if not drink:
            self.speak_dialog("NoDrinkHeard")
            return
        elif self.check_for_signal('CORE_useHesitation', -1):
            self.speak_dialog('one_moment', private=True)

        if self._drink_in_database(drink):
            self.speak(self._generate_drink_dialog(drink, message))
            if self.neon_core:
                if len(self.results) == 1:
                    if not self.check_for_signal("CORE_skipWakeWord", -1):
                        self.speak_dialog("HowAboutMore", expect_response=True)
                        self.enable_intent('CaffeineContentGoodbyeIntent')
                        self.request_check_timeout(self.default_intent_timeout, 'CaffeineContentGoodbyeIntent')
                    else:
                        self.speak_dialog("StayCaffeinated")
                else:
                    self.speak_dialog("MoreDrinks", expect_response=True)
                    self.await_confirmation(self.get_utterance_user(message), "more")
        else:
            self.speak_dialog("NotFound", {'drink': drink})

    def convert_metric(self, caff_oz, caff_mg):
        """
        Convert from imperial to metric units
        :param caff_oz: (float) oz from lookup
        :param caff_mg: (int) mg from lookup
        :return: mg, vol, units
        """

        if caff_oz <= 8.45351:
            caff_mg = str(self._drink_convert_to_metric(250, caff_mg, caff_oz))
            caff_vol = '250'
            drink_units = 'milliliters'
        elif caff_oz <= 16.907:
            caff_mg = str(self._drink_convert_to_metric(500, caff_mg, caff_oz))
            caff_vol = '500'
            drink_units = 'milliliters'
        else:
            caff_mg = str(self._drink_convert_to_metric(1000, caff_mg, caff_oz))
            caff_vol = '1'
            drink_units = 'liter'
        # caff_vol = caff_oz
        return caff_mg, caff_vol, drink_units

    def handle_goodbye_intent(self, message):
        """
        Note: now the "reply" intents are deactivated,
              since the user specified the end of the skill
              by saying "goodbye"
        """

        # Remove any awaiting confirmation
        try:
            user = self.get_utterance_user(message)
            self.actions_to_confirm.pop(user)
        except Exception as e:
            LOG.error(e)

        self.disable_intent('CaffeineContentGoodbyeIntent')
        # self.disable_intent('CaffeineYesIDoIntent')
        # self.disable_intent('Caffeine_no_intent')
        # LOG.debug('3- Goodbye')
        self.speak_dialog("StayCaffeinated")

    @staticmethod
    def _drink_convert_to_metric(total, caffeine_oz, oz):
        return int((caffeine_oz / (oz * 29.5735)) * total)

    def converse(self, utterances, lang="en-us", message=None):
        user = self.get_utterance_user(message)
        LOG.debug(self.actions_to_confirm)
        if user in self.actions_to_confirm.keys():
            result = self.check_yes_no_response(message)
            if result == -1:
                # This isn't a response, ignore it
                return False
            elif not result:
                # User said no
                self.speak_dialog("HowAboutMore", expect_response=True) if \
                    not self.check_for_signal("CORE_skipWakeWord", -1) else self.speak_dialog("StayCaffeinated")
                self.enable_intent('CaffeineContentGoodbyeIntent')
                self.request_check_timeout(self.default_intent_timeout, 'CaffeineContentGoodbyeIntent')
                return True
            elif result:
                # User said yes
                LOG.info(self.results)
                self._get_drink_text(message)
                # self.speak(self._get_drink_text())
                # self.speak("Provided by CaffeineWiz.")
                self.speak("Provided by CaffeineWiz. Say how about caffeine content of another drink or say goodbye.",
                           True) \
                    if not self.check_for_signal("CORE_skipWakeWord", -1) else \
                    self.speak("Provided by CaffeineWiz. Stay caffeinated!")
                self.enable_intent('CaffeineContentGoodbyeIntent')
                self.request_check_timeout(self.default_intent_timeout, 'CaffeineContentGoodbyeIntent')
                return True
        return False

    def stop(self):
        self.clear_signals('WIZ')

    def _get_drink_text(self, message, caff_list=None):
        cnt = 0
        spoken = []
        if not caff_list:
            caff_list = self.results
            LOG.info(caff_list)
        for i in range(len(caff_list)):
            if caff_list[i][0] not in spoken:
                oz = float(caff_list[i][1])
                caffeine = float(caff_list[i][2])

                drink = caff_list[i][0]
                units = self.preference_unit(message)['measure']

                if units == "metric":
                    caff_mg, caff_vol, drink_units = self.convert_metric(oz, caffeine)
                else:
                    caff_mg = str(caffeine)
                    caff_vol = str(oz)
                    drink_units = 'ounces'

                self.speak_dialog('MultipleCaffeine', {'drink': drink,
                                                       'caffeine_content': caff_mg,
                                                       'caffeine_units': self.translate('milligrams'),
                                                       'drink_size': caff_vol,
                                                       'drink_units': drink_units})
                spoken.append(caff_list[i][0])
                sleep(0.5)  # Prevent simultaneous speak inserts
            cnt = cnt + 1

    def _add_more_caffeine_data(self):
        """
        Add in some arbitrary additional data.
        """
        self.from_caffeine_wiz.append(['rocket chocolate', '.4', '150'])
        self.from_caffeine_wiz.extend(x[:-2] for x in
                                      self.from_caffeine_informer
                                      if str(x[:-2]) not in str(self.from_caffeine_wiz))
        sorted(self.from_caffeine_wiz)
        # LOG.info(self.from_caffeine_wiz)

    def _get_new_info(self, reply=False):
        """fetches and combines new data from the two caffeine sources"""
        time_check = datetime.datetime.now()

        try:
            # prep the html pages:
            page = urllib.request.urlopen("https://www.caffeineinformer.com/the-caffeine-database").read()
            soup = BeautifulSoup(page, "html.parser")

            htmldoc = urllib.request.urlopen("http://caffeinewiz.com/").read()
            soup2 = BeautifulSoup(htmldoc, "html.parser")

            # extract the parts that we need.
            # note that the html formats are very different, so we are using 2 separate approaches:
            # 1 - using strings and ast.literal:
            raw_j2 = str(soup.find_all('script', type="text/javascript")[2])
            new_url = raw_j2[:raw_j2.rfind("function pause") - 6][raw_j2.rfind("tbldata = [") + 11:].lower()
            new = web_utils.strip_tags(new_url)
            self.from_caffeine_informer = list(ast.literal_eval(new))
            # LOG.warning(self.from_caffeine_informer)

            # Add STT parsable names
            for drink in self.from_caffeine_informer:
                parsed_name = normalize(drink[0].replace('-', ' '))
                if drink[0] != parsed_name:
                    # LOG.debug(parsed_name)
                    new_drink = [parsed_name] + drink[1:]
                    # LOG.debug(new_drink)
                    self.from_caffeine_informer.append(new_drink)
                    # LOG.warning(self.from_caffeine_informer[len(self.from_caffeine_informer) - 1])

            # 2 - by parsing the table on a given page:
            areatable = soup2.find('table')
            if areatable:
                self.from_caffeine_wiz = list(
                    (web_utils.chunks([i.text.lower().replace("\n", "")
                                       for i in areatable.findAll('td') if i.text != "\xa0"], 3)))
            # LOG.warning(self.from_caffeine_wiz)

            # Add STT parsable names
            for drink in self.from_caffeine_wiz:
                parsed_name = normalize(drink[0].replace('-', ' '))
                if drink[0] != parsed_name:
                    # LOG.debug(parsed_name)
                    new_drink = [parsed_name] + drink[1:]
                    # LOG.debug(new_drink)
                    self.from_caffeine_wiz.append(new_drink)
                    # LOG.warning(self.from_caffeine_wiz[len(self.from_caffeine_wiz) - 1])

            # LOG.info(type(self.to_g))
            # saving and pickling the results:
            with self.file_system.open('drinkList_from_caffeine_wiz.txt',
                                       'wb+') as from_caffeine_wiz_file:
                pickle.dump(self.from_caffeine_wiz, from_caffeine_wiz_file)

            with self.file_system.open('drinkList_from_caffeine_informer.txt',
                                       'wb+') as from_caffeine_informer_file:
                pickle.dump(self.from_caffeine_informer, from_caffeine_informer_file)
            self._add_more_caffeine_data()
            # self.configuration_available["devVars"]["caffeineUpdate"] = time_check
            # self.create_signal("NGI_YAML_config_update")
            # time_check = str(time_check)
        except Exception as e:
            LOG.error(e)

        try:
            if self.neon_core:
                LOG.debug(type(self.ngi_settings))
                self.ngi_settings.update_yaml_file("lastUpdate", value=str(time_check))
                # self.local_config.update_yaml_file("devVars", "caffeineUpdate", time_check)
            self.check_for_signal("WIZ_getting_new_content")
            if reply:
                self.speak_dialog("UpdateComplete")
        except Exception as e:
            LOG.error("An error occurred during the CaffeineWiz update: " + str(e))
            self.check_for_signal("WIZ_getting_new_content")

    def _clean_drink_name(self, drink: str) -> [str, None]:
        if not drink:
            return None
        drink = drink.lower()
        # Strip leading "a"
        if drink.split(maxsplit=1)[0] == "a":
            drink.lstrip("a")
        if drink.startswith("cup of") or drink.startswith("glass of"):
            drink = drink.split(" of ", 1)[1]
        drink = drink.translate({ord(i): None for i in '?:!/;@#$'}).rstrip().replace(" '", "'")
        # Check for common mis-matched names
        drink = self.translate_drinks.get(drink, drink)
        LOG.info(drink)
        return drink

    def _drink_in_database(self, drink: str) -> bool:
        return any(i for i in self.from_caffeine_wiz if i[0] in drink or drink in i[0])

    def _get_matching_drinks(self, drink: str) -> list:
        return [i for i in self.from_caffeine_wiz if i[0] in drink or drink in i[0]]

    def _generate_drink_dialog(self, drink: str, message) -> str:
        """
        Generates the dialog and populates self.results for the requested drink
        :param drink: raw input drink to find
        :param message: message associated with request
        :return: generated dialog to speak
        """
        self.results = self._get_matching_drinks(drink)
        LOG.debug(self.results)
        if len(self.results) == 1:
            '''Return the only result'''
            # self.speak(("The best match is: " + str(self.results[0][0]) +
            #             ", which has " + str(self.results[0][2]) + " milligrams caffeine in "
            #             + str(self.results[0][1])) + " ounces. Provided by CaffeineWiz")
            drink = str(self.results[0][0])
            caff_mg = float(self.results[0][2])
            caff_oz = float(self.results[0][1])

        else:
            '''Find the best match from all of the returned results'''
            matched_drink_names = [self.results[i][0] for i in range(len(self.results))]
            match = difflib.get_close_matches(drink, matched_drink_names, 1)
            if match:
                match2 = [i for i in self.results if i[0] in match]
            else:
                match2 = [i for i in self.results if i[0] in matched_drink_names[0]]
            LOG.debug(match)
            LOG.debug(match2)
            drink = str(match2[0][0])
            caff_mg = float(match2[0][2])
            caff_oz = float(match2[0][1])
            # self.speak(("The best match is: " + str(match2[0][0]) +
            #             ", which has " + str(match2[0][2]) + " milligrams caffeine in "
            #             + str(match2[0][1])) + " ounces. Provided by CaffeineWiz")
        preference_unit = self.preference_unit(message)
        # self.digits = preference_unit['measure'] \
        #     if preference_unit['measure'] else 'imperial'
        if preference_unit['measure'] == 'metric':
            caff_mg, caff_vol, drink_units = self.convert_metric(caff_oz, caff_mg)
        else:
            caff_mg = str(caff_mg)
            caff_vol = str(caff_oz)
            drink_units = 'ounces'

        LOG.info(f"{drink} | {caff_mg} | {caff_vol} | {drink_units}")
        to_speak = self.dialog_renderer.render('DrinkCaffeine', {'drink': drink,
                                                                 'caffeine_content': caff_mg,
                                                                 'caffeine_units': self.translate('milligrams'),
                                                                 'drink_size': caff_vol,
                                                                 'drink_units': drink_units})
        return to_speak


def create_skill():
    return CaffeineWizSkill()
