package com.nexus.agent.agent

import android.content.Context
import android.util.Log
import com.nexus.agent.NexusService
import com.nexus.agent.audio.SherpaTTS
import com.nexus.agent.llm.LLMClient
import com.nexus.agent.tools.ToolRegistry
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json

/**
 * AgentLoop — the ReAct (Reason → Act → Observe) loop for Nexus.
 *
 * On each user turn:
 *  1. Build a prompt with tool schema + conversation history
 *  2. Call LLM → parse JSON response
 *  3. If action: execute tool, append observation, loop
 *  4. If answer: return final text (caller speaks it via TTS)
 *  5. Hard cap: max MAX_ITERATIONS tool calls per turn (prevents infinite loops on stage)
 */
class AgentLoop(
    private val context: Context,
    private val llm: LLMClient,
    private val tts: SherpaTTS,
    private val onStateChange: (NexusService.Companion.State) -> Unit
) {

    companion object {
        private const val TAG = "AgentLoop"
        private const val MAX_ITERATIONS = 5
        private const val MAX_HISTORY_TURNS = 6  // keep last 6 turns in context
    }

    private val json = Json { ignoreUnknownKeys = true; isLenient = true }
    private val toolRegistry = ToolRegistry(context)

    // Sliding window conversation history
    private val history = mutableListOf<ChatMessage>()

    // ── Public API ───────────────────────────────────────────────────────────────

    /**
     * Process a user utterance. Returns the final answer text.
     * This is a suspending call — runs on whatever coroutine context the caller provides.
     */
    suspend fun process(userInput: String): String {
        history.add(ChatMessage("user", userInput))
        trimHistory()

        var iterations = 0
        var observation = ""

        while (iterations < MAX_ITERATIONS) {
            val prompt = buildPrompt(observation)
            Log.d(TAG, "LLM call #${iterations + 1}")

            val rawResponse = llm.infer(prompt, maxTokens = 512)
            Log.d(TAG, "LLM raw: $rawResponse")

            val response = parseResponse(rawResponse) ?: run {
                Log.w(TAG, "Failed to parse LLM response — returning as plain text")
                history.add(ChatMessage("assistant", rawResponse))
                return rawResponse
            }

            when {
                // ── Final answer ───────────────────────────────────────────────
                response.answer != null -> {
                    history.add(ChatMessage("assistant", response.answer))
                    return response.answer
                }

                // ── Tool call ──────────────────────────────────────────────────
                response.action != null -> {
                    Log.i(TAG, "Tool call: ${response.action}(${response.params})")

                    // Signal escalation to UI if it's an Office Kit hand-off
                    if (response.action == "escalate_to_laptop") {
                        onStateChange(NexusService.Companion.State.ESCALATING)
                    }

                    observation = toolRegistry.execute(response.action, response.params ?: emptyMap())
                    Log.d(TAG, "Tool result: $observation")
                    iterations++
                }

                else -> {
                    Log.w(TAG, "Response had neither action nor answer")
                    return "I'm not sure how to handle that. Could you rephrase?"
                }
            }
        }

        // Exceeded max iterations — return graceful fallback
        return "I hit my step limit on that one. Let me try a simpler approach — what specifically did you need?"
    }

    fun clearHistory() = history.clear()

    // ── Prompt Building ──────────────────────────────────────────────────────────

    private fun buildPrompt(lastObservation: String): String {
        val tools = toolRegistry.schema()
        val historyStr = history.takeLast(MAX_HISTORY_TURNS * 2)
            .joinToString("\n") { "${it.role.uppercase()}: ${it.content}" }

        val observationBlock = if (lastObservation.isNotBlank())
            "\nOBSERVATION: $lastObservation" else ""

        return """<|im_start|>system
You are Nexus, a local AI assistant running entirely on this iQOO 15 phone — no cloud, no internet required.
You are smart, fast, and privacy-first.

You have these tools available:
$tools

RULES:
- Always respond with a JSON object (no markdown, no code blocks, just raw JSON).
- If you need to use a tool, respond: {"thought": "...", "action": "tool_name", "params": {"key": "value"}}
- If you have a final answer, respond: {"thought": "...", "answer": "your reply to the user"}
- Be concise. Voice output — keep answers under 3 sentences unless detail is explicitly asked for.
- Never hallucinate tool results. Always call the tool, wait for the observation.
<|im_end|>
<|im_start|>user
$historyStr$observationBlock
<|im_end|>
<|im_start|>assistant
"""
    }

    // ── Response Parsing ─────────────────────────────────────────────────────────

    private fun parseResponse(raw: String): LLMResponse? {
        // Strip any accidental markdown code fences
        val cleaned = raw.trim()
            .removePrefix("```json").removePrefix("```")
            .removeSuffix("```")
            .trim()

        // Find the first complete JSON object in the response
        val start = cleaned.indexOf('{')
        val end = cleaned.lastIndexOf('}')
        if (start == -1 || end == -1) return null

        return try {
            json.decodeFromString<LLMResponse>(cleaned.substring(start..end))
        } catch (e: Exception) {
            Log.w(TAG, "JSON parse error: ${e.message}")
            null
        }
    }

    private fun trimHistory() {
        while (history.size > MAX_HISTORY_TURNS * 2) {
            history.removeAt(0)
        }
    }

    // ── Data Classes ─────────────────────────────────────────────────────────────

    @Serializable
    private data class LLMResponse(
        val thought: String = "",
        val action: String? = null,
        val params: Map<String, String>? = null,
        val answer: String? = null
    )

    private data class ChatMessage(val role: String, val content: String)
}
