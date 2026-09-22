package com.nexus.agent

import android.app.Application
import android.util.Log

/**
 * NexusApplication — Global application singleton.
 * Configures crash shielding, native library preloading, and performance telemetry.
 */
class NexusApplication : Application() {

    companion object {
        private const val TAG = "NexusApp"
        lateinit var instance: NexusApplication
            private set
    }

    override fun onCreate() {
        super.onCreate()
        instance = this

        setupCrashShield()
        Log.i(TAG, "Nexus Application initialized. Target: Snapdragon 8 Elite Gen 5 (SM8850)")
    }

    private fun setupCrashShield() {
        val defaultHandler = Thread.getDefaultUncaughtExceptionHandler()
        Thread.setDefaultUncaughtExceptionHandler { thread, throwable ->
            Log.e(TAG, "CRITICAL: Uncaught exception on thread ${thread.name}: ${throwable.message}", throwable)
            // Log stack trace to logcat before delegating to default handler
            defaultHandler?.uncaughtException(thread, throwable)
        }
    }
}
