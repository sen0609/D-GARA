package com.example.adbsmarttest

import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class CookieConsentActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        // 使用新的 Cookie 布局文件
        setContentView(R.layout.activity_cookie_consent)

        // --- 核心改动：从Intent中获取所有Cookie相关的参数 ---
        val title = intent.getStringExtra("param_title") ?: "默认Cookie标题"
        val message = intent.getStringExtra("param_message") ?: "这是默认的Cookie消息内容。"
        val acceptBtnText = intent.getStringExtra("param_accept_btn_text") ?: "全部接受"
        val rejectBtnText = intent.getStringExtra("param_reject_btn_text") ?: "全部拒绝"
        val manageBtnText = intent.getStringExtra("param_manage_btn_text") ?: "管理设置"

        // 从Python传入日志内容
        val logTag = intent.getStringExtra("param_log_tag") ?: "CookieConsentLogger"
        val acceptLogEvent = intent.getStringExtra("param_accept_log_event") ?: "EVENT:COOKIE_ACCEPTED_ALL"
        val rejectLogEvent = intent.getStringExtra("param_reject_log_event") ?: "EVENT:COOKIE_REJECTED_ALL"
        val manageLogEvent = intent.getStringExtra("param_manage_log_event") ?: "EVENT:COOKIE_MANAGE_SETTINGS"

        // --- 将参数应用到UI上 ---
        findViewById<TextView>(R.id.cookie_title).text = title
        findViewById<TextView>(R.id.cookie_message).text = message

        val acceptButton = findViewById<Button>(R.id.accept_all_button)
        val rejectButton = findViewById<Button>(R.id.reject_all_button)
        val manageButton = findViewById<Button>(R.id.manage_settings_button)

        acceptButton.text = acceptBtnText
        rejectButton.text = rejectBtnText
        manageButton.text = manageBtnText

        // --- 根据参数设置按钮行为 ---
        acceptButton.setOnClickListener {
            Log.i(logTag, acceptLogEvent) // 打印“接受”的日志
            finish() // 关闭Activity
        }

        rejectButton.setOnClickListener {
            Log.i(logTag, rejectLogEvent) // 打印“拒绝”的日志
            finish() // 关闭Activity
        }

        manageButton.setOnClickListener {
            Log.i(logTag, manageLogEvent) // 打印“管理”的日志
            finish() // 关闭Activity
        }
    }
}