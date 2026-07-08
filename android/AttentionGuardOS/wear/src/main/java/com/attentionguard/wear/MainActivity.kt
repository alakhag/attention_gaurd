package com.attentionguard.wear

import android.app.Activity
import android.os.Bundle
import android.graphics.Color
import android.view.Gravity
import android.widget.*
import org.json.JSONObject

class MainActivity : Activity() {
    private lateinit var root: LinearLayout
    private var firstId: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(18, 18, 18, 18)
            setBackgroundColor(Color.BLACK)
        }

        setContentView(root)
        renderLoading()
        refresh()
    }

    private fun renderLoading() {
        root.removeAllViews()
        root.addView(text("🛡", 34f))
        root.addView(text("Checking…", 18f))
    }

    private fun refresh() {
        Thread {
            try {
                val payload = WearBackendClient.fetchPhone()
                runOnUiThread { renderPhone(payload) }
            } catch (_: Exception) {
                runOnUiThread { renderError() }
            }
        }.start()
    }

    private fun renderPhone(payload: JSONObject) {
        root.removeAllViews()

        val summary = payload.optString("summary", "Status unavailable")
        val items = payload.optJSONArray("items")

        root.addView(text("🛡", 34f))
        root.addView(text(summary, 18f))

        if (items == null || items.length() == 0) {
            firstId = null
            root.addView(text("✓ Clear", 22f))
        } else {
            val first = items.getJSONObject(0)
            firstId = first.optString("id")

            root.addView(text(first.optString("title", "Attention"), 20f))
            root.addView(text(first.optString("body", ""), 14f))

            val row = LinearLayout(this).apply {
                orientation = LinearLayout.HORIZONTAL
                gravity = Gravity.CENTER
            }

            row.addView(button("Done") {
                firstId?.let { act(true, it) }
            })

            row.addView(button("Later") {
                firstId?.let { act(false, it) }
            })

            root.addView(row)

            if (items.length() > 1) {
                root.addView(text("+${items.length() - 1} more", 14f))
            }
        }

        root.addView(button("Refresh") {
            renderLoading()
            refresh()
        })

        root.addView(button("Sync") {
            sync()
        })
    }

    private fun act(done: Boolean, id: String) {
        renderLoading()

        Thread {
            try {
                if (done) WearBackendClient.resolve(id)
                else WearBackendClient.dismiss(id)

                val payload = WearBackendClient.fetchPhone()
                runOnUiThread { renderPhone(payload) }
            } catch (_: Exception) {
                runOnUiThread { renderError() }
            }
        }.start()
    }

    private fun sync() {
        renderLoading()

        Thread {
            try {
                WearBackendClient.syncGoogle()
                val payload = WearBackendClient.fetchPhone()
                runOnUiThread { renderPhone(payload) }
            } catch (_: Exception) {
                runOnUiThread { renderError() }
            }
        }.start()
    }

    private fun renderError() {
        root.removeAllViews()
        root.addView(text("Could not check", 18f))
        root.addView(button("Retry") {
            renderLoading()
            refresh()
        })
    }

    private fun text(value: String, size: Float): TextView {
        return TextView(this).apply {
            text = value
            textSize = size
            setTextColor(Color.WHITE)
            gravity = Gravity.CENTER
            maxLines = 4
        }
    }

    private fun button(value: String, action: () -> Unit): Button {
        return Button(this).apply {
            text = value
            setOnClickListener { action() }
        }
    }
}