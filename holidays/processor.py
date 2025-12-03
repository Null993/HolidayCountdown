# processor.py
import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pytz

from .parser import Holiday

# 补班/调休关键字
_MAKEUP_KEYWORDS = {"补班", "调休", "上班", "补上班", "调班", "workday", "makeup"}


# ===========================
#  名称处理
# ===========================
def normalize_name(raw_name: Optional[str]) -> str:
    """
    将事件名规范化，例如：
      '劳动节 第1天/共3天' => '劳动节'
      '劳动节 补班 第1天/共1天' => '劳动节 补班'
      '元旦 假期 第1天' => '元旦'
    清除“假期/假日/放假”，但保留补班/调休关键词。
    """
    if not raw_name:
        return ""

    s = raw_name.strip()

    # 截断 Day、"第x天" 之类
    m = re.search(r"\s第", s)
    if m:
        s = s[:m.start()].strip()

    # 多空白合并
    s = re.sub(r"\s+", " ", s)

    # 删除“假期/假日/放假”等描述词
    s = re.sub(r"\b(假期|假日|放假)\b", "", s)

    return s.strip()


def is_makeup_event(raw_name: Optional[str]) -> bool:
    """判断是否为补班/调休事件"""
    if not raw_name:
        return False
    t = raw_name.lower()
    return any(kw in t for kw in _MAKEUP_KEYWORDS)


# ===========================
#  时区处理
# ===========================
def to_local(dt: datetime, target_tzinfo) -> datetime:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=target_tzinfo)
    return dt.astimezone(target_tzinfo)


# ===========================
#  主函数
# ===========================
def merge_and_filter_holidays(holidays: List[Holiday], tz_str="Asia/Shanghai") -> List[Holiday]:

    system_now = datetime.now().astimezone()
    local_tz = pytz.timezone(tz_str)

    merged: Dict[str, dict] = {}        # 假期合并表
    makeup_days: Dict[str, set] = {}    # key → {补班日期}
    makeup_pending = []                 # 先暂存调休原始记录

    # ========================================================
    # STEP 1：先扫描所有事件，合并假期；调休只暂存，不生成 key
    # ========================================================
    for h in holidays:
        if h.end is None:
            continue

        begin_local = to_local(h.begin, local_tz)
        end_local = to_local(h.end, local_tz)

        # 跳过早于当前年份的事件
        if end_local.year < system_now.year:
            continue

        base_name = normalize_name(h.name)
        if not base_name:
            continue

        # ====== (1) 遇到调休，不生成 key，必须先暂存 ======
        if is_makeup_event(base_name):

            # 洁名（假期名，不带“补班/调休”）
            clean_name = (
                base_name.replace("补班", "")
                .replace("调休", "")
                .replace("上班", "")
                .strip()
            )

            makeup_pending.append({
                "base_name": base_name,      # 如 "劳动节 调休"
                "clean_name": clean_name,    # 如 "劳动节"
                "date": begin_local.date(),  # 调休当天
                "holiday_obj": h
            })
            continue

        # ====== (2) 普通假期：使用 <name>::<begin_year> 合并 ======
        begin_year = begin_local.year
        key = f"{base_name}::{begin_year}"

        if key not in merged:
            merged[key] = {
                "name": base_name,
                "begin": begin_local,
                "end": end_local,
                "events": [h],
                "uid": h.uid,
                "all_day": getattr(h, "all_day", False),
                "raw_description": getattr(h, "raw_description", "")
            }
        else:
            # 拉伸时间范围
            if begin_local < merged[key]["begin"]:
                merged[key]["begin"] = begin_local
            if end_local > merged[key]["end"]:
                merged[key]["end"] = end_local
            merged[key]["events"].append(h)

    # ========================================================
    # STEP 2：调休匹配真实假期（正确处理跨年调休）
    # ========================================================
    for item in makeup_pending:
        clean_name = item["clean_name"]
        dt = item["date"]

        # 遍历所有实际假期，寻找归属
        for key, data in merged.items():
            holiday_name = data["name"]
            begin_d = data["begin"].date()
            end_d = data["end"].date()

            # 名字必须精确匹配
            if holiday_name != clean_name:
                continue

            # 日期必须落在 假期前后 ±14 天
            if begin_d - timedelta(days=14) <= dt <= end_d + timedelta(days=14):
                makeup_days.setdefault(key, set()).add(dt)
                break

    # ========================================================
    # STEP 3：生成 Holiday 对象（计算实际天数）
    # ========================================================
    result: List[Holiday] = []

    for key, data in merged.items():
        begin_local = data["begin"]
        end_local = data["end"]

        if end_local.date() < system_now.date():
            continue

        # 假期总天数
        total_days = (end_local.date() - begin_local.date()).days + 1

        # 调休日期集合
        workday_set = makeup_days.get(key, set())

        # 周末天数
        weekend_days = sum(
            1 for i in range(total_days)
            if (begin_local.date() + timedelta(days=i)).weekday() >= 5
        )

        # 去除调休天
        days_excl_makeup = max(0, total_days - len(workday_set))
        days_excl_makeup_weekend = max(0, total_days - len(workday_set) - weekend_days)

        result.append(Holiday(
            name=data["name"],
            begin=begin_local,
            end=end_local,
            uid=data.get("uid"),
            all_day=data.get("all_day", False),
            raw_description=data.get("raw_description", ""),
            duration=total_days,
            days_excl_makeup=days_excl_makeup,
            days_excl_makeup_weekend=days_excl_makeup_weekend
        ))

    # 排序
    result.sort(key=lambda h: h.begin)
    return result
