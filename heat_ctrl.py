'''
# heat_ctrl: Heat Controller

Controls heaters around the house based on inputs such as room temperature and
amount of solar electricity being generated.
'''

import json
import time
import traceback

import astral
import requests


MAX_DAY_TEMP = 24
MAX_NIGHT_TEMP = 22
MIN_NIGHT_TEMP = 19

HEATER_KILOWATTS = 1.2

SCHEMES = {
    'weekday': [
        {'rate': 'offpeak', 'start': 0, 'end': 7,},
        {'rate': 'shoulder', 'start': 7, 'end': 15,},
        {'rate': 'peak', 'start': 15, 'end': 23,},
        {'rate': 'offpeak', 'start': 23, 'end': 24,},
    ],
    'weekend': [
        {'rate': 'offpeak', 'start': 0, 'end': 24,},
    ],
}

SCHEME_MAP = {  # time.struct_time tm_wday, Monday = 0
    0: 'weekday',
    1: 'weekday',
    2: 'weekday',
    3: 'weekday',
    4: 'weekday',
    5: 'weekend',
    6: 'weekend',
}

LOCATION = astral.Location(info=(
    'Blackburn',
    'Victoria',
    -37.82,
    145.15,
    'Australia/Melbourne',
    50,
))


class HeatCtrl(object):  # pylint: disable=too-few-public-methods
    '''Main class for heat_ctrl module.'''

    def __init__(self):
        '''Constructor for HeatCtrl objects.'''
        self.demand = float(0)
        self.heater_on = True

    def main(self):  # pylint: disable=too-many-branches,too-many-statements
        '''Main method for the HeatCtrl class.'''

        req = requests.get('http://dashing:3030/events', stream=True, timeout=120)

        for line in req.iter_lines(chunk_size=32):
            # filter out keep-alive new lines
            if line:
                night = False
                curr_time = time.localtime()
                e_time = time.mktime(curr_time)  # epoch time
                day = curr_time.tm_wday
                hour = curr_time.tm_hour
                sunrise = LOCATION.sunrise()
                sunset = LOCATION.sunset()
                e_sr = time.mktime(sunrise.timetuple())  # epoch sunrise
                e_ss = time.mktime(sunrise.timetuple())  # epoch sunset

                if e_time < e_sr or e_time > e_ss:
                    # if pre-sunrise or post-sunset, then it is nighttime
                    night = True

                try:
                    data = json.loads(line[line.index("{"):])
                except:  # pylint: disable=bare-except
                    print "Failed to JSON decode this string:"
                    print "'%s'" % line
                    continue

                if 'id' not in data:
                    print "Failed to find 'id' element in data"
                    continue

                if data['id'] == "griddemand":
                    self.demand = float(data['value'])
                    if data['title'] == "Selling":
                        self.demand = self.demand * -1
                    continue

                if data['id'] != "masterbed":
                    # print "!! : %s" % data
                    continue

                room_temp = int(data['temperature'][:-1])
                scheme = SCHEME_MAP[day]
                for r in SCHEMES[scheme]:  # pylint: disable=invalid-name
                    if hour >= r['start'] and hour < r['end']:
                        rate = r['rate']

                print "--"
                print "Current demand: %s" % self.demand
                print "Current temperature: %s" % room_temp
                print "Current date: %s-%s-%s; time: %s:%s; weekday: %s" % (
                    curr_time.tm_year, curr_time.tm_mon, curr_time.tm_mday,
                    hour, curr_time.tm_min,
                    day,
                )
                print "Current rate scheme: %s" % rate
                print "Sunrise is %s; Sunset is %s" % (sunrise, sunset)
                print "Currently nighttime? %s" % night
                print "Currently heater is on? %s" % self.heater_on

                if night:
                    if rate != "offpeak":
                        print "Result: TOGGLE OFF; Reason: %s electricity @ night" % rate
                        self.heater_on = False
                        continue
                    if room_temp >= MAX_NIGHT_TEMP:
                        print "Result: TOGGLE OFF; Reason: room is %s (or hotter) @ night" % MAX_NIGHT_TEMP
                        self.heater_on = False
                        continue
                    if room_temp < MIN_NIGHT_TEMP:
                        print "Result: TOGGLE ON; Reason: room is below %s @ night" % MIN_NIGHT_TEMP
                        self.heater_on = True
                        continue
                    print "Result: NO ACTION; Reason: room is >= %s and < %s @ night" % (
                        MIN_NIGHT_TEMP,
                        MAX_NIGHT_TEMP,
                    )
                    continue

                # must be day...
                if room_temp >= MAX_DAY_TEMP:
                    print "Result: TOGGLE OFF; Reason: room is %s (or hotter) @ day" % MAX_DAY_TEMP
                    self.heater_on = False
                    continue
                if not self.heater_on and self.demand <= (HEATER_KILOWATTS * -1):
                    print "Result: TOGGLE ON; Reason: heater is off and exporting %skW @ day" % self.demand * -1
                    self.heater_on = True
                    continue
                if self.demand > 0:
                    print "Result: TOGGLE OFF; Reason: buying %skW @ day" % self.demand
                    self.heater_on = False
                    continue
                print "Result: NO ACTION; Reason: exporting %skW @ day" % self.demand * -1


if __name__ == '__main__':
    HC = HeatCtrl()
    while True:
        try:
            HC.main()
        except Exception, err:  # pylint: disable=broad-except
            print "\nException from main()\n"
            print traceback.format_exc()

        time.sleep(180)
