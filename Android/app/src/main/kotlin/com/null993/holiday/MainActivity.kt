package com.null993.holiday

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.core.content.ContextCompat
import com.null993.holiday.data.PreferencesStore
import com.null993.holiday.ui.MainScreen
import com.null993.holiday.service.CountdownService

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        PreferencesStore.init(applicationContext)

        // Start foreground service safely
        val svc = Intent(this, CountdownService::class.java)
        ContextCompat.startForegroundService(this, svc)

        setContent {
            MainScreen()
        }
    }
}
