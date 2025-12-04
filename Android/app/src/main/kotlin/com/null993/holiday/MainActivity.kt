package com.null993.holiday

import android.content.Intent
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.SystemBarStyle
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.core.content.ContextCompat
import androidx.core.view.WindowCompat
import androidx.core.view.WindowInsetsControllerCompat
import com.null993.holiday.data.PreferencesStore
import com.null993.holiday.ui.MainScreen
import com.null993.holiday.service.CountdownService


class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        PreferencesStore.init(applicationContext)
        WindowCompat.setDecorFitsSystemWindows(window, false)
        // Start foreground service safely
        val svc = Intent(this, CountdownService::class.java)
        ContextCompat.startForegroundService(this, svc)

        val controller = WindowInsetsControllerCompat(window, window.decorView)

        // 若状态栏背景是亮色，则使用深色图标
        controller.isAppearanceLightStatusBars = true
        // 导航栏同理
        controller.isAppearanceLightNavigationBars = true

        setContent {
            enableEdgeToEdge(
                statusBarStyle = SystemBarStyle.auto(
                    lightScrim = android.graphics.Color.TRANSPARENT,   // 把遮罩设为透明
                    darkScrim = android.graphics.Color.TRANSPARENT
                ),
                navigationBarStyle = SystemBarStyle.auto(
                    lightScrim = android.graphics.Color.TRANSPARENT,
                    darkScrim = android.graphics.Color.TRANSPARENT
                )
            )



            MainScreen()
        }
    }
}
