# NEON AI (TM) SOFTWARE, Software Development Kit & Application Development System
#
# Copyright 2008-2020 Neongecko.com Inc. | All Rights Reserved
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
# US Patents 2008-2020: US7424516, US20140161250, US20140177813, US8638908, US8068604, US8553852, US10530923, US10530924
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
from NGI.utilities import beautifulSoupHelper as bU
from mycroft.skills.core import MycroftSkill
from time import sleep
# from mycroft.util import create_signal, check_for_signal
from mycroft.util.log import LOG
from mycroft.util.parse import normalize

TIME_TO_CHECK = 3600


class CaffeineWizSkill(MycroftSkill):
    def __init__(self):
        super(CaffeineWizSkill, self).__init__(name="CaffeineWizSkill")
        # self.digits = self.user_info_available['units']['measure'] \
        #     if self.user_info_available['units']['measure'] else 'imperial'
        self.results = None
        # default_config = {"lastUpdate": None}
        # self.init_settings(default_config)
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

        # Fallback if configuration is unavailable

        # New parameter that needs to be added to yaml:
        # 2019-04-04 14:55:06.686601
        try:
            # self.last_updated = datetime.datetime.strptime(self.configuration_available["devVars"]["caffeineUpdate"],
            #                                                '%Y-%m-%d %H:%M:%S.%f')
            if self.settings.get("lastUpdate"):
                self.last_updated = datetime.datetime.strptime(self.settings["lastUpdate"],
                                                               '%Y-%m-%d %H:%M:%S.%f')
            else:
                self.last_updated = None
        except Exception as e:
            LOG.info(e)
            self.last_updated = None
            # self.last_updated = self.configuration_available["devVars"]["caffeineUpdate"]
        LOG.debug(self.last_updated)
        # using tdelta variable and datetime module to calculate the difference between the current moment and the
        # last time the update was performed
        self.from_caffeine_wiz = None
        self.from_caffeine_informer = None

        # LOG.debug(f"DM: {self.from_caffeine_informer}")
        # LOG.debug(f"DM: {self.from_caffeine_wiz}")

    def combine_and_chocolate(self):
        self.from_caffeine_wiz.append(['rocket chocolate', '.4', '150'])
        self.from_caffeine_wiz.extend(x[:-2] for x in
                                      self.from_caffeine_informer
                                      if str(x[:-2]) not in str(self.from_caffeine_wiz))
        sorted(self.from_caffeine_wiz)
        # LOG.info(self.from_caffeine_wiz)

    def get_new_info(self, reply=False):
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
            new = bU.strip_tags(new_url)
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
                    (bU.chunks([i.text.lower().replace("\n", "")
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
            with open(join(abspath(dirname(__file__)), 'drinkList_from_caffeine_wiz.txt'),
                      'wb+') as from_caffeine_wiz_file:
                pickle.dump(self.from_caffeine_wiz, from_caffeine_wiz_file)

            with open(join(abspath(dirname(__file__)), 'drinkList_from_caffeine_informer.txt'),
                      'wb+') as from_caffeine_informer_file:
                pickle.dump(self.from_caffeine_informer, from_caffeine_informer_file)
            self.combine_and_chocolate()
            # self.configuration_available["devVars"]["caffeineUpdate"] = time_check
            # self.create_signal("NGI_YAML_config_update")
            # time_check = str(time_check)
        except Exception as e:
            LOG.error(e)

        try:
            LOG.debug(type(self.ngi_settings))
            self.ngi_settings.update_yaml_file("lastUpdate", value=str(time_check))
            # self.local_config.update_yaml_file("devVars", "caffeineUpdate", time_check)
            self.check_for_signal("WIZ_getting_new_content")
            if reply:
                self.speak("Update completed.")
        except Exception as e:
            LOG.error("An error occurred during the CaffeineWiz update: " + str(e))

    def initialize(self):
        caffeine_intent = IntentBuilder("CaffeineContentIntent"). \
            require("CaffeineKeyword").require("drink").build()
        self.register_intent(caffeine_intent, self.handle_caffeine_intent)

        # yes_i_do_intent = IntentBuilder("CaffeineYesIDoIntent"). \
        #     require("YesIDo").build()
        # self.register_intent(yes_i_do_intent, self.handle_yes_i_do_intent)
        #
        # no_intent = IntentBuilder("Caffeine_no_intent"). \
        #     require("NoIntent").build()
        # self.register_intent(no_intent, self.handle_no_intent)

        goodbye_intent = IntentBuilder("CaffeineContentGoodbyeIntent"). \
            require("GoodbyeKeyword").build()
        self.register_intent(goodbye_intent, self.handle_goodbye_intent)

        update_caffeine = IntentBuilder("Caffeine_update").require("UpdateCaffeine").build()
        self.register_intent(update_caffeine, self.handle_caffeine_update)

        self.disable_intent('CaffeineContentGoodbyeIntent')
        # self.disable_intent('CaffeineYesIDoIntent')
        # self.disable_intent('Caffeine_no_intent')

        tdelta = datetime.datetime.now() - self.last_updated if self.last_updated else datetime.timedelta(hours=1.1)
        LOG.info(tdelta)
        # if more than one hour, calculate and fetch new data again:
        if tdelta.total_seconds() > TIME_TO_CHECK \
                or not pathlib.Path(join(abspath(dirname(__file__)), 'drinkList_from_caffeine_informer.txt')).exists() \
                or not pathlib.Path(join(abspath(dirname(__file__)), 'drinkList_from_caffeine_wiz.txt')).exists():
            self.create_signal("WIZ_getting_new_content")
            # starting a separate process because websites might take a while to respond
            t = multiprocessing.Process(target=self.get_new_info())
            t.start()
        else:
            # if less than 1 hour, unpickle saved results from the appropriate files:
            with open(join(abspath(dirname(__file__)), 'drinkList_from_caffeine_wiz.txt'),
                      'rb') as from_caffeine_wiz_file:
                self.from_caffeine_wiz = pickle.load(from_caffeine_wiz_file)

            with open(join(abspath(dirname(__file__)), 'drinkList_from_caffeine_informer.txt'),
                      'rb') as from_caffeine_informer_file:
                self.from_caffeine_informer = pickle.load(from_caffeine_informer_file)
                # combine them as in get_new_info and add rocket chocolate:
                self.combine_and_chocolate()

    def handle_caffeine_update(self, message):
        LOG.debug(message)
        self.speak("Sure. Updating CaffeineWiz")
        t = multiprocessing.Process(target=self.get_new_info(reply=True))
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

    def handle_caffeine_intent(self, message):
        # flac_filename = message.data.get("flac_filename")
        drink = str(message.data.get("drink")).lower().lstrip("a ") if message.data.get("drink") \
            else None
        if not drink:
            self.speak("I could not understand the drink that you requested")
        elif self.check_for_signal('CORE_useHesitation', -1):
            self.speak_dialog('one_moment', private=True)
            # self.speak("Sure.")
        LOG.info(f"heard: {drink}")
        drink = drink.translate({ord(i): None for i in '?:!/;@#$'}).rstrip().replace(" '", "'")
        # LOG.info(drink)
        if drink in self.translate_drinks.keys():
            drink = self.translate_drinks[drink]
        # drink = "coke zero" if drink == "coke 0" else drink
        # drink = "coca-cola classic" if drink == "coca-cola" or drink == "coke" else drink
        LOG.info(drink)
        # Catch "cup of x" requests
        if drink.startswith("cup of") or drink.startswith("glass of"):
            drink = drink.split(" of ", 1)[1]
        if any(i for i in self.from_caffeine_wiz if i[0] in drink or drink in i[0]):
            self.results = [i for i in self.from_caffeine_wiz if i[0] in drink or drink in i[0]]
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
                ranging = [self.results[i][0] for i in range(len(self.results))]
                match = difflib.get_close_matches(drink, ranging, 1)
                if match:
                    match2 = [i for i in self.results if i[0] in match]
                else:
                    match2 = [i for i in self.results if i[0] in ranging[0]]
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

            self.speak_dialog('DrinkCaffeine', {'drink': drink,
                                                'caffeine_content': caff_mg,
                                                'caffeine_units': 'milligrams',
                                                'drink_size': caff_vol,
                                                'drink_units': drink_units})

            if len(self.results) == 1:
                self.speak("Say how about caffeine content of another drink or say goodbye.", True) if \
                    not self.check_for_signal("CORE_skipWakeWord", -1) else self.speak("Stay caffeinated!")
                self.enable_intent('CaffeineContentGoodbyeIntent')
                self.request_check_timeout(self.default_intent_timeout, 'CaffeineContentGoodbyeIntent')
            else:
                self.speak("I have more drinks that match. Would you like to hear them?", True)
                self.await_confirmation(self.get_utterance_user(message), "more")
                # self.enable_intent('CaffeineYesIDoIntent')
                # self.enable_intent('Caffeine_no_intent')
                # self.request_check_timeout(self.default_intent_timeout, "CaffeineYesIDoIntent")
                # self.request_check_timeout(self.default_intent_timeout, "Caffeine_no_intent")

        else:
            self.speak_dialog("NotFound", {'drink': drink})
            # self.speak("I am sorry, " + drink + " is not on my list. Let my creators know and "
            #            "they will teach me new information!")

    def convert_metric(self, caff_oz, caff_mg):
        """
        Convert from imperial to metric units
        :param caff_oz: (float) oz from lookup
        :param caff_mg: (int) mg from lookup
        :return: mg, vol, units
        """

        if caff_oz <= 8.45351:
            caff_mg = str(self._drink_conversion(250, caff_mg, caff_oz))
            caff_vol = '250'
            drink_units = 'milliliters'
        elif caff_oz <= 16.907:
            caff_mg = str(self._drink_conversion(500, caff_mg, caff_oz))
            caff_vol = '500'
            drink_units = 'milliliters'
        else:
            caff_mg = str(self._drink_conversion(1000, caff_mg, caff_oz))
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
        self.speak('Goodbye. Stay caffeinated!', False)

    @staticmethod
    def _drink_conversion(total, caffeine_oz, oz):
        return int((caffeine_oz / (oz * 29.5735)) * total)

    def _get_drink_text(self, message, caff_list=None):
        cnt = 0
        # msg = pre_msg = ''
        spoken = []
        if not caff_list:
            caff_list = self.results
            LOG.info(caff_list)
        for i in range(len(caff_list)):
            if caff_list[i][0] not in spoken:
                oz = float(caff_list[i][1])
                caffeine = float(caff_list[i][2])

                # msg += 'The drink ' + \
                #        caff_list[i][0] + ' has '
                drink = caff_list[i][0]
                units = self.preference_unit(message)['measure']

                if units == "metric":
                    caff_mg, caff_vol, drink_units = self.convert_metric(oz, caffeine)
                else:
                    # msg += str(caffeine) + ' milligrams caffeine in ' \
                    #        + str(oz) + ' ounces. '
                    caff_mg = str(caffeine)
                    caff_vol = str(oz)
                    drink_units = 'ounces'
                # else:
                #     caff_mg, caff_vol, drink_units = self.convert_metric(oz, caffeine)
                    # if oz <= 8.45351:
                    #     msg += str(self._drink_conversion(250, caffeine, oz)) + \
                    #            ' milligrams caffeine in 250 milliliters. '
                    # elif oz <= 16.907:
                    #     msg += str(self._drink_conversion(500, caffeine, oz)) + \
                    #            ' milligrams caffeine per 500 milliliters. '
                    # else:
                    #     msg += str(self._drink_conversion(1000, caffeine, oz)) + \
                    #            ' milligrams caffeine per liter. '

                self.speak_dialog('MultipleCaffeine', {'drink': drink,
                                                       'caffeine_content': caff_mg,
                                                       'caffeine_units': 'milligrams',
                                                       'drink_size': caff_vol,
                                                       'drink_units': drink_units})
                spoken.append(caff_list[i][0])
                sleep(0.5)  # Prevent simultaneous speak inserts
            cnt = cnt + 1

        # if cnt > 1:
        #     pre_msg = 'I found ' + str(cnt) + ' drinks that match. Here they are: '

        # return pre_msg + msg

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
                self.speak("Say how about caffeine content of another drink or say goodbye.", True) if \
                    not self.check_for_signal("CORE_skipWakeWord", -1) else self.speak("Stay caffeinated!")
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


def create_skill():
    return CaffeineWizSkill()
