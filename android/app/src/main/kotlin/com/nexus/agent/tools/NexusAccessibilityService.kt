package com.nexus.agent.tools

import android.accessibilityservice.AccessibilityService
import android.accessibilityservice.GestureDescription
import android.graphics.Path
import android.graphics.Rect
import android.util.Log
import android.view.accessibility.AccessibilityEvent
import android.view.accessibility.AccessibilityNodeInfo
import java.util.concurrent.atomic.AtomicBoolean

/**
 * NexusAccessibilityService — Native on-phone interaction & screen reading engine.
 *
 * Core capability for:
 *  - "Read what's on my screen and summarize it" (Creative Phone Use + Problem Fit)
 *  - Automated app navigation and clicking (AI-Native Build)
 *  - Global actions (Back, Home, Notifications shade, Quick Settings)
 *
 * Grounded in Android's Accessibility API standards: non-destructive, declared, disclosed assistive tool.
 */
class NexusAccessibilityService : AccessibilityService() {

    companion object {
        private const val TAG = "NexusAccessibility"
        
        @Volatile
        var instance: NexusAccessibilityService? = null
            private set

        fun isConnected(): Boolean = instance != null
    }

    private val isGestureInProgress = AtomicBoolean(false)

    override fun onServiceConnected() {
        super.onServiceConnected()
        instance = this
        Log.i(TAG, "Nexus Accessibility Service connected and active")
    }

    override fun onAccessibilityEvent(event: AccessibilityEvent?) {
        // High frequency event stream — we query on demand via rootInActiveWindow
    }

    override fun onInterrupt() {
        Log.w(TAG, "Nexus Accessibility Service interrupted")
    }

    override fun onDestroy() {
        super.onDestroy()
        instance = null
        Log.i(TAG, "Nexus Accessibility Service destroyed")
    }

    // ── Screen Inspection ────────────────────────────────────────────────────────

    /**
     * Recursively dumps all visible, meaningful UI text with view hierarchy context.
     * Sanitizes redundant whitespace and filters empty containers.
     */
    fun dumpScreenHierarchy(): String {
        val root = rootInActiveWindow ?: return "Screen content unavailable (Window is empty or protected)."
        val sb = StringBuilder()
        sb.append("ACTIVE WINDOW: ").append(root.packageName ?: "Unknown App").append("\n")
        
        val visited = HashSet<Int>()
        traverseNode(root, 0, sb, visited)
        root.recycle()
        
        val output = sb.toString().trim()
        return if (output.isBlank()) "Screen is currently blank or contains non-accessible graphical elements." else output
    }

    private fun traverseNode(node: AccessibilityNodeInfo?, depth: Int, sb: StringBuilder, visited: HashSet<Int>) {
        if (node == null) return
        val nodeHash = node.hashCode()
        if (visited.contains(nodeHash)) return
        visited.add(nodeHash)

        if (!node.isVisibleToUser) return

        val text = node.text?.toString()?.trim()
        val desc = node.contentDescription?.toString()?.trim()
        val className = node.className?.toString()?.substringAfterLast('.') ?: "View"
        val isClickable = node.isClickable
        val isScrollable = node.isScrollable

        val bounds = Rect()
        node.getBoundsInScreen(bounds)

        // Only emit if there is informative text or actionable control
        val content = when {
            !text.isNullOrBlank() && !desc.isNullOrBlank() && text != desc -> "$text ($desc)"
            !text.isNullOrBlank() -> text
            !desc.isNullOrBlank() -> desc
            isClickable -> "[Clickable $className]"
            else -> null
        }

        if (content != null && bounds.width() > 0 && bounds.height() > 0) {
            val indent = "  ".repeat(depth.coerceAtMost(6))
            val actionTag = if (isClickable) " [clickable]" else if (isScrollable) " [scrollable]" else ""
            sb.append(indent)
                .append("- ")
                .append(content)
                .append(actionTag)
                .append(" @ [${bounds.left},${bounds.top} to ${bounds.right},${bounds.bottom}]")
                .append("\n")
        }

        for (i in 0 until node.childCount) {
            val child = node.getChild(i)
            traverseNode(child, depth + 1, sb, visited)
            child?.recycle()
        }
    }

