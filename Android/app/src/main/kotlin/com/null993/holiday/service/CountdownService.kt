package com.null993.holiday.service

import android.Manifest
import android.app.*
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.content.ContextCompat
import com.null993.holiday.MainActivity
import com.null993.holiday.data.CountdownRepository

class CountdownService : Service() {

    private val handler = Handler(Looper.getMainLooper())
    private lateinit var notificationManager: NotificationManager
    private val channelId = "holiday_countdown_channel"

    override fun onCreate() {
        super.onCreate()
        notificationManager = getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
        createChannel()
        // startForeground does not require POST_NOTIFICATIONS permission check for the initial call,
        // but subsequent updates might trigger lint warnings.
        startForeground(1, buildNotification("加载中..."))
        startTimerLoop()
    }

    private fun createChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(channelId, "假期倒计时", NotificationManager.IMPORTANCE_LOW)
            notificationManager.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(text: String): Notification {
        val intent = Intent(this, MainActivity::class.java)
        val pending = PendingIntent.getActivity(this, 0, intent, PendingIntent.FLAG_IMMUTABLE)

        return NotificationCompat.Builder(this, channelId)
            .setContentTitle("假期倒计时")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_lock_idle_alarm)
            .setContentIntent(pending)
            .setOnlyAlertOnce(true) 
            .setForegroundServiceBehavior(NotificationCompat.FOREGROUND_SERVICE_IMMEDIATE)
            .build()
    }

    private fun startTimerLoop() {
        handler.post(object : Runnable {
            override fun run() {
                val text = CountdownRepository.getCountdownText()
                
                // Check permission for Android 13+ before notifying
                if (Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU || 
                    ContextCompat.checkSelfPermission(this@CountdownService, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) {
                    notificationManager.notify(1, buildNotification(text))
                }
                
                handler.postDelayed(this, 1000)
            }
        })
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        handler.removeCallbacksAndMessages(null)
        super.onDestroy()
    }
}
