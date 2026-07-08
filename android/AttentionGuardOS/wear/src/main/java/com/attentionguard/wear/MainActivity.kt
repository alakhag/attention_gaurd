package com.attentionguard.wear

import android.app.Activity
import android.os.Bundle
import android.graphics.Color
import android.view.Gravity
import android.widget.*
import org.json.JSONObject

class MainActivity: Activity() {
    private lateinit var root: LinearLayout
    private var firstId: String? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.CENTER
            setPadding(18,18,18,18)
            setBackgroundColor(Color.BLACK)
        }
        setContentView(root)
        renderLoading()
        refresh()
    }

    private fun renderLoading(){
        root.removeAllViews()
        root.addView(text("🛡", 34f))
        root.addView(text("Checking…", 18f))
    }

    private fun refresh(){
        Thread{
            try{
                val p = WearBackendClient.fetchPhone()
                runOnUiThread{ renderPhone(p) }
            }catch(_:Exception){
                runOnUiThread{ renderError() }
            }
        }.start()
    }

    private fun renderPhone(p: JSONObject){
        root.removeAllViews()
        val summary = p.optString("summary","Status unavailable")
        root.addView(text("🛡", 34f))
        root.addView(text(summary, 18f))
        val arr = p.optJSONArray("items")
        if(arr == null || arr.length()==0){
            firstId = null
            root.addView(text("✓ Clear", 22f))
        } else {
            val first = arr.getJSONObject(0)
            firstId = first.optString("id")
            root.addView(text(first.optString("title"), 20f))
            root.addView(text(first.optString("body"), 14f))
            val row = LinearLayout(this).apply{orientation=LinearLayout.HORIZONTAL; gravity=Gravity.CENTER}
            row.addView(button("Done"){ firstId?.let { act(true,it) } })
            row.addView(button("Later"){ firstId?.let { act(false,it) } })
            root.addView(row)
            if(arr.length()>1) root.addView(text("+${arr.length()-1} more", 14f))
        }
        root.addView(button("Refresh"){ renderLoading(); refresh() })
        root.addView(button("Sync"){ sync() })
    }

    private fun act(done:Boolean,id:String){
        renderLoading()
        Thread{
            try{
                if(done) WearBackendClient.resolve(id) else WearBackendClient.dismiss(id)
                val p=WearBackendClient.fetchPhone()
                runOnUiThread{ renderPhone(p) }
            }catch(_:Exception){ runOnUiThread{ renderError() } }
        }.start()
    }

    private fun sync(){
        renderLoading()
        Thread{
            try{
                WearBackendClient.syncGoogle()
                val p=WearBackendClient.fetchPhone()
                runOnUiThread{ renderPhone(p) }
            }catch(_:Exception){ runOnUiThread{ renderError() } }
        }.start()
    }

    private fun renderError(){ root.removeAllViews(); root.addView(text("Could not check",18f)); root.addView(button("Retry"){renderLoading(); refresh()}) }
    private fun text(s:String, size:Float)=TextView(this).apply{text=s; textSize=size; setTextColor(Color.WHITE); gravity=Gravity.CENTER; maxLines=4}
    private fun button(s:String, f:()->Unit)=Button(this).apply{text=s; setOnClickListener{f()}}
}
