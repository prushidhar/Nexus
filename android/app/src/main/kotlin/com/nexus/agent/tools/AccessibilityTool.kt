package com.nexus.agent.tools

import android.accessibilityservice.AccessibilityService
import android.util.Log

/**
 * AccessibilityTool — High-level tool wrapper used by ToolRegistry and AgentLoop.
 * Communicates with the active NexusAccessibilityService singleton.
 */
class AccessibilityTool {

    companion object {
        private const val TAG = "AccessibilityTool"
    }

    /**
     * Reads all visible text on screen with UI hierarchy metadata.
     */
    fun readCurrentScreen(): String {
        val service = NexusAccessibilityService.instance
        if (service == null) {
            Log.w(TAG, "AccessibilityService is not enabled by user")
            return "Accessibility permission not granted. Please enable 'Nexus Assist' in Android Settings -> Accessibility."
        }

        val dump = service.dumpScreenHierarchy()
        Log.i(TAG, "Read screen content (${dump.length} characters)")
        return dump
    }

    /**
     * Taps a button, tab, or text field containing [label].
     */
    fun tapNodeWithText(label: String): Boolean {
        val service = NexusAccessibilityService.instance ?: return false
        val success = service.clickNodeByText(label)
        Log.i(TAG, "Attempted tap on '$label': success=$success")
        return success
    }

    /**
     * Taps at specific screen coordinates (useful for canvas elements, games, or non-text controls).
     */
    fun tapCoordinates(x: Float, y: Float): Boolean {
        val service = NexusAccessibilityService.instance ?: return false
        return service.tapCoordinates(x, y)
    }

    /**
     * Scrolls the current view up or down.
     */
    fun scroll(direction: String): Boolean {
        val service = NexusAccessibilityService.instance ?: return false
        val forward = direction.equals("down", ignoreCase = true) || direction.equals("forward", ignoreCase = true)
        return service.scrollScreen(forward)
    }

    /**
     * Global phone navigation actions: back, home, notifications, recents.
     */
    fun navigateGlobal(action: String): String {
        val service = NexusAccessibilityService.instance ?: return "Accessibility service not active"
        val actionCode = when (action.lowercase()) {
            "back" -> AccessibilityService.GLOBAL_ACTION_BACK
            "home" -> AccessibilityService.GLOBAL_ACTION_HOME
            "notifications" -> AccessibilityService.GLOBAL_ACTION_NOTIFICATIONS
            "recents" -> AccessibilityService.GLOBAL_ACTION_RECENTS
            "quick_settings" -> AccessibilityService.GLOBAL_ACTION_QUICK_SETTINGS
            else -> return "Unknown action: $action"
        }
        val res = service.executeGlobal(actionCode)
        return if (res) "Executed $action successfully" else "Failed to execute $action"
    }
}
