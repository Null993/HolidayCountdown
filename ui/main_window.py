# ui/main_window.py
import requests
from PyQt6 import QtWidgets, QtGui, QtCore
from typing import List

from PyQt6.QtWidgets import QTableWidgetItem

from holidays.parser import Holiday
from holidays.fetcher import fetch_ics
from holidays.parser import parse_ics
from holidays.processor import merge_and_filter_holidays
from holidays.scheduler import time_until, compute_smart_holiday_days
import json
from datetime import datetime, time as dt_time
import os

CACHE_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "holiday_data.ics"))
CONFIG_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "config.json"))


class HolidayItemWidget(QtWidgets.QWidget):
    def __init__(self, holiday: Holiday, parent=None):
        super().__init__(parent)
        self.days_excl_makeup_weekend_label = None
        self.days_excl_makeup_label = None
        self.countdown_label = None
        self.name_label = None
        self.date_label = None
        self.duration_label = None
        self.holiday = holiday
        self.init_ui()

        self.topmost = False
        self.locked = False
        self._locked_pos = None
        self._locked_size = None

    def init_ui(self):
        layout = QtWidgets.QHBoxLayout()
        if self.holiday.flag_None:
            self.name_label = QtWidgets.QLabel("节日")
            self.date_label = QtWidgets.QLabel("日期")
            self.duration_label = QtWidgets.QLabel("放假天数")
            self.days_excl_makeup_label = QtWidgets.QLabel("排除调休")
            self.days_excl_makeup_weekend_label = QtWidgets.QLabel("排除调休和双休")
            self.countdown_label = QtWidgets.QLabel("倒计时")
        else:
            self.name_label = QtWidgets.QLabel(self.holiday.name)
            self.date_label = QtWidgets.QLabel(f"{self.holiday.begin.date()} → {self.holiday.end.date()}")
            self.duration_label = QtWidgets.QLabel(f"{self.holiday.duration}")
            self.days_excl_makeup_label = QtWidgets.QLabel(f"{self.holiday.days_excl_makeup}")
            self.days_excl_makeup_weekend_label = QtWidgets.QLabel(f"{self.holiday.days_excl_makeup_weekend}")
            self.countdown_label = QtWidgets.QLabel("")
        layout.addWidget(self.name_label, 1,alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.date_label, 2,alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.duration_label, 1,alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.days_excl_makeup_label, 1,alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.days_excl_makeup_weekend_label, 1,alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.countdown_label, 1,alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)

    def update_countdown(self, now=None):
        dt = self.holiday.begin
        t = time_until(dt, now)
        if t.total_seconds() <= 0:
            self.countdown_label.setText("进行中/已开始")
        else:
            days = t.days
            hours = (t.seconds // 3600) % 24
            minutes = (t.seconds // 60) % 60
            seconds = t.seconds % 60
            self.countdown_label.setText(f"{days}天 {hours:02d}:{minutes:02d}:{seconds:02d}")


class MainWindow(QtWidgets.QMainWindow):
    REFRESH_ICS = QtCore.QTimer
    UPDATE_UI_TIMER = QtCore.QTimer
    HOLIDAY_HAED = Holiday(True)

    def __init__(self, config_path=CONFIG_PATH):
        super().__init__()
        self.topmost = False
        self.locked = False
        self.opacity = 1.0

        self.config_path = os.path.abspath(config_path)
        self.config = self.load_config()

        # 从配置恢复状态
        self.topmost = self.config.get("topmost", False)
        self.locked = self.config.get("locked", False)
        self.opacity = self.config.get("opacity", 1.0)

        # 其他初始化
        self.holidays: List[Holiday] = []
        self.items: List[HolidayItemWidget] = []
        self.init_ui()
        self.start_timers()
        self.load_ics_and_refresh()
        self._dragging = False
        self._drag_pos = None


    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            cfg = {
                "ics_url": "https://www.shuyz.com/githubfiles/china-holiday-calender/master/holidayCal.ics",
                "offwork_time": "18:00",
                "autostart": False,
                "smart_count": True,
                "refresh_interval_minutes": 60,
                "topmost": False,
                "locked": False,
                "opacity": 1.0,
            }
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            return cfg

    def save_config(self):
        self.config["topmost"] = self.topmost
        self.config["locked"] = self.locked
        self.config["opacity"] = self.opacity
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def init_ui(self):
        self.setWindowTitle("节假日与下班倒计时")
        central = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout()

        # === 顶部控制栏 ===
        controls = QtWidgets.QHBoxLayout()

        self.refresh_btn = QtWidgets.QPushButton("刷新 ICS")
        self.refresh_btn.clicked.connect(self.load_ics_and_refresh)
        controls.addWidget(self.refresh_btn)

        # --- 新增控制组件 ---
        self.pin_chk = QtWidgets.QCheckBox("置顶")
        self.pin_chk.setChecked(self.topmost)
        self.pin_chk.stateChanged.connect(self.toggle_topmost)
        controls.addWidget(self.pin_chk)

        self.lock_chk = QtWidgets.QCheckBox("锁定")
        self.lock_chk.setChecked(self.locked)
        self.lock_chk.stateChanged.connect(self.toggle_lock)
        controls.addWidget(self.lock_chk)

        controls.addWidget(QtWidgets.QLabel("透明度"))
        self.opacity_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(30, 100)
        self.opacity_slider.setValue(int(self.opacity * 100))
        self.opacity_slider.setFixedWidth(100)
        self.opacity_slider.valueChanged.connect(self.change_opacity)
        controls.addWidget(self.opacity_slider)

        controls.addStretch()
        v.addLayout(controls)

        # === 节假日列表 ===
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        # 修复1: 设置合理的最小高度，确保列表可见
        self.scroll.setMinimumHeight(200)
        self.list_container = QtWidgets.QWidget()
        self.list_layout = QtWidgets.QVBoxLayout()
        self.list_container.setLayout(self.list_layout)
        self.scroll.setWidget(self.list_container)
        v.addWidget(self.scroll, 1)

        # === 底部：下班设置 & 统计 ===
        bottom = QtWidgets.QHBoxLayout()
        bottom_left = QtWidgets.QVBoxLayout()

        off_layout = QtWidgets.QHBoxLayout()
        off_layout.addWidget(QtWidgets.QLabel("下班时间 (HH:MM):"))
        self.off_time_edit = QtWidgets.QLineEdit(self.config.get("offwork_time", "18:00"))
        off_layout.addWidget(self.off_time_edit)
        self.off_apply_btn = QtWidgets.QPushButton("应用")
        self.off_apply_btn.clicked.connect(self.apply_offwork_time)
        off_layout.addWidget(self.off_apply_btn)
        bottom_left.addLayout(off_layout)

        self.off_countdown_label = QtWidgets.QLabel("")
        bottom_left.addWidget(self.off_countdown_label)
        bottom.addLayout(bottom_left)
        bottom.addStretch()

        stats_layout = QtWidgets.QVBoxLayout()
        self.total_label = QtWidgets.QLabel("总假期天数: -")
        self.excl_makeup_label = QtWidgets.QLabel("排除调休: 0")
        self.excl_makeup_weekend_label = QtWidgets.QLabel("排除调休和双休: 0")
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.excl_makeup_label)
        stats_layout.addWidget(self.excl_makeup_weekend_label)
        bottom.addLayout(stats_layout)
        v.addLayout(bottom)

        central.setLayout(v)
        self.setCentralWidget(central)

        # 修复2: 设置合理的初始大小和最小尺寸
        self.setMinimumSize(700, 400)
        self.resize(700, 500)
        self.setWindowOpacity(self.opacity)

        # === 托盘 ===
        self.tray = QtWidgets.QSystemTrayIcon(self)
        icon = QtGui.QIcon.fromTheme("calendar")
        if icon.isNull():
            pix = QtGui.QPixmap(32, 32)
            pix.fill(QtGui.QColor("orange"))
            icon = QtGui.QIcon(pix)
        self.tray.setIcon(icon)
        menu = QtWidgets.QMenu()
        show_action = menu.addAction("显示主界面")
        show_action.triggered.connect(self.show_and_raise)
        exit_action = menu.addAction("退出")
        exit_action.triggered.connect(QtWidgets.QApplication.quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

        # 应用启动时的置顶与锁定状态
        QtCore.QTimer.singleShot(100, self._apply_window_state)

    def _apply_window_state(self):
        """应用配置中的窗口状态"""
        # 修复3: 先设置置顶状态
        if self.topmost:
            self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowType.WindowStaysOnTopHint)
            self.show()

        # 修复4: 再应用锁定状态（避免重复show造成闪烁）
        if self.locked:
            current_size = self.size()
            self.setMinimumSize(current_size)
            self.setMaximumSize(current_size)
            self.setWindowTitle("节假日与下班倒计时 🔒")

    # === 修复5: 优化置顶切换逻辑，减少闪烁 ===
    def toggle_topmost(self, state):
        self.topmost = bool(state)
        self.save_config()

        # 保存旧的窗口标志
        old_flags = self.windowFlags()
        new_flags = None

        if self.topmost:
            new_flags = old_flags | QtCore.Qt.WindowType.WindowStaysOnTopHint
        else:
            new_flags = old_flags & ~QtCore.Qt.WindowType.WindowStaysOnTopHint

        # 如果窗口标志没有改变，直接返回
        if new_flags == old_flags:
            return

        # 保存窗口的几何位置
        geometry = self.geometry()
        was_visible = self.isVisible()

        # 设置新的窗口标志
        self.setWindowFlags(new_flags)

        # 如果窗口原本可见，才调用 show()
        if was_visible:
            self.show()

        # 恢复窗口的几何位置
        self.setGeometry(geometry)

    # === 修复6: 修复锁定功能 ===
    def toggle_lock(self, state):
        self.locked = bool(state)
        self.save_config()

        if self.locked:
            # 锁定：固定当前尺寸
            current_size = self.size()
            self.setMinimumSize(current_size)
            self.setMaximumSize(current_size)
            self.setWindowTitle("节假日与下班倒计时 🔒")
        else:
            # 解锁：恢复可调整大小
            self.setMinimumSize(700, 400)
            self.setMaximumSize(16777215, 16777215)  # Qt默认最大值
            self.setWindowTitle("节假日与下班倒计时")

    def change_opacity(self, value):
        self.opacity = value / 100.0
        self.setWindowOpacity(self.opacity)
        self.save_config()

    def show_and_raise(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def on_tray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.Trigger:
            self.show_and_raise()

    def closeEvent(self, event):
        event.ignore()
        self.hide()
        self.tray.showMessage("节假日倒计时", "程序已最小化到托盘，双击图标可以恢复。",
                              QtWidgets.QSystemTrayIcon.MessageIcon.Information, 2000)

    def start_timers(self):
        self.ui_timer = QtCore.QTimer(self)
        self.ui_timer.timeout.connect(self.update_countdowns)
        self.ui_timer.start(1000)

        interval_ms = int(self.config.get("refresh_interval_minutes", 60)) * 60 * 1000
        self.refresh_timer = QtCore.QTimer(self)
        self.refresh_timer.timeout.connect(self.load_ics_and_refresh)
        self.refresh_timer.start(interval_ms)

    def clear_list(self):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.setParent(None)

    def load_ics_and_refresh(self):
        ics_url = self.config.get("ics_url")
        data = None

        try:
            self.refresh_btn.setText("正在获取 ICS...")
            QtWidgets.QApplication.processEvents()
            resp = requests.get(ics_url, timeout=10)
            resp.raise_for_status()
            data = resp.text
            os.makedirs(os.path.dirname(CACHE_PATH), exist_ok=True)
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                f.write(data)
            print(f"✅ 已更新本地 ICS 缓存: {CACHE_PATH}")
            self.refresh_btn.setText("刷新 ICS")
        except Exception as e:
            print(f"⚠️ 获取 ICS 失败: {e}")
            self.refresh_btn.setText("刷新 ICS")
            if os.path.exists(CACHE_PATH):
                with open(CACHE_PATH, "r", encoding="utf-8") as f:
                    data = f.read()
                QtWidgets.QMessageBox.information(
                    self, "离线模式",
                    "无法获取最新假期信息，已使用本地缓存。"
                )
            else:
                QtWidgets.QMessageBox.warning(
                    self, "错误",
                    "无法获取假期数据，且没有本地缓存。"
                )
                return

        if data:
            holidays = parse_ics(data)
            holidays = merge_and_filter_holidays(holidays)
            self.holidays = holidays
            self.refresh_list()
            self.refresh_stats()

    def refresh_list(self):
        self.clear_list()
        self.items = []
        flag_head = False
        for h in self.holidays:
            if not flag_head:
                item = HolidayItemWidget(MainWindow.HOLIDAY_HAED)
                self.items.append(item)
                self.list_layout.addWidget(item)
                flag_head = True
            item = HolidayItemWidget(h)
            self.items.append(item)
            self.list_layout.addWidget(item)
        self.list_layout.addStretch()

    def refresh_stats(self):
        total, excl_makeup, excl_makeup_weekend = compute_smart_holiday_days(self.holidays)
        self.total_label.setText(f"总天数: {total}")
        self.excl_makeup_label.setText(f"排除调休: {excl_makeup}")
        self.excl_makeup_weekend_label.setText(f"排除调休和双休: {excl_makeup_weekend}")

    def update_countdowns(self):
        now = datetime.now()
        for item in self.items:
            if item.holiday.flag_None == True:
                continue
            item.update_countdown(now=now)
        try:
            hh, mm = map(int, self.config.get("offwork_time", "18:00").split(":"))
            today_off = datetime.combine(datetime.today(), dt_time(hour=hh, minute=mm))
            t = time_until(today_off, now=now)
            if t.total_seconds() <= 0:
                self.off_countdown_label.setText("已过下班时间")
            else:
                sec = int(t.total_seconds())
                h = sec // 3600
                m = (sec % 3600) // 60
                s = sec % 60
                self.off_countdown_label.setText(f"下班倒计时：{h}时 {m}分 {s}秒")
        except Exception as e:
            self.off_countdown_label.setText("下班时间格式错误，请输入 HH:MM")

    def apply_offwork_time(self):
        txt = self.off_time_edit.text().strip()
        try:
            hh, mm = map(int, txt.split(":"))
            assert 0 <= hh < 24 and 0 <= mm < 60
            self.config["offwork_time"] = txt
            self.save_config()
            QtWidgets.QMessageBox.information(self, "已保存", f"下班时间已设为 {txt}")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "错误", "时间格式应为 HH:MM（24 小时）")

    # def toggle_smart(self):
    #     val = bool(self.smart_chk.isChecked())
    #     self.config["smart_count"] = val
    #     self.save_config()
    #     self.refresh_stats()