plugins {
    alias(libs.plugins.android.application)
    alias(libs.plugins.kotlin.android)
    alias(libs.plugins.kotlin.serialization)
    alias(libs.plugins.kotlin.parcelize)
}

android {
    namespace = "com.nexus.agent"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.nexus.agent"
        minSdk = 31          // Android 12 — required for foreground service mic + RECORD_AUDIO
        targetSdk = 35
        versionCode = 1
        versionName = "1.0.0-hackathon"

        testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"

        ndk {
            abiFilters += listOf("arm64-v8a")  // iQOO 15 is arm64 only (Snapdragon 8 Elite)
        }
    }

    buildTypes {
        release {
            isMinifyEnabled = false
            proguardFiles(
                getDefaultProguardFile("proguard-android-optimize.txt"),
                "proguard-rules.pro"
            )
        }
        debug {
            isDebuggable = true
        }
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    kotlinOptions {
        jvmTarget = "17"
    }

    packaging {
        resources {
            excludes += "/META-INF/{AL2.0,LGPL2.1}"
        }
    }
}

dependencies {
    // ── Qualcomm GenieX (Qwen3-4B on Hexagon NPU) ──────────────────────────────
    compileOnly("com.qualcomm.geniex:geniex-android:1.0.0")

    // ── sherpa-onnx (STT + TTS + VAD — one dep for all audio I/O) ───────────────
    implementation("com.github.k2-fsa:sherpa-onnx-android:1.10.18")

    // ── MediaPipe / Google AI Edge (Gemma 3 1B fallback LLM) ────────────────────
    implementation("com.google.mediapipe:tasks-genai:0.10.14")

    // ── ML Kit Text Recognition (camera OCR — zero extra download) ───────────────
    implementation("com.google.mlkit:text-recognition:16.0.0")

    // ── Kotlin Serialization (TaskDescriptor JSON) ───────────────────────────────
    implementation(libs.kotlinx.serialization.json)

    // ── Coroutines ───────────────────────────────────────────────────────────────
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-android:1.7.3")
    implementation("org.jetbrains.kotlinx:kotlinx-coroutines-core:1.7.3")

    // ── AndroidX essentials ──────────────────────────────────────────────────────
    implementation(libs.androidx.core.ktx)
    implementation(libs.androidx.appcompat)
    implementation(libs.material)
    implementation(libs.androidx.constraintlayout)
    implementation(libs.androidx.lifecycle.runtime.ktx)
    implementation(libs.androidx.lifecycle.viewmodel.ktx)

    // ── Camera (CameraX — for CameraTool) ────────────────────────────────────────
    implementation(libs.androidx.camera.core)
    implementation(libs.androidx.camera.camera2)
    implementation(libs.androidx.camera.lifecycle)
    implementation(libs.androidx.camera.view)

    // ── Test ─────────────────────────────────────────────────────────────────────
    testImplementation(libs.junit)
    androidTestImplementation(libs.androidx.junit)
}
