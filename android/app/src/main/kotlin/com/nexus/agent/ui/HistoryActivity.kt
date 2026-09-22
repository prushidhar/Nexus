package com.nexus.agent.ui

import android.graphics.Color
import android.os.Bundle
import android.view.View
import android.widget.LinearLayout
import android.widget.ScrollView
import android.widget.TextView
import androidx.appcompat.app.AppCompatActivity

/**
 * HistoryActivity — Session conversation replay and execution log.
 */
class HistoryActivity : AppCompatActivity() {

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(buildHistoryLayout())
    }

    private fun buildHistoryLayout(): View {
        val density = resources.displayMetrics.density
        val dp = { v: Int -> (v * density).toInt() }

        val root = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setBackgroundColor(Color.parseColor("#0B0E14"))
            setPadding(dp(16), dp(16), dp(16), dp(16))
        }

        val header = TextView(this).apply {
            text = "NEXUS // CONVERSATION HISTORY"
            textSize = 18f
            setTextColor(Color.parseColor("#00E5FF"))
            typeface = android.graphics.Typeface.DEFAULT_BOLD
            setPadding(0, 0, 0, dp(12))
        }
        root.addView(header)

        val sv = ScrollView(this).apply {
            layoutParams = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT,
                LinearLayout.LayoutParams.MATCH_PARENT
            )
        }

        val listContainer = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
        }

        val placeholder = TextView(this).apply {
            text = "All on-device turns and Office Kit handoffs are logged here locally.\nData is 100% private and stored in internal app memory."
            textSize = 13f
            setTextColor(Color.parseColor("#90A4AE"))
        }
        listContainer.addView(placeholder)

        sv.addView(listContainer)
        root.addView(sv)

        return root
    }
}
