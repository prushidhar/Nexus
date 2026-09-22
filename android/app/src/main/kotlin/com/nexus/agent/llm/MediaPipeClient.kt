package com.nexus.agent.llm

import android.content.Context
import android.util.Log
import com.google.mediapipe.tasks.genai.llminference.LlmInference
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlin.coroutines.resume

/**
 * MediaPipeClient — Gemma 3 1B (4-bit) running on the iQOO 15's GPU via Google AI Edge.
 *
 * This is the FALLBACK path. Activate only if GenieXClient.init() returns false.
 *
 * SETUP REQUIRED:
 *   1. Download gemma3-1b-it-int4.task from https://huggingface.co/google/gemma-3-1b-it-litert-preview
 *      (or use the MediaPipe Model Maker download utility)
 *   2. Push to device: adb push gemma3-1b-it-int4.task /sdcard/Download/
 *   3. Update MODEL_PATH below if storing in app-specific internal storage
 *
 * Performance on iQOO 15 (Adreno 840 GPU):
 *   Gemma 3 1B 4-bit: ~20-40 tok/s → first token ~1-2s → acceptable for voice
 */
class MediaPipeClient(private val context: Context) : LLMClient {

    companion object {
        private const val TAG = "MediaPipeClient"
        // Adjust this path to wherever the .task file lives on the device
        private const val MODEL_PATH = "/sdcard/Download/gemma3-1b-it-int4.task"
        private const val MAX_TOKENS_DEFAULT = 512
    }

    @Volatile private var inference: LlmInference? = null

    override suspend fun init(): Boolean = withContext(Dispatchers.IO) {
        try {
            val options = LlmInference.LlmInferenceOptions.builder()
                .setModelPath(MODEL_PATH)
                .setMaxTokens(1024)
                .setPreferredBackend(LlmInference.Backend.GPU)  // Adreno 840
                .build()

            inference = LlmInference.createFromOptions(context, options)
            Log.i(TAG, "MediaPipe Gemma 3 1B initialized on GPU")
            true
        } catch (e: Exception) {
            Log.e(TAG, "MediaPipe init failed: ${e.message}", e)
            false
        }
    }

    override suspend fun infer(prompt: String, maxTokens: Int): String =
        withContext(Dispatchers.IO) {
            val mp = inference ?: return@withContext "[Error: MediaPipe not initialized]"

            // Adapt ChatML prompt to Gemma instruction format
            val gemmaPrompt = adaptPromptToGemma(prompt)

            try {
                // MediaPipe LlmInference.generateResponse() is synchronous in this version
                mp.generateResponse(gemmaPrompt)
            } catch (e: Exception) {
                Log.e(TAG, "MediaPipe inference error: ${e.message}", e)
                """{"thought": "Error.", "answer": "MediaPipe error: ${e.message}"}"""
            }
        }

    override fun release() {
        inference?.close()
        inference = null
        Log.i(TAG, "MediaPipe client released")
    }

    /**
     * Convert our ChatML prompt format (designed for Qwen3) to Gemma's instruction format.
     * Extracts the system prompt and last user message for a clean Gemma turn.
     */
    private fun adaptPromptToGemma(chatMlPrompt: String): String {
        // Extract system block
        val systemRegex = Regex("<\\|im_start\\|>system\\n(.+?)<\\|im_end\\|>", RegexOption.DOT_MATCHES_ALL)
        val userRegex = Regex("<\\|im_start\\|>user\\n(.+?)<\\|im_end\\|>", RegexOption.DOT_MATCHES_ALL)

        val systemContent = systemRegex.find(chatMlPrompt)?.groupValues?.get(1)?.trim() ?: ""
        val userMessages = userRegex.findAll(chatMlPrompt).map { it.groupValues[1].trim() }.toList()
        val lastUser = userMessages.lastOrNull() ?: ""

        return "<start_of_turn>user\n$systemContent\n\n$lastUser<end_of_turn>\n<start_of_turn>model\n"
    }
}
