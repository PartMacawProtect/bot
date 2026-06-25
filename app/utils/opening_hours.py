import datetime
import pytz
from aiogram.types import BusinessOpeningHours

DAY_NAMES = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]


def check_opening_hours(opening_hours: BusinessOpeningHours) -> bool:
    tz = pytz.timezone(opening_hours.time_zone_name)
    now = datetime.datetime.now(tz)

    print(f"🕐 [opening_hours] Current time: {now.strftime('%Y-%m-%d %H:%M:%S %Z')} (timezone: {opening_hours.time_zone_name})")
    print(f"📅 [opening_hours] Day of week: {DAY_NAMES[now.weekday()]} (weekday index: {now.weekday()})")

    monday_start = now - datetime.timedelta(
        days=now.weekday(),
        hours=now.hour,
        minutes=now.minute,
        seconds=now.second,
        microseconds=now.microsecond,
    )
    minutes_since_monday = (now - monday_start).total_seconds() / 60

    print(f"⏳ [opening_hours] Minutes since Monday 00:00: {minutes_since_monday:.1f}")
    print(f"📋 [opening_hours] Total intervals to check: {len(opening_hours.opening_hours)}")

    for i, day in enumerate(opening_hours.opening_hours):
        match = day.opening_minute <= minutes_since_monday <= day.closing_minute
        print(
            f"   Interval [{i}]: opening_minute={day.opening_minute}, closing_minute={day.closing_minute} "
            f"→ {'✅ MATCH (working hours)' if match else '❌ no match'}"
        )
        if match:
            print(f"🔕 [opening_hours] Result: it IS working hours → returning False (bot should stay silent)")
            return False  # Сейчас рабочее время

    print(f"🟢 [opening_hours] Result: it is NOT working hours → returning True (bot may respond)")
    return True  # Нерабочее время