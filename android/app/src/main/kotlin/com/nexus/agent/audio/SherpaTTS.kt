package com.nexus.agent.audio

import android.content.Context
import android.speech.tts.TextToSpeech
import android.speech.tts.UtteranceProgressListener
import android.util.Log
import com.k2fsa.sherpa.onnx.OfflineTts
import com.k2fsa.sherpa.onnx.OfflineTtsConfig
import com.k2fsa.sherpa.onnx.OfflineTtsVitsModelConfig
import com.k2fsa.sherpa.onnx.OfflineTtsModelConfig
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import java.util.Locale
import kotlin.coroutines.resume

/**
 * SherpaTTS — on-device text-to-speech using sherpa-onnx with a Piper voice.
 *
 * Primary: en_US-lessac-low (Piper ONNX export) — fast, natural, offline
 * Fallback: Android built-in TextToSpeech — zero setup, wired on day one
 *
 * Model files expected in assets/models/sherpa/tts/:
 *   en_US-lessac-low.onnx
 *   en_US-lessac-low.onnx.json  (espeak-ng phonemizer config)
 *   espeak-ng-data/              (phoneme data directory)
 *
 * Download from: https://github.com/k2-fsa/sherpa-onnx/releases
 *   → look for "vits-piper-en_US-lessac-low" in release assets
 *
 * IMPORTANT: Ship Android TTS as primary on day-1 and layer sherpa-onnx on top.
 * Reason: Android TTS is zero-setup and won't break under time pressure.
 */
class SherpaTTS(private val context: Context) {

    companion object {
        private const val TAG = "SherpaTTS"
        private const val ASSETS_TTS_DIR = "models/sherpa/tts"
        private const val VOICE_NAME = "en_US-lessac-low"
    }

    private var sherpaTts: OfflineTts? = null
    private var androidTts: TextToSpeech? = null
    private var useSherpa = false

    // Track current playback for cancellation
    @Volatile private var isSpeaking = false

    init {
        // Always init Android TTS as baseline — it's instant and never fails
        initAndroidTts()
        // Then try to layer sherpa-onnx on top
        initSherpaTts()
    }

    /**
     * Speak [text] aloud. Suspends until speech completes.
     * Trims text to avoid overly long TTS outputs on stage.
     */
    suspend fun speak(text: String) = withContext(Dispatchers.IO) {
        if (text.isBlank()) return@withContext

        // Clamp to ~500 chars for voice output — judges want concise replies
        val trimmed = if (text.length > 500) text.take(497) + "…" else text
        Log.d(TAG, "Speaking (${if (useSherpa) "Sherpa" else "Android"}): $trimmed")

        isSpeaking = true
        try {
            if (useSherpa && sherpaTts != null) {
                speakWithSherpa(trimmed)
            } else {
                speakWithAndroid(trimmed)
            }
        } finally {
            isSpeaking = false
        }
    }

    fun stopSpeaking() {
        isSpeaking = false
        sherpaTts?.stop()
        androidTts?.stop()
    }

    fun release() {
        androidTts?.shutdown()
        // OfflineTts cleanup (sherpa-onnx v1.10+)
        // sherpaTts?.release()
    }

    // ── Sherpa-onnx Piper TTS ────────────────────────────────────────────────────

