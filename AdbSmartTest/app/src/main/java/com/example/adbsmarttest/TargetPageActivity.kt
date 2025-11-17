package com.example.adbsmarttest

import android.os.Bundle
import android.util.Log // 确保导入 Log
import androidx.appcompat.app.AppCompatActivity

class TargetPageActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_target_page)
        Log.i("TargetPageActivity", "onCreate: 目标页面已成功加载！") // <-- 新增日志
    }
}