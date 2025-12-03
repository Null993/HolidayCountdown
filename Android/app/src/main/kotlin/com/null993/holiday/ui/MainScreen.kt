package com.null993.holiday.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material.icons.outlined.Info
import androidx.compose.material.icons.filled.NightsStay
import androidx.compose.material.icons.filled.WbSunny
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Density
import androidx.compose.ui.unit.IntOffset
import androidx.compose.ui.unit.IntRect
import androidx.compose.ui.unit.IntSize
import androidx.compose.ui.unit.LayoutDirection
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.window.PopupPositionProvider
import com.null993.holiday.data.CountdownRepository
import com.null993.holiday.data.Holiday
import com.null993.holiday.data.PreferencesStore
import kotlinx.coroutines.delay
import java.time.Duration
import java.time.LocalDate
import java.time.LocalTime
import java.time.format.DateTimeFormatter
import java.time.temporal.ChronoUnit

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun MainScreen() {
    var holidays by remember { mutableStateOf(emptyList<Holiday>()) }
    var repoStatus by remember { mutableStateOf("") }
    var refreshTrigger by remember { mutableStateOf(0) }

    var midTimeStr by remember { mutableStateOf(PreferencesStore.getOffworkMid()) }
    var nightTimeStr by remember { mutableStateOf(PreferencesStore.getOffworkNight()) }
    var midCountdown by remember { mutableStateOf("--:--:--") }
    var nightCountdown by remember { mutableStateOf("--:--:--") }

    var activeHolidayTooltip by remember { mutableStateOf<Holiday?>(null) }

    // 定时更新假期数据
    LaunchedEffect(refreshTrigger) {
        while (true) {
            holidays = CountdownRepository.getHolidays()
            val error = CountdownRepository.getLoadError()
            val prefix = CountdownRepository.getStatusPrefix()

            repoStatus = when {
                error != null -> error
                holidays.isEmpty() -> "正在加载..."
                else -> "${prefix}已加载 ${holidays.size} 个假期"
            }
            delay(1000)
        }
    }

    // 下班时间倒计时
    LaunchedEffect(Unit) {
        while (true) {
            val now = LocalTime.now()
            midCountdown = calculateCountdown(now, midTimeStr)
            nightCountdown = calculateCountdown(now, nightTimeStr)
            delay(1000)
        }
    }

    Scaffold(
        topBar = {
            CenterAlignedTopAppBar(
                title = {
                    Text(
                        "节假日倒计时",
                        style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold)
                    )
                },
                actions = {
                    IconButton(onClick = {
                        CountdownRepository.triggerReload()
                        refreshTrigger++
                    }) {
                        Icon(Icons.Default.Refresh, contentDescription = "刷新")
                    }
                }
            )
        },
        bottomBar = {
            BottomSection(
                midTime = midTimeStr,
                onMidTimeChange = {
                    midTimeStr = it
                    PreferencesStore.setOffworkMid(it)
                },
                midCountdown = midCountdown,
                nightTime = nightTimeStr,
                onNightTimeChange = {
                    nightTimeStr = it
                    PreferencesStore.setOffworkNight(it)
                },
                nightCountdown = nightCountdown,
                totalHolidays = holidays.sumOf { it.duration }.toInt(),
                totalExclMakeup = holidays.sumOf { it.daysExclMakeup },
                totalExclWeekend = holidays.sumOf { it.daysExclMakeupWeekend }
            )
        }
    ) { innerPadding ->

        Column(
            modifier = Modifier
                .padding(innerPadding)
                .fillMaxSize()
                .background(MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.3f))
        ) {
            if (repoStatus.isNotEmpty()) StatusBanner(repoStatus)

            Card(
                modifier = Modifier
                    .padding(16.dp)
                    .weight(1f),
                elevation = CardDefaults.cardElevation(2.dp)
            ) {
                Column {
                    Row(
                        Modifier
                            .fillMaxWidth()
                            .background(MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.7f))
                            .padding(12.dp)
                    ) {
                        HeaderCell("节日", 1.5f)
                        HeaderCell("日期", 2.4f)
                        HeaderCell("天数", 0.9f)
                        HeaderCell("去调休", 1f)
                        HeaderCell("去双调", 1f)
                        HeaderCell("倒计时", 1.8f)
                    }

                    HorizontalDivider()

                    LazyColumn(contentPadding = PaddingValues(bottom = 8.dp)) {
                        items(holidays, key = { it.hashCode() }) { holiday ->
                            HolidayRow(
                                holiday = holiday,
                                isTooltipVisible = activeHolidayTooltip == holiday,
                                onRowClick = {
                                    activeHolidayTooltip =
                                        if (activeHolidayTooltip == holiday) null else holiday
                                }
                            )
                            HorizontalDivider(
                                color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.5f),
                                thickness = 0.5.dp,
                                modifier = Modifier.padding(horizontal = 16.dp)
                            )
                        }
                    }
                }
            }
        }
    }
}


