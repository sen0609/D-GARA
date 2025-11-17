package com.example.adbsmarttest

import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class LocationPermissionActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_location_permission)

        // --- 核心改动：从Intent中获取所有参数 ---
        val title = intent.getStringExtra("param_title") ?: "默认标题"
        val message = intent.getStringExtra("param_message") ?: "默认消息内容。"
        val allowBtnText = intent.getStringExtra("param_allow_btn_text") ?: "允许"
        val denyBtnText = intent.getStringExtra("param_deny_btn_text") ?: "拒绝"

        // 我们甚至可以让Python决定日志的内容，增加灵活性
        val logTag = intent.getStringExtra("param_log_tag") ?: "ReactBench_Event"
        val allowLogEvent = intent.getStringExtra("param_allow_log_event") ?: "EVENT:PERMISSION_ALLOWED"
        val denyLogEvent = intent.getStringExtra("param_deny_log_event") ?: "EVENT:PERMISSION_DENIED"

        // --- 将参数应用到UI上 ---
        findViewById<TextView>(R.id.permission_title).text = title
        findViewById<TextView>(R.id.permission_message).text = message

        val allowButton = findViewById<Button>(R.id.allow_button)
        val denyButton = findViewById<Button>(R.id.deny_button)

        allowButton.text = allowBtnText
        denyButton.text = denyBtnText

        // --- 根据参数设置按钮行为 ---
        allowButton.setOnClickListener {
            Log.i(logTag, allowLogEvent) // 打印允许的日志
            finish()
        }

        denyButton.setOnClickListener {
            Log.i(logTag, denyLogEvent) // 打印拒绝的日志
            finish()
        }
    }
}