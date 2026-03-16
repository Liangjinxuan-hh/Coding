# DripMotion Startup & Acceptance Checklist

This checklist is designed for repeated daily bring-up and quick regression checks.

## 1) Prerequisites

- Windows 10/11
- Python 3.10+
- Camera device available
- Optional: Arduino/serial device connected

## 2) One-time Dependency Install

Run from project root:

```powershell
python -m pip install -r bridge/requirements.txt
python -m pip install -r Face/PythonProject/requirements.txt
python -m pip install -r Hand/requirements.txt
```

## 3) Standard Startup (Recommended)

Run from project root:

```powershell
\.venv312\Scripts\Activate.ps1
powershell -ExecutionPolicy Bypass -File scripts/start_dripmotion.ps1
```

Expected:
- bridge job starts successfully
- web job starts successfully
- browser opens `http://127.0.0.1:8081` manually by user

## 4) Manual Startup (Fallback)

### 4.1 Start bridge

```powershell
Set-Location bridge
python -m uvicorn server:app --reload --port 5050
```

### 4.2 Start web static server (new terminal)

```powershell
Set-Location ..
python -m http.server 8081 --bind 127.0.0.1 --directory web
```

### 4.3 Open web page

- Open `http://127.0.0.1:8081`

## 5) Runtime Control Flow Check

In web page:
- click "开启面部交互" and confirm state turns to running
- click "结束面部交互" and confirm state turns to stopped
- wait 3-5 seconds before starting hand module (camera release window)
- click "开启手势交互" and confirm state turns to running
- click "结束手势交互" and confirm state turns to stopped

Expected API behavior:
- `GET /health` returns status ok
- `GET /api/control/status` returns module states
- `POST /api/control` start/stop changes target module state

## 6) Acceptance Test Matrix

### A. Bridge availability
- [ ] `http://127.0.0.1:5050/health` returns JSON with `status: ok`
- [ ] web status changes from disconnected to connected

### B. Face module
- [ ] module can start from web control
- [ ] camera window appears
- [ ] status card updates (`direction`, `eye`, `mouth`)
- [ ] frame preview updates
- [ ] serial status text updates correctly in UI

### C. Hand module
- [ ] module can start from web control
- [ ] camera window appears
- [ ] LED columns and gesture log update
- [ ] command events trigger model movement

### D. Web command mapping
- [ ] button `上移` moves up
- [ ] button `下移` moves down
- [ ] button `左转` rotates left
- [ ] button `右转` rotates right
- [ ] button `停止` stops motion

### E. End-to-end relay
- [ ] Face/Hand command event appears in web and triggers action
- [ ] module start/stop broadcast reflected in chips

## 7) Shutdown Procedure

If started by `Start-Job` script:

```powershell
Get-Job
Stop-Job -Name bridge
Stop-Job -Name web
Remove-Job -Name bridge,web
```

If started manually:
- press `Ctrl+C` in each terminal

## 8) Known Operational Notes

- Only one process should own the same camera at a time.
- Archived legacy Face copy has been moved to:
  - `Face/_archive/PythonProject_legacy_20260316`
- Active Face source of truth is:
  - `Face/PythonProject`
