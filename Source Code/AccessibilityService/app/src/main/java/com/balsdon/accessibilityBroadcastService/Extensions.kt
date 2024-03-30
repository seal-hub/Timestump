package com.balsdon.accessibilityBroadcastService

import android.content.Context
import java.io.File

const val ACCESSIBILITY_CONTROL_BROADCAST_ACTION = "com.balsdon.talkback.accessibility"

fun Context.showToast(message: String) {
    android.widget.Toast.makeText(this, message, android.widget.Toast.LENGTH_SHORT)
        .show()
}

fun log(label: String, message: String, ack: Boolean = false) {
    android.util.Log.d(label, "$message")
    if (ack) {
        var code = message.split(" ").last()
        var fileName = "$label-$code"
        //TODO: fix
//        AccessibilityDeveloperService.instance?.baseContext?.filesDir?.let {
//            val file = File(it.path, fileName)
//            file.createNewFile()
//            android.util.Log.d(label, it.path)
//        } ?: android.util.Log.d(label, "ERROR in creating new file")
    }
}