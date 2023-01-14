#################
#
# Controls family state (Working, vacation, etc.)
#
# TODO: Read vacation plans from calendar


import hassapi as hass
from datetime import datetime
from globals import *
from scheduler import Scheduler

class FamilyStateController(hass.Hass):
    """
    Utility to control scheduling, providing family state (WORKING, NONWORKING & VACATION)
    Also controls an input_number if it's day or night, usable in graphs to provide x-scale 12h shading

    Configuration expected in apps.yaml:
    family_state_controller:
      module: family_state
      class: FamilyStateController
      input_select: input_select.myfamily_mode_indicator
      night_select: input_number.mynight_time_indicator
    """
#TODO: Late evening + nigh should depend on state of next day, not current


    def initialize(self):
        self.set_log_level("DEBUG")
        self.log("Family state controller")
        handle = self.run_in(self.unpause_all_automations, 1)
        #handle = self.run_in(self.check_weekday, 1)
        handle = self.run_in(self.set_input_datetimes, 5)
        handle = self.run_daily(self.unpause_all_automations, "08:30:00") # Go back to full automation
        handle = self.run_daily(self.unpause_all_automations, "22:30:00") # Go back to full automation
        handle = self.run_daily(self.set_input_datetimes, "02:00:00")
        #handle = self.run_daily(self.check_weekday, "03:06:00")
        handle = self.run_daily(self.set_daytime, "08:00:00")
        handle = self.run_daily(self.set_nighttime, "20:00:00")

        try:
            self.input_select = self.args["input_select"]
        except KeyError:
            self.log("Missing input_select configuration. Cannot continue")
        try:
            self.night_select = self.args["night_select"]
        except KeyError:
            self.night_select = None
            self.log("Missing night_select configuration. Gracefully degrading")

        self.listen_state(self.state_changed, 'input_select.family_mode')


    def state_changed(self, entity, attribute, old, new, kwargs):
        self.log("State change - detected")
        self.set_input_datetimes("XYZ")  # TODO: Check why kwargs is needed


