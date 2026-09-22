package com.nexus.agent.agent

import kotlinx.serialization.Serializable

/**
 * TaskDescriptor — the JSON contract between the phone agent and the laptop watcher.
 *
 * Written to clipboard (or dropped as a file) via Office Kit.
 * The laptop watcher reads this, processes it with Qwen3-4B (longer context),
 * and writes a TaskResult back through the same Office Kit channel.
 *
 * Keep this schema stable during the hackathon — any change requires matching
 * changes in laptop/watcher.py.
 */
@Serializable
data class TaskDescriptor(
    /** UUID — used to match results back to requests */
    val id: String,

    /** What kind of task this is — used by the laptop watcher to route logic */
    val type: TaskType,

    /** The raw content to process (document text, long context, etc.) */
    val payload: String,

    /** What the laptop should do with the payload */
    val instruction: String,

    /** How the result should come back. "clipboard" = Office Kit clipboard sync */
    val returnChannel: String = "clipboard",

    /** ISO 8601 timestamp — helps the watcher detect stale tasks */
    val createdAt: String = java.time.Instant.now().toString()
)

@Serializable
data class TaskResult(
    /** Matches the TaskDescriptor.id this result is responding to */
    val taskId: String,

    /** The processed result text */
    val result: String,

    /** Approximate token count processed on the laptop */
    val tokenCount: Int = 0,

    /** Which model/runtime produced this result */
    val source: String = "laptop_qwen3_4b_q4km",

    /** ISO 8601 timestamp */
    val completedAt: String = java.time.Instant.now().toString()
)

@Serializable
enum class TaskType {
    /** Summarise or analyse a long document that exceeds phone context */
    LONG_CONTEXT_ANALYSIS,

    /** Look up information on the web (requires Browser Use on laptop) */
    WEB_LOOKUP,

    /** Process / reformat a large amount of text (transcripts, receipts, etc.) */
    DOCUMENT_PROCESS,

    /** Write or debug code with full context */
    CODE_ASSIST,

    /** Generic — no special routing */
    GENERIC
}
