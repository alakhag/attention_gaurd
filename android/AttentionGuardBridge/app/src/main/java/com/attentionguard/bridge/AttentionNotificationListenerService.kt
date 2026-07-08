package com.attentionguard.bridge

import android.app.Notification
import android.content.pm.PackageManager
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification

class AttentionNotificationListenerService : NotificationListenerService() {
    override fun onNotificationPosted(sbn: StatusBarNotification) {
        val extras = sbn.notification.extras

        val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString()
        val text = extras.getCharSequence(Notification.EXTRA_TEXT)?.toString()
        val bigText = extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString()
        val body = bigText ?: text

        if (title.isNullOrBlank() && body.isNullOrBlank()) return
        if (sbn.packageName == packageName) return

        val event = NotificationEvent(
            packageName = sbn.packageName,
            appName = appLabel(sbn.packageName),
            title = title,
            body = body,
            timestampMillis = sbn.postTime,
            notificationKey = sbn.key
        )

        BackendClient.postNotification(event)
    }

    private fun appLabel(pkg: String): String {
        return try {
            val appInfo = packageManager.getApplicationInfo(pkg, 0)
            packageManager.getApplicationLabel(appInfo).toString()
        } catch (_: PackageManager.NameNotFoundException) {
            pkg
        }
    }
}