    // ── Interaction Actions ──────────────────────────────────────────────────────

    /**
     * Finds the first clickable node matching or containing [targetText] (case-insensitive)
     * and performs ACTION_CLICK.
     */
    fun clickNodeByText(targetText: String): Boolean {
        val root = rootInActiveWindow ?: return false
        val cleanTarget = targetText.lowercase().trim()
        
        val matchedNodes = mutableListOf<AccessibilityNodeInfo>()
        findMatchingNodes(root, cleanTarget, matchedNodes)

        // Prefer clickable nodes directly, or walk up to clickable parent
        for (node in matchedNodes) {
            var current: AccessibilityNodeInfo? = node
            while (current != null) {
                if (current.isClickable) {
                    val clicked = current.performAction(AccessibilityNodeInfo.ACTION_CLICK)
                    Log.i(TAG, "Clicked node matching '$targetText': result=$clicked")
                    root.recycle()
                    return clicked
                }
                current = current.parent
            }
        }
        root.recycle()
        return false
    }

    private fun findMatchingNodes(node: AccessibilityNodeInfo?, target: String, result: MutableList<AccessibilityNodeInfo>) {
        if (node == null) return
        val text = node.text?.toString()?.lowercase() ?: ""
        val desc = node.contentDescription?.toString()?.lowercase() ?: ""

        if (text.contains(target) || desc.contains(target)) {
            result.add(node)
        }

        for (i in 0 until node.childCount) {
            findMatchingNodes(node.getChild(i), target, result)
        }
    }

    /**
     * Dispatches a synthetic tap gesture to exact screen coordinates [x, y].
     */
    fun tapCoordinates(x: Float, y: Float, onComplete: ((Boolean) -> Unit)? = null): Boolean {
        val path = Path().apply {
            moveTo(x, y)
        }
        val stroke = GestureDescription.StrokeDescription(path, 0, 50)
        val gesture = GestureDescription.Builder().addStroke(stroke).build()

        isGestureInProgress.set(true)
        return dispatchGesture(gesture, object : GestureResultCallback() {
            override fun onCompleted(gestureDescription: GestureDescription?) {
                super.onCompleted(gestureDescription)
                isGestureInProgress.set(false)
                Log.d(TAG, "Tap gesture at ($x, $y) completed successfully")
                onComplete?.invoke(true)
            }

            override fun onCancelled(gestureDescription: GestureDescription?) {
                super.onCancelled(gestureDescription)
                isGestureInProgress.set(false)
                Log.w(TAG, "Tap gesture at ($x, $y) cancelled")
                onComplete?.invoke(false)
            }
        }, null)
    }

    /**
     * Performs vertical scrolling on the screen.
     */
    fun scrollScreen(forward: Boolean): Boolean {
        val root = rootInActiveWindow ?: return false
        val action = if (forward) AccessibilityNodeInfo.ACTION_SCROLL_FORWARD else AccessibilityNodeInfo.ACTION_SCROLL_BACKWARD
        
        val scrollableNode = findScrollableNode(root)
        val result = scrollableNode?.performAction(action) ?: false
        root.recycle()
        return result
    }

    private fun findScrollableNode(node: AccessibilityNodeInfo?): AccessibilityNodeInfo? {
        if (node == null) return null
        if (node.isScrollable) return node
        for (i in 0 until node.childCount) {
            val res = findScrollableNode(node.getChild(i))
            if (res != null) return res
        }
        return null
    }

    // ── Global System Controls ───────────────────────────────────────────────────

    fun executeGlobal(actionType: Int): Boolean {
        return performGlobalAction(actionType)
    }
}
