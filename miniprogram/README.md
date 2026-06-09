# 📅 节假日倒计时 - 微信小程序版

本项目是 [HolidayCountdown](https://github.com/Null993/HolidayCountdown) 的微信小程序移植版，提供中国法定节假日查询与智能倒计时功能。

## 功能特性

- 🗓️ **节假日列表**：展示所有即将到来的中国法定节假日，含放假日期、天数、调休扣除统计
- ⏱️ **倒计时**：每个节假日显示精确倒计时（天/时/分/秒）
- ☀️🌙 **双下班倒计时**：可分别设置中午和晚上的下班时间，实时倒计时
- 📊 **智能统计**：总天数、排除调休后天数、排除调休和周末后的纯放假天数
- 🔄 **数据自动更新**：首页启动时自动从官方 ICS 源获取最新节假日数据
- 📱 **离线缓存**：ICS 数据缓存到本地，断网时使用缓存

## 项目结构

```
miniprogram/
├── app.js                  # 应用入口
├── app.json                # 应用配置
├── app.wxss                # 全局样式
├── project.config.json     # 项目配置（⚠ 需替换 appid）
├── sitemap.json            # 搜索配置
├── pages/
│   └── index/
│       ├── index.js        # 主页面逻辑
│       ├── index.wxml      # 主页面模板
│       ├── index.wxss      # 主页面样式
│       └── index.json      # 页面配置
└── utils/
    ├── ics-parser.js       # ICS 文件解析器（手动解析，无依赖）
    ├── holiday-processor.js# 节假日处理器（合并/调休匹配/智能统计）
    └── util.js             # 工具函数
```

## 使用前准备

1. **获取 AppID**：在 [微信公众平台](https://mp.weixin.qq.com/) 注册小程序，获取 AppID
2. **替换 AppID**：将 `project.config.json` 中的 `appid` 替换为你的真实 AppID
3. **域名白名单**：在微信公众平台的「开发 - 开发管理 - 服务器域名」中添加：
   - `request` 域名：`https://www.shuyz.com`
4. **导入项目**：在微信开发者工具中导入 `miniprogram/` 目录

## 技术要点

- **ICS 解析**：手动解析 ICS 文本，不依赖第三方库（移植自 Android 版 `IcsParser.kt`）
- **节假日处理**：核心算法移植自 Python 版 `holidays/processor.py`，含名称规范化、多天合并、调休匹配
- **数据缓存**：使用 `wx.setStorageSync` 缓存 ICS 原始文本和用户配置
- **倒计时**：使用 `setInterval` 每秒更新一次
- **配色方案**：深色主题（#0f0f1a），与桌面版视觉一致

## 数据来源

节假日数据来自 [china-holiday-calender](https://github.com/lanceliao/china-holiday-calender) 项目提供的 ICS 文件。

## 与桌面版/Android 版的差异

- ❌ 移除了系统托盘、窗口置顶/锁定、透明度调节（桌面特有功能）
- ❌ 移除了前台通知服务（Android 特有功能）
- ✅ 保留了所有核心功能：节假日列表、双倒计时、智能统计、数据缓存
- ✨ 新增了移动端友好的触控交互和深色主题
