# ui/main_window.py
import sys

import requests
from PyQt6 import QtWidgets, QtGui, QtCore
from typing import List

from PyQt6.QtWidgets import QApplication

from holidays.parser import Holiday
from holidays.parser import parse_ics
from holidays.processor import merge_and_filter_holidays
from holidays.scheduler import time_until, compute_smart_holiday_days
import json
from datetime import datetime, time as dt_time
import os

ICS_CACHE_PATH =  "holiday_data.ics"
CONFIG_PATH = "config.json"
ICON_PATH = "icon.ico"


def resource_path(relative_path):
    """获取打包后资源的正确路径"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


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
        self.status_bar = None
        self.night_countdown_label = None
        self.mid_countdown_label = None
        self.scroll = None
        self.list_container = None
        self.refresh_timer = None
        self.excl_makeup_label = None
        self.ui_timer = None
        self.tray = None
        self.off_apply_btn = None
        self.excl_makeup_weekend_label = None
        self.off_countdown_label = None
        self.total_label = None
        self.off_mid_time_edit = None
        self.list_layout = None
        self.pin_chk = None
        self.opacity_slider = None
        self.refresh_btn = None
        self.lock_chk = None
        self.off_time_edit = None
        self.topmost = False
        self.locked = False
        self.opacity = 1.0

        self.config_path = resource_path(config_path)
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
        icon_path = resource_path(ICON_PATH)
        self.setWindowIcon(QtGui.QIcon(icon_path))

    def notify(self, title: str, text: str):
        """使用托盘气泡显示提示信息"""
        if self.tray:
            self.tray.showMessage(
                title,
                text,
                QtWidgets.QSystemTrayIcon.MessageIcon.Information,
                2000
            )

    # === 新增：统一的安全弹窗函数 === (弃用，换成托盘气泡)
    def show_safe_dialog(self, title: str, text: str, icon=QtWidgets.QMessageBox.Icon.Information):
        """
        安全弹窗：在主窗口置顶状态下仍能正常显示在最前面
        """
        msg = QtWidgets.QMessageBox(self)
        msg.setIcon(icon)
        msg.setWindowTitle(title)
        msg.setText(text)

        # 若主窗口置顶，则同步置顶
        if self.windowFlags() & QtCore.Qt.WindowType.WindowStaysOnTopHint:
            msg.setWindowFlags(msg.windowFlags() | QtCore.Qt.WindowType.WindowStaysOnTopHint)

        # 强制前置
        msg.setWindowModality(QtCore.Qt.WindowModality.ApplicationModal)
        msg.show()
        msg.raise_()
        msg.activateWindow()

        msg.exec()

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
        self.setWindowTitle("节假日与下班倒计时 v1.3.1  By Null993")
        central = QtWidgets.QWidget()
        v = QtWidgets.QVBoxLayout()

        # === 顶部控制栏 ===
        controls = QtWidgets.QHBoxLayout()

        self.refresh_btn = QtWidgets.QPushButton("刷新 ICS")
        self.refresh_btn.clicked.connect(self.on_refresh_clicked)
        controls.addWidget(self.refresh_btn)

        # --- 新增控制组件 ---
        self.pin_chk = QtWidgets.QCheckBox("置顶")
        self.pin_chk.setChecked(self.topmost)
        self.pin_chk.stateChanged.connect(self.on_pin_changed)
        controls.addWidget(self.pin_chk)

        self.lock_chk = QtWidgets.QCheckBox("锁定")
        self.lock_chk.setChecked(self.locked)
        self.lock_chk.stateChanged.connect(self.on_lock_changed)
        controls.addWidget(self.lock_chk)

        controls.addWidget(QtWidgets.QLabel("透明度"))
        self.opacity_slider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(30, 100)
        self.opacity_slider.setValue(int(self.opacity * 100))
        self.opacity_slider.setFixedWidth(100)
        self.opacity_slider.valueChanged.connect(self.on_opacity_changed)
        controls.addWidget(self.opacity_slider)

        controls.addStretch()
        v.addLayout(controls)

        # === 节假日列表 ===
        self.scroll = QtWidgets.QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setMinimumHeight(200)
        self.list_container = QtWidgets.QWidget()
        self.list_layout = QtWidgets.QVBoxLayout()
        self.list_container.setLayout(self.list_layout)
        self.scroll.setWidget(self.list_container)
        v.addWidget(self.scroll, 1)

        # === 底部：下班设置 & 统计 ===
        bottom = QtWidgets.QHBoxLayout()
        bottom_left = QtWidgets.QVBoxLayout()
        grid = QtWidgets.QGridLayout()

        # === 第一行：中午 ===
        grid.addWidget(QtWidgets.QLabel("中午下班时间 (HH:MM):"), 0, 0)
        self.off_mid_time_edit = QtWidgets.QLineEdit(self.config.get("offwork_mid_time", "12:00"))
        self.off_mid_time_edit.setFixedWidth(80)
        self.off_mid_time_edit.editingFinished.connect(lambda: self.apply_offwork_time("mid"))
        grid.addWidget(self.off_mid_time_edit, 0, 1)
        self.mid_countdown_label = QtWidgets.QLabel("中午下班倒计时：--:--:--")
        grid.addWidget(self.mid_countdown_label, 0, 2, 1, 2)

        # === 第二行：晚上 ===
        grid.addWidget(QtWidgets.QLabel("晚上下班时间 (HH:MM):"), 1, 0)
        self.off_time_edit = QtWidgets.QLineEdit(self.config.get("offwork_time", "18:00"))
        self.off_time_edit.setFixedWidth(80)
        self.off_time_edit.editingFinished.connect(lambda: self.apply_offwork_time("night"))
        grid.addWidget(self.off_time_edit, 1, 1)
        self.night_countdown_label = QtWidgets.QLabel("晚上下班倒计时：--:--:--")
        grid.addWidget(self.night_countdown_label, 1, 2, 1, 2)

        bottom_left.addLayout(grid)
        bottom.addLayout(bottom_left)
        bottom.addStretch()

        # --- 假期统计 ---
        stats_layout = QtWidgets.QVBoxLayout()
        self.total_label = QtWidgets.QLabel("总假期天数: -")
        self.excl_makeup_label = QtWidgets.QLabel("排除调休: 0")
        self.excl_makeup_weekend_label = QtWidgets.QLabel("排除调休和双休: 0")
        stats_layout.addWidget(self.total_label)
        stats_layout.addWidget(self.excl_makeup_label)
        stats_layout.addWidget(self.excl_makeup_weekend_label)
        bottom.addLayout(stats_layout)

        v.addLayout(bottom)

        # === 左下角消息提示 ===
        msg_layout = QtWidgets.QHBoxLayout()
        self.message_label = QtWidgets.QLabel("")
        self.message_label.setStyleSheet("color: gray; font-size: 12px;")
        msg_layout.addWidget(self.message_label)
        msg_layout.addStretch()
        v.addLayout(msg_layout)

        # === 状态栏（保留但不用于消息提示）===
        self.status_bar = QtWidgets.QStatusBar()
        self.setStatusBar(self.status_bar)

        central.setLayout(v)
        self.setCentralWidget(central)

        self.setMinimumSize(700, 400)
        self.resize(700, 500)
        self.setWindowOpacity(self.opacity)

        # 托盘
        self.tray = QtWidgets.QSystemTrayIcon(self)
        icon_path = resource_path(ICON_PATH)
        icon = QtGui.QIcon(icon_path)



        if icon.isNull():
            pix = QtGui.QPixmap(32, 32)
            pix.fill(QtGui.QColor("orange"))
            icon = QtGui.QIcon(pix)
        self.tray.setIcon(icon)
        menu = QtWidgets.QMenu()
        show_action = menu.addAction("显示主界面")
        show_action.triggered.connect(self.show_and_raise)
        exit_action = menu.addAction("退出")
        exit_action.triggered.connect(self.force_quit)
        self.tray.setContextMenu(menu)
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()

        QtCore.QTimer.singleShot(100, self._apply_window_state)

    # === 新增：专用消息提示函数 ===
    def show_message(self, text: str, duration: int = 3000):
        """在左下角固定label中输出短暂消息"""
        self.message_label.setText(text)
        QtCore.QTimer.singleShot(duration, lambda: self.message_label.setText(""))

    # === 替换逻辑：按钮与开关消息 ===
    def on_refresh_clicked(self):
        self.show_message("正在刷新假期数据...")
        self.load_ics_and_refresh()


    def on_pin_changed(self, state):
        self.toggle_topmost(state)
        self.show_message("窗口已置顶" if state else "窗口已取消置顶")

    def on_lock_changed(self, state):
        self.toggle_lock(state)
        self.show_message("窗口已锁定" if state else "窗口已解锁")

    def on_opacity_changed(self, value):
        self.change_opacity(value)
        self.show_message(f"透明度：{value}%")

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
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def on_tray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.Trigger:
            self.show_and_raise()

    def closeEvent(self, event):
        if getattr(self, "_force_quit", False):
            event.accept()
            return
        event.ignore()
        self.hide()
        self.tray.showMessage("节假日倒计时", "程序已最小化到托盘，双击图标可以恢复。",
                              QtWidgets.QSystemTrayIcon.MessageIcon.Information, 2000)


    def force_quit(self):
        self._force_quit = True
        self.tray.hide()
        QApplication.quit()





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
        """
        尝试从远端拉取 ICS 并更新本地缓存；若失败则回退到本地缓存（如果存在）。
        1. 请求成功后校验内容完整性（BEGIN:VCALENDAR / END:VCALENDAR / 至少一个 VEVENT）。
        2. 保存时采用原子写入（先写入临时文件再替换）。
        3. 如果远端数据无效但本地有缓存，使用本地并提示；如果本地也没有缓存则报错并返回。
        """
        ics_url = self.config.get("ics_url")
        data = None
        cache_path = resource_path(ICS_CACHE_PATH)
        cache_dir = os.path.dirname(cache_path) or "."

        # UI 反馈：开始请求
        self.refresh_btn.setText("正在获取 ICS...")
        QtWidgets.QApplication.processEvents()

        # 1) 尝试请求远端 ICS
        try:
            resp = requests.get(ics_url, timeout=10)
            resp.raise_for_status()
            candidate = resp.text

            # 简单的完整性校验 —— 确保是一个 calendar 且至少有一个 VEVENT
            text_lower = candidate.upper()
            valid = ("BEGIN:VCALENDAR" in text_lower) and ("END:VCALENDAR" in text_lower) and ("BEGIN:VEVENT" in text_lower)

            if not valid:
                # 远端返回但内容看起来不完整 -> 不覆盖本地缓存
                raise ValueError("远端 ICS 内容校验失败（不包含 BEGIN:VCALENDAR/END:VCALENDAR/BEGIN:VEVENT）")

            # 远端 ICS 看起来有效，保存到本地（原子写入）
            try:
                os.makedirs(cache_dir, exist_ok=True)
                tmp_path = cache_path + ".tmp"
                with open(tmp_path, "w", encoding="utf-8") as tf:
                    tf.write(candidate)
                # 原子替换（Windows 下也可用）
                os.replace(tmp_path, cache_path)
                print(f"✅ 已更新本地 ICS 缓存: {cache_path}")
                self.show_message("已成功更新假期数据（使用远端 ICS）。", duration=4000)
                data = candidate
            except Exception as save_exc:
                # 保存失败：回退到本地缓存（如果存在）
                print(f"⚠️ 保存本地 ICS 失败: {save_exc}")
                # 尝试使用本地缓存
                if os.path.exists(cache_path):
                    with open(cache_path, "r", encoding="utf-8") as f:
                        data = f.read()
                    self.notify("注意", "远端 ICS 获取成功但无法写入本地缓存，已使用本地缓存。")
                else:
                    self.notify("错误", f"无法保存远端 ICS，本地也没有缓存（错误：{save_exc}）")
                    self.refresh_btn.setText("刷新 ICS")
                    return

        except requests.RequestException as req_e:
            # 网络或请求层面错误：回退到本地缓存（如果存在）
            print(f"⚠️ 获取 ICS 失败（网络/请求错误）：{req_e}")
            if os.path.exists(cache_path):
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = f.read()
                # 离线模式提示
                self.notify("离线模式", "无法获取最新假期信息，已使用本地缓存。")
            else:
                self.notify("错误", f"无法获取假期数据，且没有本地缓存。网络错误：{req_e}")
                self.refresh_btn.setText("刷新 ICS")
                return
        except ValueError as val_e:
            # 远端返回但内容无效
            print(f"⚠️ 远端 ICS 内容无效：{val_e}")
            if os.path.exists(cache_path):
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = f.read()
                self.notify("提示", "远端假期数据不完整，已使用本地缓存。")
            else:
                self.notify("错误", f"远端假期数据不完整，且没有本地缓存。详情：{val_e}")
                self.refresh_btn.setText("刷新 ICS")
                return
        except Exception as unexpected:
            # 其他不可预期异常
            print(f"⚠️ 获取/处理 ICS 发生未预期错误：{unexpected}")
            if os.path.exists(cache_path):
                with open(cache_path, "r", encoding="utf-8") as f:
                    data = f.read()
                self.notify("提示", "处理假期数据时出错，已使用本地缓存。")
            else:
                self.notify("错误", f"发生错误且没有本地缓存：{unexpected}")
                self.refresh_btn.setText("刷新 ICS")
                return
        finally:
            # 恢复按钮文本（如果未提前 return）
            self.refresh_btn.setText("刷新 ICS")

        # 2) 解析 data 并刷新 UI
        if data:
            try:
                holidays = parse_ics(data)
                holidays = merge_and_filter_holidays(holidays)
                self.holidays = holidays
                self.refresh_list()
                self.refresh_stats()
            except Exception as parse_exc:
                print(f"⚠️ 解析 ICS 失败：{parse_exc}")
                self.notify("错误", f"解析假期数据失败：{parse_exc}")

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
            if item.holiday.flag_None:
                continue
            item.update_countdown(now=now)

        try:
            # === 中午下班倒计时 ===
            hh, mm = map(int, self.config.get("offwork_mid_time", "12:00").split(":"))
            mid_off = datetime.combine(datetime.today(), dt_time(hour=hh, minute=mm))
            t_mid = time_until(mid_off, now=now)
            if t_mid.total_seconds() <= 0:
                self.mid_countdown_label.setText("中午下班倒计时：已过时间")
            else:
                sec = int(t_mid.total_seconds())
                h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
                self.mid_countdown_label.setText(f"中午下班倒计时：{h}时 {m}分 {s}秒")

            # === 晚上下班倒计时 ===
            hh, mm = map(int, self.config.get("offwork_time", "18:00").split(":"))
            night_off = datetime.combine(datetime.today(), dt_time(hour=hh, minute=mm))
            t_night = time_until(night_off, now=now)
            if t_night.total_seconds() <= 0:
                self.night_countdown_label.setText("晚上下班倒计时：已过时间")
            else:
                sec = int(t_night.total_seconds())
                h, m, s = sec // 3600, (sec % 3600) // 60, sec % 60
                self.night_countdown_label.setText(f"晚上下班倒计时：{h}时 {m}分 {s}秒")

        except Exception:
            self.mid_countdown_label.setText("中午下班倒计时：格式错误")
            self.night_countdown_label.setText("晚上下班倒计时：格式错误")

    def apply_offwork_time(self, which="both"):
        try:
            changed = False
            if which in ("mid", "both"):
                time_mid = self.off_mid_time_edit.text().strip()
                hh, mm = map(int, time_mid.split(":"))
                assert 0 <= hh < 24 and 0 <= mm < 60
                self.config["offwork_mid_time"] = time_mid
                changed = True

            if which in ("night", "both"):
                time_night = self.off_time_edit.text().strip()
                hh, mm = map(int, time_night.split(":"))
                assert 0 <= hh < 24 and 0 <= mm < 60
                self.config["offwork_time"] = time_night
                changed = True

            if changed:
                self.save_config()
                self.show_message("配置已保存")
        except Exception:
            self.notify("错误", "时间格式应为 HH:MM（24 小时）")


    def show_status_message(self, msg: str, duration: int = 2000):
        """在状态栏显示短暂提示（自动淡出）"""
        label = QtWidgets.QLabel(msg)
        self.status_bar.addWidget(label)
        self.status_bar.showMessage(msg)

        # 使用 QTimer 延时清空
        QtCore.QTimer.singleShot(duration, lambda: self.status_bar.clearMessage())

