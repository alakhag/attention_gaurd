package com.attentionguard.bridge

import android.content.Intent
import android.os.Bundle
import android.provider.Settings
import android.widget.Button
import android.widget.LinearLayout
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val layout = LinearLayout(this)
        layout.orientation = LinearLayout.VERTICAL
        layout.setPadding(48, 48, 48, 48)

        val title = TextView(this)
        title.text = "Attention Guard Bridge\n\n1. Set BACKEND_URL in BackendClient.kt\n2. Grant notification access\n3. Notifications will POST to backend"
        title.textSize = 18f

        val button = Button(this)
        button.text = "Open Notification Access Settings"
        button.setOnClickListener {
            startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
        }

        layout.addView(title)
        layout.addView(button)
        setContentView(layout)
    }
}