@Composable
fun StatusBanner(status: String) {
    val isError = status.contains("失败") || status.contains("错误")
    val color = if (isError) MaterialTheme.colorScheme.errorContainer else MaterialTheme.colorScheme.secondaryContainer
    val contentColor = if (isError) MaterialTheme.colorScheme.onErrorContainer else MaterialTheme.colorScheme.onSecondaryContainer
    val icon = if (isError) Icons.Default.Warning else Icons.Outlined.Info

    Row(
        Modifier
            .fillMaxWidth()
            .background(color)
            .padding(8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, null, tint = contentColor, modifier = Modifier.size(16.dp))
        Spacer(Modifier.width(8.dp))
        Text(status, color = contentColor)
    }
}

@Composable
fun RowScope.HeaderCell(text: String, weight: Float) {
    Text(
        text,
        modifier = Modifier.weight(weight),
        textAlign = TextAlign.Center,
        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
        color = MaterialTheme.colorScheme.onPrimaryContainer
    )
}

class AboveAnchorTooltipPositionProvider(private val density: Density) : PopupPositionProvider {
    override fun calculatePosition(
        anchorBounds: IntRect,
        windowSize: IntSize,
        layoutDirection: LayoutDirection,
        popupContentSize: IntSize
    ): IntOffset {
        val x = anchorBounds.left + (anchorBounds.width - popupContentSize.width) / 2
        val offset = with(density) { 8.dp.roundToPx() }
        val y = (anchorBounds.top - popupContentSize.height - offset).coerceAtLeast(0)
        return IntOffset(x, y)
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HolidayRow(holiday: Holiday, isTooltipVisible: Boolean, onRowClick: () -> Unit) {
    val now = LocalDate.now()
    val isPast = holiday.endDate.isBefore(now)
    val isOngoing = !now.isBefore(holiday.startDate) && !now.isAfter(holiday.endDate)

    val textColor = when {
        isPast -> MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f)
        isOngoing -> MaterialTheme.colorScheme.primary
        else -> MaterialTheme.colorScheme.onSurface
    }

    val rowBg =
        if (isOngoing) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.15f)
        else Color.Transparent

    val tooltipState = rememberTooltipState(isPersistent = true)

    LaunchedEffect(isTooltipVisible) {
        if (isTooltipVisible) tooltipState.show() else tooltipState.dismiss()
    }

    val density = LocalDensity.current
    val positionProvider = remember(density) { AboveAnchorTooltipPositionProvider(density) }

