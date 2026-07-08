package com.attentionguard.wear

import android.app.PendingIntent
import android.content.Intent
import androidx.wear.watchface.complications.data.ComplicationData
import androidx.wear.watchface.complications.data.ComplicationType
import androidx.wear.watchface.complications.data.LongTextComplicationData
import androidx.wear.watchface.complications.data.PlainComplicationText
import androidx.wear.watchface.complications.data.ShortTextComplicationData
import androidx.wear.watchface.complications.datasource.ComplicationDataSourceService
import androidx.wear.watchface.complications.datasource.ComplicationRequest
import org.json.JSONObject

class AttentionComplicationDataSourceService : ComplicationDataSourceService() {

    override fun onComplicationRequest(
        request: ComplicationRequest,
        listener: ComplicationRequestListener
    ) {
        Thread {
            val data = try {
                val payload = WearBackendClient.fetchPhone()
                buildComplicationData(request.complicationType, payload)
            } catch (_: Exception) {
                buildFallbackData(request.complicationType)
            }

            listener.onComplicationData(data)
        }.start()
    }

    override fun getPreviewData(type: ComplicationType): ComplicationData {
        return when (type) {
            ComplicationType.LONG_TEXT -> buildLongData(
                text = "Nothing important missed",
                title = "Attention Guard",
                contentDescription = "Attention Guard clear"
            )
            else -> buildShortData(
                text = "Clear",
                title = "✓",
                contentDescription = "Attention Guard clear"
            )
        }
    }

    private fun buildComplicationData(type: ComplicationType, payload: JSONObject): ComplicationData {
        val count = payload.optInt("attention_count", 0)
        val summary = payload.optString("summary", "Attention Guard")
        val items = payload.optJSONArray("items")
        val firstTitle = if (items != null && items.length() > 0) {
            items.optJSONObject(0)?.optString("title", "Attention")
        } else {
            null
        }

        return if (count <= 0) {
            when (type) {
                ComplicationType.LONG_TEXT -> buildLongData(
                    text = "Nothing important missed",
                    title = "Attention Guard",
                    contentDescription = "Attention Guard: nothing important missed"
                )
                else -> buildShortData(
                    text = "Clear",
                    title = "✓",
                    contentDescription = "Attention Guard clear"
                )
            }
        } else {
            when (type) {
                ComplicationType.LONG_TEXT -> buildLongData(
                    text = summary,
                    title = firstTitle ?: "Attention Guard",
                    contentDescription = "Attention Guard: $summary"
                )
                else -> buildShortData(
                    text = count.toString(),
                    title = "Attention",
                    contentDescription = "Attention Guard: $summary"
                )
            }
        }
    }

    private fun buildFallbackData(type: ComplicationType): ComplicationData {
        return when (type) {
            ComplicationType.LONG_TEXT -> buildLongData(
                text = "Could not check",
                title = "Attention Guard",
                contentDescription = "Attention Guard could not check"
            )
            else -> buildShortData(
                text = "Check",
                title = "!",
                contentDescription = "Attention Guard could not check"
            )
        }
    }

    private fun buildShortData(
        text: String,
        title: String,
        contentDescription: String
    ): ComplicationData {
        return ShortTextComplicationData.Builder(
            text = PlainComplicationText.Builder(text).build(),
            contentDescription = PlainComplicationText.Builder(contentDescription).build()
        )
            .setTitle(PlainComplicationText.Builder(title).build())
            .setTapAction(openAppPendingIntent())
            .build()
    }

    private fun buildLongData(
        text: String,
        title: String,
        contentDescription: String
    ): ComplicationData {
        return LongTextComplicationData.Builder(
            text = PlainComplicationText.Builder(text).build(),
            contentDescription = PlainComplicationText.Builder(contentDescription).build()
        )
            .setTitle(PlainComplicationText.Builder(title).build())
            .setTapAction(openAppPendingIntent())
            .build()
    }

    private fun openAppPendingIntent(): PendingIntent {
        val intent = Intent(this, MainActivity::class.java)
        return PendingIntent.getActivity(
            this,
            108,
            intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
    }
}
