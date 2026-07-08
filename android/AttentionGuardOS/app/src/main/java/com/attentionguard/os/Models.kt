package com.attentionguard.os
data class NotificationEvent(val packageName:String,val appName:String,val title:String?,val body:String?,val timestampMillis:Long,val notificationKey:String)
data class AttentionItem(val id:String,val title:String,val body:String,val source:String,val category:String,val urgency:String,val reason:String,val recommendedAction:String)
