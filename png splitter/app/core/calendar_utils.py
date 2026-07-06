import calendar
from datetime import date


def working_days(year, month, saturday=False, sunday=False, holidays=None):
    holidays = set(holidays or [])
    total = 0
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        current = date(year, month, day)
        if current in holidays:
            continue
        weekday = current.weekday()
        if weekday < 5 or (weekday == 5 and saturday) or (weekday == 6 and sunday):
            total += 1
    return total
