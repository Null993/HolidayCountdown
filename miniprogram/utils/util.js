/**
 * 工具函数
 */

/**
 * 计算到目标时间的倒计时
 * @param {Date} target - 目标时间
 * @param {Date} now - 当前时间（可选）
 * @returns {{ days: number, hours: number, minutes: number, seconds: number, totalSeconds: number }}
 */
function timeUntil(target, now) {
  if (!now) now = new Date();
  const diff = target - now;
  const totalSeconds = Math.max(0, Math.floor(diff / 1000));

  const days = Math.floor(totalSeconds / 86400);
  const hours = Math.floor((totalSeconds % 86400) / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = totalSeconds % 60;

  return { days, hours, minutes, seconds, totalSeconds };
}

/**
 * 格式化日期范围为字符串
 * @param {Date} begin
 * @param {Date} end
 * @returns {string} 如 "01/28 → 02/04"
 */
function formatDateRange(begin, end) {
  const bM = begin.getMonth() + 1;
  const bD = begin.getDate();
  const eM = end.getMonth() + 1;
  const eD = end.getDate();
  return `${bM}/${bD} → ${eM}/${eD}`;
}

/**
 * 格式化倒计时字符串
 * @param {{ days: number, hours: number, minutes: number, seconds: number }} cd
 * @returns {string}
 */
function formatCountdown(cd) {
  if (cd.totalSeconds <= 0) return '进行中';
  if (cd.days > 30) return `${cd.days}天`;
  if (cd.days > 0) return `${cd.days}天`;
  if (cd.hours > 0) return `今天`;
  return `今天`;
}

/**
 * 格式化小时分钟倒计时
 * @param {{ days: number, hours: number, minutes: number, seconds: number }} cd
 * @returns {string}
 */
function formatHourCountdown(cd) {
  if (cd.totalSeconds <= 0) return '已过时间';
  return `${cd.hours}时 ${cd.minutes}分 ${cd.seconds}秒`;
}

/**
 * 获取今天的 HH:MM 时间点
 * @param {string} timeStr - "HH:MM" 格式
 * @returns {Date}
 */
function getTodayTime(timeStr) {
  const [h, m] = timeStr.split(':').map(Number);
  const now = new Date();
  return new Date(now.getFullYear(), now.getMonth(), now.getDate(), h, m, 0);
}

/**
 * 验证时间格式 HH:MM
 * @param {string} str
 * @returns {boolean}
 */
function isValidTime(str) {
  if (!/^\d{1,2}:\d{2}$/.test(str)) return false;
  const [h, m] = str.split(':').map(Number);
  return h >= 0 && h < 24 && m >= 0 && m < 60;
}

/**
 * 加载配置
 * @param {string} key - 存储键
 * @param {*} defaultVal - 默认值
 * @returns {*}
 */
function loadConfig(key, defaultVal) {
  try {
    const val = wx.getStorageSync(key);
    return val !== '' ? val : defaultVal;
  } catch (e) {
    return defaultVal;
  }
}

/**
 * 保存配置
 * @param {string} key
 * @param {*} value
 */
function saveConfig(key, value) {
  try {
    wx.setStorageSync(key, value);
  } catch (e) {
    console.error('保存配置失败', e);
  }
}

/**
 * 获取默认配置
 */
function getDefaultConfig() {
  return {
    icsUrl: 'https://www.shuyz.com/githubfiles/china-holiday-calender/master/holidayCal.ics',
    offworkMidTime: '12:00',
    offworkTime: '18:00',
    refreshIntervalMinutes: 60
  };
}

module.exports = {
  timeUntil,
  formatDateRange,
  formatCountdown,
  formatHourCountdown,
  getTodayTime,
  isValidTime,
  loadConfig,
  saveConfig,
  getDefaultConfig
};