    TooltipBox(
        positionProvider = positionProvider,
        tooltip = {
            Surface(
                shape = RoundedCornerShape(8.dp),
                color = MaterialTheme.colorScheme.primary,
                contentColor = MaterialTheme.colorScheme.onPrimary,
                shadowElevation = 4.dp
            ) {
                val yearText =
                    if (holiday.startDate.year == holiday.endDate.year)
                        "${holiday.startDate.year}"
                    else
                        "${holiday.startDate.year} - ${holiday.endDate.year}"

                Text(
                    "年份: $yearText",
                    modifier = Modifier.padding(horizontal = 12.dp, vertical = 6.dp)
                )
            }
        },
        state = tooltipState
    ) {
        Row(
            Modifier
                .fillMaxWidth()
                .clickable { onRowClick() }
                .background(rowBg)
                .padding(12.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            Text(
                holiday.name,
                modifier = Modifier.weight(1.5f),
                textAlign = TextAlign.Center,
                color = textColor,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                style = MaterialTheme.typography.bodyMedium.copy(
                    fontWeight = if (isOngoing) FontWeight.Bold else FontWeight.Normal
                )
            )

            val dateStr =
                if (holiday.startDate == holiday.endDate)
                    holiday.startDate.format(DateTimeFormatter.ofPattern("MM.dd"))
                else
                    "${holiday.startDate.format(DateTimeFormatter.ofPattern("MM.dd"))}-${holiday.endDate.format(DateTimeFormatter.ofPattern("MM.dd"))}"

            Text(
                dateStr,
                modifier = Modifier.weight(2.4f),
                textAlign = TextAlign.Center,
                color = textColor,
                fontFamily = FontFamily.Monospace,
                style = MaterialTheme.typography.bodySmall
            )

            val statsStyle = MaterialTheme.typography.bodyMedium
            Text("${holiday.duration}", Modifier.weight(0.9f), textAlign = TextAlign.Center, color = textColor, style = statsStyle)
            Text("${holiday.daysExclMakeup}", Modifier.weight(1f), textAlign = TextAlign.Center, color = textColor, style = statsStyle)
            Text("${holiday.daysExclMakeupWeekend}", Modifier.weight(1f), textAlign = TextAlign.Center, color = textColor, style = statsStyle)

            val countdownText = when {
                isPast -> "已结束"
                isOngoing -> "进行中"
                else -> "${ChronoUnit.DAYS.between(now, holiday.startDate)}天"
            }

            Text(
                countdownText,
                modifier = Modifier.weight(1.8f),
                textAlign = TextAlign.Center,
                color = if (isOngoing) MaterialTheme.colorScheme.primary else textColor,
                style = MaterialTheme.typography.bodyMedium.copy(
                    fontWeight = if (isOngoing) FontWeight.Bold else FontWeight.Normal
                )
            )
        }
    }
}

@Composable
fun BottomSection(
    midTime: String,
    onMidTimeChange: (String) -> Unit,
    midCountdown: String,
    nightTime: String,
    onNightTimeChange: (String) -> Unit,
    nightCountdown: String,
    totalHolidays: Int,
    totalExclMakeup: Int,
    totalExclWeekend: Int
) {
    ElevatedCard(
        Modifier
            .fillMaxWidth()
            .padding(16.dp)
    ) {
        Column(Modifier.padding(16.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                OffworkTimerItem(
                    label = "午休",
                    icon = Icons.Default.WbSunny,
                    timeStr = midTime,
                    onTimeChange = onMidTimeChange,
                    countdown = midCountdown,
                    modifier = Modifier.weight(1f)
                )
                Spacer(Modifier.width(16.dp))
                OffworkTimerItem(
                    label = "下班",
                    icon = Icons.Default.NightsStay,
                    timeStr = nightTime,
                    onTimeChange = onNightTimeChange,
                    countdown = nightCountdown,
                    modifier = Modifier.weight(1f)
                )
            }

            HorizontalDivider(Modifier.padding(vertical = 12.dp))

            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceEvenly) {
                StatItem("总天数", "$totalHolidays")
                StatItem("去调休", "$totalExclMakeup")
                StatItem("去双休调休", "$totalExclWeekend")
            }
        }
    }
}

@Composable
fun OffworkTimerItem(
    label: String,
    icon: ImageVector,
    timeStr: String,
    onTimeChange: (String) -> Unit,
    countdown: String,
    modifier: Modifier = Modifier
) {
    Column(modifier = modifier, horizontalAlignment = Alignment.CenterHorizontally) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, null, Modifier.size(16.dp), tint = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.width(4.dp))
            Text(label, style = MaterialTheme.typography.labelLarge)
        }

        Spacer(Modifier.height(4.dp))

        OutlinedTextField(
            value = timeStr,
            onValueChange = onTimeChange,
            modifier = Modifier
                .width(80.dp)
                .height(48.dp),
            textStyle = MaterialTheme.typography.bodyMedium.copy(textAlign = TextAlign.Center),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            singleLine = true
        )

        Spacer(Modifier.height(4.dp))

        Text(
            countdown,
            style = MaterialTheme.typography.bodyMedium.copy(
                fontFamily = FontFamily.Monospace,
                fontWeight = FontWeight.Medium
            ),
            color = if (countdown == "已过") Color.Gray else MaterialTheme.colorScheme.secondary
        )
    }
}

@Composable
fun StatItem(label: String, value: String) {
    Column(horizontalAlignment = Alignment.CenterHorizontally) {
        Text(
            value,
            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold)
        )
        Text(
            label,
            style = MaterialTheme.typography.labelSmall,
            color = MaterialTheme.colorScheme.outline
        )
    }
}

fun calculateCountdown(now: LocalTime, targetStr: String): String {
    return try {
        val parts = targetStr.split(":")
        if (parts.size != 2) return "格式"
        val target = LocalTime.of(parts[0].toInt(), parts[1].toInt())

        if (now.isAfter(target)) return "已过"

        val diff = Duration.between(now, target)
        val hours = diff.toHours()
        val mins = diff.toMinutes() % 60
        val secs = diff.seconds % 60
        String.format("%02d:%02d:%02d", hours, mins, secs)
    } catch (e: Exception) {
        "错误"
    }
}
