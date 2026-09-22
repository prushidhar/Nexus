package com.nexus.agent.audio

import android.content.Context
import android.os.VibrationEffect
import android.os.Vibrator
import android.util.Log
import kotlinx.coroutines.delay

/**
 * WakeWordDetector — triggers the listening loop when the user says "Hey Nexus".
 *
 * Mode A (primary — ship at event): Push-to-talk (PTT) mode.
 *   The MainActivity sends TRIGGER_LISTEN broadcast → this detector fires the callback.
 *   This is the MVP: zero model, zero ONNX integration, zero risk.
 *
 * Mode B (stretch — add during Green Light phase): openWakeWord ONNX.
 *   openWakeWord doesn't ship a prebuilt Android aar. You need to run its ONNX model
 *   through onnxruntime-android (already a transitive dep of sherpa-onnx).
 *   Model download: https://github.com/dscripka/openWakeWord/releases
 *     → hey_nexus.onnx  (or use 'hey_jarvis' and relabel it for the demo)
 *   Wire this ONLY after the core loop is proven solid — it's polish, not scoring.
 *
 * The detector calls [onTriggered](true) when a wake event is detected.
 * The caller (NexusService) then calls SherpaASR.recordAndTranscribe().
 */
class WakeWordDetector(private val context: Context) {

    companion object {
        private const val TAG = "WakeWordDetector"
        const val ACTION_PTT_TRIGGER = "com.nexus.agent.PTT_TRIGGER"

        // Vibration pattern for wake feedback (short, distinctive)
        private val WAKE_VIBRATION = longArrayOf(0, 50, 50, 100)
    }

    private var callback: ((Boolean) -> Unit)? = null
    private var pttReceiver: android.content.BroadcastReceiver? = null

    /**
     * Start listening. [onTriggered] is called with `true` when wake is detected.
     * This is a suspending function that loops until [stop] is called.
     */
    suspend fun listen(onTriggered: (Boolean) -> Unit) {
        callback = onTriggered
        registerPttReceiver()

        // Park here — events come via BroadcastReceiver
        Log.i(TAG, "WakeWordDetector listening (PTT mode)")
        while (pttReceiver != null) {
            delay(100)
        }
    }

    fun triggerManually() {
        Log.d(TAG, "Manual PTT trigger")
        vibrateWake()
        callback?.invoke(true)
    }

    fun stop() {
        pttReceiver?.let {
            try { context.unregisterReceiver(it) } catch (_: Exception) {}
        }
        pttReceiver = null
        callback = null
        Log.d(TAG, "WakeWordDetector stopped")
    }

    // ── PTT Receiver ─────────────────────────────────────────────────────────────

    private fun registerPttReceiver() {
        val receiver = object : android.content.BroadcastReceiver() {
            override fun onReceive(ctx: android.content.Context?, intent: android.content.Intent?) {
                if (intent?.action == ACTION_PTT_TRIGGER) {
                    Log.d(TAG, "PTT broadcast received")
                    vibrateWake()
                    callback?.invoke(true)
                }
            }
        }
        val filter = android.content.IntentFilter(ACTION_PTT_TRIGGER)
        context.registerReceiver(receiver, filter, android.content.Context.RECEIVER_NOT_EXPORTED)
        pttReceiver = receiver
    }

    // ── Wake Word ONNX (Stretch — not needed for MVP) ────────────────────────────
    // Uncomment and complete after core loop is proven
    /*
    private var onnxSession: ai.onnxruntime.OrtSession? = null
    private val env = ai.onnxruntime.OrtEnvironment.getEnvironment()
    
    private fun initOnnxWakeWord(modelPath: String) {
        onnxSession = env.createSession(modelPath)
        Log.i(TAG, "openWakeWord ONNX loaded from $modelPath")
    }
    
    private fun scoreFrame(audioBuffer: FloatArray): Float {
        val input = ai.onnxruntime.OnnxTensor.createTensor(env, arrayOf(audioBuffer))
        val result = onnxSession!!.run(mapOf("input" to input))
        return (result[0].value as Array<FloatArray>)[0][0]
    }
    
    // Run this in a coroutine loop on a 16kHz audio stream:
    // while (running) {
    //   val frame = recordFrame(320)  // 20ms at 16kHz
    //   if (scoreFrame(frame) > 0.5f) { callback?.invoke(true) }
    // }
    */

    // ── Haptics ──────────────────────────────────────────────────────────────────

    private fun vibrateWake() {
        try {
            val vibrator = context.getSystemService(Vibrator::class.java)
            vibrator?.vibrate(VibrationEffect.createWaveform(WAKE_VIBRATION, -1))
        } catch (e: Exception) {
            Log.w(TAG, "Vibration failed: ${e.message}")
        }
    }
}
