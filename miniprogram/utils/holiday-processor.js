/**
 * 节假日处理器
 * 合并多天假期、识别调休补班、计算智能天数
 * 移植自 Python holidays/processor.py
 */

const _MAKEUP_KEYWORDS = ['补班', '调休', '上班', '补上班', '调班', 'workday', 'makeup'];

/**
 * 判断是否为调休/补班事件
 */
function isMakeupEvent(rawName) {
  if (!rawName) return false;
  const t = rawName.toLowerCase();
  return _MAKEUP_KEYWORDS.some(kw => t.includes(kw));
}

/**
 * 规范化节假日名称
 * 例如:
 *   '劳动节 第1天/共3天' => '劳动节'
 *   '劳动节 补班 第1天/共1天' => '劳动节 补班'
 *   '元旦 假期 第1天' => '元旦'
 */
function normalizeName(rawName) {
  if (!rawName) return '';
  let s = rawName.trim();

  // 截断 " 第x天" 部分
  const dayIdx = s.search(/\s第/);
  if (dayIdx !== -1) {
    s = s.substring(0, dayIdx).trim();
  }

  // 合并多个空白
  s = s.replace(/\s+/g, ' ');

  // 删除"假期/假日/放假"等描述词（保留补班/调休关键词）
  s = s.replace(/(假期|假日|放假)/g, '');

  return s.trim();
}

/**
 * 判断某天是否为周末（周六或周日）
 */
function isWeekend(date) {
  const day = date.getDay();
  return day === 0 || day === 6;
}

/**
 * 合并并过滤节假日
 * @param {Array} holidays - 从 ICS 解析的原始节假日列表
 * @returns {Array} 处理后的节假日列表
 */
function mergeAndFilterHolidays(holidays) {
  const now = new Date();
  const currentYear = now.getFullYear();

  // 假期合并表: key -> { name, begin, end, events }
  const merged = {};
  // 调休表: key -> Set(调休日期字符串)
  const makeupDays = {};
  // 暂存调休原始记录
  const makeupPending = [];

  // ============================================================
  // STEP 1: 扫描所有事件，合并假期；调休只暂存
  // ============================================================
  for (const h of holidays) {
    if (!h.end) continue;

    // 跳过早年事件（早于当前年份 - 1，保留一些余量）
    if (h.end.getFullYear() < currentYear - 1) continue;

    const baseName = normalizeName(h.name);
    if (!baseName) continue;

    // (1) 调休事件：不生成 key，先暂存
    if (isMakeupEvent(baseName)) {
      // 洁名（去掉补班/调休/上班关键词）
      const cleanName = baseName.replace(/补班|调休|上班/g, '').trim();

      makeupPending.push({
        baseName: baseName,
        cleanName: cleanName,
        date: new Date(h.begin.getFullYear(), h.begin.getMonth(), h.begin.getDate()),
        holidayObj: h
      });
      continue;
    }

    // (2) 普通假期：使用 <name>::<beginYear> 合并
    const beginYear = h.begin.getFullYear();
    const key = `${baseName}::${beginYear}`;

    if (!merged[key]) {
      merged[key] = {
        name: baseName,
        begin: new Date(h.begin),
        end: new Date(h.end),
        events: [h],
        uid: h.uid || ''
      };
    } else {
      // 拉伸时间范围
      if (h.begin < merged[key].begin) {
        merged[key].begin = new Date(h.begin);
      }
      if (h.end > merged[key].end) {
        merged[key].end = new Date(h.end);
      }
      merged[key].events.push(h);
    }
  }

  // ============================================================
  // STEP 2: 调休匹配真实假期
  // ============================================================
  for (const item of makeupPending) {
    const cleanName = item.cleanName;
    const dt = item.date;

    for (const [key, data] of Object.entries(merged)) {
      const holidayName = data.name;
      const beginDate = new Date(data.begin.getFullYear(), data.begin.getMonth(), data.begin.getDate());
      const endDate = new Date(data.end.getFullYear(), data.end.getMonth(), data.end.getDate());

      // 名字必须精确匹配
      if (holidayName !== cleanName) continue;

      // 日期必须落在假期前后 ±14 天
      const before14 = new Date(beginDate);
      before14.setDate(before14.getDate() - 14);
      const after14 = new Date(endDate);
      after14.setDate(after14.getDate() + 14);

      if (dt >= before14 && dt <= after14) {
        // 使用 date string 作为 key
        const dateStr = formatDateStr(dt);
        if (!makeupDays[key]) {
          makeupDays[key] = new Set();
        }
        makeupDays[key].add(dateStr);
        break;
      }
    }
  }

  // ============================================================
  // STEP 3: 生成处理后的 Holiday 对象
  // ============================================================
  const result = [];

  for (const [key, data] of Object.entries(merged)) {
    const beginLocal = data.begin;
    const endLocal = data.end;
    const endDateOnly = new Date(endLocal.getFullYear(), endLocal.getMonth(), endLocal.getDate());

    // 跳过已结束的假期
    const todayOnly = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    if (endDateOnly < todayOnly) continue;

    // 假期总天数 (inclusive)
    const totalDays = Math.floor((endLocal - beginLocal) / (1000 * 60 * 60 * 24)) + 1;

    // 调休日期集合
    const workdaySet = makeupDays[key] || new Set();

    // 计算范围内的周末天数
    let weekendDays = 0;
    for (let i = 0; i < totalDays; i++) {
      const d = new Date(beginLocal);
      d.setDate(d.getDate() + i);
      if (isWeekend(d)) {
        weekendDays++;
      }
    }

    // 排除调休天数
    const daysExclMakeup = Math.max(0, totalDays - workdaySet.size);
    // 排除调休和周末
    const daysExclMakeupWeekend = Math.max(0, totalDays - workdaySet.size - weekendDays);

    result.push({
      name: data.name,
      begin: new Date(beginLocal),
      end: new Date(endLocal),
      uid: data.uid,
      duration: totalDays,
      daysExclMakeup: daysExclMakeup,
      daysExclMakeupWeekend: daysExclMakeupWeekend,
      makeupDays: Array.from(workdaySet)
    });
  }

  // 按开始时间排序
  result.sort((a, b) => a.begin - b.begin);
  return result;
}

/**
 * 计算总统计天数的便捷函数
 */
function computeSmartHolidayDays(holidays) {
  let totalDays = 0;
  let daysExclMakeup = 0;
  let daysExclMakeupWeekend = 0;

  for (const h of holidays) {
    totalDays += h.duration;
    daysExclMakeup += h.daysExclMakeup;
    daysExclMakeupWeekend += h.daysExclMakeupWeekend;
  }

  return { totalDays, daysExclMakeup, daysExclMakeupWeekend };
}

/**
 * 格式化日期为 YYYY-MM-DD 字符串
 */
function formatDateStr(date) {
  const y = date.getFullYear();
  const m = String(date.getMonth() + 1).padStart(2, '0');
  const d = String(date.getDate()).padStart(2, '0');
  return `${y}-${m}-${d}`;
}

module.exports = {
  mergeAndFilterHolidays,
  computeSmartHolidayDays,
  formatDateStr
};
