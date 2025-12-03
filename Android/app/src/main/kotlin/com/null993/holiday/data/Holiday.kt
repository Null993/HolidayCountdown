package com.null993.holiday.data

import java.time.LocalDate
import java.time.temporal.ChronoUnit

data class Holiday(
    val name: String,
    val startDate: LocalDate,
    val endDate: LocalDate = startDate
) {
    // 计算属性：持续天数
    val duration: Long
        get() = ChronoUnit.DAYS.between(startDate, endDate) + 1

    // 这些属性在Python版中是动态计算的，这里我们可以暂时设为可变或默认值
    // 真正排除调休的逻辑比较复杂，通常需要知道哪些天是调休。
    // 简单起见，我们先只存储基础信息，复杂逻辑在 ViewModel 或 Repository 中处理。
    var daysExclMakeup: Int = 0
    var daysExclMakeupWeekend: Int = 0
}