    private fun initSherpaTts() {
        try {
            val ttsDir = copyAssetsToInternal(ASSETS_TTS_DIR)
            val voiceOnnx = "$ttsDir/$VOICE_NAME.onnx"
            val voiceJson = "$ttsDir/$VOICE_NAME.onnx.json"
            val dataDirPath = "$ttsDir/espeak-ng-data"

            if (!java.io.File(voiceOnnx).exists()) {
                Log.w(TAG, "Piper voice ONNX not found at $voiceOnnx — using Android TTS")
                return
            }

            val config = OfflineTtsConfig(
                model = OfflineTtsModelConfig(
                    vits = OfflineTtsVitsModelConfig(
                        model = voiceOnnx,
                        lexicon = "",
                        tokens = "",
                        dataDir = dataDirPath,
                    ),
                    numThreads = 2,
                    debug = false,
                    provider = "cpu",  // Piper runs fine on CPU; NPU not needed for TTS
                ),
            )

            sherpaTts = OfflineTts(config)
            useSherpa = true
            Log.i(TAG, "Sherpa-onnx Piper TTS initialized: $VOICE_NAME")
        } catch (e: Exception) {
            Log.w(TAG, "Sherpa TTS init failed, using Android TTS: ${e.message}")
            useSherpa = false
        }
    }

    private suspend fun speakWithSherpa(text: String) {
        val tts = sherpaTts ?: return speakWithAndroid(text)

        val audio = tts.generate(text = text, sid = 0, speed = 1.0f)

        // Play using AudioTrack for minimal latency
        val track = android.media.AudioTrack.Builder()
            .setAudioAttributes(
                android.media.AudioAttributes.Builder()
                    .setUsage(android.media.AudioAttributes.USAGE_ASSISTANT)
                    .setContentType(android.media.AudioAttributes.CONTENT_TYPE_SPEECH)
                    .build()
            )
            .setAudioFormat(
                android.media.AudioFormat.Builder()
                    .setEncoding(android.media.AudioFormat.ENCODING_PCM_FLOAT)
                    .setSampleRate(audio.sampleRate)
                    .setChannelMask(android.media.AudioFormat.CHANNEL_OUT_MONO)
                    .build()
            )
            .setBufferSizeInBytes(audio.samples.size * 4)
            .setTransferMode(android.media.AudioTrack.MODE_STATIC)
            .build()

        track.write(audio.samples, 0, audio.samples.size, android.media.AudioTrack.WRITE_BLOCKING)
        track.play()

        // Wait for playback to finish
        val durationMs = (audio.samples.size.toLong() * 1000L) / audio.sampleRate
        kotlinx.coroutines.delay(durationMs + 200L)
        track.stop()
        track.release()
    }

    // ── Android built-in TTS (always-available fallback) ─────────────────────────

    private fun initAndroidTts() {
        androidTts = TextToSpeech(context) { status ->
            if (status == TextToSpeech.SUCCESS) {
                androidTts?.language = Locale.US
                androidTts?.setSpeechRate(1.05f)  // slightly faster — better for agent replies
                Log.i(TAG, "Android TTS initialized")
            }
        }
    }

    private suspend fun speakWithAndroid(text: String) = suspendCancellableCoroutine { cont ->
        val tts = androidTts ?: run { cont.resume(Unit); return@suspendCancellableCoroutine }

        val uttId = "nexus_${System.currentTimeMillis()}"
        tts.setOnUtteranceProgressListener(object : UtteranceProgressListener() {
            override fun onStart(utteranceId: String?) {}
            override fun onDone(utteranceId: String?) { if (!cont.isCompleted) cont.resume(Unit) }
            override fun onError(utteranceId: String?) { if (!cont.isCompleted) cont.resume(Unit) }
        })
        tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, uttId)
    }

    private fun copyAssetsToInternal(assetDir: String): String {
        val destDir = java.io.File(context.filesDir, assetDir)
        if (destDir.exists()) return destDir.absolutePath
        destDir.mkdirs()

        fun copyRecursive(src: String, dest: java.io.File) {
            val children = context.assets.list(src) ?: return
            if (children.isEmpty()) {
                // It's a file
                context.assets.open(src).use { input ->
                    dest.outputStream().use { output -> input.copyTo(output) }
                }
            } else {
                dest.mkdirs()
                children.forEach { child ->
                    copyRecursive("$src/$child", java.io.File(dest, child))
                }
            }
        }
        copyRecursive(assetDir, destDir)
        return destDir.absolutePath
    }
}
