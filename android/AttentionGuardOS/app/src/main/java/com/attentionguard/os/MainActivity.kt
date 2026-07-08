package com.attentionguard.os

import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.*
import android.provider.Settings
import android.view.Gravity
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.core.app.ActivityCompat
import androidx.core.content.ContextCompat
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

class MainActivity : AppCompatActivity() {
    private val backendUrl = "https://attention-gaurd.onrender.com"
    private val client = OkHttpClient()
    private val jsonType = "application/json; charset=utf-8".toMediaType()

    private lateinit var root: LinearLayout
    private lateinit var summaryText: TextView
    private lateinit var listenerStatusText: TextView
    private lateinit var itemsBox: LinearLayout

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        requestNotificationPermissionIfNeeded()

        root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(40, 40, 40, 40)
        }

        summaryText = TextView(this).apply {
            text = "Checking…"
            textSize = 26f
            gravity = Gravity.CENTER_HORIZONTAL
        }

        listenerStatusText = TextView(this).apply {
            text = ""
            textSize = 14f
            gravity = Gravity.CENTER_HORIZONTAL
        }

        val notificationAccessButton = Button(this).apply {
            text = "Open Notification Access Settings"
            setOnClickListener {
                startActivity(Intent(Settings.ACTION_NOTIFICATION_LISTENER_SETTINGS))
            }
        }

        val refreshButton = Button(this).apply {
            text = "Refresh + Scan Current Notifications"
            setOnClickListener {
                refreshAndScan()
            }
        }

        val syncButton = Button(this).apply {
            text = "Sync Gmail + Calendar"
            setOnClickListener {
                syncGoogle()
            }
        }

        itemsBox = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }

        root.addView(summaryText)
        root.addView(listenerStatusText)
        root.addView(notificationAccessButton)
        root.addView(refreshButton)
        root.addView(syncButton)
        root.addView(itemsBox)

        setContentView(root)

        NotificationRenderer.showSyncing(this)
        refreshAndScan()
    }

    private fun refreshAndScan() {
        summaryText.text = "Scanning current notifications…"

        val listenerWasLive =
            AttentionNotificationListenerService.scanActiveNotificationsFromApp(this)

        listenerStatusText.text = if (listenerWasLive) {
            "Notification listener: connected"
        } else {
            "Notification listener not connected. Enable Notification Access."
        }

        // Give scan POSTs a short moment to hit backend, then load /phone.
        Handler(Looper.getMainLooper()).postDelayed({
            loadPhoneState()
        }, 700)
    }

    private fun loadPhoneState() {
        Thread {
            try {
                val request = Request.Builder()
                    .url("$backendUrl/phone")
                    .get()
                    .build()

                client.newCall(request).execute().use { response ->
                    val raw = response.body?.string()
                    if (!response.isSuccessful || raw.isNullOrBlank()) {
                        throw RuntimeException("Failed")
                    }

                    val json = JSONObject(raw)

                    runOnUiThread {
                        renderPhoneState(json)
                    }
                }
            } catch (_: Exception) {
                runOnUiThread {
                    summaryText.text = "Could not check"
                    itemsBox.removeAllViews()
                    itemsBox.addView(TextView(this).apply {
                        text = "Backend unavailable or sync failed."
                        textSize = 16f
                    })
                }
            }
        }.start()
    }

    private fun renderPhoneState(json: JSONObject) {
        val summary = json.optString("summary", "Status unavailable")
        val items = json.optJSONArray("items")

        summaryText.text = summary
        itemsBox.removeAllViews()

        if (items == null || items.length() == 0) {
            itemsBox.addView(TextView(this).apply {
                text = "\n✓ Nothing active"
                textSize = 20f
                gravity = Gravity.CENTER_HORIZONTAL
            })
            return
        }

        for (i in 0 until items.length()) {
            val item = items.getJSONObject(i)
            val id = item.optString("id")
            val title = item.optString("title", "Attention item")
            val body = item.optString("body", "")
            val reason = item.optString("reason", "")
            val action = item.optString("recommended_action", "Review")

            val card = LinearLayout(this).apply {
                orientation = LinearLayout.VERTICAL
                setPadding(0, 28, 0, 28)
            }

            card.addView(TextView(this).apply {
                text = title
                textSize = 22f
            })

            card.addView(TextView(this).apply {
                text = body
                textSize = 16f
            })

            card.addView(TextView(this).apply {
                text = "$reason\nAction: $action"
                textSize = 14f
            })

            val row = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
            }

            row.addView(Button(this).apply {
                text = "Done"
                setOnClickListener {
                    resolveItem(id)
                }
            })

            row.addView(Button(this).apply {
                text = "Later"
                setOnClickListener {
                    dismissItem(id)
                }
            })

            card.addView(row)
            itemsBox.addView(card)
        }
    }

    private fun resolveItem(id: String) {
        postAction("/attention-items/$id/resolve")
    }

    private fun dismissItem(id: String) {
        postAction("/attention-items/$id/dismiss")
    }

    private fun syncGoogle() {
        summaryText.text = "Syncing Gmail + Calendar…"
        postAction("/sync/google")
    }

    private fun postAction(path: String) {
        Thread {
            try {
                val request = Request.Builder()
                    .url("$backendUrl$path")
                    .post("{}".toRequestBody(jsonType))
                    .build()

                client.newCall(request).execute().close()

                runOnUiThread {
                    refreshAndScan()
                }
            } catch (_: Exception) {
                runOnUiThread {
                    summaryText.text = "Action failed"
                }
            }
        }.start()
    }

    private fun requestNotificationPermissionIfNeeded() {
        if (Build.VERSION.SDK_INT >= 33) {
            val granted = ContextCompat.checkSelfPermission(
                this,
                Manifest.permission.POST_NOTIFICATIONS
            ) == PackageManager.PERMISSION_GRANTED

            if (!granted) {
                ActivityCompat.requestPermissions(
                    this,
                    arrayOf(Manifest.permission.POST_NOTIFICATIONS),
                    1001
                )
            }
        }
    }
}
