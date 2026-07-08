package com.attentionguard.os

import android.content.Context
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.time.Instant

object BackendClient {
    // TODO: set exact Render URL
    private const val BACKEND_URL = "https://attention-gaurd.onrender.com"
    private val client = OkHttpClient()
    private val jsonType = "application/json; charset=utf-8".toMediaType()

    fun postNotification(context: Context, event: NotificationEvent) {
        Thread {
            try {
                val bodyJson = JSONObject()
                    .put("device_id","android-phone").put("package_name",event.packageName)
                    .put("app_name",event.appName).put("title",event.title).put("body",event.body)
                    .put("notification_key",event.notificationKey).put("timestamp", Instant.ofEpochMilli(event.timestampMillis).toString())
                client.newCall(Request.Builder().url("$BACKEND_URL/android/notifications").post(bodyJson.toString().toRequestBody(jsonType)).build()).execute().close()
                refreshPhone(context)
            } catch (_: Exception) { NotificationRenderer.showSyncError(context) }
        }.start()
    }

    fun refreshPhone(context: Context) {
        Thread {
            try {
                val phone = getJson("/phone")
                val arr = phone.optJSONArray("items")
                val items = mutableListOf<AttentionItem>()
                if (arr != null) for (i in 0 until arr.length()) {
                    val o = arr.getJSONObject(i)
                    items.add(AttentionItem(
                        id=o.optString("id"), title=o.optString("title"), body=o.optString("body"),
                        source=o.optString("source"), category=o.optString("category"), urgency=o.optString("urgency"),
                        reason=o.optString("reason"), recommendedAction=o.optString("recommended_action")
                    ))
                }
                NotificationRenderer.render(context, phone.optString("summary","Status unavailable"), items)
            } catch (_: Exception) { NotificationRenderer.showSyncError(context) }
        }.start()
    }

    fun resolve(context: Context, id: String) = postAction(context, "/attention-items/$id/resolve")
    fun dismiss(context: Context, id: String) = postAction(context, "/attention-items/$id/dismiss")
    fun syncGoogle(context: Context) = postAction(context, "/sync/google")

    private fun postAction(context: Context, path: String) {
        Thread {
            try {
                client.newCall(Request.Builder().url("$BACKEND_URL$path").post("{}".toRequestBody(jsonType)).build()).execute().close()
                refreshPhone(context)
            } catch (_: Exception) { NotificationRenderer.showSyncError(context) }
        }.start()
    }

    private fun getJson(path: String): JSONObject {
        client.newCall(Request.Builder().url("$BACKEND_URL$path").get().build()).execute().use {
            val raw = it.body?.string()
            if (!it.isSuccessful || raw.isNullOrBlank()) error("failed")
            return JSONObject(raw)
        }
    }
}
