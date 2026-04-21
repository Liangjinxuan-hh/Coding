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

function Stop-InteractiveModules {
	$moduleProcesses = Get-CimInstance Win32_Process | Where-Object {
		$_.Name -eq 'python.exe' -and (
			$_.CommandLine -match 'main\.py' -or
			$_.CommandLine -match 'main2\.py' -or
			$_.CommandLine -match 'voice_module\.py'
		)
	}

	foreach ($proc in $moduleProcesses) {
		try {
			Stop-Process -Id $proc.ProcessId -Force -ErrorAction Stop
			Write-Host ("[module] stopped stale interactive module PID: {0}" -f $proc.ProcessId) -ForegroundColor DarkYellow
		} catch {
			Write-Warning ("Failed to stop interactive module {0}: {1}" -f $proc.ProcessId, $_.Exception.Message)
		}
	}
}

Stop-ProcessByPidFile -Name "bridge" -PidFile $bridgePidFile
Stop-ProcessByPidFile -Name "web" -PidFile $webPidFile
Stop-ProcessByPort -Name "bridge" -Port 5051
Stop-ProcessByPort -Name "web" -Port 8081
Stop-InteractiveModules

Write-Host "DripMotion services stopped." -ForegroundColor Green
