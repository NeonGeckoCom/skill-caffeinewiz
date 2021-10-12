# NEON AI (TM) SOFTWARE, Software Development Kit & Application Framework
# All trademark and other rights reserved by their respective owners
# Copyright 2008-2022 Neongecko.com Inc.
# Contributors: Daniel McKnight, Guy Daniels, Elon Gasper, Richard Leeds,
# Regina Bloomstine, Casimiro Ferreira, Andrii Pernatii, Kirill Hrymailo
# BSD-3 License
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
# 1. Redistributions of source code must retain the above copyright notice,
#    this list of conditions and the following disclaimer.
# 2. Redistributions in binary form must reproduce the above copyright notice,
#    this list of conditions and the following disclaimer in the documentation
#    and/or other materials provided with the distribution.
# 3. Neither the name of the copyright holder nor the names of its
#    contributors may be used to endorse or promote products derived from this
#    software without specific prior written permission.
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO,
# THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR
# CONTRIBUTORS  BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL,
# EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO,
# PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA,
# OR PROFITS;  OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF
# LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE,  EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

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
from time import sleep
from neon_utils.skills.common_query_skill import CQSMatchLevel, CommonQuerySkill
from neon_utils.logger import LOG
from neon_utils import web_utils
from neon_utils.net_utils import check_online

from mycroft.util.parse import normalize

TIME_TO_CHECK = 3600


