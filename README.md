

# 📅 HolidayCountdown

### 一个支持智能假期解析、自动 ICS 缓存、本地下班倒计时的桌面工具（PyQt6）
![预览](预览.png)

轻量级的桌面工具，能够自动获取中国节假日 ICS 数据，并展示：

* 各假期的总天数
* 排除调休后的实际放假天数
* 排除调休与周末后的真实休息天数
* 中午与晚上两段下班倒计时
* 可选置顶、锁定窗口、透明度调节
* 具备本地 ICS 缓存，离线仍可正常使用

使用 PyQt6 开发，支持 Windows10、11（其它平台理论可运行但未测试）。

---

## ✨ 功能特点

### ✅ **假期展示功能**

* 自动从网络获取最新中国节假日 ICS 文件
* 若用户离线，则自动读取本地缓存的 ICS
* 按时间顺序显示所有假期
* 每条假期显示：

  * 假期名
  * 开始与结束日期
  * **总天数**
  * **排除调休后的天数**
  * **排除调休与周末后的天数**

### 🧠 **智能 ICS 解析**

* 根据 ICS 中的描述自动识别调休补班
* 解析失败会 fallback 到安全模式，保证不会卡住

### ⏰ **双段下班倒计时**

界面下侧展示两行两列布局：

| 下班时间              | 倒计时     |
| ----------------- | ------- |
| **中午 (12:00 默认)** | 中午下班倒计时 |
| **晚上 (18:00 默认)** | 晚上下班倒计时 |

可自定义，自动保存，无需“应用”按钮。

### 🪟 **实用窗口功能**

* **窗口置顶开关**
* **窗口锁定**（禁止拖动）
* **透明度滑条**

### 📦 **配置自动保存**

配置项包括：

* ICS 网址
* 中午下班时间
* 晚上下班时间
* 自动刷新间隔
* 是否智能计算假期

自动写入 `config.json`。

### 💾 **本地 ICS 缓存**

* 首次成功获取 ICS 后，自动写入 `holiday_data.ics`
* 下次启动时优先读取本地
* 若网络不可用不会影响功能

---

## 📥 安装方法

### ✔ 方式一：直接运行源码

确保你已经安装 Python 3.11。

```bash
pip install -r requirements.txt
python main.py
```

### ✔ 方式二：运行安装包 EXE

Release下放了一个Build好的安装包


---

## 📁 项目结构

```
HolidayCountdown/
├─ ui/
│  ├─ main_window.py        # 主界面
│  ├─ widgets/              # 组件
├─ holidays/
│  ├─ fetcher.py            # ICS 下载与缓存
│  ├─ parser.py             # ICS 解析
│  ├─ processor.py          # 假期数据处理逻辑
│  ├─ scheduler.py          # 下班倒计时
├─ main.py                  # 程序入口
├─ requirements.txt
├─ holiday_data.ics         # 本地 ICS 缓存（自动生成）
└─ config.json              # 用户配置（自动生成）
```

---

## ⚙ 配置参数说明

`config.json` 示例：

```json
{
  "ics_url": "https://www.shuyz.com/githubfiles/china-holiday-calender/master/holidayCal.ics",
  "offwork_mid_time": "12:00",
  "offwork_time": "18:00",
  "autostart": false,
  "smart_count": true,
  "refresh_interval_minutes": 60
}
```

---

## 📝 使用说明

1. 运行程序后将自动加载假期
2. 若互联网可用 → 从远程 ICS 刷新
3. 若离线 → 自动使用 `holiday_data.ics`
4. 中午 / 晚上下班时间修改后自动保存
5. 可通过右上角按钮切换：

   * 📌 置顶
   * 🔒 锁定窗口
   * 🌫 透明度调节

## 📜 License
本项目采用 Creative Commons Attribution-NonCommercial 4.0 International (CC BY-NC 4.0) 许可证发布。
