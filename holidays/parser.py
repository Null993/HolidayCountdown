# holidays/parser.py
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from itertools import count

from ics import Calendar
from typing import List
import pytz

@dataclass
class Holiday:
    uid: str
    name: str
    begin: datetime   # start datetime
    end: datetime     # end datetime (exclusive)
    all_day: bool
    raw_description: str
    duration: int
    actual_days: int
    flag_None: bool


    def __init__(self, flag_None=False, uid=None, name=None, begin=None, end=None, all_day=None, raw_description=None, duration=None, actual_days=None,):

        self.uid = uid
        self.name = name
        self.begin = begin
        self.end = end
        self.all_day = all_day
        self.raw_description = raw_description
        self.duration = duration
        self.actual_days = actual_days
        self.flag_None = flag_None


def ensure_timezone(dt, tz_str="Asia/Shanghai"):
    """确保 datetime 带上时区信息"""
    if not dt:
        return None
    tz = pytz.timezone(tz_str)
    if dt.tzinfo is None:
        return tz.localize(dt)
    else:
        return dt.astimezone(tz)

def parse_ics(ics_text: str, tz_str: str = "Asia/Shanghai") -> List[Holiday]:
    """
    使用 ics 库解析 ICS 文本，返回 Holiday 列表
    """
    cal = Calendar(ics_text)
    events = []


    for ev in cal.events:
        if ev.end.datetime.year + 1 < datetime.now().year:
            continue
        begin = ensure_timezone(ev.begin.datetime, tz_str)
        end = ensure_timezone(ev.end.datetime if ev.end else ev.begin.datetime, tz_str)
        all_day = getattr(ev, "all_day", False)

        # --- 判断是否全天事件 ---
        is_all_day = getattr(ev, "all_day", False) or "VALUE=DATE" in str(ev)
        if is_all_day:
            # 全天事件：设为当天 00:00 → 当天 23:59:59

            begin = datetime.combine(begin.date(), time(0, 0, 0, tzinfo=pytz.timezone(tz_str)))
            end = datetime.combine(end.date() - timedelta(days=1), time(23, 59, 59, tzinfo=pytz.timezone(tz_str)))

        events.append(Holiday(
            uid=str(ev.uid),
            name=str(ev.name) if ev.name else "",
            begin=begin,
            end=end,
            all_day=all_day,
            raw_description=str(ev.description) if ev.description else "",
            duration= (ev.end - ev.begin).days+1,
            actual_days=0,
        ))

    # 按开始时间排序
    events.sort(key=lambda e: e.begin)
    return events
