package com.nexus.agent.tools

import android.content.Context
import android.content.ClipData
import android.content.ClipboardManager
import android.util.Log
import com.nexus.agent.agent.TaskDescriptor
import com.nexus.agent.agent.TaskResult
import com.nexus.agent.agent.TaskType
import kotlinx.coroutines.delay
import kotlinx.coroutines.withTimeoutOrNull
import kotlinx.serialization.json.Json
import java.util.UUID

/**
 * OfficeKitBridge — the 10%-of-your-score component.
 *
 * Office Kit (iQOO/vivo's official PC connection suite) automatically syncs
 * the clipboard between the phone and the paired laptop. This bridge:
 *   1. Writes a TaskDescriptor JSON to the phone clipboard
 *   2. Office Kit detects the change and syncs it to the laptop within ~1s
 *   3. The laptop watcher.py picks it up, processes it with Qwen3-4B (long context)
 *   4. Watcher writes a TaskResult JSON back to the laptop clipboard
 *   5. Office Kit syncs it back to the phone clipboard
 *   6. We poll and detect the result
 *
 * Every call to escalate() = one Office Kit clipboard sync = HackTracker score.
 *
 * SETUP: Office Kit must be installed on the laptop (pc.vivoglobal.com) and paired
 * with this iQOO 15. Test clipboard sync before the event — pair it fresh, not
 * at the venue on crowded Wi-Fi.
 */
class OfficeKitBridge(private val context: Context) {

    companion object {
        private const val TAG = "OfficeKitBridge"

        // Poll interval for waiting for laptop response
        private const val POLL_INTERVAL_MS = 300L

        // Max wait for laptop result (30 seconds — generous for demo safety)
        private const val RESULT_TIMEOUT_MS = 30_000L

        // Prefix used to detect result vs. unrelated clipboard content
        private const val RESULT_PREFIX = "nexus_result:"
    }

    private val clipboard = context.getSystemService(ClipboardManager::class.java)
    private val json = Json { ignoreUnknownKeys = true }

    /**
     * Escalate a task to the laptop via Office Kit clipboard sync.
     * Suspends until the laptop responds or timeout occurs.
     * @return The laptop's result text, or an error message.
     */
    suspend fun escalate(task: String, payload: String): String {
        val taskId = UUID.randomUUID().toString().take(8)
        val descriptor = TaskDescriptor(
            id = taskId,
            type = TaskType.LONG_CONTEXT_ANALYSIS,
            payload = payload,
            instruction = task,
        )

        val taskJson = json.encodeToString(TaskDescriptor.serializer(), descriptor)
        Log.i(TAG, "Escalating task $taskId to laptop via Office Kit clipboard")

        // Write to clipboard — Office Kit picks this up automatically
        setClipboard(taskJson)

        // Wait for the laptop to process and write the result back
        val result = withTimeoutOrNull(RESULT_TIMEOUT_MS) {
            pollForResult(taskId)
        }

        return result?.result
            ?: "The laptop is still processing — check back in a moment. (Office Kit sync may be slow on venue Wi-Fi)"
    }

    // ── Clipboard I/O ─────────────────────────────────────────────────────────────

    private fun setClipboard(text: String) {
        val clip = ClipData.newPlainText("nexus_task", text)
        clipboard.setPrimaryClip(clip)
        Log.d(TAG, "Clipboard set (${text.length} chars)")
    }

    private fun getClipboard(): String? {
        return try {
            clipboard.primaryClip?.getItemAt(0)?.text?.toString()
        } catch (e: Exception) {
            Log.w(TAG, "Clipboard read error: ${e.message}")
            null
        }
    }

    /**
     * Polls the clipboard until a TaskResult matching [taskId] appears.
     * The laptop watcher writes: {"taskId": "...", "result": "...", ...}
     */
    private suspend fun pollForResult(taskId: String): TaskResult? {
        var lastClip = getClipboard() ?: ""

        repeat((RESULT_TIMEOUT_MS / POLL_INTERVAL_MS).toInt()) {
            delay(POLL_INTERVAL_MS)

            val clip = getClipboard() ?: return@repeat
            if (clip == lastClip) return@repeat
            lastClip = clip

            if (!clip.startsWith("{")) return@repeat  // not JSON — skip

            try {
                val result = json.decodeFromString<TaskResult>(clip)
                if (result.taskId == taskId) {
                    Log.i(TAG, "Received result for task $taskId from ${result.source}")
                    return result
                }
            } catch (_: Exception) {
                // Not a TaskResult — ignore
            }
        }
        return null
    }
}
