package com.nexus.agent.tools

import android.app.Notification
import android.service.notification.NotificationListenerService
import android.service.notification.StatusBarNotification
import android.util.Log
import java.util.concurrent.ConcurrentHashMap

/**
 * NexusNotificationService — Real-time notification interception engine.
 * Allows Nexus to proactively monitor alerts, messages, OTPs, and system notifications.
 */
class NexusNotificationService : NotificationListenerService() {

    companion object {
        private const val TAG = "NexusNotification"

        @Volatile
        var instance: NexusNotificationService? = null
            private set

        fun isConnected(): Boolean = instance != null

        // In-memory cache of active notifications mapped by key
        val notificationCache = ConcurrentHashMap<String, NotificationItem>()
    }

    data class NotificationItem(
        val key: String,
        val packageName: String,
        val appName: String,
        val title: String,
        val text: String,
        val timestamp: Long
    )

    override fun onListenerConnected() {
        super.onListenerConnected()
        instance = this
        Log.i(TAG, "Notification listener connected")
        refreshActiveNotifications()
    }

    override fun onListenerDisconnected() {
        super.onListenerDisconnected()
        instance = null
        notificationCache.clear()
        Log.i(TAG, "Notification listener disconnected")
    }

    override fun onNotificationPosted(sbn: StatusBarNotification?) {
        sbn?.let { parseAndCache(it) }
    }

    override fun onNotificationRemoved(sbn: StatusBarNotification?) {
        sbn?.let { notificationCache.remove(it.key) }
    }

    private fun refreshActiveNotifications() {
        try {
            val active = activeNotifications ?: return
            notificationCache.clear()
            for (sbn in active) {
                parseAndCache(sbn)
            }
            Log.d(TAG, "Cached ${notificationCache.size} active notifications")
        } catch (e: Exception) {
            Log.e(TAG, "Failed to refresh active notifications: ${e.message}")
        }
    }

    private fun parseAndCache(sbn: StatusBarNotification) {
        // Filter out ongoing background service indicators
        if ((sbn.notification.flags and Notification.FLAG_ONGOING_EVENT) != 0) return
        if (sbn.packageName == applicationContext.packageName) return

        val extras = sbn.notification.extras ?: return
        val title = extras.getCharSequence(Notification.EXTRA_TITLE)?.toString()?.trim() ?: ""
        val text = (extras.getCharSequence(Notification.EXTRA_BIG_TEXT)
            ?: extras.getCharSequence(Notification.EXTRA_TEXT))?.toString()?.trim() ?: ""

        if (title.isBlank() && text.isBlank()) return

        val pm = packageManager
        val appName = try {
            val appInfo = pm.getApplicationInfo(sbn.packageName, 0)
            pm.getApplicationLabel(appInfo).toString()
        } catch (_: Exception) {
            sbn.packageName
        }

        notificationCache[sbn.key] = NotificationItem(
            key = sbn.key,
            packageName = sbn.packageName,
            appName = appName,
            title = title,
            text = text,
            timestamp = sbn.postTime
        )
    }
}
