package com.nexus.agent.ui

import android.animation.ValueAnimator
import android.annotation.SuppressLint
import android.app.Service
import android.content.Context
import android.content.Intent
import android.graphics.Color
import android.graphics.PixelFormat
import android.graphics.drawable.GradientDrawable
import android.os.IBinder
import android.util.Log
import android.view.Gravity
import android.view.MotionEvent
import android.view.View
import android.view.WindowManager
import android.view.animation.LinearInterpolator
import android.widget.FrameLayout
import android.widget.ImageView
import android.widget.LinearLayout
import android.widget.TextView
import com.nexus.agent.NexusService
import com.nexus.agent.audio.WakeWordDetector

/**
 * OverlayHUD — Ultimate floating UI that persists over ANY Android application.
 *
 * Provides:
 *  1. Floating draggable Nexus orb with dynamic color states and breathing animation.
 *  2. Real-time state pill: [IDLE / LISTENING / NPU THINKING / SPEAKING / OFFICE KIT ESCALATING].
 *  3. Live response speech balloon showing streaming ReAct thoughts & tool operations.
 *  4. Direct Tap-To-Talk trigger without needing to switch out of the active app.
 */
class OverlayHUD : Service() {

    companion object {
        private const val TAG = "OverlayHUD"
        const val ACTION_UPDATE_TEXT = "com.nexus.agent.HUD_TEXT"
        const val EXTRA_TEXT = "text"
        const val EXTRA_STATE = "state"

        fun start(context: Context) {
            val intent = Intent(context, OverlayHUD::class.java)
            context.startService(intent)
        }

        fun stop(context: Context) {
            val intent = Intent(context, OverlayHUD::class.java)
            context.stopService(intent)
        }
    }

    private lateinit var windowManager: WindowManager
    private lateinit var overlayView: FrameLayout
    private lateinit var orbView: FrameLayout
    private lateinit var statePill: TextView
    private lateinit var speechBubble: TextView
    private lateinit var orbBackground: GradientDrawable
    private lateinit var params: WindowManager.LayoutParams
    private var pulseAnimator: ValueAnimator? = null

    override fun onBind(intent: Intent?): IBinder? = null

    @SuppressLint("ClickableViewAccessibility")
    override fun onCreate() {
        super.onCreate()
        windowManager = getSystemService(Context.WINDOW_SERVICE) as WindowManager

        setupLayout()
        setupTouchInteraction()
        startOrbPulseAnimation()

        Log.i(TAG, "OverlayHUD initialized and mounted to WindowManager")
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        intent?.let {
            val text = it.getStringExtra(EXTRA_TEXT)
            val state = it.getStringExtra(EXTRA_STATE)
            if (state != null) updateState(NexusService.Companion.State.valueOf(state))
            if (text != null) updateText(text)
        }
        return START_STICKY
    }

    override fun onDestroy() {
        super.onDestroy()
        pulseAnimator?.cancel()
        if (::overlayView.isInitialized) {
            try {
                windowManager.removeView(overlayView)
            } catch (e: Exception) {
                Log.w(TAG, "Error detaching HUD: ${e.message}")
            }
        }
    }

    // ── Layout Construction ──────────────────────────────────────────────────────

    private fun setupLayout() {
        val density = resources.displayMetrics.density

        params = WindowManager.LayoutParams(
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.WRAP_CONTENT,
            WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY,
            WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE or WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,
            PixelFormat.TRANSLUCENT
        ).apply {
            gravity = Gravity.TOP or Gravity.START
            x = (20 * density).toInt()
            y = (150 * density).toInt()
        }

        overlayView = FrameLayout(this)

        val container = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            gravity = Gravity.START
        }

        // 1. Orb
        val orbSize = (56 * density).toInt()
        orbView = FrameLayout(this).apply {
            layoutParams = LinearLayout.LayoutParams(orbSize, orbSize)
        }

        orbBackground = GradientDrawable().apply {
            shape = GradientDrawable.OVAL
            setColor(Color.parseColor("#00E5FF")) // Cyber cyan
            setStroke((2 * density).toInt(), Color.parseColor("#FFFFFF"))
        }
        orbView.background = orbBackground

        val icon = ImageView(this).apply {
            setImageResource(android.R.drawable.ic_btn_speak_now)
            setColorFilter(Color.BLACK)
            val pad = (14 * density).toInt()
            setPadding(pad, pad, pad, pad)
        }
        orbView.addView(icon)

