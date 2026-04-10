param()

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$root = Split-Path -Parent $scriptDir
$runtimeDir = Join-Path $root ".runtime"
$bridgePidFile = Join-Path $runtimeDir "bridge.pid"
$webPidFile = Join-Path $runtimeDir "web.pid"

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

Stop-ProcessByPidFile -Name "bridge" -PidFile $bridgePidFile
Stop-ProcessByPidFile -Name "web" -PidFile $webPidFile
Stop-ProcessByPort -Name "bridge" -Port 5051
Stop-ProcessByPort -Name "web" -Port 8081

Write-Host "DripMotion services stopped." -ForegroundColor Green
