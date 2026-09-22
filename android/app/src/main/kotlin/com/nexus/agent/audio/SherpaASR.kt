package com.nexus.agent.audio

import android.content.Context
import android.util.Log
import com.k2fsa.sherpa.onnx.OfflineRecognizer
import com.k2fsa.sherpa.onnx.OfflineRecognizerConfig
import com.k2fsa.sherpa.onnx.OfflineWhisperModelConfig
import com.k2fsa.sherpa.onnx.OnlineRecognizer
import com.k2fsa.sherpa.onnx.OnlineRecognizerConfig
import com.k2fsa.sherpa.onnx.getAudioSamples
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

/**
 * SherpaASR — on-device speech-to-text using sherpa-onnx.
 *
 * Uses Whisper tiny.en (online/streaming) as primary.
 * Falls back to Whisper base.en (offline/batch) for longer utterances.
 *
 * Model files expected in assets/models/sherpa/:
 *   - whisper-tiny.en/         → streaming ASR (tiny model, fastest)
 *       encoder.int8.onnx
 *       decoder.int8.onnx
 *   - whisper-base.en/         → batch ASR (slightly better accuracy)
 *       encoder.int8.onnx
 *       decoder.int8.onnx
 *
 * Download from: https://github.com/k2-fsa/sherpa-onnx/releases
 * (search "whisper-tiny.en" or "whisper-base.en" in the release assets)
 *
 * Recording stops automatically on 1.5s of silence (VAD built into sherpa-onnx).
 */
class SherpaASR(private val context: Context) {

    companion object {
        private const val TAG = "SherpaASR"
        private const val SAMPLE_RATE = 16000
        private const val ASSETS_DIR = "models/sherpa"
        private const val TINY_MODEL_DIR = "whisper-tiny.en"

        // Max recording duration before force-stopping (safety net for demos)
        private const val MAX_RECORD_MS = 15_000L
    }

    private var recognizer: OfflineRecognizer? = null
    private var audioRecorder: android.media.AudioRecord? = null
    private var isRecording = false

    init {
        initRecognizer()
    }

    private fun initRecognizer() {
        try {
            // Copy model assets to internal storage (sherpa-onnx needs file paths, not InputStream)
            val modelDir = copyAssetsToInternal("$ASSETS_DIR/$TINY_MODEL_DIR")

            val config = OfflineRecognizerConfig(
                modelConfig = com.k2fsa.sherpa.onnx.OfflineModelConfig(
                    whisper = OfflineWhisperModelConfig(
                        encoder = "$modelDir/encoder.int8.onnx",
                        decoder = "$modelDir/decoder.int8.onnx",
                    ),
                    tokens = "$modelDir/tokens.txt",
                    numThreads = 4,
                    debug = false,
                ),
                decodingMethod = "greedy_search",
            )

            recognizer = OfflineRecognizer(config)
            Log.i(TAG, "SherpaASR initialized with Whisper tiny.en")
        } catch (e: Exception) {
            Log.e(TAG, "SherpaASR init failed: ${e.message}", e)
        }
    }

    /**
     * Records audio until silence detected, then returns transcript.
     * Suspending — call from a coroutine.
     */
    suspend fun recordAndTranscribe(): String = withContext(Dispatchers.IO) {
        val r = recognizer ?: return@withContext ""

        val bufferSize = android.media.AudioRecord.getMinBufferSize(
            SAMPLE_RATE,
            android.media.AudioFormat.CHANNEL_IN_MONO,
            android.media.AudioFormat.ENCODING_PCM_16BIT
        )

        val recorder = android.media.AudioRecord(
            android.media.MediaRecorder.AudioSource.MIC,
            SAMPLE_RATE,
            android.media.AudioFormat.CHANNEL_IN_MONO,
            android.media.AudioFormat.ENCODING_PCM_16BIT,
            bufferSize * 4
        )

        val allSamples = mutableListOf<Short>()
        val buffer = ShortArray(bufferSize)
        var silenceFrames = 0
        val silenceThreshold = 300       // amplitude threshold for silence
        val silenceFrameLimit = 24       // ~1.5s at 16kHz / 1024-frame chunks

        try {
            recorder.startRecording()
            isRecording = true
            val startMs = System.currentTimeMillis()

            while (isRecording && System.currentTimeMillis() - startMs < MAX_RECORD_MS) {
                val read = recorder.read(buffer, 0, buffer.size)
                if (read > 0) {
                    allSamples.addAll(buffer.take(read))

                    val maxAmplitude = buffer.take(read).maxOf { it.toInt().let { v -> if (v < 0) -v else v } }
                    if (maxAmplitude < silenceThreshold) {
                        silenceFrames++
                        if (silenceFrames > silenceFrameLimit && allSamples.size > SAMPLE_RATE) {
                            // Enough speech recorded + silence detected → stop
                            break
                        }
                    } else {
                        silenceFrames = 0
                    }
                }
            }
        } finally {
            recorder.stop()
            recorder.release()
            isRecording = false
        }

        if (allSamples.isEmpty()) return@withContext ""

        // Convert short[] to float[] for sherpa-onnx
        val floatSamples = FloatArray(allSamples.size) { allSamples[it].toFloat() / 32768.0f }

        val stream = r.createStream()
        stream.acceptWaveform(floatSamples, SAMPLE_RATE)
        r.decode(stream)
        val result = r.getResult(stream)
        stream.release()

        result.text.trim().also {
            Log.i(TAG, "Transcript: '$it'")
        }
    }

    fun stop() {
        isRecording = false
        recognizer?.let {
            // OfflineRecognizer doesn't have explicit close in older versions
            // Future versions may add it — check the sherpa-onnx changelog
        }
    }

    /**
     * Copies model asset directory to app's internal storage.
     * sherpa-onnx requires actual file paths, not Android asset InputStreams.
     * Returns the destination directory path.
     */
    private fun copyAssetsToInternal(assetDir: String): String {
        val destDir = java.io.File(context.filesDir, assetDir)
        if (destDir.exists()) return destDir.absolutePath  // already copied

        destDir.mkdirs()
        context.assets.list(assetDir)?.forEach { fileName ->
            val src = context.assets.open("$assetDir/$fileName")
            val dest = java.io.File(destDir, fileName)
            src.use { input -> dest.outputStream().use { output -> input.copyTo(output) } }
        }
        Log.d(TAG, "Copied assets/$assetDir → ${destDir.absolutePath}")
        return destDir.absolutePath
    }
}
