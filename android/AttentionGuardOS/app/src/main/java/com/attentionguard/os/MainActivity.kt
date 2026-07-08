package com.attentionguard.os

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.*
import android.provider.Settings
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat

class MainActivity: AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        requestNotificationPermission()
        NotificationRenderer.showSyncing(this)
        BackendClient.refreshPhone(this)
        val layout=LinearLayout(this).apply{orientation=LinearLayout.VERTICAL; setPadding(48,48,48,48)}
        val title=TextView(this).apply{text="Attention OS\n\nPhone sensor + status notification.\n\nUse Galaxy Watch app for glance."; textSize=18f}
        val access=Button(this).apply{text="Open Notification Access Settings"; setOnClickListener{startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))}}
        val refresh=Button(this).apply{text="Refresh Attention Guard"; setOnClickListener{NotificationRenderer.showSyncing(this@MainActivity); BackendClient.refreshPhone(this@MainActivity)}}
        val sync=Button(this).apply{text="Sync Gmail + Calendar"; setOnClickListener{NotificationRenderer.showSyncing(this@MainActivity); BackendClient.syncGoogle(this@MainActivity)}}
        layout.addView(title); layout.addView(access); layout.addView(refresh); layout.addView(sync); setContentView(layout)
    }
    private fun requestNotificationPermission(){
        if(Build.VERSION.SDK_INT>=33 && ContextCompat.checkSelfPermission(this,Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED){
            ActivityCompat.requestPermissions(this,arrayOf(Manifest.permission.POST_NOTIFICATIONS),1001)
        }
    }
}