        // 2. State Pill
        statePill = TextView(this).apply {
            text = "NEXUS READY"
            textSize = 10f
            setTextColor(Color.WHITE)
            typeface = android.graphics.Typeface.DEFAULT_BOLD
            val pillBg = GradientDrawable().apply {
                shape = GradientDrawable.RECTANGLE
                cornerRadius = 12 * density
                setColor(Color.parseColor("#CC111111"))
            }
            background = pillBg
            setPadding((8 * density).toInt(), (3 * density).toInt(), (8 * density).toInt(), (3 * density).toInt())
            val lp = LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.WRAP_CONTENT,
                LinearLayout.LayoutParams.WRAP_CONTENT
            )
            lp.topMargin = (4 * density).toInt()
            layoutParams = lp
        }

        // 3. Speech / Thought Balloon
        speechBubble = TextView(this).apply {
            text = "Offline AI Active (Snapdragon 8 Elite NPU)"
            textSize = 12f
            setTextColor(Color.parseColor("#E0E0E0"))
            val bubbleBg = GradientDrawable().apply {
                shape = GradientDrawable.RECTANGLE
                cornerRadius = 8 * density
                setColor(Color.parseColor("#EE1A1A24"))
                setStroke(1, Color.parseColor("#334466"))
            }
            background = bubbleBg
            setPadding((10 * density).toInt(), (6 * density).toInt(), (10 * density).toInt(), (6 * density).toInt())
            val lp = LinearLayout.LayoutParams((220 * density).toInt(), LinearLayout.LayoutParams.WRAP_CONTENT)
            lp.topMargin = (4 * density).toInt()
            layoutParams = lp
        }

        container.addView(orbView)
        container.addView(statePill)
        container.addView(speechBubble)

        overlayView.addView(container)
        windowManager.addView(overlayView, params)
    }

    // ── Drag & Tap Gestures ──────────────────────────────────────────────────────

    @SuppressLint("ClickableViewAccessibility")
    private fun setupTouchInteraction() {
        var initialX = 0
        var initialY = 0
        var initialTouchX = 0f
        var initialTouchY = 0f
        var isClick = true

        orbView.setOnTouchListener { _, event ->
            when (event.action) {
                MotionEvent.ACTION_DOWN -> {
                    initialX = params.x
                    initialY = params.y
                    initialTouchX = event.rawX
                    initialTouchY = event.rawY
                    isClick = true
                    true
                }
                MotionEvent.ACTION_MOVE -> {
                    val dx = (event.rawX - initialTouchX).toInt()
                    val dy = (event.rawY - initialTouchY).toInt()
                    if (Math.abs(dx) > 10 || Math.abs(dy) > 10) {
                        isClick = false
                    }
                    params.x = initialX + dx
                    params.y = initialY + dy
                    windowManager.updateViewLayout(overlayView, params)
                    true
                }
                MotionEvent.ACTION_UP -> {
                    if (isClick) {
                        // Direct trigger: broadcast PTT event to NexusService
                        val intent = Intent(WakeWordDetector.ACTION_PTT_TRIGGER)
                        sendBroadcast(intent)
                    }
                    true
                }
                else -> false
            }
        }
    }

    // ── Animations & State Transitions ───────────────────────────────────────────

    private fun startOrbPulseAnimation() {
        pulseAnimator = ValueAnimator.ofFloat(1.0f, 1.15f, 1.0f).apply {
            duration = 1800
            repeatCount = ValueAnimator.INFINITE
            interpolator = LinearInterpolator()
            addUpdateListener { animator ->
                val scale = animator.animatedValue as Float
                orbView.scaleX = scale
                orbView.scaleY = scale
            }
            start()
        }
    }

    fun updateState(state: NexusService.Companion.State) {
        val (color, label) = when (state) {
            NexusService.Companion.State.IDLE -> Pair("#00E5FF", "NEXUS IDLE")
            NexusService.Companion.State.LISTENING -> Pair("#00E676", "LISTENING...")
            NexusService.Companion.State.THINKING -> Pair("#FFD600", "HEXAGON NPU REASONING")
            NexusService.Companion.State.SPEAKING -> Pair("#FF6D00", "SPEAKING")
            NexusService.Companion.State.ESCALATING -> Pair("#D500F9", "OFFICE KIT ESCALATION")
        }
        orbBackground.setColor(Color.parseColor(color))
        statePill.text = label
    }

    fun updateText(text: String) {
        speechBubble.text = text
    }
}
