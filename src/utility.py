import math
import sys

def dynamic_console_text(message):
    sys.stdout.write(f"{message}",)
    sys.stdout.flush()

def avg(numList):
    return sum(numList) / len(numList)

def round_to_n(num, sigfig):
    if not num: return 0
    power = -int(math.floor(math.log10(abs(num)))) + (sigfig - 1)
    factor = (10 ** power)
    return round(num * factor) / factor

def convert_seconds_to_dayshoursminutes(seconds):
    seconds_to_minute   = 60
    seconds_to_hour     = 60 * seconds_to_minute
    seconds_to_day      = 24 * seconds_to_hour

    days    =   seconds // seconds_to_day
    seconds    %=  seconds_to_day

    hours   =   seconds // seconds_to_hour
    seconds    %=  seconds_to_hour

    minutes =   seconds // seconds_to_minute
    seconds    %=  seconds_to_minute

    return ("%d days, %d hours, %d minutes, %d seconds" % (days, hours, minutes, seconds))
