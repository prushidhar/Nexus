package com.nexus.agent.agent

import android.content.Context
import android.util.Log
import com.nexus.agent.tools.AccessibilityTool
import com.nexus.agent.tools.CameraTool
import com.nexus.agent.tools.NotificationTool
import com.nexus.agent.tools.OfficeKitBridge
import kotlinx.coroutines.runBlocking

/**
 * ToolRegistry — maps tool names to implementations and provides the tool schema
 * injected into every LLM prompt.
 *
 * Adding a new tool: implement BaseTool, add an entry to the map and schema below.
 * The LLM never sees code — it only sees the schema in the system prompt.
 */
class ToolRegistry(private val context: Context) {

    companion object {
        private const val TAG = "ToolRegistry"
    }

    // ── Tool instances ────────────────────────────────────────────────────────────

    private val accessibilityTool = AccessibilityTool()
    private val cameraTool = CameraTool(context)
    private val notificationTool = NotificationTool()
    private val officeKitBridge = OfficeKitBridge(context)

    // ── Dispatch table ────────────────────────────────────────────────────────────

    suspend fun execute(toolName: String, params: Map<String, String>): String {
        return try {
            when (toolName) {
                "read_screen" -> {
                    accessibilityTool.readCurrentScreen()
                }
                "tap_element" -> {
                    val label = params["label"] ?: return "Error: missing 'label' param"
                    val success = accessibilityTool.tapNodeWithText(label)
                    if (success) "Tapped '$label' successfully" else "Could not find element '$label' on screen"
                }
                "open_app" -> {
                    val pkg = params["package"] ?: return "Error: missing 'package' param"
                    openApp(pkg)
                }
                "camera_ocr" -> {
                    cameraTool.captureAndExtractText()
                }
                "read_notifications" -> {
                    notificationTool.readActiveNotifications()
                }
                "escalate_to_laptop" -> {
                    val task = params["task"] ?: return "Error: missing 'task' param"
                    val payload = params["payload"] ?: ""
                    officeKitBridge.escalate(task, payload)
                }
                "get_time" -> {
                    java.time.LocalDateTime.now()
                        .format(java.time.format.DateTimeFormatter.ofPattern("EEEE, d MMMM yyyy, h:mm a"))
                }
                "calculate" -> {
                    val expr = params["expression"] ?: return "Error: missing 'expression' param"
                    evaluateExpression(expr)
                }
                else -> {
                    Log.w(TAG, "Unknown tool: $toolName")
                    "Tool '$toolName' is not available on this device."
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "Tool '$toolName' threw: ${e.message}", e)
            "Error executing $toolName: ${e.message}"
        }
    }

    // ── Schema (injected into every LLM system prompt) ──────────────────────────

    fun schema(): String = """
Available tools (call exactly one per response if needed):

- read_screen()
  Returns all visible text on the current phone screen.
  Use when the user says "what's on my screen", "read this", "what does it say".

- tap_element(label: str)
  Taps a UI element containing the given text label.
  Use for navigation: "open Settings", "click the back button".

- open_app(package: str)
  Opens an Android app by package name.
  Common packages: com.android.settings, com.google.android.gm, com.whatsapp

- camera_ocr()
  Captures a photo with the front/rear camera and extracts text via OCR.
  Use when the user points the phone at physical text: receipts, documents, whiteboards.

- read_notifications()
  Returns the current list of active notifications with app name and text.
  Use when the user asks "do I have any messages" or "what are my notifications".

- escalate_to_laptop(task: str, payload: str)
  Sends a complex task to the laptop (via Office Kit) for deeper processing with a longer context window.
  Use for: long document analysis, multi-step web research, processing large amounts of text.
  The result will be returned here when the laptop finishes.

- get_time()
  Returns current date and time.

- calculate(expression: str)
  Evaluates a simple math expression. Example: "15% of 2340"
""".trimIndent()

    // ── Helpers ──────────────────────────────────────────────────────────────────

    private fun openApp(packageName: String): String {
        return try {
            val intent = context.packageManager.getLaunchIntentForPackage(packageName)
            if (intent != null) {
                intent.addFlags(android.content.Intent.FLAG_ACTIVITY_NEW_TASK)
                context.startActivity(intent)
                "Opened $packageName"
            } else {
                "App '$packageName' not found on this device"
            }
        } catch (e: Exception) {
            "Failed to open app: ${e.message}"
        }
    }

    private fun evaluateExpression(expr: String): String {
        // Simple percentage and arithmetic parser — enough for most voice queries
        return try {
            // Handle "X% of Y" pattern
            val percentPattern = Regex("""(\d+(?:\.\d+)?)%\s+of\s+(\d+(?:\.\d+)?)""")
            val pMatch = percentPattern.find(expr)
            if (pMatch != null) {
                val pct = pMatch.groupValues[1].toDouble()
                val total = pMatch.groupValues[2].toDouble()
                val result = pct / 100.0 * total
                "${pct}% of ${total} = $result"
            } else {
                // Fallback: return the expression unchanged and let the LLM reason
                "I can compute basic percentages. For complex math, please be more specific."
            }
        } catch (e: Exception) {
            "Could not evaluate: $expr"
        }
    }
}
