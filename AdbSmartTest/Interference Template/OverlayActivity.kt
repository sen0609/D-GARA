package com.example.adbsmarttest

import android.os.Bundle
import android.view.LayoutInflater
import android.view.View
import android.widget.FrameLayout
import androidx.activity.addCallback
import androidx.appcompat.app.AppCompatActivity
import com.example.adbsmarttest.databinding.ActivityOverlayBinding

/**
 * 通用弹窗型 Activity：将你的内容布局“插”到卡片里。
 */
class OverlayActivity : AppCompatActivity() {

    companion object {
        const val EXTRA_CONTENT_LAYOUT = "content_layout"          // Int: R.layout.xxx
        const val EXTRA_CANCEL_ON_OUTSIDE = "cancel_on_outside"    // Boolean
        const val EXTRA_DIM_AMOUNT = "dim_amount"                  // Float 0..1
        const val EXTRA_MAX_WIDTH_DP = "max_width_dp"              // Int (eg. 360)
        const val EXTRA_SHOW_CLOSE = "show_close"                  // Boolean
        const val EXTRA_CARD_PADDING_DP = "card_padding_dp"        // Int
    }

    private lateinit var binding: ActivityOverlayBinding

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityOverlayBinding.inflate(layoutInflater)
        setContentView(binding.root)


        val contentLayout = intent.getIntExtra(EXTRA_CONTENT_LAYOUT, 0)
        val cancelOnOutside = intent.getBooleanExtra(EXTRA_CANCEL_ON_OUTSIDE, true)
        val dimAmount = intent.getFloatExtra(EXTRA_DIM_AMOUNT, -1f)
        val maxWidthDp = intent.getIntExtra(EXTRA_MAX_WIDTH_DP, 360)
        val showClose = intent.getBooleanExtra(EXTRA_SHOW_CLOSE, true)
        val paddingDp = intent.getIntExtra(EXTRA_CARD_PADDING_DP, 16)


        val density = resources.displayMetrics.density
        binding.cardContainer.layoutParams.width = (maxWidthDp * density).toInt()
        val padPx = (paddingDp * density).toInt()
        binding.cardContainer.setContentPadding(padPx, padPx, padPx, padPx)


        binding.btnClose.visibility = if (showClose) View.VISIBLE else View.GONE
        binding.btnClose.setOnClickListener { finish() }


        if (contentLayout != 0) {
            LayoutInflater.from(this).inflate(contentLayout, binding.contentSlot, true)
        }


        if (cancelOnOutside) {
            binding.root.setOnClickListener { finish() }
            binding.cardContainer.setOnClickListener { /* consume */ }
        }


        if (dimAmount in 0f..1f) {
            window.setDimAmount(dimAmount)
        }


        onBackPressedDispatcher.addCallback(this) { finish() }
    }
}


private fun AppCompatActivity.setDim(d: Float) {
    @Suppress("DEPRECATION")
    window.setDimAmount(d)
}
