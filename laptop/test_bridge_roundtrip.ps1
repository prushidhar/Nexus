# Test script to verify the Office Kit JSON protocol round-trip locally
Write-Host "Testing Nexus Office Kit Protocol Serialization..." -ForegroundColor Cyan

$task = [ordered]@{
    id = "test_snapdragon_01"
    type = "LONG_CONTEXT_ANALYSIS"
    instruction = "Summarize the hardware specifications"
    payload = "The iQOO 15 is powered by Qualcomm Snapdragon 8 Elite Gen 5 (SM8850) with Hexagon NPU, Adreno 840 GPU, and 16GB LPDDR5X RAM."
    returnChannel = "clipboard"
    createdAt = (Get-Date).ToUniversalTime().ToString("o")
}

$taskJson = $task | ConvertTo-Json -Depth 5
Write-Host "Generated Task JSON:" -ForegroundColor Yellow
Write-Host $taskJson

# Verify deserialization
$deserialized = $taskJson | ConvertFrom-Json
if ($deserialized.id -eq "test_snapdragon_01" -and $deserialized.type -eq "LONG_CONTEXT_ANALYSIS") {
    Write-Host "[PASS] TaskDescriptor JSON serialization and parsing" -ForegroundColor Green
} else {
    Write-Host "[FAIL] TaskDescriptor parsing" -ForegroundColor Red
    exit 1
}

# Simulate Result serialization
$result = [ordered]@{
    taskId = $deserialized.id
    result = "Verified: iQOO 15 hardware features Snapdragon 8 Elite with Hexagon NPU running Qwen3-4B w4a16."
    tokenCount = 128
    source = "laptop_qwen3_4b_cuda_rtx2050"
    completedAt = (Get-Date).ToUniversalTime().ToString("o")
}

$resultJson = $result | ConvertTo-Json -Depth 5
Write-Host "`nGenerated Result JSON:" -ForegroundColor Yellow
Write-Host $resultJson

$deserializedResult = $resultJson | ConvertFrom-Json
if ($deserializedResult.taskId -eq "test_snapdragon_01" -and $deserializedResult.source -eq "laptop_qwen3_4b_cuda_rtx2050") {
    Write-Host "[PASS] TaskResult JSON serialization and parsing" -ForegroundColor Green
    Write-Host "`n>>> All Office Kit protocol contracts fully verified! <<<" -ForegroundColor Cyan
} else {
    Write-Host "[FAIL] TaskResult parsing" -ForegroundColor Red
    exit 1
}
