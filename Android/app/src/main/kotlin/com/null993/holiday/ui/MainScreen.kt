package com.null993.holiday.ui

import androidx.compose.foundation.background
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
import androidx.compose.material3.HorizontalDivider
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
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
    var holidays by remember { mutableStateOf<List<Holiday>>(emptyList()) }
    var repoStatus by remember { mutableStateOf("") }
    var refreshTrigger by remember { mutableStateOf(0) }
    
    var midTimeStr by remember { mutableStateOf(PreferencesStore.getOffworkMid()) }
    var nightTimeStr by remember { mutableStateOf(PreferencesStore.getOffworkNight()) }
    var midCountdown by remember { mutableStateOf("--:--:--") }
    var nightCountdown by remember { mutableStateOf("--:--:--") }
    
    LaunchedEffect(refreshTrigger) {
        while (true) {
            holidays = CountdownRepository.getHolidays()
            val error = CountdownRepository.getLoadError()
            val prefix = CountdownRepository.getStatusPrefix()
            
            repoStatus = if (error != null) {
                error
            } else if (holidays.isEmpty()) {
                "正在加载..."
            } else {
                "${prefix}已加载 ${holidays.size} 个假期"
            }
            delay(1000)
        }
    }

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
                    IconButton(onClick = { CountdownRepository.triggerReload() }) {
                        Icon(Icons.Default.Refresh, contentDescription = "刷新")
                    }
                },
                colors = TopAppBarDefaults.centerAlignedTopAppBarColors(
                    containerColor = MaterialTheme.colorScheme.surface,
                    titleContentColor = MaterialTheme.colorScheme.primary
                )
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
            // Status Bar
            if (repoStatus.isNotEmpty()) {
                StatusBanner(repoStatus)
            }

            // Table
            Card(
                modifier = Modifier
                    .padding(horizontal = 16.dp, vertical = 8.dp)
                    .weight(1f),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                elevation = CardDefaults.cardElevation(defaultElevation = 2.dp)
            ) {
                Column {
                    // Header
                    Row(
                        modifier = Modifier
                            .fillMaxWidth()
                            .background(MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.7f))
                            .padding(vertical = 12.dp, horizontal = 8.dp)
                    ) {
                        HeaderCell("节日", 1.5f)
                        HeaderCell("日期", 2.4f)
                        HeaderCell("天数", 0.9f)
                        HeaderCell("去调休", 1f)
                        HeaderCell("去双调", 1f)
                        HeaderCell("倒计时", 1.8f)
                    }

                    HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)

                    // List
                    LazyColumn(
                        contentPadding = PaddingValues(bottom = 8.dp)
                    ) {
                        items(holidays) { holiday ->
                            HolidayRow(holiday)
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
        modifier = Modifier
            .fillMaxWidth()
            .background(color)
            .padding(vertical = 8.dp, horizontal = 16.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        Icon(icon, contentDescription = null, tint = contentColor, modifier = Modifier.size(16.dp))
        Spacer(modifier = Modifier.width(8.dp))
        Text(text = status, style = MaterialTheme.typography.labelMedium, color = contentColor)
    }
}

@Composable
fun RowScope.HeaderCell(text: String, weight: Float) {
    Text(
        text = text,
        style = MaterialTheme.typography.labelMedium.copy(fontWeight = FontWeight.Bold),
        modifier = Modifier.weight(weight),
        textAlign = TextAlign.Center,
        color = MaterialTheme.colorScheme.onPrimaryContainer
    )
}

@Composable
fun HolidayRow(holiday: Holiday) {
    val now = LocalDate.now()
    val isPast = holiday.endDate.isBefore(now)
    val isOngoing = !now.isBefore(holiday.startDate) && !now.isAfter(holiday.endDate)
    
    val textColor = when {
        isPast -> MaterialTheme.colorScheme.onSurface.copy(alpha = 0.4f)
        isOngoing -> MaterialTheme.colorScheme.primary
        else -> MaterialTheme.colorScheme.onSurface
    }
    
    val rowBg = if (isOngoing) MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.15f) else Color.Transparent

    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(rowBg)
            .padding(vertical = 12.dp, horizontal = 8.dp),
        verticalAlignment = Alignment.CenterVertically
    ) {
        // Name
        Text(
            text = holiday.name, 
            modifier = Modifier.weight(1.5f), 
            textAlign = TextAlign.Center,
            color = textColor,
            style = MaterialTheme.typography.bodyMedium.copy(
                fontWeight = if (isOngoing) FontWeight.Bold else FontWeight.Normal
            ),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
        
        // Date Range
        val dateStr = if (holiday.startDate == holiday.endDate) {
            holiday.startDate.format(DateTimeFormatter.ofPattern("MM.dd"))
        } else {
            "${holiday.startDate.format(DateTimeFormatter.ofPattern("MM.dd"))}-${holiday.endDate.format(DateTimeFormatter.ofPattern("MM.dd"))}"
        }
        Text(
            text = dateStr, 
            modifier = Modifier.weight(2.4f), 
            textAlign = TextAlign.Center,
            style = MaterialTheme.typography.bodySmall,
            color = textColor,
            fontFamily = FontFamily.Monospace
        )
        
        // Stats
        val statsStyle = MaterialTheme.typography.bodyMedium
        Text(text = "${holiday.duration}", modifier = Modifier.weight(0.9f), textAlign = TextAlign.Center, style = statsStyle, color = textColor)
        Text(text = "${holiday.daysExclMakeup}", modifier = Modifier.weight(0.9f), textAlign = TextAlign.Center, style = statsStyle, color = textColor)
        Text(text = "${holiday.daysExclMakeupWeekend}", modifier = Modifier.weight(0.9f), textAlign = TextAlign.Center, style = statsStyle, color = textColor)
        
        // Countdown
        val countdownText = when {
            isPast -> "已结束"
            isOngoing -> "进行中"
            else -> "${ChronoUnit.DAYS.between(now, holiday.startDate)}天"
        }
        Text(
            text = countdownText, 
            modifier = Modifier.weight(1.8f), 
            textAlign = TextAlign.Center,
            color = if (isOngoing) MaterialTheme.colorScheme.primary else textColor,
            style = MaterialTheme.typography.bodyMedium.copy(fontWeight = if (isOngoing) FontWeight.Bold else FontWeight.Normal)
        )
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
        modifier = Modifier
            .fillMaxWidth()
            .padding(16.dp),
        elevation = CardDefaults.cardElevation(defaultElevation = 4.dp),
        colors = CardDefaults.elevatedCardColors(containerColor = MaterialTheme.colorScheme.surface)
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            // Timers Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                OffworkTimerItem(
                    label = "午休",
                    icon = Icons.Default.WbSunny,
                    timeStr = midTime,
                    onTimeChange = onMidTimeChange,
                    countdown = midCountdown,
                    modifier = Modifier.weight(1f)
                )
                Spacer(modifier = Modifier.width(16.dp))
                OffworkTimerItem(
                    label = "下班",
                    icon = Icons.Default.NightsStay,
                    timeStr = nightTime,
                    onTimeChange = onNightTimeChange,
                    countdown = nightCountdown,
                    modifier = Modifier.weight(1f)
                )
            }

            HorizontalDivider(modifier = Modifier.padding(vertical = 12.dp))
            
            // Stats Row
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.SpaceEvenly
            ) {
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
            Icon(icon, contentDescription = null, modifier = Modifier.size(16.dp), tint = MaterialTheme.colorScheme.primary)
            Spacer(modifier = Modifier.width(4.dp))
            Text(label, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
        }
        
        Spacer(modifier = Modifier.height(4.dp))
        
        OutlinedTextField(
            value = timeStr,
            onValueChange = onTimeChange,
            modifier = Modifier.width(80.dp).height(48.dp),
            textStyle = MaterialTheme.typography.bodyMedium.copy(textAlign = TextAlign.Center),
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
            singleLine = true,
            colors = OutlinedTextFieldDefaults.colors(
                focusedTextColor = MaterialTheme.colorScheme.onSurface,
                unfocusedTextColor = MaterialTheme.colorScheme.onSurface,
                unfocusedBorderColor = MaterialTheme.colorScheme.outline.copy(alpha = 0.5f)
            )
        )
        
        Spacer(modifier = Modifier.height(4.dp))
        
        Text(
            text = countdown,
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
        Text(text = value, style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold), color = MaterialTheme.colorScheme.onSurface)
        Text(text = label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.outline)
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
