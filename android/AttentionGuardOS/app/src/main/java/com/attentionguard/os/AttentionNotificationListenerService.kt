package com.attentionguard.os

import android.app.Notification
import android.content.pm.PackageManager
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification

class AttentionNotificationListenerService: NotificationListenerService() {
    private val recent = mutableMapOf<String, Pair<Long,String>>()
    override fun onListenerConnected(){ super.onListenerConnected(); BackendClient.refreshPhone(this) }

    override fun onNotificationPosted(sbn: StatusBarNotification) {
        val extras=sbn.notification.extras
        val title=extras.getCharSequence(Notification.EXTRA_TITLE)?.toString()
        val text=extras.getCharSequence(Notification.EXTRA_TEXT)?.toString()
        val big=extras.getCharSequence(Notification.EXTRA_BIG_TEXT)?.toString()
        val body=big ?: text
        if(title.isNullOrBlank() && body.isNullOrBlank()) return
        if(sbn.packageName==packageName) return
        val payload="${sbn.packageName}|$title|$body"; val now=System.currentTimeMillis()
        val last=recent[sbn.key]
        if(last!=null && now-last.first<2500 && last.second==payload) return
        recent[sbn.key]=now to payload
        val event=NotificationEvent(sbn.packageName, appLabel(sbn.packageName), title, body, sbn.postTime, sbn.key)
        BackendClient.postNotification(this,event)
    }

    private fun appLabel(pkg:String):String = try {
        val info=packageManager.getApplicationInfo(pkg,0); packageManager.getApplicationLabel(info).toString()
    } catch(_:PackageManager.NameNotFoundException){ pkg }
}
