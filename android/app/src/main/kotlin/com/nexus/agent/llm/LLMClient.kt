package com.nexus.agent.llm

/**
 * LLMClient — common interface for all on-device LLM backends.
 *
 * Implementations:
 *  - GenieXClient   → Qwen3-4B on Hexagon NPU via Qualcomm GenieX SDK (primary)
 *  - MediaPipeClient → Gemma 3 1B on GPU via Google MediaPipe (fallback)
 *
 * The AgentLoop holds an LLMClient reference and doesn't care which is running.
 */
interface LLMClient {

    /**
     * Initialize the model. Call once before first infer().
     * @return true if init succeeded, false if the backend is unavailable.
     */
    suspend fun init(): Boolean

    /**
     * Generate a text completion for [prompt].
     * @param prompt    Full formatted prompt (system + history + current turn)
     * @param maxTokens Maximum tokens to generate
     * @return          Generated text, or an error message string
     */
    suspend fun infer(prompt: String, maxTokens: Int = 512): String

    /**
     * Free any native resources held by the model.
     * Call from Service.onDestroy().
     */
    fun release()
}
