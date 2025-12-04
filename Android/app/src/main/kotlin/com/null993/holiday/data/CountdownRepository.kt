package com.null993.holiday.data

import android.util.Log
import kotlinx.coroutines.*
import java.time.DayOfWeek
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit

object CountdownRepository {

    private var holidays: List<Holiday> = emptyList()
    private var lastLoaded: LocalDateTime? = null
    private var isUsingCache = false
    private var isUsingAssets = false
    private var loadError: String? = null
    private val ioScope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    private const val DEFAULT_ICS = "https://www.shuyz.com/githubfiles/china-holiday-calender/master/holidayCal.ics"

    init {
        Log.d("CountdownRepo", "Repo initialized")
        ioScope.launch {
            reloadHolidaysAsync()
        }
    }

    fun triggerReload() {
        Log.d("CountdownRepo", "Manual reload triggered")
        loadError = null
        ioScope.launch {
            reloadHolidaysAsync()
        }
    }

    fun getHolidays(): List<Holiday> {
        return holidays
    }

    fun getLoadError(): String? {
        return loadError
    }

    fun getStatusPrefix(): String {
        return when {
            isUsingCache -> "[离线]"
            isUsingAssets -> "[预置]"
            else -> ""
        }
    }

    private suspend fun reloadHolidaysAsync() {
        try {
            Log.d("CountdownRepo", "Starting download...")
            val url = PreferencesStore.getIcsUrl() ?: DEFAULT_ICS
            val icsContent = IcsParser.downloadIcsContent(url)
            PreferencesStore.saveIcsCache(icsContent)
            val parsed = IcsParser.parseIcsContent(icsContent)
            holidays = processHolidays(parsed)
            lastLoaded = LocalDateTime.now()
            isUsingCache = false
            isUsingAssets = false
            loadError = null
            Log.d("CountdownRepo", "Loaded ${holidays.size} holidays from network")
        } catch (e: Exception) {
            Log.e("CountdownRepo", "Failed to download holidays: ${e.message}")
            var content = PreferencesStore.loadIcsCache()
            var source = "cache"

            if (content == null) {
                Log.d("CountdownRepo", "No cache, trying assets...")
                content = PreferencesStore.loadIcsFromAssets()
                source = "assets"
            }

            if (content != null) {
                try {
                    val parsed = IcsParser.parseIcsContent(content)
                    holidays = processHolidays(parsed)

                    if (source == "cache") {
                        isUsingCache = true
                        isUsingAssets = false
                        loadError = "网络连接失败，已显示本地缓存"
                    } else {
                        isUsingCache = false
                        isUsingAssets = true
                        loadError = "网络连接失败，已显示预置数据"
                    }
                    Log.d("CountdownRepo", "Loaded ${holidays.size} holidays from $source")
                } catch (parseEx: Exception) {
                    Log.e("CountdownRepo", "Failed to parse $source", parseEx)
                    loadError = "无法获取数据 (网络错误且本地数据损坏)"
                }
            } else {
                loadError = "无法获取数据 (请检查网络)"
            }
        }
    }

    // =========================
    // Processor-equivalent logic
    // =========================

    /**
     * 规范化名称：去掉“第X天/第X日”等后缀、合并空格、去掉“假期/假日/放假”这类描述词。
     * 保留“补班/调休/上班”等关键词（以便后续判断），但本函数在生成 baseName 时不会刻意删除它们。
     */
    private fun normalizeName(rawName: String?): String {
        if (rawName == null) return ""
        var s = rawName.trim()

        // 如果存在 " 第" 类后缀（比如 " 第1天"），截断
        val idx = s.indexOf(" 第")
        if (idx != -1) {
            s = s.substring(0, idx).trim()
        }

        // 压缩多余空白为单个空格
        s = s.replace(Regex("\\s+"), " ")

        // 删除描述性词（中文边界处理：直接替换这些字符片段）
        s = s.replace(Regex("(假期|假日|放假)"), "")

        return s.trim()
    }

    /**
     * 判断是否为调休/补班事件（启发式）
     * 传入 name 字符串即可（也可包含 description）
     */
    private fun isMakeupEvent(nameOrDesc: String?): Boolean {
        if (nameOrDesc == null) return false
        val lower = nameOrDesc.lowercase()
        val keywords = listOf("补班", "调休", "上班", "补上班", "调班", "workday", "makeup")
        return keywords.any { lower.contains(it) }
    }

    // 用于暂存补班事件（按日期拆分）
    private data class PendingMakeup(
        val baseName: String,   // normalizeName(h.name)
        val cleanName: String,  // 去掉补班/调休等词后的名字，用来和假期 baseName 精确比对
        val date: LocalDate
    )

