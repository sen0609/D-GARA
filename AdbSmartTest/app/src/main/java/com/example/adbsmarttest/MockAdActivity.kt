package com.example.adbsmarttest

import android.os.Bundle
import android.view.View
import android.widget.FrameLayout
import android.widget.ImageButton
import android.widget.ImageView
import androidx.appcompat.app.AppCompatActivity

class MockAdActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_IMAGE_RES = "image_res" // 可传入 R.drawable.xxx
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_mock_ad)

        val adImage = findViewById<ImageView>(R.id.adImage)
        val btnClose = findViewById<ImageButton>(R.id.btnClose)
        val root = findViewById<FrameLayout>(R.id.root)
        val card = findViewById<View>(R.id.adCard)

        // 如果外部传了图片资源就用它，否则用本地一张默认图
        val resId = intent.getIntExtra(EXTRA_IMAGE_RES, 0)
        if (resId != 0) {
            adImage.setImageResource(resId)
        } else {
            adImage.setImageResource(R.drawable.mock_ad) // ← 换成你的实际图片名
        }

        // 关闭按钮
        btnClose.setOnClickListener { finishWithFade() }

        // 点遮罩关闭，点卡片不关闭
        root.setOnClickListener { finishWithFade() }
        card.setOnClickListener { /* consume click */ }
    }

    override fun onBackPressed() {
        super.onBackPressed()     // 如果想完全拦截返回键，可去掉这行
        finishWithFade()
    }

    private fun finishWithFade() {
        finish()
        // 这是个过时 API 的提醒（warning），先用不影响运行
        overridePendingTransition(android.R.anim.fade_in, android.R.anim.fade_out)
    }
}