# Not used, sensor.weekday + input_select.family_state is used instead
    def check_weekday(self, kwargs):
        self.log("Setting family state based on weekday")
        family_state = self.get_state(self.input_select)
        self.log(f"Current state: {family_state}", level="DEBUG")
        if family_state != VACATION:
            sch = Scheduler()
            if sch.check_nonworkingday():
                self.log("It's week-end or holiday!")
                self.select_option(self.input_select, NON_WORKING)
            else:
                self.log("It's work day")
                self.select_option(self.input_select, WORKING)

            # day = datetime.today().weekday()  # TODO: self.datetime
            # if day >= 5:
            #     self.log("It's week-end!")
            #     self.select_option(self.input_select, NON_WORKING)
            # else:
            #     self.log("It's work day")
            #     self.select_option(self.input_select, WORKING)
        family_state = self.get_state(self.input_select)
        self.log(f"New state: {family_state}", level="DEBUG")

    def set_daytime(self, kwargs):
        self.log("Set daytime")
        if self.night_select is not None:
            self.set_value(self.night_select, 0.0)

    def set_nighttime(self, kwargs):
        self.log("Set nighttime")
        if self.night_select is not None:
            self.set_value(self.night_select, 1.0)

    def get_timing(self, type):
        """
        type: working, non-working
        :return: dict with timings based on month of the year
        """
        # TODO: Create time object - add relative time (minutes) to base time

        timings = []
        try:
            now = self.get_now()
            month = str(now.month)
            if len(str(month)) < 2:
                month = "0" + month
            self.log(f"Reading timings for month (str) {month}")
            for l in self.args["schedule"]["timings"][type.lower()][month]:
                timings.append(l)
        except KeyError:
            try:
                now = self.get_now()
                month = now.month
                self.log(f"Reading timings for month (int) {month}")
                for l in self.args["schedule"]["timings"][type.lower()][month]:
                    timings.append(l)
            except KeyError:
                self.log(f"No {type} timings key for {month}. Disabling scheduling.")
                return None

        #self.log(f"Timings {timings}")
        schedule = dict(
            morning_on_1 = timings[0],
            morning_on_2 = timings[1],
            morning_on_3 = timings[2],
            morning_off_1 = timings[3],
            morning_off_2 = timings[4],
            morning_off_3 = timings[5],
            afternoon_on_1 = timings[6],
            afternoon_on_2 = timings[7],
            afternoon_on_3 = timings[8],
            evening_off_1 = timings[9],
            evening_off_2 = timings[10],
            evening_off_3 = timings[11],
            night_off = timings[12])
        self.log(f"Schedule {schedule}")

        return schedule

    def set_input_datetimes(self, param1):
        #self.log(f"param1 {param1}")
        family_mode = self.get_state("input_select.family_mode")
        self.log(f"Family mode {family_mode.lower()}")

        sch = self.get_timing(family_mode.lower())
        input_number_base = "input_datetime.schedule_"

        #self.log(f"Setting {input_number_base+'morning_on_1'} to {sch['morning_on_1']}:00")
        self.set_input_datetime(input_number_base+"morning_on_1", sch["morning_on_1"]+':00')
        self.set_input_datetime(input_number_base+"morning_on_2", sch["morning_on_2"]+':00')
        self.set_input_datetime(input_number_base+"morning_on_3", sch["morning_on_3"]+':00')
        self.set_input_datetime(input_number_base+"morning_off_1", sch["morning_off_1"]+':00')
        self.set_input_datetime(input_number_base+"morning_off_2", sch["morning_off_2"]+':00')
        self.set_input_datetime(input_number_base+"morning_off_3", sch["morning_off_3"]+':00')
        self.set_input_datetime(input_number_base+"afternoon_on_1", sch["afternoon_on_1"]+':00')
        self.set_input_datetime(input_number_base+"afternoon_on_2", sch["afternoon_on_2"]+':00')
        self.set_input_datetime(input_number_base+"afternoon_on_3", sch["afternoon_on_3"]+':00')
        self.set_input_datetime(input_number_base+"evening_off_1", sch["evening_off_1"]+':00')
        self.set_input_datetime(input_number_base+"evening_off_2", sch["evening_off_2"]+':00')
        self.set_input_datetime(input_number_base+"evening_off_3", sch["evening_off_3"]+':00')
        self.set_input_datetime(input_number_base+"night_off", sch["night_off"]+':00')

        input_boolean_base = "input_boolean.schedule_"
        self.set_input_boolean(input_boolean_base+"morning_on_1", sch["morning_on_1"] != '--:--')
        self.set_input_boolean(input_boolean_base+"morning_on_2", sch["morning_on_2"] != '--:--')
        self.set_input_boolean(input_boolean_base+"morning_on_3", sch["morning_on_3"] != '--:--')
        self.set_input_boolean(input_boolean_base+"morning_off_1", sch["morning_off_1"] != '--:--')
        self.set_input_boolean(input_boolean_base+"morning_off_2", sch["morning_off_2"] != '--:--')
        self.set_input_boolean(input_boolean_base+"morning_off_3", sch["morning_off_3"] != '--:--')
        self.set_input_boolean(input_boolean_base+"afternoon_on_1", sch["afternoon_on_1"] != '--:--')
        self.set_input_boolean(input_boolean_base+"afternoon_on_2", sch["afternoon_on_2"] != '--:--')
        self.set_input_boolean(input_boolean_base+"afternoon_on_3", sch["afternoon_on_3"] != '--:--')
        self.set_input_boolean(input_boolean_base+"evening_off_1", sch["evening_off_1"] != '--:--')
        self.set_input_boolean(input_boolean_base+"evening_off_2", sch["evening_off_2"] != '--:--')
        self.set_input_boolean(input_boolean_base+"evening_off_3", sch["evening_off_3"] != '--:--')
        self.set_input_boolean(input_boolean_base+"night_off", sch["night_off"] != '--:--')

    def set_input_boolean(self, input_helper, value):
        self.log(f"Setting boolean {input_helper} to {value}", level="DEBUG")
        if value:
            self.call_service('input_boolean/turn_on', entity_id=input_helper)
        else:
            self.call_service('input_boolean/turn_off', entity_id=input_helper)

    def set_input_select(self, input_helper, value):
        self.log(f"Setting input_select {input_helper} to {value}", level="DEBUG")
        if value:
            self.call_service('input_select/select_option', entity_id=input_helper, option=value)

#    action:
#       service: input_select.select_option
#    data:
#        entity_id: input_select.alarmselect
#       option: off


    def set_input_datetime(self, input_helper, value):
        self.log(f"Setting datetime {input_helper} to {value}", level="DEBUG")
        if value != '--:--:00':
            self.call_service('input_datetime/set_datetime', entity_id=input_helper, time=value)
        else:
            self.log(f"Skipping this entry")
            # TODO: Set to 00:00 ??
#service: input_datetime.set_datetime
#data:
#  time: "10:05:00"
#target:
#  entity_id: input_datetime.schedule_morning_off_1

    def unpause_all_automations(self, param1):
        self.log(f"unpause_automations started") #, level="DEBUG")

        for x in self.args["light_sources"]:
            self.log(f"reading params - {x}", level="DEBUG")
            self.unpause_automation(x)

    def unpause_automation(self, automation):
        auto = "automation.lights_on_" + automation
        self.log(f"unpause_automation {auto}") #, level="DEBUG")
        self.call_service('automation/turn_on', entity_id=auto)
        auto = "automation.lights_off_" + automation
        self.call_service('automation/turn_on', entity_id=auto)
        auto = "input_select.automation_mode_" + automation
        self.set_input_select( auto, "Auto")

        #motion?=


#    - event: unpause_auto_on
#      event_data_template:
#        light_source: testlampa
