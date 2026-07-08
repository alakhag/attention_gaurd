package com.attentionguard.os

import android.app.Notification
import android.content.Context
import android.content.pm.PackageManager
import android.os.Handler
import android.os.Looper
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import java.lang.ref.WeakReference

class AttentionNotificationListenerService : NotificationListenerService() {
    private val recent = mutableMapOf<String, Pair<Long, String>>()
    private val handler = Handler(Looper.getMainLooper())
    private val scanEveryMs = 60_000L

    private val periodicScan = object : Runnable {
        override fun run() {
            scanActiveNotificationsNow()
            handler.postDelayed(this, scanEveryMs)
        }
    }

    override fun onCreate() {
        super.onCreate()
        activeService = WeakReference(this)
    }

    override fun onDestroy() {
        handler.removeCallbacks(periodicScan)
        activeService = null
        super.onDestroy()
    }

    override fun onListenerConnected() {
        super.onListenerConnected()
        activeService = WeakReference(this)

        // Important: when notification access connects, import existing active notifications too.
        scanActiveNotificationsNow()

        // Keep backend roughly aligned with current notification shade.
        handler.removeCallbacks(periodicScan)
        handler.postDelayed(periodicScan, scanEveryMs)

        BackendClient.refreshPhone(this)
    }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        sendStatusBarNotification(sbn)
    }

    fun scanActiveNotificationsNow() {
        try {
            activeNotifications?.forEach { sbn ->
                sendStatusBarNotification(sbn, force = true)
            }
            BackendClient.refreshPhone(this)
        } catch (_: Exception) {
            // Notification access may not be enabled yet.
        }
    }

    private fun sendStatusBarNotification(
        sbn: StatusBarNotification,
        force: Boolean = false
    ) {
        val extras = sbn.notification.extras

        val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString()
        val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString()
        val bigText = extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString()
        val subText = extras.getCharSequence(Notification.EXTRA_SUB_TEXT)?.toString()
        val body = bigText ?: text ?: subText

        if (title.isNullOrBlank() && body.isNullOrBlank()) return
        if (sbn.packageName == packageName) return

        val payload = "${sbn.packageName}|$title|$body"
        val now = System.currentTimeMillis()
        val last = recent[sbn.key]

        // Normal live notification callbacks get debounced.
        // Manual active shade scans force-send so backend can recover after restart/redeploy.
        if (!force && last != null && now - last.first < 2500 && last.second == payload) return

        recent[sbn.key] = now to payload
        cleanupRecent(now)

        val event = NotificationEvent(
            packageName = sbn.packageName,
            appName = appLabel(sbn.packageName),
            title = title,
            body = body,
            timestampMillis = sbn.postTime,
            notificationKey = sbn.key
        )

        BackendClient.postNotification(this, event)
    }

    private fun cleanupRecent(now: Long) {
        val iterator = recent.iterator()
        while (iterator.hasNext()) {
            val entry = iterator.next()
            if (now - entry.value.first > 120_000L) {
                iterator.remove()
            }
        }
    }

    private fun appLabel(pkg: String): String {
        return try {
            val info = packageManager.getApplicationInfo(pkg, 0)
            packageManager.getApplicationLabel(info).toString()
        } catch (_: PackageManager.NameNotFoundException) {
            pkg
        }
    }

    companion object {
        private var activeService: WeakReference<AttentionNotificationListenerService>? = null

        fun scanActiveNotificationsFromApp(context: Context): Boolean {
            val service = activeService?.get()
            return if (service != null) {
                service.scanActiveNotificationsNow()
                true
            } else {
                // Listener is not currently bound. Still refresh backend so UI doesn't hang.
                BackendClient.refreshPhone(context)
                false
            }
        }
    }
}
