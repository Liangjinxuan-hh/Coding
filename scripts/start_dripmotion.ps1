param(
    [switch]$InstallDeps
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $scriptDir
$bridgeDir = Join-Path $root "bridge"
$webDir = Join-Path $root "web"
$faceDir = Join-Path $root "Face\PythonProject"
$handDir = Join-Path $root "Hand"
$bridgePort = 5051
$webPort = 8081
$pythonExe = "python"
$py312 = Join-Path $root ".venv312\Scripts\python.exe"
$pyDefault = Join-Path $root ".venv\Scripts\python.exe"
$runtimeDir = Join-Path $root ".runtime"
$bridgePidFile = Join-Path $runtimeDir "bridge.pid"
$webPidFile = Join-Path $runtimeDir "web.pid"
if (Test-Path $py312) {
    $pythonExe = (Resolve-Path $py312).Path
} elseif (Test-Path $pyDefault) {
    $pythonExe = (Resolve-Path $pyDefault).Path
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

$env:DRIP_BRIDGE_PORT = "$bridgePort"
$env:DRIP_EVENT_ENDPOINT = "http://127.0.0.1:$bridgePort/api/events"
$env:DRIP_LOCAL_PREVIEW = "0"

function Ensure-RuntimeDir {
    if (-not (Test-Path $runtimeDir)) {
        New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
    }
}

function Stop-ProcessByPidFile {
    param (
        [string]$Name,
        [string]$PidFile
    )

    if (-not (Test-Path $PidFile)) {
        return
    }

    $rawPid = Get-Content $PidFile -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($rawPid -match '^\d+$') {
        $pidNum = [int]$rawPid
        $proc = Get-Process -Id $pidNum -ErrorAction SilentlyContinue
        if ($proc) {
            try {
                Stop-Process -Id $pidNum -Force -ErrorAction Stop
                Write-Host ("[{0}] stopped (PID: {1})" -f $Name, $pidNum) -ForegroundColor DarkYellow
            } catch {
                Write-Warning ("Failed to stop {0} PID {1}: {2}" -f $Name, $pidNum, $_.Exception.Message)
            }
        }
    }

    Remove-Item $PidFile -ErrorAction SilentlyContinue
}

function Stop-ProcessByPort {
    param (
        [int]$Port,
        [string]$Name
    )

    $listeners = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue
    if (-not $listeners) {
        return
    }

    foreach ($listener in $listeners) {
        $pidNum = $listener.OwningProcess
        if ($pidNum -and $pidNum -gt 0) {
            try {
                Stop-Process -Id $pidNum -Force -ErrorAction Stop
                Write-Host ("[{0}] stopped by port {1} (PID: {2})" -f $Name, $Port, $pidNum) -ForegroundColor DarkYellow
            } catch {
                Write-Warning ("Failed to stop PID {0} on port {1}: {2}" -f $pidNum, $Port, $_.Exception.Message)
            }
        }
    }
}

function Start-ModuleProcess {
    param (
        [string]$Name,
        [string]$ArgumentList,
        [string]$PidFile
    )

    $proc = Start-Process -FilePath $pythonExe -ArgumentList $ArgumentList -WorkingDirectory $root -WindowStyle Hidden -PassThru
    Set-Content -Path $PidFile -Value "$($proc.Id)" -Encoding ascii
    Write-Host "[$Name] started (PID: $($proc.Id))" -ForegroundColor DarkCyan
}

function Stop-CameraModules {
    $cameraProcesses = Get-CimInstance Win32_Process | Where-Object {
        $_.Name -eq 'python.exe' -and (
            $_.CommandLine -match 'main\.py' -or
            $_.CommandLine -match 'main2\.py'
        )
    }

    foreach ($proc in $cameraProcesses) {
        try {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
            Write-Host ("Stopped stale camera process {0}: {1}" -f $proc.ProcessId, $proc.CommandLine) -ForegroundColor DarkYellow
        } catch {
            Write-Warning ("Failed to stop camera process {0}: {1}" -f $proc.ProcessId, $_.Exception.Message)
        }
    }
}

Write-Host "Using Python interpreter: $pythonExe" -ForegroundColor DarkGray
Ensure-RuntimeDir
Stop-ProcessByPidFile -Name "bridge" -PidFile $bridgePidFile
Stop-ProcessByPidFile -Name "web" -PidFile $webPidFile
Stop-ProcessByPort -Name "bridge" -Port $bridgePort
Stop-ProcessByPort -Name "web" -Port $webPort
Stop-CameraModules
$bridgeArgs = "-m uvicorn bridge.server:app --host 127.0.0.1 --port $bridgePort"
$webArgs = "-m http.server $webPort --bind 127.0.0.1 --directory web"
Start-ModuleProcess -Name "bridge" -ArgumentList $bridgeArgs -PidFile $bridgePidFile
Start-ModuleProcess -Name "web" -ArgumentList $webArgs -PidFile $webPidFile

Write-Host "DripMotion stack launched. Open http://127.0.0.1:8081 (bridge: $bridgePort)" -ForegroundColor Green
Write-Host "Use page controls to start or stop face and hand modules." -ForegroundColor Green
Write-Host "Camera modules are not started at launch; click the web buttons to enable them." -ForegroundColor Green
Write-Host "Run Stop_DripMotion.bat to stop bridge and web." -ForegroundColor Yellow
Start-Process "http://127.0.0.1:8081"
