import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import pytz

from .parser import Holiday  # 你的 Holiday dataclass
# 如果 time_until 在别处，请确保引用到能处理 aware datetimes 的版本

# 可扩展的关键词集合
_MAKEUP_KEYWORDS = {"补班", "调休", "上班", "补上班", "调班", "workday", "makeup"}

def normalize_name(raw_name: Optional[str]) -> str:
    """
    把原始事件名规范化：
    '劳动节 第1天/共1天' -> '劳动节'
    '劳动节 补班 第1天/共1天' -> '劳动节 补班'
    '元旦 假期 第1天/共3天' -> '元旦'
    保留 '补班'/'调休' 等词，移除 '假期'/'假日' 等描叙词。
    """
    if not raw_name:
        return ""

    s = raw_name.strip()

    # 1) 在遇到 ' 第' / '第' / '/共' / ' Day' / ' day' / '/共' 等后缀时截断。
    #    使用非捕获组匹配这些常见后缀的开始位置（中文和英文场景）
    # m = re.search(r"(?:\s*第\b|\s*/共\b|\s+Day\b|\s+day\b)", s)
    m = re.search(r"\s第", s)
    if m:
        s = s[:m.start()].strip()

    # 2) 压缩多余空白（把多个空格替换为一个空格）
    s = re.sub(r"\s+", " ", s)

    # 3) 去掉描述性词 '假期'/'假日'/'假' 等，但保留 '补班'/'调休'/'上班' 等关键词。
    #    这里我们仅移除孤立的 '假期' 或 '假日' 单词（边界匹配）。
    s = re.sub(r"\b(假期|假日|放假)\b", "", s)

    # 4) 再次清理首尾空白并返回
    s = s.strip()
    return s

def is_makeup_event(raw_name_or_desc: Optional[str]) -> bool:
    """
    根据名字或描述判断是否为补班/调休/上班事件（启发式）。
    返回 True 表示这是一个上班/补班/调休事件（应计入调休天数）。
    """
    if not raw_name_or_desc:
        return False
    txt = raw_name_or_desc.lower()
    for kw in _MAKEUP_KEYWORDS:
        if kw in txt:
            return True
    return False

