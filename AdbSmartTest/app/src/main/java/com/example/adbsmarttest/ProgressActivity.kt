package com.example.adbsmarttest

import android.animation.ValueAnimator
import android.os.Bundle
import android.util.Log
import android.view.animation.LinearInterpolator
import android.widget.Button
import android.widget.ProgressBar
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity
import androidx.core.animation.doOnEnd

class ProgressActivity : AppCompatActivity() {

    // 将动画器声明为成员变量，以便在任何地方都能访问和取消它
    private var progressAnimator: ValueAnimator? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_progress)

        // --- 1. 获取所有参数，包括新增的“持续时间”参数 ---
        val title = intent.getStringExtra("param_title") ?: "正在更新应用"
        val message = intent.getStringExtra("param_message") ?: "请稍候..."
        val buttonText = intent.getStringExtra("param_button_text") ?: "取消"
        val initialProgress = intent.getIntExtra("param_progress", 0) // 初始进度
        val durationInSeconds = intent.getIntExtra("param_duration_seconds", 0) // 动画持续时间（秒）

        val logTag = intent.getStringExtra("param_log_tag") ?: "ProgressActivityLogger"
        val logEvent = intent.getStringExtra("param_log_event") ?: "EVENT:PROGRESS_CANCELLED"

        // --- 2. 找到视图 ---
        val titleTextView = findViewById<TextView>(R.id.progress_title)
        val messageTextView = findViewById<TextView>(R.id.progress_message)
        val progressBar = findViewById<ProgressBar>(R.id.dialog_progress_bar)
        val actionButton = findViewById<Button>(R.id.progress_button)

        // --- 3. 应用初始参数到UI ---
        titleTextView.text = title
        messageTextView.text = message
        actionButton.text = buttonText
        progressBar.progress = initialProgress

        // --- 4. 核心：如果传入了持续时间，就启动动画 ---
        if (durationInSeconds > 0) {
            startProgressAnimation(progressBar, messageTextView, durationInSeconds)
        }

        // --- 5. 设置按钮行为 ---
        actionButton.setOnClickListener {
            progressAnimator?.cancel() // 如果动画正在进行，取消它
            Log.i(logTag, logEvent)
            finish()
        }
    }

    /**
     * 启动进度条动画的方法
     * @param progressBar 要驱动的进度条
     * @param messageView 用于显示百分比的文本视图
     * @param durationInSeconds 动画的总时长（秒）
     */
    private fun startProgressAnimation(progressBar: ProgressBar, messageView: TextView, durationInSeconds: Int) {
        // 创建一个从0到100的整数值动画器
        progressAnimator = ValueAnimator.ofInt(0, 100).apply {
            duration = durationInSeconds * 1000L // 将秒转换为毫秒
            interpolator = LinearInterpolator() // 使用线性插值器，确保进度匀速增长

            // 添加一个监听器，在动画的每一“帧”更新UI
            addUpdateListener { animation ->
                val animatedValue = animation.animatedValue as Int
                progressBar.progress = animatedValue
                messageView.text = "处理中... $animatedValue%"
            }

            // 监听动画结束事件
            doOnEnd {
                messageView.text = "处理完成！"
                // 可以在这里自动关闭，或者改变按钮状态
                findViewById<Button>(R.id.progress_button).text = "完成"
            }
        }

        // 启动动画！
        progressAnimator?.start()
    }

    override fun onDestroy() {
        super.onDestroy()
        // 在Activity销毁时，务必取消动画，防止内存泄漏
        progressAnimator?.cancel()
    }
}