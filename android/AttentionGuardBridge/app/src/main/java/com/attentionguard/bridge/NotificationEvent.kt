package com.attentionguard.bridge

data class NotificationEvent(
    val packageName: String,
    val appName: String,
    val title: String?,
    val body: String?,
    val timestampMillis: Long,
    val notificationKey: String
)
