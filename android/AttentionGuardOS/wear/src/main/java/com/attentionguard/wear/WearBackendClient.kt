package com.attentionguard.wear

import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject

object WearBackendClient {
    // TODO: set exact Render URL
    private const val BACKEND_URL = "https://attention-gaurd.onrender.com"
    private val client = OkHttpClient()
    private val jsonType = "application/json; charset=utf-8".toMediaType()

    fun fetchPhone(): JSONObject {
        client.newCall(Request.Builder().url("$BACKEND_URL/phone").get().build()).execute().use {
            val raw = it.body?.string()
            if(!it.isSuccessful || raw.isNullOrBlank()) error("failed")
            return JSONObject(raw)
        }
    }

    fun resolve(id:String){ post("/attention-items/$id/resolve") }
    fun dismiss(id:String){ post("/attention-items/$id/dismiss") }
    fun syncGoogle(){ post("/sync/google") }

    private fun post(path:String){
        client.newCall(Request.Builder().url("$BACKEND_URL$path").post("{}".toRequestBody(jsonType)).build()).execute().close()
    }
}
