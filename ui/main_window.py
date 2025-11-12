# ui/main_window.py
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

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "..", "config.json")

class HolidayItemWidget(QtWidgets.QWidget):
    def __init__(self, holiday: Holiday, parent=None):
        super().__init__(parent)
        self.countdown_label = None
        self.name_label = None
        self.date_label = None
        self.duration_label = None
        self.actual_days_label = None
        self.holiday = holiday
        self.init_ui()

    def init_ui(self):
        layout = QtWidgets.QHBoxLayout()
        if self.holiday.flag_None:
            self.name_label = QtWidgets.QLabel("节日")
            self.date_label = QtWidgets.QLabel("日期")
            self.duration_label = QtWidgets.QLabel("放假天数")
            self.actual_days_label = QtWidgets.QLabel("实际天数")
            self.countdown_label = QtWidgets.QLabel("倒计时")
        else:
            self.name_label = QtWidgets.QLabel(self.holiday.name)
            self.date_label = QtWidgets.QLabel(f"{self.holiday.begin.date()} → {self.holiday.end.date()}")
            self.duration_label = QtWidgets.QLabel(f"{self.holiday.duration}")
            self.actual_days_label = QtWidgets.QLabel(f"{self.holiday.actual_days}")
            self.countdown_label = QtWidgets.QLabel("")
        layout.addWidget(self.name_label, 1)
        layout.addWidget(self.date_label, 2)
        layout.addWidget(self.duration_label, 1)
        layout.addWidget(self.actual_days_label, 1)
        layout.addWidget(self.countdown_label, 1)
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
    REFRESH_ICS = QtCore.QTimer    # placeholder for type hint
    UPDATE_UI_TIMER = QtCore.QTimer
    HOLIDAY_HAED = Holiday(True)
    def __init__(self, config_path=CONFIG_PATH):
        super().__init__()
        self.listhead = HolidayItemWidget(MainWindow.HOLIDAY_HAED)
        self.tableWidget = None
        self.refresh_timer = None
        self.ui_timer = None
        self.tray = None
        self.actual_label = None
        self.total_label = None
        self.off_countdown_label = None
        self.off_apply_btn = None
        self.off_time_edit = None
        self.list_layout = None
        self.list_container = None
        self.scroll = None
        self.smart_chk = None
        self.refresh_btn = None
        self.config_path = os.path.abspath(config_path)
        self.config = self.load_config()
        self.holidays: List[Holiday] = []
        self.items: List[HolidayItemWidget] = []
        self.init_ui()
        self.start_timers()
        self.load_ics_and_refresh()

    def load_config(self):
        if os.path.exists(self.config_path):
            with open(self.config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        else:
            # fallback defaults
            cfg = {"ics_url": "https://www.shuyz.com/githubfiles/china-holiday-calender/master/holidayCal.ics",
                   "offwork_time": "18:00",
                   "autostart": False,
                   "smart_count": True,
                   "refresh_interval_minutes": 60}
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(cfg, f, indent=2, ensure_ascii=False)
            return cfg

    def save_config(self):
        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(self.config, f, indent=2, ensure_ascii=False)

    def init_ui(self):
        self.setWindowTitle("节假日与下班倒计时")
        central = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout()
        # top controls
        controls = QtWidgets.QHBoxLayout()
        self.refresh_btn = QtWidgets.QPushButton("刷新 ICS")
        self.refresh_btn.clicked.connect(self.load_ics_and_refresh)
        controls.addWidget(self.refresh_btn)

        self.smart_chk = QtWidgets.QCheckBox("智能计算实际放假天数")
        self.smart_chk.setChecked(self.config.get("smart_count", True))
        self.smart_chk.stateChanged.connect(self.toggle_smart)
        controls.addWidget(self.smart_chk)

        controls.addStretch()
        v.addLayout(controls)

        # holidays list
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.list_container = QtWidgets.QWidget()
        self.list_layout = QtWidgets.QVBoxLayout()
        self.list_container.setLayout(self.list_layout)
        self.scroll.setWidget(self.list_container)
        v.addWidget(self.scroll, 1)

        # bottom: offwork settings & stats
        bottom = QtWidgets.QHBoxLayout()
        bottom_left = QtWidgets.QVBoxLayout()
        # offwork configuration
        off_layout = QtWidgets.QHBoxLayout()
        off_layout.addWidget(QtWidgets.QLabel("下班时间 (HH:MM):"))
        self.off_time_edit = QtWidgets.QLineEdit(self.config.get("offwork_time", "18:00"))
        off_layout.addWidget(self.off_time_edit)
        self.off_apply_btn = QtWidgets.QPushButton("应用")
        self.off_apply_btn.clicked.connect(self.apply_offwork_time)
        off_layout.addWidget(self.off_apply_btn)
        bottom_left.addLayout(off_layout)

        # show today's offwork countdown
        self.off_countdown_label = QtWidgets.QLabel("")
        bottom_left.addWidget(self.off_countdown_label)

        bottom.addLayout(bottom_left)
        bottom.addStretch()

        # stats area
        stats_layout = QtWidgets.QVBoxLayout()
        self.total_label = QtWidgets.QLabel("总假期天数: -")
        self.actual_label = QtWidgets.QLabel("实际放假天数: -")
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.actual_label)
        bottom.addLayout(stats_layout)

        v.addLayout(bottom)

        central.setLayout(v)
        self.setCentralWidget(central)
        self.resize(700, 500)

        # system tray
        self.tray = QtWidgets.QSystemTrayIcon(self)
        icon = QtGui.QIcon.fromTheme("calendar")  # fallback; you can set custom icon
        if icon.isNull():
            # fallback tiny icon
            pix = QtGui.QPixmap(32,32)
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

    def show_and_raise(self):
        self.show()
        self.raise_()
        self.activateWindow()

    def on_tray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.Trigger:
            self.show_and_raise()

    def closeEvent(self, event):
        # minimize to tray instead of quitting
        event.ignore()
        self.hide()
        self.tray.showMessage("节假日倒计时", "程序已最小化到托盘，双击图标可以恢复。", QtWidgets.QSystemTrayIcon.MessageIcon.Information, 2000)

    def start_timers(self):
        # UI update timer (1s)
        self.ui_timer = QtCore.QTimer(self)
        self.ui_timer.timeout.connect(self.update_countdowns)
        self.ui_timer.start(1000)

        # ICS refresh timer
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
        url = self.config.get("ics_url")
        if not url:
            return
        txt = fetch_ics(url)
        if not txt:
            QtWidgets.QMessageBox.warning(self, "下载失败", f"无法获取 ICS（{url}）。请检查网络或配置。")
            return
        holidays = parse_ics(txt)
        # 优化合并与过滤
        holidays = merge_and_filter_holidays(holidays)

            
            
        self.holidays = holidays
        self.refresh_list()
        self.refresh_stats()



    def refresh_list(self):
        self.clear_list()
        self.items = []
        # self.items.append(self.HOLIDAY_HAED)
        flag_head = False
        for h in self.holidays:
            if not flag_head:
                item = HolidayItemWidget(MainWindow.HOLIDAY_HAED)
                self.items.append(item)
                self.list_layout.addWidget(item)
                flag_head = True
                # continue
            item = HolidayItemWidget(h)
            self.items.append(item)
            self.list_layout.addWidget(item)
        self.list_layout.addStretch()

    def refresh_stats(self):
        total, actual = compute_smart_holiday_days(self.holidays)
        self.total_label.setText(f"总假期天数: {total}")
        if self.config.get("smart_count", True):
            self.actual_label.setText(f"实际放假天数（已减调休）: {actual}")
        else:
            self.actual_label.setText("实际放假天数（智能计算已关闭）")

    def update_countdowns(self):
        now = datetime.now()
        for item in self.items:
            if item.holiday.flag_None == True:
                continue
            item.update_countdown(now=now)
        # Update offwork countdown
        try:
            hh, mm = map(int, self.config.get("offwork_time", "18:00").split(":"))
            today_off = datetime.combine(datetime.today(), dt_time(hour=hh, minute=mm))
            # local naive -> treat as local time
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
        # basic validation HH:MM
        try:
            hh, mm = map(int, txt.split(":"))
            assert 0 <= hh < 24 and 0 <= mm < 60
            self.config["offwork_time"] = txt
            self.save_config()
            QtWidgets.QMessageBox.information(self, "已保存", f"下班时间已设为 {txt}")
        except Exception as e:
            QtWidgets.QMessageBox.warning(self, "错误", "时间格式应为 HH:MM（24 小时）")

    def toggle_smart(self):
        val = bool(self.smart_chk.isChecked())
        self.config["smart_count"] = val
        self.save_config()
        self.refresh_stats()