class CaffeineWizSkill(CommonQuerySkill):
    def __init__(self):
        super(CaffeineWizSkill, self).__init__(name="CaffeineWizSkill")
        # if skill_needs_patching(self):
        #     LOG.warning("Patching Neon skill for non-neon core")
        #     stub_missing_parameters(self)

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
            "and w root beer": "a&w root beer",
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

        self.last_updated = None  # TODO: This should be a direct settings reference
        try:
            if self.settings.get("lastUpdate"):
                self.last_updated = datetime.datetime.strptime(self.settings["lastUpdate"], '%Y-%m-%d %H:%M:%S.%f')
        except Exception as e:
            LOG.info(e)
        LOG.debug(self.last_updated)
        self.from_caffeine_wiz = list()
        self.from_caffeine_informer = list()

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
        if (tdelta.total_seconds() > TIME_TO_CHECK
            or not pathlib.Path(join(abspath(dirname(__file__)), 'drinkList_from_caffeine_informer.txt')).exists()
            or not pathlib.Path(join(abspath(dirname(__file__)), 'drinkList_from_caffeine_wiz.txt')).exists()) and \
                check_online(("https://www.caffeineinformer.com/the-caffeine-database", "http://caffeinewiz.com/")):
            # starting a separate process because websites might take a while to respond
            t = multiprocessing.Process(target=self._get_new_info())
            t.start()
        else:
            LOG.info("Using cached caffeine data")
            # Open cached results from the appropriate files:
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
                elif f" {drink.lower()} " in to_speak.lower():
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

    def convert_metric(self, caff_oz: float, caff_mg: int):
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
    def _drink_convert_to_metric(total, caffeine_oz, oz):  # TODO: Annotate and simplify this method DM
        return int((caffeine_oz / (oz * 29.5735)) * total)

    def converse(self, message=None):
        user = self.get_utterance_user(message)
        LOG.debug(self.actions_to_confirm)
        if user in self.actions_to_confirm.keys():
            result = self.check_yes_no_response(message)
            if result == -1:
                # This isn't a response, ignore it
                return False
            elif not result:
                # User said no
                if self.local_config.get("interface", {}).get("wake_word_enabled", True):
                    self.speak_dialog("HowAboutMore", expect_response=True)
                    self.enable_intent('CaffeineContentGoodbyeIntent')
                    self.request_check_timeout(self.default_intent_timeout, 'CaffeineContentGoodbyeIntent')
                else:
                    self.speak_dialog("StayCaffeinated")
                return True
            elif result:
                # User said yes
                LOG.info(self.results)
                self._get_drink_text(message)
                # self.speak(self._get_drink_text())
                # self.speak("Provided by CaffeineWiz.")
                self.speak("Provided by CaffeineWiz. Stay caffeinated!")
                return True
        return False

    def stop(self):
        pass

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
        self.from_caffeine_wiz.remove(["beverage", "quantity (oz)", "caffeine content (mg)"])
        # LOG.info(self.from_caffeine_wiz)

    def _get_new_info(self, reply=False):
        """fetches and combines new data from the two caffeine sources"""
        time_check = datetime.datetime.now()

        # Update from caffeineinformer
        try:
            # prep the html pages:
            page = urllib.request.urlopen("https://www.caffeineinformer.com/the-caffeine-database").read()
            soup = BeautifulSoup(page, "html.parser")

            # extract the parts that we need.
            # note that the html formats are very different, so we are using 2 separate approaches:
            # 1 - using strings and ast.literal:
            raw_j2 = str(soup.find_all('script', type="text/javascript")[2])
            new_url = raw_j2[:raw_j2.rfind("function pause") - 6][raw_j2.rfind("tbldata = [") + 11:].lower()
            new = web_utils.strip_tags(new_url)
            self.from_caffeine_informer = list(ast.literal_eval(new))
            # LOG.warning(self.from_caffeine_informer)
        except Exception as e:
            LOG.error(f"Error updating from sources: {e}")

        # Update from caffeinewiz
        try:
            htmldoc = urllib.request.urlopen("http://caffeinewiz.com/").read()
            soup2 = BeautifulSoup(htmldoc, "html.parser")

            # 2 - by parsing the table on a given page:
            areatable = soup2.find('table')
            if areatable:
                self.from_caffeine_wiz = list(
                    (web_utils.chunks([i.text.lower().replace("\n", "")
                                       for i in areatable.findAll('td') if i.text != "\xa0"], 3)))
            # LOG.warning(self.from_caffeine_wiz)
        except Exception as e:
            LOG.error(e)

        # Add Normalized drink names
        try:
            for drink in self.from_caffeine_informer:
                parsed_name = normalize(drink[0].replace('-', ' '))
                if drink[0] != parsed_name:
                    # LOG.debug(parsed_name)
                    new_drink = [parsed_name] + drink[1:]
                    # LOG.debug(new_drink)
                    self.from_caffeine_informer.append(new_drink)
                    # LOG.warning(self.from_caffeine_informer[len(self.from_caffeine_informer) - 1])

            for drink in self.from_caffeine_wiz:
                parsed_name = normalize(drink[0].replace('-', ' '))
                if drink[0] != parsed_name:
                    # LOG.debug(parsed_name)
                    new_drink = [parsed_name] + drink[1:]
                    # LOG.debug(new_drink)
                    self.from_caffeine_wiz.append(new_drink)
                    # LOG.warning(self.from_caffeine_wiz[len(self.from_caffeine_wiz) - 1])
        except Exception as e:
            LOG.error(e)

        # saving and pickling the results:
        with self.file_system.open('drinkList_from_caffeine_wiz.txt',
                                   'wb+') as from_caffeine_wiz_file:
            pickle.dump(self.from_caffeine_wiz, from_caffeine_wiz_file)

        with self.file_system.open('drinkList_from_caffeine_informer.txt',
                                   'wb+') as from_caffeine_informer_file:
            pickle.dump(self.from_caffeine_informer, from_caffeine_informer_file)
        self._add_more_caffeine_data()

        try:
            self.update_skill_settings({"lastUpdate": str(time_check)}, skill_global=True)
            if reply:
                self.speak_dialog("UpdateComplete")
        except Exception as e:
            LOG.error("An error occurred during the CaffeineWiz update: " + str(e))
            # self.check_for_signal("WIZ_getting_new_content")

    def _clean_drink_name(self, drink: str) -> str:
        """
        Normalizes an input drink name and handles known common alternative names
        :param drink: Parsed user requested drink
        :return: normalized drink or None if no name was parsed
        """
        if not drink:
            LOG.error(f"No Drink name provided to normalize")
            return ""
        drink = drink.lower()

        try:
            # Strip leading "a"
            drink = drink.split(maxsplit=1)[1] if drink.split(maxsplit=1)[0] == "a" else drink
        except IndexError:
            LOG.error(f"Invalid drink passed: {drink}")
            return ""
        if drink.startswith("cup of") or drink.startswith("glass of"):
            drink = drink.split(" of", 1)[1].strip()
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
