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
import os.path
import pickle
import urllib.request
from threading import Event, Thread

from typing import Optional, Tuple
from adapt.intent import IntentBuilder
from bs4 import BeautifulSoup
from time import sleep

from lingua_franca import load_language
from mycroft_bus_client import Message
from neon_utils.user_utils import get_user_prefs, get_message_user
from neon_utils.skills.common_query_skill import \
    CQSMatchLevel, CommonQuerySkill
from neon_utils.logger import LOG
from neon_utils import web_utils

from mycroft.util.parse import normalize
from mycroft.skills import intent_handler


TIME_TO_CHECK = 3600


class CaffeineWizSkill(CommonQuerySkill):
    def __init__(self):
        super(CaffeineWizSkill, self).__init__(name="CaffeineWizSkill")
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

        self.from_caffeine_wiz = list()
        self.from_caffeine_informer = list()
        self._update_event = Event()

        load_language('en')  # Load for drink name normalization

    @property
    def last_updated(self) -> Optional[datetime.datetime]:
        if self.settings.get("lastUpdate"):
            return datetime.datetime.strptime(self.settings["lastUpdate"],
                                              '%Y-%m-%d %H:%M:%S.%f')
        return None

    @property
    def ww_enabled(self):
        resp = self.bus.wait_for_response(Message("neon.query_wake_words_state"))
        if not resp:
            LOG.warning("No WW Status reported")
            return None
        if resp.data.get('enabled', True):
            return True
        return False

    def initialize(self):
        goodbye_intent = IntentBuilder("CaffeineContentGoodbyeIntent")\
            .require("goodbye").build()
        self.register_intent(goodbye_intent, self.handle_goodbye_intent)
        self.disable_intent('CaffeineContentGoodbyeIntent')

        tdelta = datetime.datetime.now() - self.last_updated if \
            self.last_updated else datetime.timedelta(hours=1.1)
        LOG.info(tdelta)
        # if more than one hour, calculate and fetch new data again:
        if any((tdelta.total_seconds() > TIME_TO_CHECK,
                not self.file_system.exists(
                    'drinkList_from_caffeine_informer.txt'),
                not self.file_system.exists(
                    'drinkList_from_caffeine_wiz.txt'))):
            # starting a separate process because this might take some time
            t = Thread(target=self._get_new_info, daemon=False)
            t.start()
        else:
            self._update_event.set()
            LOG.info("Using cached caffeine data")
            # Open cached results from the appropriate files:
            with self.file_system.open('drinkList_from_caffeine_wiz.txt',
                                       'rb') as from_caffeine_wiz_file:
                self.from_caffeine_wiz = pickle.load(from_caffeine_wiz_file)

            with self.file_system.open('drinkList_from_caffeine_informer.txt',
                                       'rb') as from_caffeine_informer_file:
                self.from_caffeine_informer = \
                    pickle.load(from_caffeine_informer_file)
            # combine them as in get_new_info and add rocket chocolate:
            self._add_more_caffeine_data()

    @intent_handler(IntentBuilder("CaffeineUpdate").require("update_caffeine"))
    def handle_caffeine_update(self, message):
        LOG.debug(message)
        self.speak_dialog("updating")
        t = Thread(target=self._get_new_info, kwargs={"reply": True},
                   daemon=True)
        t.start()
        if not self._update_event.wait(30):
            LOG.error("Timeout waiting for update")

    @intent_handler(IntentBuilder("CaffeineContentIntent")
                    .require("query_caffeine").require("drink"))
    def handle_caffeine_intent(self, message):

        drink = self._clean_drink_name(message.data.get("drink", None))
        if not drink:
            self.speak_dialog("no_drink_heard")
            return

        if not self._update_event.isSet():
            self.speak_dialog('one_moment', private=True)
            if not self._update_event.wait(30):
                LOG.error("Update taking more than 30s, clearing event")
                self._update_event.set()
        elif get_user_prefs(message)['response_mode'].get('hesitation'):
            self.speak_dialog('one_moment', private=True)

        if self._drink_in_database(drink):
            dialog, results = self._generate_drink_dialog(drink, message)
            if dialog:
                self.speak(dialog)
            else:
                self.speak_dialog("not_found", {'drink': drink})

            if self.neon_core:
                if len(results) == 1:
                    if self.ww_enabled:
                        self.speak_dialog("how_about_more",
                                          expect_response=True)
                        self.enable_intent('CaffeineContentGoodbyeIntent')
                        self.request_check_timeout(
                            self.default_intent_timeout,
                            ['CaffeineContentGoodbyeIntent'])
                    else:
                        self.speak_dialog("stay_caffeinated")
                else:
                    self.activate()
                    if self.ask_yesno("more_drinks") == "yes":
                        self._speak_alternate_results(message, results)
                        self.speak_dialog("provided_by_caffeinewiz")
                    else:
                        self.speak_dialog("stay_caffeinated")
        else:
            self.speak_dialog("not_found", {'drink': drink})

    def CQS_match_query_phrase(self, utt, message: Message = None):
        LOG.info(message)
        # TODO: Language agnostic parsing here
        if " of " in utt:
            drink = utt.split(" of ", 1)[1]
        elif " in " in utt:
            drink = utt.split(" in ", 1)[1]
        else:
            drink = utt
        drink = self._clean_drink_name(drink)
        if not drink:
            return None

        if not self._update_event.isSet():
            self._update_event.wait(30)

        if self._drink_in_database(drink):
            try:
                to_speak, results = self._generate_drink_dialog(drink, message)
                if not to_speak:
                    # No dialog generated
                    return None
                if self.voc_match(utt, "caffeine"):
                    conf = CQSMatchLevel.EXACT
                elif f" {drink.lower()} " in to_speak.lower():
                    # If the exact drink name was matched
                    # but caffeine not requested, consider this a general match
                    conf = CQSMatchLevel.GENERAL
                else:
                    # We didn't match "caffeine" or an exact drink name
                    # this request isn't for this skill
                    return None
            except Exception as e:
                LOG.error(e)
                LOG.error(drink)
                return None
        else:
            to_speak = self.dialog_renderer.render("not_found",
                                                   {"drink": drink})
            results = None
            if self.voc_match(utt, "caffeine"):
                conf = CQSMatchLevel.CATEGORY
            else:
                return None
        LOG.info(f"results={results}")
        user = get_message_user(message) if message else 'local'
        return utt, conf, to_speak, {"user": user,
                                     "message": message.serialize() if message
                                     else None,
                                     "results": results}

    def CQS_action(self, phrase, data):
        results = data.get("results")
        message = Message.deserialize(data.get("message")) if \
            data.get("message") else None
        if self.neon_core:
            self.make_active()
            if len(results) == 1:
                self.speak_dialog("stay_caffeinated")
            else:
                # TODO: This is patching poor handling in get_response
                from neon_utils.signal_utils import wait_for_signal_clear
                wait_for_signal_clear("isSpeaking", 30)
                if self.ask_yesno("more_drinks") == "yes":
                    LOG.info("YES")
                    self._speak_alternate_results(message, results)
                    self.speak_dialog("provided_by_caffeinewiz")
                else:
                    LOG.info("NO")
                    self.speak_dialog("stay_caffeinated")

    @staticmethod
    def convert_metric(caff_oz: float, caff_mg: float) -> (str, str, str):
        """
        Convert from imperial to metric units
        :param caff_oz: (float) oz from lookup
        :param caff_mg: (int) mg from lookup
        :return: mg, vol, units
        """

        def _drink_convert_to_metric(normalized_ml, caffeine_oz, oz):
            return int((caffeine_oz / (oz * 29.5735)) * normalized_ml)

        if caff_oz < 16:
            caff_mg = str(_drink_convert_to_metric(250, caff_mg, caff_oz))
            caff_vol = '250'
            unit_resource = 'word_milliliters'
        elif caff_oz < 32:
            caff_mg = str(_drink_convert_to_metric(500, caff_mg, caff_oz))
            caff_vol = '500'
            unit_resource = 'word_milliliters'
        else:
            caff_mg = str(_drink_convert_to_metric(1000, caff_mg, caff_oz))
            caff_vol = '1'
            unit_resource = 'word_liter'
        # caff_vol = caff_oz
        return caff_mg, caff_vol, unit_resource

    def handle_goodbye_intent(self, message):
        """
        Note: now the "reply" intents are deactivated,
              since the user specified the end of the skill
              by saying "goodbye"
        """

        # Remove any awaiting confirmation
        try:
            user = get_message_user(message)
            self.actions_to_confirm.pop(user)
        except Exception as e:
            LOG.error(e)

        self.disable_intent('CaffeineContentGoodbyeIntent')
        self.speak_dialog("stay_caffeinated")

    def stop(self):
        pass

    def _speak_alternate_results(self, message, caff_list=None):
        """
        Speak alternate drink data from caff_list
        :param message: Message associated with request
        :param caff_list: List of alternate drinks as
            returned by _generate_drink_dialog
        """
        cnt = 0
        spoken = []
        if not caff_list:
            LOG.error("No results to handle")
            return
        for i in range(len(caff_list)):
            # TODO: Check for stop request
            if caff_list[i][0] not in spoken:
                oz = float(caff_list[i][1])
                caffeine = float(caff_list[i][2])

                drink = caff_list[i][0]
                units = get_user_prefs(message)['units']['measure']

                if units == "metric":
                    caff_mg, caff_vol, unit_dialog = \
                        self.convert_metric(oz, caffeine)
                else:
                    caff_mg = str(caffeine)
                    caff_vol = str(oz)
                    unit_dialog = 'word_ounces'

                self.speak_dialog('multiple_drinks',
                                  {'drink': drink,
                                   'caffeine_content': caff_mg,
                                   'caffeine_units': self.translate(
                                       'word_milligrams'),
                                   'drink_size': caff_vol,
                                   'drink_units': self.translate(unit_dialog)})
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
                                      if str(x[:-2]) not in
                                      str(self.from_caffeine_wiz))
        invalid_entry = ["beverage", "quantity (oz)", "caffeine content (mg)"]
        if invalid_entry in self.from_caffeine_wiz:
            self.from_caffeine_wiz.remove(invalid_entry)
        sorted(self.from_caffeine_wiz)

    def _get_new_info(self, reply=False):
        """fetches and combines new data from the two caffeine sources"""
        self._update_event.clear()
        success = False
        time_check = datetime.datetime.now()

        # TODO: caffeineinformer update failing DM
        # Update from caffeineinformer
        try:
            # prep the html pages:
            page = urllib.request.urlopen(
                "https://www.caffeineinformer.com/the-caffeine-database")\
                .read()
            soup = BeautifulSoup(page, "html.parser")

            # extract the parts that we need.
            # note that the html formats are very different, so we are using 2 separate approaches:
            # 1 - using strings and ast.literal:
            raw_j2 = str(soup.find_all('script', type="text/javascript")[2])
            new_url = raw_j2[:raw_j2.rfind("function pause") - 6][
                      raw_j2.rfind("tbldata = [") + 11:].lower()
            new = web_utils.strip_tags(new_url)
            self.from_caffeine_informer = list(ast.literal_eval(new))
            # LOG.warning(self.from_caffeine_informer)
        except Exception as e:
            LOG.error(f"Error updating from caffeineinformer: {e}")
            self.from_caffeine_informer = self.from_caffeine_informer or list()

        # Update from caffeinewiz
        try:
            htmldoc = urllib.request.urlopen("http://caffeinewiz.com/").read()
            soup2 = BeautifulSoup(htmldoc, "html.parser")

            # 2 - by parsing the table on a given page:
            areatable = soup2.find('table')
            if areatable:
                self.from_caffeine_wiz = list(
                    (web_utils.chunks([i.text.lower().replace("\n", "")
                                       for i in areatable.findAll('td')
                                       if i.text != "\xa0"], 3)))
            # LOG.warning(self.from_caffeine_wiz)
        except Exception as e:
            LOG.error(f"Error updating from caffeinewiz: {e}")
            self.from_caffeine_wiz = self.from_caffeine_wiz or list()

        # Add Normalized drink names
        def _normalize_drink_list(drink_list):
            for drink in drink_list:
                try:
                    parsed_name = normalize(drink[0].replace('-', ' '), 'en')
                    if drink[0] != parsed_name:
                        new_drink = [parsed_name] + drink[1:]
                        LOG.debug(f"Normalizing {drink[0]} to {new_drink[0]}")
                        drink_list.append(new_drink)
                except Exception as x:
                    LOG.error(x)
        try:
            _normalize_drink_list(self.from_caffeine_informer)
            _normalize_drink_list(self.from_caffeine_wiz)
        except Exception as e:
            LOG.error(e)

        # saving and pickling the results:
        if not self.from_caffeine_wiz:
            LOG.info("Loading Caffeine data from bundled defaults")
            with open(os.path.join(os.path.dirname(__file__), "data",
                                   "caffeine_wiz_data.pickle"),
                      'rb') as f:
                self.from_caffeine_wiz = pickle.load(f)
        with self.file_system.open('drinkList_from_caffeine_wiz.txt',
                                   'wb+') as from_caffeine_wiz_file:
            pickle.dump(self.from_caffeine_wiz, from_caffeine_wiz_file)

        if self.from_caffeine_informer:
            with self.file_system.open('drinkList_from_caffeine_informer.txt',
                                       'wb+') as from_caffeine_informer_file:
                pickle.dump(self.from_caffeine_informer,
                            from_caffeine_informer_file)
        self._add_more_caffeine_data()

        try:
            # TODO: Check for CW and CI success
            if self.from_caffeine_wiz:
                self.update_skill_settings({"lastUpdate": str(time_check)},
                                           skill_global=True)
                if reply:
                    self.speak_dialog("update_complete")
                success = True
            elif reply:
                LOG.error("CaffeineWiz source failed to update!")
                self.speak_dialog("update_error")
        except Exception as e:
            LOG.error(f"An error occurred during the CaffeineWiz update: {e}")
            # self.check_for_signal("WIZ_getting_new_content")
        self._update_event.set()
        return success

    def _clean_drink_name(self, drink: str) -> str:
        """
        Normalizes an input drink name and handles known alternative names
        :param drink: Parsed user requested drink
        :return: normalized drink or None if no name was parsed
        """
        if not drink:
            LOG.error(f"No Drink name provided to normalize")
            return ""
        drink = drink.lower()

        try:
            # Strip leading "a"
            drink = drink.split(maxsplit=1)[1] if \
                drink.split(maxsplit=1)[0] == "a" else drink
        except IndexError:
            LOG.error(f"Invalid drink passed: {drink}")
            return ""
        if drink.startswith("cup of") or drink.startswith("glass of"):
            drink = drink.split(" of", 1)[1].strip()
        drink = drink.translate({ord(i): None for i in '?:!/;@#$'})\
            .rstrip().replace(" '", "'")
        # Check for common mis-matched names
        drink = self.translate_drinks.get(drink, drink)
        LOG.info(drink)
        return drink

    def _drink_in_database(self, drink: str) -> bool:
        return any(i for i in self.from_caffeine_wiz
                   if i[0] in drink or drink in i[0])

    def _get_matching_drinks(self, drink: str) -> list:
        return [i for i in self.from_caffeine_wiz
                if i[0] in drink or drink in i[0]]

    def _generate_drink_dialog(self, drink: str,
                               message: Message) -> Optional[Tuple[str, list]]:
        """
        Generates the dialog and alternate results for the requested drink
        :param drink: raw input drink to find
        :param message: message associated with request
        :return: generated dialog to speak
        """
        results = self._get_matching_drinks(drink)
        LOG.debug(results)
        if len(results) == 0:
            return None
        if len(results) == 1:
            # Return the only result
            drink = str(results[0][0])
            caff_mg = float(results[0][2])
            caff_oz = float(results[0][1])

        else:
            # Find the best match from all of the returned results
            matched_drink_names = [results[i][0]
                                   for i in range(len(results))]
            match = difflib.get_close_matches(drink, matched_drink_names, 1)
            if match:
                match2 = [i for i in results if i[0] in match]
            else:
                match2 = [i for i in results
                          if i[0] in matched_drink_names[0]]
            LOG.debug(match)
            LOG.debug(match2)
            drink = str(match2[0][0])
            caff_mg = float(match2[0][2])
            caff_oz = float(match2[0][1])
        if get_user_prefs(message)['units']['measure'] == 'metric':
            caff_mg, caff_vol, unit_dialog = self.convert_metric(caff_oz,
                                                                 caff_mg)
        else:
            caff_mg = str(caff_mg)
            caff_vol = str(caff_oz)
            unit_dialog = 'word_ounces'

        LOG.info(f"{drink} | {caff_mg} | {caff_vol} | {unit_dialog}")
        to_speak = self.dialog_renderer.render('drink_caffeine', {
            'drink': drink,
            'caffeine_content': caff_mg,
            'caffeine_units': self.translate('word_milligrams'),
            'drink_size': caff_vol,
            'drink_units': self.translate(unit_dialog)})
        return to_speak, results


def create_skill():
    return CaffeineWizSkill()
