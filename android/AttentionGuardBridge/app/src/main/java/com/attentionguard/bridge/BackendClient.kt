package com.attentionguard.bridge

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.time.Instant

object BackendClient {
    // Replace with deployed URL, e.g. https://attention-guard-realtime.onrender.com
    private const val BACKEND_URL = "http://10.0.2.2:8000"
    private val client = OkHttpClient()
    private val jsonType = "application/json; charset=utf-8".toMediaType()

    fun postNotification(event: NotificationEvent) {
        Thread {
            try {
                val bodyJson = JSONObject()
                    .put("device_id", "android-phone")
                    .put("package_name", event.packageName)
                    .put("app_name", event.appName)
                    .put("title", event.title)
                    .put("body", event.body)
                    .put("notification_key", event.notificationKey)
                    .put("timestamp", Instant.ofEpochMilli(event.timestampMillis).toString())

                val request = Request.Builder()
                    .url("$BACKEND_URL/android/notifications")
                    .post(bodyJson.toString().toRequestBody(jsonType))
                    .build()

                client.newCall(request).execute().use { _ -> }
            } catch (_: Exception) {
                // Prototype: ignore network failure.
            }
        }.start()
    }
}
