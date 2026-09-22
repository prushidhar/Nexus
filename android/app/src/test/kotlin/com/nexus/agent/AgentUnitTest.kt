package com.nexus.agent

import com.nexus.agent.agent.TaskDescriptor
import com.nexus.agent.agent.TaskResult
import com.nexus.agent.agent.TaskType
import kotlinx.serialization.json.Json
import org.junit.Assert.*
import org.junit.Test

/**
 * AgentUnitTest — Verifies data serialization, protocol integrity, and ReAct parsing.
 */
class AgentUnitTest {

    private val json = Json { ignoreUnknownKeys = true; isLenient = true }

    @Test
    fun testTaskDescriptorSerialization() {
        val task = TaskDescriptor(
            id = "task_unit_101",
            type = TaskType.LONG_CONTEXT_ANALYSIS,
            payload = "Test technical payload for Snapdragon 8 Elite NPU",
            instruction = "Summarize the payload",
            returnChannel = "clipboard",
            createdAt = "2026-09-22T06:00:00Z"
        )

        val serialized = json.encodeToString(TaskDescriptor.serializer(), task)
        assertTrue(serialized.contains("task_unit_101"))
        assertTrue(serialized.contains("LONG_CONTEXT_ANALYSIS"))

        val deserialized = json.decodeFromString(TaskDescriptor.serializer(), serialized)
        assertEquals("task_unit_101", deserialized.id)
        assertEquals(TaskType.LONG_CONTEXT_ANALYSIS, deserialized.type)
        assertEquals("Summarize the payload", deserialized.instruction)
    }

    @Test
    fun testTaskResultSerialization() {
        val result = TaskResult(
            taskId = "task_unit_101",
            result = "Synthesized analysis from RTX 2050 CUDA",
            tokenCount = 120,
            source = "laptop_qwen3_4b_cuda_rtx2050",
            completedAt = "2026-09-22T06:01:00Z"
        )

        val serialized = json.encodeToString(TaskResult.serializer(), result)
        val deserialized = json.decodeFromString(TaskResult.serializer(), serialized)

        assertEquals("task_unit_101", deserialized.taskId)
        assertEquals(120, deserialized.tokenCount)
        assertEquals("laptop_qwen3_4b_cuda_rtx2050", deserialized.source)
    }

    @Test
    fun testReActJsonExtraction() {
        // Test stripping code blocks from raw LLM output
        val rawLlmOutput = """
            ```json
            {
                "thought": "User wants screen summary",
                "action": "read_screen",
                "params": {}
            }
            ```
        """.trimIndent()

        val cleaned = rawLlmOutput.trim()
            .removePrefix("```json").removePrefix("```")
            .removeSuffix("```")
            .trim()

        val start = cleaned.indexOf('{')
        val end = cleaned.lastIndexOf('}')
        assertTrue(start != -1 && end != -1)

        val jsonStr = cleaned.substring(start..end)
        assertTrue(jsonStr.contains("read_screen"))
        assertTrue(jsonStr.contains("thought"))
    }
}
