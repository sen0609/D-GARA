package com.example.adbsmarttest

import android.content.Intent
import android.os.Bundle
import android.util.Log // 确保导入 Log
import androidx.appcompat.app.AppCompatActivity

class RedirectActivity : AppCompatActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        Log.i("RedirectActivity", "onCreate: 跳转活动已启动！") // <-- 新增日志

        // 1. 创建一个意图（Intent）来启动我们的目标页面
        val intent = Intent(this, TargetPageActivity::class.java)

        // 2. 启动目标页面
        Log.i("RedirectActivity", "onCreate: 正在启动TargetPageActivity...") // <-- 新增日志
        startActivity(intent)

        // 3. 立刻关闭当前这个RedirectActivity
        finish()
    }
}