/**
 * 节假日与下班倒计时 - 主页面
 * 移植自 Python 版 ui/main_window.py + Android 版 MainScreen.kt
 */

const { parseIcs } = require('../../utils/ics-parser');
const { mergeAndFilterHolidays, computeSmartHolidayDays } = require('../../utils/holiday-processor');
const { timeUntil, formatDateRange, formatCountdown, formatHourCountdown, getTodayTime, isValidTime, loadConfig, saveConfig, getDefaultConfig } = require('../../utils/util');

// 随机欢迎语
const WELCOME_MSGS = [
  '今天也要加油鸭 🦆',
  '距离假期还有多远？',
  '努力工作，准时下班 💪',
  '又是元气满满的一天 ✨',
  '再坚持一下，假期就在前方 🏝️',
  '打工人，今天你快乐吗 😊',
  '早安，打工人 ☀️',
  '摸鱼快乐，生活万岁 🐟',
  '假期倒计时小助手 ⏰'
];

const HOLIDAY_CACHE_KEY = 'holiday_parsed_cache'; // 存预解析 JSON，而非原始 ICS
const CONFIG_KEY = 'app_config';
const DEFAULT_ICS_URL = 'https://www.shuyz.com/githubfiles/china-holiday-calender/master/holidayCal.ics';

