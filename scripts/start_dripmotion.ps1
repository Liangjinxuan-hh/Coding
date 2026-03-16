param(
    [switch]$InstallDeps
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $scriptDir
$bridgeDir = Join-Path $root "bridge"
$webDir = Join-Path $root "web"
$faceDir = Join-Path $root "Face\PythonProject"
$handDir = Join-Path $root "Hand"
$pythonExe = "python"
$py312 = Join-Path $root ".venv312\Scripts\python.exe"
$pyDefault = Join-Path $root ".venv\Scripts\python.exe"
if (Test-Path $py312) {
    $pythonExe = $py312
} elseif (Test-Path $pyDefault) {
    $pythonExe = $pyDefault
}

if ($InstallDeps) {
    Write-Host "Installing bridge dependencies..." -ForegroundColor Cyan
    & $pythonExe -m pip install -r (Join-Path $bridgeDir "requirements.txt")

    $faceReq = Join-Path $faceDir "requirements.txt"
    if (Test-Path $faceReq) {
        Write-Host "Installing face module dependencies..." -ForegroundColor Cyan
        & $pythonExe -m pip install -r $faceReq
    }

    $handReq = Join-Path $handDir "requirements.txt"
    if (Test-Path $handReq) {
        Write-Host "Installing hand module dependencies..." -ForegroundColor Cyan
        & $pythonExe -m pip install -r $handReq
    }
}

function Start-ModuleJob {
    param (
        [string]$Name,
        [string]$WorkingDir,
        [string]$Command
    )

    if (-not (Test-Path $WorkingDir)) {
        Write-Warning ("Skip {0}: path not found {1}" -f $Name, $WorkingDir)
        return
    }

    $job = Start-Job -Name $Name -ScriptBlock {
        param($Dir, $Cmd)
        Set-Location $Dir
        Invoke-Expression $Cmd
    } -ArgumentList $WorkingDir, $Command

    Write-Host "[$Name] started (Job Id: $($job.Id))" -ForegroundColor DarkCyan
}

$bridgeCmd = "& `"$pythonExe`" -m uvicorn server:app --reload --port 5050"
$webCmd = "& `"$pythonExe`" -m http.server 8081 --bind 127.0.0.1 --directory web"
Start-ModuleJob -Name "bridge" -WorkingDir $bridgeDir -Command $bridgeCmd
Start-ModuleJob -Name "web" -WorkingDir $root -Command $webCmd

Write-Host "DripMotion stack launched. Open http://127.0.0.1:8081" -ForegroundColor Green
Write-Host "Use page controls to start or stop face and hand modules." -ForegroundColor Green
Write-Host "Run Get-Job to inspect jobs, and Stop-Job -Name bridge/web to stop." -ForegroundColor Yellow
