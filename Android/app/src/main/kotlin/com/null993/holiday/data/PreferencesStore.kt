package com.null993.holiday.data

import android.content.Context
import android.content.SharedPreferences
import java.io.File

object PreferencesStore {
    private const val NAME = "holiday_prefs"
    private const val KEY_ICS = "ics_url"
    private const val KEY_OFFWORK_MID = "offwork_mid"
    private const val KEY_OFFWORK_NIGHT = "offwork_night"
    
    private const val CACHE_FILE = "holidays_cache.ics"
    private const val ASSET_FILE = "holidayCal.ics"

    private var prefs: SharedPreferences? = null
    private var appContext: Context? = null

    fun init(context: Context) {
        appContext = context.applicationContext
        prefs = context.getSharedPreferences(NAME, Context.MODE_PRIVATE)
    }

    fun setIcsUrl(url: String) { prefs?.edit()?.putString(KEY_ICS, url)?.apply() }
    fun getIcsUrl(): String? = prefs?.getString(KEY_ICS, null)
    
    fun setOffworkMid(time: String) { prefs?.edit()?.putString(KEY_OFFWORK_MID, time)?.apply() }
    fun getOffworkMid(): String = prefs?.getString(KEY_OFFWORK_MID, "12:00") ?: "12:00"
    
    fun setOffworkNight(time: String) { prefs?.edit()?.putString(KEY_OFFWORK_NIGHT, time)?.apply() }
    fun getOffworkNight(): String = prefs?.getString(KEY_OFFWORK_NIGHT, "18:00") ?: "18:00"

    fun saveIcsCache(content: String) {
        try {
            appContext?.openFileOutput(CACHE_FILE, Context.MODE_PRIVATE)?.use {
                it.write(content.toByteArray())
            }
        } catch (e: Exception) {
            e.printStackTrace()
        }
    }

    fun loadIcsCache(): String? {
        return try {
            appContext?.openFileInput(CACHE_FILE)?.bufferedReader()?.use {
                it.readText()
            }
        } catch (e: Exception) {
            null
        }
    }
    
    fun loadIcsFromAssets(): String? {
        return try {
            appContext?.assets?.open(ASSET_FILE)?.bufferedReader()?.use {
                it.readText()
            }
        } catch (e: Exception) {
            null
        }
    }
    
    fun hasCache(): Boolean {
        val context = appContext ?: return false
        val file = File(context.filesDir, CACHE_FILE)
        return file.exists()
    }
}