    /**
     * 主逻辑：接收 IcsParser.parseIcsContent 的输出（List<Holiday>），
     * 返回处理好的 List<Holiday>，并填充 daysExclMakeup, daysExclMakeupWeekend
     */
    private fun processHolidays(raw: List<Holiday>): List<Holiday> {
        val systemNow = LocalDate.now()
        val systemNowYear = systemNow.year

        // merged: key -> { "name": baseName, "begin": LocalDate, "end": LocalDate, "original_events": MutableList<Holiday> }
        val merged = mutableMapOf<String, MutableMap<String, Any>>()

        // 暂存所有补班事件（按天拆分）
        val makeupPending = mutableListOf<PendingMakeup>()

        // 匹配后的补班日期集合，key 对应 merged 的 key
        val makeupDaysMap = mutableMapOf<String, MutableSet<LocalDate>>()

        // === Step1: 扫描并合并普通假期，暂存调休事件 ===
        for (h in raw) {
            // 跳过没有结束时间，以及早于当前年的事件（按 endDate 判定）
            if (h.endDate.year < systemNowYear) continue

            val baseName = normalizeName(h.name)
            if (baseName.isEmpty()) continue

            // 判断是否为补班/调休事件（使用原始 name 字段判断）
            if (isMakeupEvent(h.name)) {
                // 生成 cleanName：从 baseName 删除补班/调休/上班等词（但保留其它部分与空格）
                var cleanName = baseName
                listOf("补班", "调休", "上班", "补上班", "调班", "workday", "makeup").forEach {
                    cleanName = cleanName.replace(it, "")
                }
                cleanName = normalizeName(cleanName)

                // 按天拆分补班区间，逐个加入 pending
                var d = h.startDate
                while (!d.isAfter(h.endDate)) {
                    makeupPending.add(PendingMakeup(baseName, cleanName, d))
                    d = d.plusDays(1)
                }
                continue
            }

            // 普通假期：以 begin year 分组，key = "<baseName>::<beginYear>"
            val beginYear = h.startDate.year
            val key = "${baseName}::${beginYear}"

            val cell = merged.getOrPut(key) {
                mutableMapOf(
                    "name" to baseName,
                    "begin" to h.startDate,
                    "end" to h.endDate,
                    "original_events" to mutableListOf<Holiday>()
                )
            }

            val currBegin = cell["begin"] as LocalDate
            val currEnd = cell["end"] as LocalDate

            if (h.startDate.isBefore(currBegin)) cell["begin"] = h.startDate
            if (h.endDate.isAfter(currEnd)) cell["end"] = h.endDate

            @Suppress("UNCHECKED_CAST")
            (cell["original_events"] as MutableList<Holiday>).add(h)
        }

        // === Step2: 把 pending 的补班分配到合并后的假期中 ===
        for (pending in makeupPending) {
            val dt = pending.date

            for ((key, data) in merged) {
                val holidayName = data["name"] as String
                val begin = data["begin"] as LocalDate
                val end = data["end"] as LocalDate

                // 名称必须严格匹配（cleanName 与合并后的 name 一致）
                if (holidayName != pending.cleanName) continue

                // 范围匹配：假期前后 14 天内
                val rangeStart = begin.minusDays(14)
                val rangeEnd = end.plusDays(14)

                if (!dt.isBefore(rangeStart) && !dt.isAfter(rangeEnd)) {
                    val set = makeupDaysMap.getOrPut(key) { mutableSetOf() }
                    set.add(dt)
                    break
                }
            }
        }

        // === Step3: 计算统计并生成结果 Holiday 列表 ===
        val result = mutableListOf<Holiday>()

        for ((key, data) in merged) {
            val name = data["name"] as String
            val begin = data["begin"] as LocalDate
            val end = data["end"] as LocalDate

            // 跳过已全部结束的假期（按本地日期比较）
            if (end.isBefore(systemNow)) continue

            val durationDays = ChronoUnit.DAYS.between(begin, end) + 1

            // 该假期对应的补班集合（可能为空）
            val workDaySet = makeupDaysMap[key] ?: emptySet()
            val makeupCount = workDaySet.size

            // 计算假期区间内的周末天数（包含首尾）
            var weekendDays = 0
            var d = begin
            while (!d.isAfter(end)) {
                val dow = d.dayOfWeek
                if (dow == DayOfWeek.SATURDAY || dow == DayOfWeek.SUNDAY) weekendDays++
                d = d.plusDays(1)
            }

            val daysExclMakeup = (durationDays - makeupCount).coerceAtLeast(0)
            val daysExclMakeupWeekend = (durationDays - makeupCount - weekendDays).coerceAtLeast(0)


            val h = Holiday(name, begin, end)
            h.daysExclMakeup = daysExclMakeup.toInt()
            h.daysExclMakeupWeekend = daysExclMakeupWeekend.toInt()

            result.add(h)
        }

        // 排序并返回
        return result.sortedBy { it.startDate }
    }

    // ============================
    // UI / Service 需要的工具函数
    // ============================

    fun getCountdownText(): String {
        val now = LocalDate.now()
        val next = holidays.firstOrNull { !it.endDate.isBefore(now) }

        if (holidays.isEmpty()) {
            return loadError ?: "正在加载数据..."
        }

        val prefix = getStatusPrefix()
        val prefixStr = if (prefix.isNotEmpty()) "$prefix " else ""

        return if (next != null) {
            if (!now.isBefore(next.startDate) && !now.isAfter(next.endDate)) {
                "${prefixStr}今天是 ${next.name} !"
            } else {
                val days = ChronoUnit.DAYS.between(now, next.startDate)
                "${prefixStr}距离 ${next.name} 还有 ${days} 天 (${next.startDate.format(DateTimeFormatter.ISO_DATE)})"
            }
        } else {
            "${prefixStr}没有找到未来的假期"
        }
    }
}
