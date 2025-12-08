# HolidayCountdown-Android（假期倒计时 Android 版）

基于 **Jetpack Compose** 的中国法定节假日倒计时应用。  
它是桌面版 Holiday-Countdown 的 Android 移植版本，保持原版的解析算法与核心逻辑。

![预览](安卓预览.jpg)

---

## 🙏 数据来源（Credit）

本项目所使用的节假日 ICS 数据来源自：

**📌 https://github.com/lanceliao/china-holiday-calender**

感谢该项目为中国节假日提供高质量 ICS 数据。

---

## ✨ 主要功能

### 📅 节假日倒计时
实时显示距离下一个假期的天数（含进行中状态）。

### 📊 假期统计
* 起止日期与总天数  
* **自动识别调休/补班**  
* **排除双休的净休息时间**  

### ⏱ 下班倒计时
* 支持自定义午休 / 夜间下班时间  
* 实时动态倒计时  

### 🔔 通知栏常驻
* 前台服务实时刷新倒计时  
* 不打开 App 也能查看  

### 💾 缓存与离线
* 成功联网一次即可离线使用  
* 预置 ICS 数据，无需首启联网  
* 每次启动自动尝试刷新  

---

## 🛠 技术栈

* Kotlin  
* Jetpack Compose (Material3)  
* Coroutines  
* OkHttp  
* java.time（含 desugaring）  
* MVVM + Repository  

---

## 📦 编译与运行

1. 使用 Android Studio Otter 或更新版本  
2. 打开 `HolidayCountdown/Android` 目录  
3. 同步 Gradle  
4. 运行到 Android 15.0+ 设备（其他版本系统尚未测试）

---

## 📂 项目结构

```text
app/src/main/
├── assets/                 # 预置 ICS 数据 (holidayCal.ics)
├── kotlin/com/example/holiday/
│   ├── data/               # ICS 解析、模型、Repository
│   ├── service/            # 前台服务
│   ├── ui/                 # Compose UI
│   └── MainActivity.kt     # 程序入口
└── AndroidManifest.xml     # 权限、服务声明
````

---

## 📜 License 
本项目采用 **CC BY-NC 4.0** 协议发布。