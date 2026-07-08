package com.attentionguard.os

import android.content.*

class AttentionActionReceiver: BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        when(intent.action){
            ACTION_DONE -> intent.getStringExtra(EXTRA_ATTENTION_ID)?.let { NotificationRenderer.cancelItem(context,it); BackendClient.resolve(context,it) }
            ACTION_LATER -> intent.getStringExtra(EXTRA_ATTENTION_ID)?.let { NotificationRenderer.cancelItem(context,it); BackendClient.dismiss(context,it) }
            ACTION_REFRESH -> { NotificationRenderer.showSyncing(context); BackendClient.refreshPhone(context) }
        }
    }
    companion object {
        const val ACTION_DONE="com.attentionguard.os.ACTION_DONE"
        const val ACTION_LATER="com.attentionguard.os.ACTION_LATER"
        const val ACTION_REFRESH="com.attentionguard.os.ACTION_REFRESH"
        const val EXTRA_ATTENTION_ID="attention_id"
    }
}
