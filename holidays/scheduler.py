# holidays/scheduler.py
from datetime import datetime, timedelta, date
from typing import List, Tuple
from .parser import Holiday
import re
import pytz

def time_until(dt: datetime, now: datetime = None, tz_str="Asia/Shanghai") -> timedelta:
    tz = pytz.timezone(tz_str)

    # 若目标时间没有时区，则补全
    if dt.tzinfo is None:
        dt = tz.localize(dt)

    # 当前时间
    if now is None:
        now = datetime.now(tz)
    elif now.tzinfo is None:
        now = tz.localize(now)

    return dt - now

def is_makeup_event(holiday: Holiday) -> bool:
    """
    判断事件是否为“调休/补班/上班”事件的 heuristic。
    ICS 的描述/标题里常含“调休/补班/上班/补班”字样。
    """
    keywords = ["调休", "补班", "补上班", "上班调休", "上班日"]
    txt = (holiday.name + " " + holiday.raw_description).lower()
    for kw in keywords:
        if kw in txt:
            return True
    return False

def is_holiday_event(holiday: Holiday) -> bool:
    """
    判断事件是否是节假日（放假）事件。
    标题/描述包含“放假/节日/假期”等关键字。
    """
    keywords = ["放假", "假期", "节日", "休息", "holiday", "festival"]
    txt = (holiday.name + " " + holiday.raw_description).lower()
    for kw in keywords:
        if kw in txt:
            return True
    # 如果既不是明显调休也不是明显放假，则依赖时间长度（全天/多天）判断
    # e.g. 连续多天的事件通常是放假
    duration_days = (holiday.end.date() - holiday.begin.date()).days + 1
    if duration_days >= 1:
        return True
    return False

def compute_smart_holiday_days(holidays: List[Holiday]) -> Tuple[int, int, int]:
    """
    计算 (total_holiday_days, actual_holiday_days)：
    - total_holiday_days: 从所有被识别为假期的事件累计的天数（按日期计数）
    - actual_holiday_days: total - 调休/补班天数（调休会在 ICS 中作为上班日或单独事件，heuristic 检测）
    NOTE: 该实现采用保守/启发式方法：把识别为 'is_makeup_event' 的事件计为调休/补班。
    """

    total_days = 0
    # actual_days = 0
    days_excl_makeup = 0
    days_excl_makeup_weekend = 0
    for h in holidays:
        total_days += (h.end - h.begin).days + 1
        days_excl_makeup += h.days_excl_makeup
        days_excl_makeup_weekend += h.days_excl_makeup_weekend

    return total_days, days_excl_makeup, days_excl_makeup_weekend
