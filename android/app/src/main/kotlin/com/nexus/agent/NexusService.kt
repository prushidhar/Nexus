package com.nexus.agent

import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.os.IBinder
import android.util.Log
import androidx.core.app.NotificationCompat
import com.nexus.agent.agent.AgentLoop
import com.nexus.agent.audio.SherpaASR
import com.nexus.agent.audio.SherpaTTS
import com.nexus.agent.audio.WakeWordDetector
import com.nexus.agent.llm.GenieXClient
import com.nexus.agent.llm.MediaPipeClient
import com.nexus.agent.ui.MainActivity
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.launch

/**
 * NexusService — Core Foreground Service for Nexus Phone-Native AI Agent.
 *
 * Runs as a foreground service to maintain microphone and NPU access
 * across arbitrary Android activities and screen lock states.
 * Coordinates:
 *   1. Wake word / PTT trigger detection
 *   2. On-device Speech-to-Text via sherpa-onnx (Whisper tiny.en + VAD)
 *   3. ReAct agent loop powered by Qualcomm Hexagon NPU (Qwen3-4B w4a16)
 *   4. System tool execution (Accessibility, Camera OCR, Notifications, Office Kit)
 *   5. On-device Text-to-Speech via Piper ONNX / Android TTS
 */
class NexusService : Service() {

    companion object {
        private const val TAG = "NexusService"
        private const val CHANNEL_ID = "nexus_agent_channel"
        private const val NOTIFICATION_ID = 1001

        const val ACTION_STATE_CHANGED = "com.nexus.agent.STATE_CHANGED"
        const val EXTRA_STATE = "state"

        enum class State { IDLE, LISTENING, THINKING, SPEAKING, ESCALATING }
    }

    private val serviceScope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    private lateinit var wakeWordDetector: WakeWordDetector
    private lateinit var asr: SherpaASR
    private lateinit var tts: SherpaTTS
    private lateinit var llmClient: GenieXClient
    private lateinit var fallbackClient: MediaPipeClient
    private lateinit var agentLoop: AgentLoop

    override fun onCreate() {
        super.onCreate()
        Log.i(TAG, "NexusService starting up on Snapdragon 8 Elite...")
        createNotificationChannel()
        startForeground(NOTIFICATION_ID, buildNotification("Nexus is ready"))
        initPipeline()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY
    }

    override fun onDestroy() {
        super.onDestroy()
        serviceScope.cancel()
        wakeWordDetector.stop()
        asr.stop()
        tts.release()
        Log.i(TAG, "NexusService stopped cleanly")
    }

    override fun onBind(intent: Intent?): IBinder? = null

    // ── Pipeline Initialization ──────────────────────────────────────────────────

    private fun initPipeline() {
        serviceScope.launch {
            try {
                // 1. Initialize LLMs
                llmClient = GenieXClient(applicationContext)
                val llmReady = llmClient.init()
                if (!llmReady) {
                    Log.w(TAG, "GenieX NPU init returned false — initializing MediaPipe GPU fallback")
                    fallbackClient = MediaPipeClient(applicationContext)
                    fallbackClient.init()
                }

                // 2. Initialize Audio components
                asr = SherpaASR(applicationContext)
                tts = SherpaTTS(applicationContext)

                // 3. Initialize Wake Word detector
                wakeWordDetector = WakeWordDetector(applicationContext)

                // 4. Wire Agent Loop
                agentLoop = AgentLoop(
                    context = applicationContext,
                    llm = if (llmReady) llmClient else fallbackClient,
                    tts = tts,
                    onStateChange = ::broadcastState
                )

                // 5. Start listening loop
                startListeningLoop()
                broadcastState(State.IDLE)
                Log.i(TAG, "Pipeline fully initialized and operational")

            } catch (e: Exception) {
                Log.e(TAG, "Pipeline init error: ${e.message}", e)
                updateNotification("Pipeline init error — see logs")
            }
        }
    }

    // ── Listening & Turn Handling ────────────────────────────────────────────────

    private fun startListeningLoop() {
        serviceScope.launch {
            wakeWordDetector.listen { triggered ->
                if (triggered) {
                    Log.d(TAG, "Wake trigger received")
                    broadcastState(State.LISTENING)
                    handleVoiceTurn()
                }
            }
        }
    }

    private fun handleVoiceTurn() {
        serviceScope.launch {
            try {
                val transcript = asr.recordAndTranscribe()
                if (transcript.isBlank()) {
                    Log.d(TAG, "Empty transcript recorded — returning to IDLE")
                    broadcastState(State.IDLE)
                    return@launch
                }

                Log.i(TAG, "User input transcribed: '$transcript'")
                broadcastState(State.THINKING)

                val reply = agentLoop.process(transcript)

                broadcastState(State.SPEAKING)
                tts.speak(reply)

                broadcastState(State.IDLE)
            } catch (e: Exception) {
                Log.e(TAG, "Error in voice turn: ${e.message}", e)
                broadcastState(State.IDLE)
            }
        }
    }

    // ── Helpers & State Notifications ────────────────────────────────────────────

    private fun broadcastState(state: State) {
        val intent = Intent(ACTION_STATE_CHANGED).putExtra(EXTRA_STATE, state.name)
        sendBroadcast(intent)
        updateNotification(
            when (state) {
                State.IDLE        -> "Nexus is listening (NPU Active)"
                State.LISTENING   -> "🎤 Listening..."
                State.THINKING    -> "🧠 Hexagon NPU Reasoning..."
                State.SPEAKING    -> "🔊 Speaking..."
                State.ESCALATING  -> "↗ Office Kit Cross-Device Escalation..."
            }
        )
    }

    private fun createNotificationChannel() {
        val channel = NotificationChannel(
            CHANNEL_ID,
            "Nexus Agent",
            NotificationManager.IMPORTANCE_LOW
        ).apply { description = "Nexus voice agent background service" }
        getSystemService(NotificationManager::class.java).createNotificationChannel(channel)
    }

    private fun buildNotification(text: String): Notification {
        val pendingIntent = PendingIntent.getActivity(
            this, 0,
            Intent(this, MainActivity::class.java),
            PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle("Nexus")
            .setContentText(text)
            .setSmallIcon(android.R.drawable.ic_btn_speak_now)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
    }

    private fun updateNotification(text: String) {
        val nm = getSystemService(NotificationManager::class.java)
        nm.notify(NOTIFICATION_ID, buildNotification(text))
    }
}
