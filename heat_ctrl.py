'''
# heat_ctrl: Heat Controller

Controls heaters around the house based on inputs such as room temperature and
amount of solar electricity being generated.
'''

import json
import time
import traceback

import astral
import ouimeaux.environment
import requests


ROOMS = {
    'masterbed': {
        'heater_kw': 1.4,
        'state': None,
        'state_overriden': None,
        'switch_object': None,
        'max_day_temp': 24,     # switch off when t >= 24
        'min_day_temp': 17,     # switch  on when t <  17
        'max_night_temp': 20,   # switch off when t >= 20
        'min_night_temp': 19,   # switch  on when t <  19
    },
    'girlsbed': {
        'heater_kw': 1.0,
        'state': None,
        'state_overriden': None,
        'switch_object': None,
        'max_day_temp': 24,     # switch off when t >= 24
        'min_day_temp': 15,     # switch  on when t <  15
        'max_night_temp': 19,   # switch off when t >= 18
        'min_night_temp': 18,   # switch  on when t <  17
    },
}

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

        env = ouimeaux.environment.Environment()
        env.start()
        for room in ROOMS:
            ROOMS[room]['switch_object'] = env.get_switch(room)

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
                e_ss = time.mktime(sunset.timetuple())  # epoch sunset

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

                if data['id'] not in ROOMS:
                    # print "!! : %s" % data
                    continue

                room = data['id']
                rdict = ROOMS[room]

                room_temp = int(data['temperature'][:-1])
                scheme = SCHEME_MAP[day]
                for r in SCHEMES[scheme]:  # pylint: disable=invalid-name
                    if hour >= r['start'] and hour < r['end']:
                        rate = r['rate']

                print "--"
                print "Current demand: %s" % self.demand
                print "Current temperature in %s: %s" % (room, room_temp)
                print "Current date: %s-%02d-%02d; time: %02d:%02d; weekday: %s" % (
                    curr_time.tm_year, curr_time.tm_mon, curr_time.tm_mday,
                    hour, curr_time.tm_min,
                    day,
                )

                if rdict['state_overriden'] is not None:
                    if rdict['state_overriden'] + (4 * 3600) > time.time():
                        print "Switch state overriden, skipping..."
                        continue

                if rdict['state'] is None:
                    rdict['state'] = rdict['switch_object'].get_state(force_update=True)
                elif rdict['state'] != rdict['switch_object'].get_state(force_update=True):
                    print "Switch overriden, taking no further action on switch for 4 hours"
                    rdict['state'] = None
                    rdict['state_overriden'] = time.time()
                    continue

                print "Current rate scheme: %s" % rate
                print "Sunrise is %s; Sunset is %s" % (sunrise, sunset)
                print "Currently nighttime? %s" % night
                print "Currently '%s' heater state is: %s" % (room, rdict['state'],)

                if night:
                    if room_temp < rdict['min_night_temp']:
                        print "Result: ENSURE ON; Reason: room is below %s @ night" % rdict['min_night_temp']
                        rdict['switch_object'].on()
                        rdict['state'] = rdict['switch_object'].get_state()
                        continue
                    if room_temp >= rdict['max_night_temp']:
                        print "Result: ENSURE OFF; Reason: room is %s (or hotter) @ night" % rdict['max_night_temp']
                        rdict['switch_object'].off()
                        rdict['state'] = rdict['switch_object'].get_state()
                        continue
                    print "Result: NO ACTION; Reason: room is >= %s and < %s @ night" % (
                        rdict['min_night_temp'],
                        rdict['max_night_temp'],
                    )
                    continue

                # must be day...
                if room_temp < rdict['min_day_temp']:
                    print "Result: ENSURE ON; Reason: room is below %s @ day" % rdict['min_day_temp']
                    rdict['switch_object'].on()
                    rdict['state'] = rdict['switch_object'].get_state()
                    continue
                if room_temp >= rdict['max_day_temp']:
                    print "Result: ENSURE OFF; Reason: room is %s (or hotter) @ day" % rdict['max_day_temp']
                    rdict['switch_object'].off()
                    rdict['state'] = rdict['switch_object'].get_state()
                    continue
                if rdict['state'] != 1 and self.demand <= (rdict['heater_kw'] * -1):
                    print "Result: ENSURE ON; Reason: heater is off and exporting %skW @ day" % (self.demand * -1)
                    rdict['switch_object'].on()
                    rdict['state'] = rdict['switch_object'].get_state()
                    continue
                if self.demand > 0:
                    print "Result: ENSURE OFF; Reason: buying %skW @ day" % self.demand
                    rdict['switch_object'].off()
                    rdict['state'] = rdict['switch_object'].get_state()
                    continue
                print "Result: NO ACTION; Reason: exporting %skW @ day" % (self.demand * -1)


if __name__ == '__main__':
    HC = HeatCtrl()
    while True:
        try:
            HC.main()
        except Exception, err:  # pylint: disable=broad-except
            print "\nException from main()\n"
            print traceback.format_exc()

        time.sleep(60)