def to_local(dt: datetime, target_tzinfo) -> datetime:
    """
    把 dt 转换到 target_tzinfo（一个 tzinfo），同时处理 naive/aware。
    如果 dt 为 None，返回 None。
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        # 将 naive 视为本地时区时间 (assign local tz)
        # 使用 replace 而非 localize，是因为我们假定这个 naive 的时间就是当地时间
        return dt.replace(tzinfo=target_tzinfo)
    # 如果已带时区，则转换到目标 tz
    return dt.astimezone(target_tzinfo)

def merge_and_filter_holidays(holidays: List[Holiday], tz_str="Asia/Shanghai") -> List[Holiday]:
    """
    合并、过滤并计算假期显示信息
    返回 List[Holiday]，并确保同名不同年不会被合并为一个假期。
    合并键使用: "<normalized_name>::<begin_year>"
    """
    system_now = datetime.now().astimezone()
    # local_tz = system_now.tzinfo
    local_tz = pytz.timezone(tz_str)
    merged = {}
    makeup_days: Dict[str, set] = {}

    # === Step 1. 合并同名同年假期（使用 begin 的本地年份作为分组） ===
    for h in holidays:
        # 跳过没有结束时间或结束时间早于当前年的事件（保持你原先的意图，但用本地化时间判断）
        if h.end is None:
            continue

        # 先把 begin/end 转为本地时区，再取年份与进行比较
        begin_local = to_local(h.begin, local_tz)
        end_local = to_local(h.end, local_tz)

        # 如果整个事件在 system_now 之前的年份，跳过
        if end_local.year < system_now.year:
            continue

        base_name = normalize_name(h.name)
        if not base_name:
            continue

        # 使用 begin_local 的年份作为分组键（避免把不同年的同名假期合并）
        begin_year = begin_local.year
        key = f"{base_name}::{begin_year}"
        if is_makeup_event(key):
            # 记录补班对应的节假日（去掉“补班”等词）
            related_name = key.replace("补班", "").replace("调休", "").replace(" ", "").strip()
            makeup_days.setdefault(related_name, set()).add(begin_local.date())
            #
            # if key not in merged:
            #     merged[key] = {
            #         "name": base_name,
            #         "list_work_day": [begin_local],
            #         "days": 1,
            #         "events": [h],
            #         "uid": h.uid,
            #         "all_day": getattr(h, "all_day", False),
            #         "raw_description": getattr(h, "raw_description", "")
            #     }
            # else:
            #     # 扩展 begin/end 为覆盖整个合并分组的最小/最大范围
            #     merged[key]["days"] += 1
            #     merged[key]["list_work_day"].append(end_local)
            #     merged[key]["events"].append(h)
        else:
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
                # 扩展 begin/end 为覆盖整个合并分组的最小/最大范围
                if begin_local < merged[key]["begin"]:
                    merged[key]["begin"] = begin_local
                if end_local > merged[key]["end"]:
                    merged[key]["end"] = end_local
                merged[key]["events"].append(h)

    # === Step 2. 计算字段并过滤已结束的假期 ===
    result: List[Holiday] = []

    for key, data in merged.items():
        begin_local = data["begin"]

        end_local = data["end"]
        # 如果假期已经全部结束（按本地日期比较），跳过
        if end_local.date() < system_now.date():
            continue

        # 计算总天数（按日期计数，包含首尾）
        duration_days = (end_local.date() - begin_local.date()).days + 1

        # 获取该假期对应的补班天集合（若没有则空集合）
        work_day_set = makeup_days.get(key, set())

        # 实际放假天数 = 总天数 - 补班天数（按日期数）
        actual_days = max(0, duration_days - len(work_day_set))


        # for e in data["events"]:
        #     if is_makeup_event((e.name or "") + " " + (getattr(e, "raw_description", "") or "")):
        #         b = to_local(e.begin, local_tz)
        #         ed = to_local(e.end if e.end else e.begin, local_tz)
        #         adjust_days += (ed.date() - b.date()).days + 1
        #
        # actual_days = max(0, duration_days - adjust_days)



        # 状态与倒计时（可选：你可以把这部分封装到 Holiday 的方法）
        if begin_local.date() <= system_now.date() <= end_local.date():
            status = "进行中"
            end_of_last_day = datetime.combine(end_local.date(), datetime.max.time()).replace(tzinfo=local_tz)
            delta = end_of_last_day - system_now
            total_seconds = int(max(0, delta.total_seconds()))
            days_left = delta.days
            hh = total_seconds // 3600
            mm = (total_seconds % 3600) // 60
            ss = total_seconds % 60
            countdown_text = f"距假期结束还有 {days_left} 天 ({hh}时{mm}分{ss}秒)"
        else:
            status = "未开始"
            begin_start = datetime.combine(begin_local.date(), datetime.min.time()).replace(tzinfo=local_tz)
            delta = begin_start - system_now
            total_seconds = int(max(0, delta.total_seconds()))
            days_left = max(0, delta.days)
            hh = total_seconds // 3600
            mm = (total_seconds % 3600) // 60
            ss = total_seconds % 60
            countdown_text = f"距放假还有 {days_left} 天 ({hh}时{mm}分{ss}秒)"

        # 构造并追加 Holiday 对象（假设 Holiday 支持这些字段；若没有，可根据你的定义调整）
        result.append(Holiday(
            name=data["name"],
            begin=begin_local,
            end=end_local,
            uid=data.get("uid"),
            all_day=data.get("all_day", False),
            raw_description=data.get("raw_description", ""),
            # 若你的 Holiday dataclass/类包含下面字段，请启用它们；否则可省略或扩展类定义
            duration=duration_days,
            actual_days=actual_days,
            # status=status,
            # countdown_text=countdown_text
        ))

        # # 附加补班信息
        # result[-1].work_days = workdays
        # result[-1].status = status
        # result[-1].countdown_text = countdown_text

    # === Step 3. 排序（按 begin） ===
    result.sort(key=lambda h: h.begin)
    return result
