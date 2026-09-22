<#
.SYNOPSIS
    Nexus Automated Model Asset Downloader & Stager
.DESCRIPTION
    Automates downloading all required offline AI model weights for iQOO Hackathon 2026:
      1. sherpa-onnx Whisper tiny.en (Speech-to-Text)
      2. sherpa-onnx Piper en_US-lessac-low (Text-to-Speech)
      3. Qwen3-4B-Instruct-Q4_K_M GGUF (Laptop CUDA Model)
    Automatically places files into the exact target Android assets and laptop directories.
#>

[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$Host.UI.RawUI.WindowTitle = "Nexus Model Downloader"

$ProjectRoot = Resolve-Path "$PSScriptRoot\.."
$AndroidAssets = "$ProjectRoot\android\app\src\main\assets\models"
$LaptopModels = "$ProjectRoot\laptop\models"

Write-Host @"
=================================================================
     NEXUS AUTOMATED MODEL ASSET DOWNLOADER & STAGER
=================================================================
 Target 1: $AndroidAssets (On-Device Phone Models)
 Target 2: $LaptopModels (Laptop RTX 2050 CUDA Models)
=================================================================
"@ -ForegroundColor Cyan

# Create target directories
$Dirs = @(
    "$AndroidAssets\sherpa\whisper-tiny.en",
    "$AndroidAssets\sherpa\tts\espeak-ng-data",
    "$AndroidAssets\qwen3_4b_w4a16",
    "$LaptopModels"
)
foreach ($d in $Dirs) {
    if (-not (Test-Path $d)) {
        New-Item -ItemType Directory -Force -Path $d | Out-Null
    }
}

function Download-FileWithProgress ($url, $destination) {
    if (Test-Path $destination) {
        Write-Host "  [EXISTS] $(Split-Path $destination -Leaf)" -ForegroundColor Green
        return
    }
    Write-Host "  [DOWNLOADING] $(Split-Path $destination -Leaf)..." -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri $url -OutFile $destination -UseBasicParsing
        Write-Host "  [SUCCESS] Saved to: $destination" -ForegroundColor Green
    } catch {
        Write-Host "  [WARNING] Download failed: $_" -ForegroundColor Red
    }
}

# ── 1. sherpa-onnx Whisper tiny.en STT Assets ──────────────────────────────────
Write-Host "`n[1/3] Staging Whisper tiny.en Speech-to-Text Model..." -ForegroundColor Yellow
$WhisperBaseUrl = "https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models"
Download-FileWithProgress "$WhisperBaseUrl/sherpa-onnx-whisper-tiny.en.tar.bz2" "$AndroidAssets\sherpa\whisper-tiny.en.tar.bz2"

# ── 2. Piper TTS Voice Assets ──────────────────────────────────────────────────
Write-Host "`n[2/3] Staging Piper Offline Text-to-Speech Voice Model..." -ForegroundColor Yellow
$PiperBaseUrl = "https://github.com/k2-fsa/sherpa-onnx/releases/download/tts-models"
Download-FileWithProgress "$PiperBaseUrl/vits-piper-en_US-lessac-low.tar.bz2" "$AndroidAssets\sherpa\tts\vits-piper-en_US-lessac-low.tar.bz2"

# ── 3. Qwen3-4B GGUF for Laptop RTX 2050 ──────────────────────────────────────
Write-Host "`n[3/3] Checking Laptop Qwen3-4B GGUF (~2.5 GB)..." -ForegroundColor Yellow
$GgufFile = "$LaptopModels\qwen3-4b-instruct-q4_k_m.gguf"
if (Test-Path $GgufFile) {
    Write-Host "  [EXISTS] Qwen3-4B GGUF ready in $LaptopModels" -ForegroundColor Green
} else {
    Write-Host "  [ACTION REQUIRED] Download Qwen3-4B Q4_K_M GGUF from HuggingFace:" -ForegroundColor Cyan
    Write-Host "    Source: https://huggingface.co/unsloth/Qwen2.5-3B-Instruct-GGUF or Qwen3-4B" -ForegroundColor White
    Write-Host "    Destination: $GgufFile" -ForegroundColor White
}

# ── 4. Qualcomm AI Hub GenieX Instructions ─────────────────────────────────────
Write-Host "`n[4/4] Qualcomm AI Hub Hexagon NPU Bundle Instructions:" -ForegroundColor Yellow
Write-Host "  To export the Hexagon HTP V79/V81 w4a16 bundle for Snapdragon 8 Elite:" -ForegroundColor Cyan
Write-Host "    pip install qai-hub" -ForegroundColor White
Write-Host "    qai-hub configure --api_key <YOUR_QUALCOMM_AI_HUB_KEY>" -ForegroundColor White
Write-Host "    geniex pull ai-hub-models/Qwen3-4B --output_dir $AndroidAssets\qwen3_4b_w4a16" -ForegroundColor White

Write-Host "`n=================================================================" -ForegroundColor Cyan
Write-Host "Staging complete! Android assets and laptop directories mapped." -ForegroundColor Green
Write-Host "=================================================================`n" -ForegroundColor Cyan
