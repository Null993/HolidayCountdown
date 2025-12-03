package com.null993.holiday.data

import android.util.Log
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import okhttp3.OkHttpClient
import okhttp3.Request
import java.time.LocalDate
import java.time.format.DateTimeFormatter
import java.util.concurrent.TimeUnit

object IcsParser {
    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .build()

    suspend fun loadHolidaysSuspend(url: String): List<Holiday> {
        val content = downloadIcsContent(url)
        return parseIcsContent(content)
    }

    suspend fun downloadIcsContent(url: String): String = withContext(Dispatchers.IO) {
        try {
            val req = Request.Builder().url(url).build()
            client.newCall(req).execute().use { resp ->
                if (!resp.isSuccessful) {
                    Log.e("IcsParser", "Network error: ${resp.code}")
                    throw Exception("网络错误: ${resp.code}")
                }
                val body = resp.body?.string() ?: ""
                Log.d("IcsParser", "Downloaded ${body.length} chars")
                body
            }
        } catch (e: Exception) {
            Log.e("IcsParser", "Download failed: ${e.message}", e)
            throw e
        }
    }
    
    fun parseIcsContent(content: String): List<Holiday> {
        return parseIcs(content)
    }

    private fun parseIcs(text: String): List<Holiday> {
        val lines = text.lines()
        val result = mutableListOf<Holiday>()

        var insideEvent = false
        var name = ""
        var dtstartStr = ""
        var dtendStr = ""

        for (line in lines) {
            val trimmed = line.trim()
            if (trimmed == "BEGIN:VEVENT") {
                insideEvent = true
                name = ""
                dtstartStr = ""
                dtendStr = ""
                continue
            }
            if (trimmed == "END:VEVENT") {
                if (insideEvent && name.isNotEmpty() && dtstartStr.isNotEmpty()) {
                    val start = parseDate(dtstartStr)
                    val end = if (dtendStr.isNotEmpty()) parseDate(dtendStr) else null

                    if (start != null) {

                        var finalEnd = when {
                            end == null -> start
                            end.isEqual(start) -> start
                            else -> end.minusDays(1)
                        }

                        if (finalEnd.isBefore(start)) {
                            finalEnd = start
                        }
                        result.add(Holiday(name, start, finalEnd))
                    } else {
                        Log.w("IcsParser", "Failed to parse date: $dtstartStr")
                    }
                }
                insideEvent = false
                continue
            }

            if (insideEvent) {
                when {
                    trimmed.startsWith("SUMMARY:") -> name = trimmed.removePrefix("SUMMARY:")
                    trimmed.startsWith("DTSTART") -> dtstartStr = extractDateValue(trimmed)
                    trimmed.startsWith("DTEND") -> dtendStr = extractDateValue(trimmed)
                }
            }
        }
        
        Log.d("IcsParser", "Parsed ${result.size} holidays")
        return result
    }

    private fun extractDateValue(line: String): String {
        val parts = line.split(":", limit = 2)
        return if (parts.size == 2) parts[1] else ""
    }

    private fun parseDate(s: String): LocalDate? {
        return try {
            val raw = s.trim()
            when {
                raw.length >= 8 -> LocalDate.parse(raw.substring(0, 8), DateTimeFormatter.ofPattern("yyyyMMdd"))
                else -> null
            }
        } catch (e: Exception) {
            Log.e("IcsParser", "Date parse error: $s", e)
            null
        }
    }
}
