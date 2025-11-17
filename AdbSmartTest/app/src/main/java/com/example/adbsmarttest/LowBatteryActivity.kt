package com.example.adbsmarttest

import android.os.Bundle
import android.util.Log
import android.widget.Button
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

class LowBatteryActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_low_battery)

        // --- 从Intent中获取所有参数 ---
        val title = intent.getStringExtra("param_title") ?: "默认标题"
        val message = intent.getStringExtra("param_message") ?: "默认消息内容。"
        val buttonText = intent.getStringExtra("param_button_text") ?: "确认"

        // 从Python传入日志内容
        val logTag = intent.getStringExtra("param_log_tag") ?: "ReactBench_Event"
        val logEvent = intent.getStringExtra("param_log_event") ?: "EVENT:LOW_BATTERY_ACKNOWLEDGED"

        // --- 找到所有视图 ---
        val titleTextView = findViewById<TextView>(R.id.low_battery_title)
        val messageTextView = findViewById<TextView>(R.id.low_battery_message)
        val okButton = findViewById<Button>(R.id.ok_button)

        // --- 将参数应用到UI上 ---
        titleTextView.text = title
        messageTextView.text = message
        okButton.text = buttonText

        // --- 设置按钮行为 ---
        okButton.setOnClickListener {
            Log.i(logTag, logEvent) // 打印日志
            finish() // 关闭Activity
        }
    }
}