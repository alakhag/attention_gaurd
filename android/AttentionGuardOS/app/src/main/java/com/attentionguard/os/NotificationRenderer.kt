package com.attentionguard.os

import android.app.*
import android.content.*
import android.os.Build
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import kotlin.math.abs

object NotificationRenderer {
    private const val SUMMARY_CHANNEL = "attention_summary"
    private const val ITEM_CHANNEL = "attention_items"
    private const val SUMMARY_ID = 108

    fun render(context: Context, summary: String, items: List<AttentionItem>) {
        createChannels(context)
        showSummary(context, summary, items)
        items.take(5).forEach { showItem(context, it) }
    }

    fun showSyncing(context: Context) = showRaw(context, "Checking attention status…", "Attention Guard is checking.")
    fun showSyncError(context: Context) = showRaw(context, "Could not check everything", "Open app/dashboard to verify.")

    private fun showSummary(context: Context, summary: String, items: List<AttentionItem>) {
        val style = NotificationCompat.InboxStyle()
        if (items.isEmpty()) style.addLine("✓ Nothing active")
        else items.take(5).forEach { style.addLine("${it.title}: ${it.recommendedAction}") }
        val refresh = pending(context, AttentionActionReceiver.ACTION_REFRESH, null, 900)
        val n = NotificationCompat.Builder(context, SUMMARY_CHANNEL)
            .setSmallIcon(android.R.drawable.ic_dialog_info).setContentTitle("Attention Guard").setContentText(summary)
            .setStyle(style).setOngoing(true).setOnlyAlertOnce(true).setVisibility(NotificationCompat.VISIBILITY_PUBLIC)
            .setPriority(NotificationCompat.PRIORITY_DEFAULT).addAction(android.R.drawable.ic_popup_sync,"Refresh",refresh).build()
        notify(context, SUMMARY_ID, n)
    }

    private fun showRaw(context: Context, text: String, detail: String) {
        createChannels(context)
        val refresh = pending(context, AttentionActionReceiver.ACTION_REFRESH, null, 901)
        val n = NotificationCompat.Builder(context, SUMMARY_CHANNEL)
            .setSmallIcon(android.R.drawable.ic_dialog_info).setContentTitle("Attention Guard").setContentText(text)
            .setStyle(NotificationCompat.BigTextStyle().bigText(detail)).setOngoing(true).setOnlyAlertOnce(true)
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC).setPriority(NotificationCompat.PRIORITY_DEFAULT)
            .addAction(android.R.drawable.ic_popup_sync,"Refresh",refresh).build()
        notify(context, SUMMARY_ID, n)
    }

    private fun showItem(context: Context, item: AttentionItem) {
        val done = pending(context, AttentionActionReceiver.ACTION_DONE, item.id, abs((item.id+"d").hashCode()))
        val later = pending(context, AttentionActionReceiver.ACTION_LATER, item.id, abs((item.id+"l").hashCode()))
        val n = NotificationCompat.Builder(context, ITEM_CHANNEL)
            .setSmallIcon(android.R.drawable.ic_dialog_info).setContentTitle(item.title.ifBlank{"Attention item"})
            .setContentText(item.body.ifBlank{item.reason}).setStyle(NotificationCompat.BigTextStyle().bigText("${item.body}\n${item.reason}\nAction: ${item.recommendedAction}"))
            .setVisibility(NotificationCompat.VISIBILITY_PUBLIC).setPriority(NotificationCompat.PRIORITY_DEFAULT).setOnlyAlertOnce(true)
            .addAction(android.R.drawable.checkbox_on_background,"Done",done)
            .addAction(android.R.drawable.ic_menu_close_clear_cancel,"Later",later).build()
        notify(context, itemId(item.id), n)
    }

    fun cancelItem(context: Context, id: String) = NotificationManagerCompat.from(context).cancel(itemId(id))

    private fun pending(context: Context, action:String, id:String?, request:Int): PendingIntent {
        val intent = Intent(context, AttentionActionReceiver::class.java).apply { this.action=action; if(id!=null) putExtra(AttentionActionReceiver.EXTRA_ATTENTION_ID,id) }
        return PendingIntent.getBroadcast(context, request, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
    }

    private fun itemId(id:String)=10000+abs(id.hashCode()%50000)
    private fun notify(context:Context,id:Int,n:Notification){ try{ NotificationManagerCompat.from(context).notify(id,n) }catch(_:SecurityException){} }

    private fun createChannels(context: Context) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val m = context.getSystemService(Context.NOTIFICATION_SERVICE) as NotificationManager
            m.createNotificationChannel(NotificationChannel(SUMMARY_CHANNEL,"Attention Guard Status",NotificationManager.IMPORTANCE_DEFAULT).apply{lockscreenVisibility=Notification.VISIBILITY_PUBLIC})
            m.createNotificationChannel(NotificationChannel(ITEM_CHANNEL,"Attention Items",NotificationManager.IMPORTANCE_DEFAULT).apply{lockscreenVisibility=Notification.VISIBILITY_PUBLIC})
        }
    }
}
