# Nexus Mock llama-server (PowerShell Native with Interactive Web UI)
# Serves http://127.0.0.1:8080/ (Interactive Dashboard) + /health + /v1/chat/completions

$Port = 8080
$WebRoot = Join-Path $PSScriptRoot "web"
$IndexHtmlPath = Join-Path $WebRoot "index.html"

$Listener = New-Object System.Net.HttpListener
$Listener.Prefixes.Add("http://127.0.0.1:$Port/")

try {
    $Listener.Start()
} catch {
    Write-Host "[ERROR] Could not start listener on port $Port" -ForegroundColor Red
    exit 1
}

Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  NEXUS MOCK LLAMA-SERVER // SNAPDRAGON <=> RTX 2050 SIMULATOR" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host " Web UI:     http://127.0.0.1:$Port/" -ForegroundColor Green
Write-Host " Endpoints:  GET /health | POST /v1/chat/completions" -ForegroundColor Green
Write-Host " Ready for browser access and Office Kit task escalations." -ForegroundColor White
Write-Host "=================================================================" -ForegroundColor Cyan

while ($Listener.IsListening) {
    try {
        $Context = $Listener.GetContext()
        $Request = $Context.Request
        $Response = $Context.Response

        $Url = $Request.Url.AbsolutePath
        $Method = $Request.HttpMethod

        $Timestamp = Get-Date -Format "HH:mm:ss"
        Write-Host "[$Timestamp] $Method $Url" -ForegroundColor DarkGray

        # ── 1. Serve Web UI on Root / ──────────────────────────────────────────
        if (($Url -eq "/" -or $Url -eq "/index.html") -and $Method -eq "GET") {
            if (Test-Path $IndexHtmlPath) {
                $HtmlBytes = [System.IO.File]::ReadAllBytes($IndexHtmlPath)
                $Response.ContentType = "text/html; charset=utf-8"
                $Response.StatusCode = 200
                $Response.OutputStream.Write($HtmlBytes, 0, $HtmlBytes.Length)
                $Response.Close()
                continue
            }
        }

        # ── 2. Health Endpoint ────────────────────────────────────────────────
        if ($Url -eq "/health" -and $Method -eq "GET") {
            $RespText = '{"status": "ok", "model": "Qwen3-4B-Instruct-Q4_K_M", "vram_free_mb": 1450}'
            $RespBytes = [System.Text.Encoding]::UTF8.GetBytes($RespText)
            $Response.ContentType = "application/json"
            $Response.StatusCode = 200
            $Response.OutputStream.Write($RespBytes, 0, $RespBytes.Length)
            $Response.Close()
            continue
        }

        # ── 3. Chat Completions Endpoint ──────────────────────────────────────
        if ($Url -eq "/v1/chat/completions" -and $Method -eq "POST") {
            $Reader = New-Object System.IO.StreamReader($Request.InputStream, [System.Text.Encoding]::UTF8)
            $BodyRaw = $Reader.ReadToEnd()
            $BodyJson = $BodyRaw | ConvertFrom-Json

            $UserMessage = ($BodyJson.messages | Where-Object { $_.role -eq "user" } | Select-Object -Last 1).content
            $SubStrLen = [Math]::Min(80, $UserMessage.Length)
            $Snippet = $UserMessage.Substring(0, $SubStrLen)
            Write-Host "    Processing Prompt: $Snippet..." -ForegroundColor Yellow

            Start-Sleep -Milliseconds 350

            $SimulatedAnswer = "[NEXUS HIGH-CONTEXT SYNTHESIS - RTX 2050 CUDA]`n`nAnalysis completed across 16,384 token window:`n1. Snapdragon 8 Elite Hexagon NPU handles sub-second voice triage offline.`n2. Laptop RTX 2050 GPU processes extended context without phone thermal load.`n3. System verified 100% operational via Office Kit interconnect."

            $PromptTokens = [Math]::Round($UserMessage.Length / 4)
            $CompletionTokens = 95
            $TotalTokens = $PromptTokens + $CompletionTokens

            $ResponsePayload = [ordered]@{
                id = "chatcmpl-" + [System.Guid]::NewGuid().ToString().Substring(0, 8)
                object = "chat.completion"
                created = [int][double]::Parse((Get-Date -UFormat %s))
                model = "Qwen3-4B-Instruct-Q4_K_M"
                choices = @(
                    @{
                        index = 0
                        message = @{
                            role = "assistant"
                            content = $SimulatedAnswer
                        }
                        finish_reason = "stop"
                    }
                )
                usage = @{
                    prompt_tokens = $PromptTokens
                    completion_tokens = $CompletionTokens
                    total_tokens = $TotalTokens
                }
            } | ConvertTo-Json -Depth 5

            $ResponseBytes = [System.Text.Encoding]::UTF8.GetBytes($ResponsePayload)
            $Response.ContentType = "application/json"
            $Response.StatusCode = 200
            $Response.OutputStream.Write($ResponseBytes, 0, $ResponseBytes.Length)
            $Response.Close()
            Write-Host "    [OK] Dispatched response (95 tokens in 350ms)" -ForegroundColor Green
            continue
        }

        # 404 for unknown endpoints
        $Response.StatusCode = 404
        $Response.Close()

    } catch {
        # Loop protection
    }
}
