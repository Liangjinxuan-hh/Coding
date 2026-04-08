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
$pythonExe = "python"
$py312 = Join-Path $root ".venv312\Scripts\python.exe"
$pyDefault = Join-Path $root ".venv\Scripts\python.exe"
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

function Stop-CameraModules {
    foreach ($moduleName in @("face", "hand")) {
        $jobs = Get-Job -Name $moduleName -ErrorAction SilentlyContinue
        if ($jobs) {
            foreach ($j in $jobs) {
                try {
                    Stop-Job -Id $j.Id -ErrorAction SilentlyContinue
                    Remove-Job -Id $j.Id -ErrorAction SilentlyContinue
                } catch {
                    Write-Warning ("Failed to cleanup existing job {0} (Id: {1})" -f $moduleName, $j.Id)
                }
            }
        }
    }

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

    # 避免重复同名作业导致端口冲突或状态混乱
    $existingJobs = Get-Job -Name $Name -ErrorAction SilentlyContinue
    if ($existingJobs) {
        foreach ($j in $existingJobs) {
            try {
                Stop-Job -Id $j.Id -ErrorAction SilentlyContinue
                Remove-Job -Id $j.Id -ErrorAction SilentlyContinue
            } catch {
                Write-Warning ("Failed to cleanup existing job {0} (Id: {1})" -f $Name, $j.Id)
            }
        }
    }

    $job = Start-Job -Name $Name -ScriptBlock {
        param($Dir, $Cmd)
        Set-Location $Dir
        Invoke-Expression $Cmd
    } -ArgumentList $WorkingDir, $Command

    Write-Host "[$Name] started (Job Id: $($job.Id))" -ForegroundColor DarkCyan
}

Write-Host "Using Python interpreter: $pythonExe" -ForegroundColor DarkGray
Stop-CameraModules
$bridgeCmd = "& `"$pythonExe`" -m uvicorn bridge.server:app --host 127.0.0.1 --port $bridgePort"
$webCmd = "& `"$pythonExe`" -m http.server 8081 --bind 127.0.0.1 --directory web"
Start-ModuleJob -Name "bridge" -WorkingDir $root -Command $bridgeCmd
Start-ModuleJob -Name "web" -WorkingDir $root -Command $webCmd

Write-Host "DripMotion stack launched. Open http://127.0.0.1:8081 (bridge: $bridgePort)" -ForegroundColor Green
Write-Host "Use page controls to start or stop face and hand modules." -ForegroundColor Green
Write-Host "Camera modules are not started at launch; click the web buttons to enable them." -ForegroundColor Green
Write-Host "Run Get-Job to inspect jobs, and Stop-Job -Name bridge/web to stop." -ForegroundColor Yellow
Start-Sleep -Seconds 1
Start-Process "http://127.0.0.1:8081"