Page({
  data: {
    theme: 'dark',
    welcomeText: '',
    holidays: [],
    countdownTexts: [],
    stats: { totalDays: 0, daysExclMakeup: 0, daysExclMakeupWeekend: 0 },
    midCountdown: '--:--:--',
    nightCountdown: '--:--:--',
    offworkMidTime: '12:00',
    offworkTime: '18:00',
    icsUrl: DEFAULT_ICS_URL,
    loading: false,
    refreshing: false,
    errorMsg: '',
    showSettings: false,
    editMidTime: '12:00',
    editNightTime: '18:00',
    settingError: '',
    toastText: ''
  },

  onLoad() {
    // 系统主题
    try {
      const info = wx.getSystemInfoSync();
      this.setData({ theme: info.theme || 'dark' });
    } catch (e) {}
    if (wx.onThemeChange) {
      wx.onThemeChange((res) => this.setData({ theme: res.theme }));
    }
    this.setData({ welcomeText: WELCOME_MSGS[Math.floor(Math.random() * WELCOME_MSGS.length)] });
    this.loadConfig();

    // 分批执行，不给主线程连续 >5s 的任务
    setTimeout(() => {
      this.loadCachedHolidays();
      setTimeout(() => {
        this.fetchIcs(false);
        setTimeout(() => this.startCountdownTimer(), 50);
      }, 50);
    }, 50);
  },

  onUnload() {
    this._destroyed = true;
    if (this._countdownTimer) {
      clearTimeout(this._countdownTimer);
      this._countdownTimer = null;
    }
  },

  // ========================================
  // 配置
  // ========================================
  loadConfig() {
    const config = loadConfig(CONFIG_KEY, getDefaultConfig());
    this.setData({
      offworkMidTime: config.offworkMidTime || '12:00',
      offworkTime: config.offworkTime || '18:00',
      icsUrl: config.icsUrl || DEFAULT_ICS_URL,
      editMidTime: config.offworkMidTime || '12:00',
      editNightTime: config.offworkTime || '18:00'
    });
  },

  saveConfigData() {
    saveConfig(CONFIG_KEY, {
      offworkMidTime: this.data.offworkMidTime,
      offworkTime: this.data.offworkTime,
      icsUrl: this.data.icsUrl
    });
  },

  // ========================================
  // 数据加载 — 从预解析 JSON 缓存恢复，无同步解析
  // ========================================
  loadCachedHolidays() {
    const cached = loadConfig(HOLIDAY_CACHE_KEY, '');
    if (!cached) return;
    try {
      const data = JSON.parse(cached);
      if (!data || !data.holidays || data.holidays.length === 0) return;

      const now = new Date();
      const countdownTexts = data.holidays.map(h => {
        const cd = timeUntil(new Date(h.beginTs), now);
        return formatCountdown(cd);
      });
      const midText = formatHourCountdown(timeUntil(getTodayTime(this.data.offworkMidTime), now));
      const nightText = formatHourCountdown(timeUntil(getTodayTime(this.data.offworkTime), now));

      this.setData({
        holidays: data.holidays,
        countdownTexts: countdownTexts,
        stats: data.stats,
        midCountdown: midText,
        nightCountdown: nightText,
        loading: false
      });
    } catch (e) {
      console.error('缓存数据异常', e);
    }
  },

  /**
   * 解析 ICS → holiday JSON → 缓存 + 渲染（用 nextTick 拆分为两步，避免阻塞）
   */
  processIcsData(icsText) {
    if (this._destroyed) return;

    wx.showLoading({ title: '解析中...', mask: true });

    // 用 setTimeout 把重解析放到下一个事件循环
    setTimeout(() => {
      if (this._destroyed) { wx.hideLoading(); return; }
      try {
        const rawHolidays = parseIcs(icsText);
        const holidays = mergeAndFilterHolidays(rawHolidays);
        const stats = computeSmartHolidayDays(holidays);

        const displayHolidays = holidays.map(h => ({
          name: h.name,
          dateRange: formatDateRange(h.begin, h.end),
          duration: h.duration,
          daysExclMakeup: h.daysExclMakeup,
          daysExclMakeupWeekend: h.daysExclMakeupWeekend,
          uid: h.uid,
          beginTs: h.begin.getTime()
        }));

        // 缓存预解析 JSON（~2KB，替代 77KB 原始 ICS）
        saveConfig(HOLIDAY_CACHE_KEY, JSON.stringify({ holidays: displayHolidays, stats: stats }));

        // 用 nextTick 拆分 setData，避免渲染卡死
        wx.nextTick(() => {
          if (this._destroyed) { wx.hideLoading(); return; }
          const now = new Date();
          const countdownTexts = displayHolidays.map(h => formatCountdown(timeUntil(new Date(h.beginTs), now)));
          const midText = formatHourCountdown(timeUntil(getTodayTime(this.data.offworkMidTime), now));
          const nightText = formatHourCountdown(timeUntil(getTodayTime(this.data.offworkTime), now));

          this.setData({
            holidays: displayHolidays,
            countdownTexts: countdownTexts,
            stats: stats,
            midCountdown: midText,
            nightCountdown: nightText
          });
          wx.hideLoading();
        });
      } catch (e) {
        console.error('解析失败', e);
        this.setData({ errorMsg: '解析假期数据失败' });
        wx.hideLoading();
      }
    }, 0);
  },

  // ========================================
  // 网络请求
  // ========================================
  fetchIcs(isManualRefresh) {
    if (isManualRefresh) this.setData({ refreshing: true });

    wx.request({
      url: this.data.icsUrl,
      method: 'GET',
      timeout: 5000,
      success: (res) => {
        if (res.statusCode === 200 && typeof res.data === 'string') {
          const data = res.data;
          if (data.includes('BEGIN:VCALENDAR') && data.includes('END:VCALENDAR') && data.includes('BEGIN:VEVENT')) {
            this.processIcsData(data);
            this.showToast('假期数据已更新');
          } else if (isManualRefresh) {
            this.showToast('数据格式异常');
          }
        } else if (isManualRefresh) {
          this.showToast('网络请求失败');
        }
      },
      fail: () => {
        // 网络失败时尝试用内置文件回退
        if (!loadConfig(HOLIDAY_CACHE_KEY, '')) {
          const fs = wx.getFileSystemManager();
          fs.readFile({
            filePath: 'assets/holidayCal.ics',
            encoding: 'utf-8',
            success: (res) => {
              this.processIcsData(res.data);
              this.showToast('已加载内置假期数据');
            },
            fail: () => {
              this.setData({ errorMsg: '无法获取假期数据，请检查网络' });
            }
          });
        } else if (isManualRefresh) {
          this.showToast('网络失败，已用缓存');
        }
      },
      complete: () => {
        this.setData({ loading: false, refreshing: false });
      }
    });
  },

  // ========================================
  // 倒计时（递归 setTimeout，永不堆积）
  // ========================================
  startCountdownTimer() {
    this.updateAllCountdowns();
    this._scheduleNextTick();
  },

  _scheduleNextTick() {
    if (this._destroyed) return;
    this._countdownTimer = setTimeout(() => {
      if (this._destroyed) return;
      this.updateAllCountdowns();
      this._scheduleNextTick();
    }, 3000);
  },

  updateAllCountdowns() {
    const holidays = this.data.holidays;
    if (!holidays || holidays.length === 0) return;

    const now = Date.now();
    const countdownTexts = holidays.map(h => formatCountdown(timeUntil(new Date(h.beginTs), new Date(now))));
    const midText = formatHourCountdown(timeUntil(getTodayTime(this.data.offworkMidTime), new Date(now)));
    const nightText = formatHourCountdown(timeUntil(getTodayTime(this.data.offworkTime), new Date(now)));

    this.setData({
      countdownTexts: countdownTexts,
      midCountdown: midText,
      nightCountdown: nightText
    });
  },

  // ========================================
  // 事件处理
  // ========================================
  onRefresh() { this.fetchIcs(true); },

  onOpenSettings() {
    this.setData({
      showSettings: true, settingError: '',
      editMidTime: this.data.offworkMidTime,
      editNightTime: this.data.offworkTime
    });
  },

  onCloseSettings() { this.setData({ showSettings: false, settingError: '' }); },

  onMidTimeInput(e) { this.setData({ editMidTime: e.detail.value, settingError: '' }); },

  onNightTimeInput(e) { this.setData({ editNightTime: e.detail.value, settingError: '' }); },

  onSaveSettings() {
    const { editMidTime, editNightTime } = this.data;
    if (!isValidTime(editMidTime)) { this.setData({ settingError: '时间格式错误，请使用 HH:MM' }); return; }
    if (!isValidTime(editNightTime)) { this.setData({ settingError: '时间格式错误，请使用 HH:MM' }); return; }
    this.setData({ offworkMidTime: editMidTime, offworkTime: editNightTime, showSettings: false, settingError: '' });
    this.saveConfigData();
    this.updateAllCountdowns();
    this.showToast('设置已保存');
  },

  noop() {},

  showToast(text) {
    this.setData({ toastText: text });
    setTimeout(() => { this.setData({ toastText: '' }); }, 3000);
  }
});
