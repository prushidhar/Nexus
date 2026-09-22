package com.nexus.agent.tools

import android.util.Log

/**
 * NotificationTool — Exposes active system notifications to the AgentLoop.
 */
class NotificationTool {

    companion object {
        private const val TAG = "NotificationTool"
    }

    /**
     * Reads all active user-facing notifications.
     */
    fun readActiveNotifications(): String {
        val cache = NexusNotificationService.notificationCache
        if (!NexusNotificationService.isConnected()) {
            return "Notification access permission not granted. Please enable 'Nexus Assist' in Settings -> Notification Access."
        }

        if (cache.isEmpty()) {
            return "No active notifications right now."
        }

        val sb = StringBuilder()
        sb.append("ACTIVE NOTIFICATIONS (${cache.size} total):\n")
        
        // Sort newest first
        val sorted = cache.values.sortedByDescending { it.timestamp }
        for (item in sorted.take(10)) {
            sb.append("• [").append(item.appName).append("] ")
                .append(item.title).append(": ")
                .append(item.text).append("\n")
        }

        Log.i(TAG, "Summarized ${cache.size} notifications")
        return sb.toString().trim()
    }
}
