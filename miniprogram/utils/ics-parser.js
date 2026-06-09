/**
 * ICS 解析器
 * 手动解析 ICS 文本，不依赖第三方库
 * 移植自 Android 版 IcsParser.kt
 */

/**
 * @typedef {Object} Holiday
 * @property {string} name - 节假日名称
 * @property {Date} begin - 开始日期
 * @property {Date} end - 结束日期
 * @property {string} uid - 唯一标识
 * @property {number} duration - 总天数
 * @property {number} days_excl_makeup - 排除调休后的天数
 * @property {number} days_excl_makeup_weekend - 排除调休和周末后的天数
 */

/**
 * 解析 ICS 文本，返回节假日列表
 * @param {string} icsText - ICS 文件文本内容
 * @returns {Holiday[]}
 */
function parseIcs(icsText) {
  const events = [];
  const lines = icsText.split('\n');

  let currentEvent = null;
  let inEvent = false;

  for (let line of lines) {
    line = line.trim();

    if (line === '') continue;

    if (line === 'BEGIN:VEVENT') {
      currentEvent = {};
      inEvent = true;
      continue;
    }

    if (line === 'END:VEVENT') {
      if (currentEvent) {
        const holiday = buildHoliday(currentEvent);
        if (holiday) {
          events.push(holiday);
        }
      }
      currentEvent = null;
      inEvent = false;
      continue;
    }

    if (!inEvent || !currentEvent) continue;

    // 处理折行：ICS 中长行以空格/制表符开头表示续行
    if (line.startsWith(' ') || line.startsWith('\t')) {
      // 简单处理：追加到上一个属性值
      const lastKey = Object.keys(currentEvent).pop();
      if (lastKey) {
        currentEvent[lastKey] += line.trim();
      }
      continue;
    }

    // 解析 key:value 或 key;params:value
    const colonIdx = line.indexOf(':');
    if (colonIdx === -1) continue;

    const keyPart = line.substring(0, colonIdx);
    const value = line.substring(colonIdx + 1);

    // 处理带参数的属性 (如 DTSTART;VALUE=DATE:20250101)
    const semiIdx = keyPart.indexOf(';');
    const key = semiIdx > -1 ? keyPart.substring(0, semiIdx) : keyPart;
    const params = semiIdx > -1 ? keyPart.substring(semiIdx + 1) : '';

    switch (key) {
      case 'UID':
        currentEvent.uid = value;
        break;
      case 'SUMMARY':
        // 处理编码：ICS 中可能使用 quoted-printable 或 base64 编码
        currentEvent.summary = decodeIcsText(value, keyPart);
        break;
      case 'DTSTART':
        if (params.includes('VALUE=DATE')) {
          // 全天事件：日期格式 YYYYMMDD
          currentEvent.startDate = parseIcsDate(value);
          currentEvent.allDay = true;
        } else {
          currentEvent.startDate = parseIcsDateTime(value);
          currentEvent.allDay = false;
        }
        break;
      case 'DTEND':
        if (params.includes('VALUE=DATE')) {
          // 全天事件：ICS 的 DTEND 是 exclusive（结束日期的次日）
          currentEvent.endDate = parseIcsDate(value);
          currentEvent.allDay = true;
        } else {
          currentEvent.endDate = parseIcsDateTime(value);
          currentEvent.allDay = false;
        }
        break;
      case 'DESCRIPTION':
        currentEvent.description = decodeIcsText(value, keyPart);
        break;
    }
  }

  // 按开始日期排序
  events.sort((a, b) => a.begin - b.begin);
  return events;
}

/**
 * 解析 ICS 日期格式 YYYYMMDD
 */
function parseIcsDate(str) {
  const year = parseInt(str.substring(0, 4), 10);
  const month = parseInt(str.substring(4, 6), 10) - 1; // JS 月份从 0 开始
  const day = parseInt(str.substring(6, 8), 10);
  return new Date(year, month, day);
}

/**
 * 解析 ICS 日期时间格式 YYYYMMDDTHHMMSS
 */
function parseIcsDateTime(str) {
  const dateStr = str.substring(0, 8);
  const timeStr = str.substring(9, 15); // 跳过 T
  const year = parseInt(dateStr.substring(0, 4), 10);
  const month = parseInt(dateStr.substring(4, 6), 10) - 1;
  const day = parseInt(dateStr.substring(6, 8), 10);
  const hour = parseInt(timeStr.substring(0, 2), 10);
  const min = parseInt(timeStr.substring(2, 4), 10);
  const sec = parseInt(timeStr.substring(4, 6), 10);
  return new Date(year, month, day, hour, min, sec);
}

/**
 * 解码 ICS 文本（处理 quoted-printable 编码）
 * ICS 中中文字符可能用 =E5=81=87=E6=9C=9F 这样的 QP 编码
 */
function decodeIcsText(value, keyPart) {
  if (!value) return '';

  // 检测 quoted-printable 编码
  if (keyPart.includes('ENCODING=QUOTED-PRINTABLE') || /=[0-9A-Fa-f]{2}/.test(value)) {
    try {
      return decodeQuotedPrintable(value);
    } catch (e) {
      return value;
    }
  }

  return value;
}

/**
 * 解码 quoted-printable 编码文本
 */
function decodeQuotedPrintable(str) {
  // 处理软换行（= 后面跟换行）
  str = str.replace(/=\r?\n/g, '');

  // 解码 =XX
  const bytes = [];
  let i = 0;
  while (i < str.length) {
    if (str[i] === '=' && i + 2 < str.length) {
      const hex = str.substring(i + 1, i + 3);
      if (/^[0-9A-Fa-f]{2}$/.test(hex)) {
        bytes.push(parseInt(hex, 16));
        i += 3;
        continue;
      }
    }
    bytes.push(str.charCodeAt(i));
    i++;
  }

  // 用 UTF-8 解码
  const decoder = new TextDecoder('utf-8');
  return decoder.decode(new Uint8Array(bytes));
}

/**
 * 从解析的事件构建 Holiday 对象
 */
function buildHoliday(event) {
  if (!event.summary || !event.startDate) return null;

  let begin = event.startDate;
  let end = event.endDate;

  // 如果没有结束日期，默认开始日当天
  if (!end) {
    end = new Date(begin);
  }

  // 全天事件处理：
  // ICS 中 DTEND 是 exclusive（如假期到1月3日，DTEND=20250104）
  // 我们需要 inclusive 的结束日期
  if (event.allDay && end > begin) {
    // DTEND 是 exclusive，往前推一天得到 inclusive 结束日期
    const inclusiveEnd = new Date(end);
    inclusiveEnd.setDate(inclusiveEnd.getDate() - 1);

    // 如果 inclusive end 小于 begin，说明是单天事件
    if (inclusiveEnd < begin) {
      end = new Date(begin);
    } else {
      end = inclusiveEnd;
    }
  }

  // 计算总天数（inclusive）
  const duration = Math.floor((end - begin) / (1000 * 60 * 60 * 24)) + 1;

  return {
    name: event.summary,
    begin: begin,
    end: end,
    uid: event.uid || '',
    duration: duration,
    days_excl_makeup: 0,
    days_excl_makeup_weekend: 0,
    allDay: event.allDay !== false,
    rawDescription: event.description || ''
  };
}

module.exports = {
  parseIcs
};
