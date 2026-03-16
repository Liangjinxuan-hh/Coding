import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import {
  FaceLandmarker,
  HandLandmarker,
  FilesetResolver,
  DrawingUtils
} from 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14';

const canvas = document.getElementById("dripCanvas");
const renderer = new THREE.WebGLRenderer({ canvas, antialias: true, alpha: true });
renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));

const scene = new THREE.Scene();
scene.background = null;

const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 50);
camera.position.set(2.8, 2.4, 3.6);

const controls = new OrbitControls(camera, canvas);
controls.enableDamping = true;
controls.enablePan = false;
controls.maxPolarAngle = Math.PI * 0.58;
controls.minDistance = 2;
controls.maxDistance = 8;

const ambient = new THREE.AmbientLight(0xbfd6ff, 0.4);
scene.add(ambient);

const keyLight = new THREE.DirectionalLight(0xffffff, 0.9);
keyLight.position.set(4, 6, 4);
scene.add(keyLight);

const rimLight = new THREE.DirectionalLight(0x65f8d3, 0.6);
rimLight.position.set(-3, 5, -2);
scene.add(rimLight);

const platform = new THREE.Mesh(
  new THREE.CylinderGeometry(2, 2.2, 0.35, 64),
  new THREE.MeshStandardMaterial({ color: 0x101b3a, roughness: 0.3, metalness: 0.4 })
);
scene.add(platform);

const deck = new THREE.Mesh(
  new THREE.CylinderGeometry(1.4, 1.5, 0.12, 48),
  new THREE.MeshStandardMaterial({ color: 0x1c315d, roughness: 0.35, metalness: 0.55 })
);
deck.position.y = 0.235;
scene.add(deck);

const topPivot = new THREE.Group();
topPivot.position.y = 0.35;
scene.add(topPivot);

const topPart = new THREE.Mesh(
  new THREE.CylinderGeometry(1.1, 1, 0.16, 48),
  new THREE.MeshStandardMaterial({ color: 0x65f8d3, emissive: 0x11332f, metalness: 0.85, roughness: 0.2 })
);
topPart.castShadow = true;
topPivot.add(topPart);

const emitter = new THREE.Mesh(
  new THREE.TorusGeometry(0.8, 0.04, 24, 64),
  new THREE.MeshStandardMaterial({ color: 0xff9d5c, emissive: 0x2a1205 })
);
emitter.position.y = 0.14;
topPivot.add(emitter);

const floor = new THREE.Mesh(
  new THREE.CircleGeometry(4, 80),
  new THREE.MeshBasicMaterial({ color: 0x0a152f, transparent: true, opacity: 0.8 })
);
floor.rotation.x = -Math.PI / 2;
floor.position.y = -0.2;
scene.add(floor);

const statusText = document.getElementById("statusText");
const heightValue = document.getElementById("heightValue");
const angleValue = document.getElementById("angleValue");
const bridgeStatusEl = document.getElementById("bridgeStatus");
const faceStateEl = document.getElementById("faceState");
const handStateEl = document.getElementById("handState");
const faceStartBtn = document.getElementById("faceStart");
const faceStopBtn = document.getElementById("faceStop");
const handStartBtn = document.getElementById("handStart");
const handStopBtn = document.getElementById("handStop");

const faceBindings = {
  status: document.getElementById("faceStatus"),
  direction: document.getElementById("faceDirection"),
  eye: document.getElementById("faceEye"),
  mouth: document.getElementById("faceMouth"),
  serial: document.getElementById("faceSerial"),
  cmd: document.getElementById("faceCommand"),
  mode: document.getElementById("faceMode"),
  stream: document.getElementById("faceStream"),
};

const handBindings = {
  badge: document.getElementById("handLastAction"),
  ledGrid: document.getElementById("handLedGrid"),
  gestures: document.getElementById("handGestureList"),
  stream: document.getElementById("handStream"),
};

const motionState = {
  moveDir: 0,
  rotateDir: 0,
  heightCm: 0,
  angleDeg: 0,
  limits: { min: 0.35, max: 0.9 },
  moveSpeed: 0.25,
  rotateSpeed: THREE.MathUtils.degToRad(60)
};

const clock = new THREE.Clock();

function resizeRenderer() {
  const width = canvas.clientWidth;
  const height = canvas.clientHeight;
  const needsResize = canvas.width !== width || canvas.height !== height;
  if (needsResize) {
    renderer.setSize(width, height, false);
    camera.aspect = width / height || 1;
    camera.updateProjectionMatrix();
  }
}

function clamp(value, min, max) {
  return Math.min(Math.max(value, min), max);
}

function updateStatus(text) {
  if (statusText) statusText.textContent = text;
  if (heightValue) heightValue.textContent = `${motionState.heightCm.toFixed(1)} cm`;
  if (angleValue) angleValue.textContent = `${motionState.angleDeg.toFixed(0)}°`;
}

function startMove(dir) {
  motionState.moveDir = dir;
  motionState.rotateDir = 0;
  updateStatus(dir > 0 ? "上表面部件 - 上升中" : "上表面部件 - 下降中");
}

function startRotate(dir) {
  motionState.rotateDir = dir;
  motionState.moveDir = 0;
  updateStatus(dir > 0 ? "上表面部件 - 左转中" : "上表面部件 - 右转中");
}

function stopMotion(label = "上表面部件 - 停止") {
  motionState.moveDir = 0;
  motionState.rotateDir = 0;
  updateStatus(label);
}

function applyCommand(action) {
  switch (action) {
    case "moveUp":
      startMove(1);
      break;
    case "moveDown":
      startMove(-1);
      break;
    case "rotateLeft":
      startRotate(1);
      break;
    case "rotateRight":
      startRotate(-1);
      break;
    case "stop":
      stopMotion();
      break;
    default:
      break;
  }
}

function stepPhysics(delta) {
  if (motionState.moveDir !== 0) {
    const offset = motionState.moveDir * motionState.moveSpeed * delta;
    topPivot.position.y = clamp(topPivot.position.y + offset, motionState.limits.min, motionState.limits.max);
    const reachedTop = topPivot.position.y >= motionState.limits.max && motionState.moveDir > 0;
    const reachedBottom = topPivot.position.y <= motionState.limits.min && motionState.moveDir < 0;
    if (reachedTop) stopMotion("上表面部件 - 达到最高点");
    if (reachedBottom) stopMotion("上表面部件 - 达到最低点");
  }

  if (motionState.rotateDir !== 0) {
    topPivot.rotation.z += motionState.rotateDir * motionState.rotateSpeed * delta;
    motionState.angleDeg = THREE.MathUtils.radToDeg(topPivot.rotation.z) % 360;
  }

  motionState.heightCm = (topPivot.position.y - motionState.limits.min) * 100;
}

function renderLoop() {
  requestAnimationFrame(renderLoop);
  const delta = clock.getDelta();
  resizeRenderer();
  stepPhysics(delta);
  controls.update();
  renderer.render(scene, camera);
  updateStatus(statusText.textContent || "上表面部件 - 就绪");
}

renderLoop();

const buttons = document.querySelectorAll(".control-btn");
buttons.forEach((btn) => {
  btn.addEventListener("click", () => {
    const command = btn.dataset.command;
    applyCommand(command);
  });
});

const aliasMap = {
  moveUp: ["上移", "上", "up"],
  moveDown: ["下移", "下", "down"],
  rotateLeft: ["左转", "左", "left"],
  rotateRight: ["右转", "右", "right"],
  stop: ["停止", "stop", "s"]
};

const FACE_COMMAND_MAP = {
  LOOK_LEFT: "rotateLeft",
  LOOK_RIGHT: "rotateRight",
  DEFAULT: "stop",
  CLOSE_EYES: "moveDown",
  OPEN_EYES: "moveUp",
  OPEN_MOUTH: "moveUp",
  CLOSE_MOUTH: "stop",
};

const HAND_COMMAND_MAP = {
  moveUp: "moveUp",
  moveDown: "moveDown",
  rotateLeft: "rotateLeft",
  rotateRight: "rotateRight",
  stop: "stop",
};

function normalizeCommand(raw) {
  if (!raw) return null;
  const trimmed = raw.trim();
  const lowered = trimmed.toLowerCase();
  for (const [action, aliases] of Object.entries(aliasMap)) {
    if (aliases.some((term) => term === trimmed || term === lowered)) {
      return action;
    }
  }
  return null;
}

class CommandHub {
  constructor() {
    window.DripCommandHub = {
      send: (cmd) => this.ingest(cmd),
      getState: () => ({
        heightCm: motionState.heightCm,
        angleDeg: motionState.angleDeg,
        status: statusText.textContent
      })
    };

    window.addEventListener("message", (event) => {
      const payload = event.data;
      if (payload && payload.type === "dd-command") {
        this.ingest(payload.payload);
      }
    });
  }

  ingest(raw) {
    const action = normalizeCommand(raw);
    if (action) {
      applyCommand(action);
    } else {
      console.warn("未识别的指令:", raw);
    }
  }
}

const hub = new CommandHub();

function updateBridgeStatus(text, tone = "idle") {
  if (!bridgeStatusEl) return;
  bridgeStatusEl.textContent = text;
  bridgeStatusEl.dataset.tone = tone;
}

function setModuleState(target, running, error = false) {
  const el = target === "face" ? faceStateEl : handStateEl;
  if (!el) return;
  el.textContent = `${target === "face" ? "面部" : "手势"}：${running ? "运行中" : "未启动"}`;
  el.classList.remove("chip--active", "chip--idle", "chip--error");
  if (error) {
    el.classList.add("chip", "chip--error");
  } else if (running) {
    el.classList.add("chip", "chip--active");
  } else {
    el.classList.add("chip", "chip--idle");
  }

  const startBtn = target === "face" ? faceStartBtn : handStartBtn;
  const stopBtn = target === "face" ? faceStopBtn : handStopBtn;
  if (startBtn) startBtn.disabled = running;
  if (stopBtn) stopBtn.disabled = !running;
}

function connectBridge() {
  if (!("WebSocket" in window)) {
    updateBridgeStatus("桥接服务：浏览器不支持 WebSocket", "error");
    return;
  }
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const host = window.location.hostname || "127.0.0.1";
  const socket = new WebSocket(`${protocol}://${host}:5050/ws`);
  socket.addEventListener("open", () => {
    updateBridgeStatus("桥接服务：已连接", "ok");
    refreshModuleStatus();
  });
  socket.addEventListener("close", () => {
    updateBridgeStatus("桥接服务：断开，重连中...", "warn");
    setTimeout(connectBridge, 2000);
  });
  socket.addEventListener("error", () => updateBridgeStatus("桥接服务：连接异常", "error"));
  socket.addEventListener("message", handleBridgeMessage);
}

function handleBridgeMessage(event) {
  try {
    const data = JSON.parse(event.data);
    handleBridgeEvent(data);
  } catch (err) {
    console.warn("无法解析桥接消息", err);
  }
}

function handleBridgeEvent(message) {
  if (!message || !message.channel) return;
  if (message.channel === "face") {
    if (message.type === "status") updateFaceCard(message.payload || {});
    if (message.type === "frame" && message.payload?.data && faceBindings.stream) {
      faceBindings.stream.src = `data:image/jpeg;base64,${message.payload.data}`;
    }
    if (message.type === "command") {
      const next = FACE_COMMAND_MAP[message.payload?.command];
      if (faceBindings.cmd && message.payload?.command) {
        faceBindings.cmd.textContent = message.payload.command;
      }
      if (next) relayExternalCommand("face", next, message.payload);
    }
    if (message.type === "voice") {
      if (faceBindings.mode) {
        faceBindings.mode.textContent = `语音:${message.payload?.status ?? "--"}`;
      }
    }
    return;
  }

  if (message.channel === "hand") {
    if (message.type === "status") updateHandCard(message.payload || {});
    if (message.type === "frame" && message.payload?.data && handBindings.stream) {
      handBindings.stream.src = `data:image/jpeg;base64,${message.payload.data}`;
    }
    if (message.type === "command") {
      const next = HAND_COMMAND_MAP[message.payload?.action];
      if (next) {
        if (handBindings.badge) {
          handBindings.badge.textContent = `手势 → ${message.payload?.action}`;
        }
        relayExternalCommand("hand", next, message.payload);
      }
    }
  }
  if (message.channel === "system" && message.type === "module") {
    const { target, running } = message.payload || {};
    if (target) setModuleState(target, Boolean(running));
  }
}

async function callModuleControl(target, action) {
  try {
    const response = await fetch(getControlUrl("/api/control"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target, action }),
    });
    const json = await response.json();
    if (!response.ok || json.status !== "ok") {
      setModuleState(target, false, true);
    } else {
      const running = json.modules?.[target];
      setModuleState(target, Boolean(running));
    }
  } catch (err) {
    console.warn("控制模块失败", err);
    setModuleState(target, false, true);
  }
}

function getControlUrl(path) {
  const host = window.location.hostname || "127.0.0.1";
  const protocol = window.location.protocol.startsWith("http")
    ? window.location.protocol
    : "http:";
  return `${protocol}//${host}:5050${path}`;
}

async function refreshModuleStatus() {
  try {
    const response = await fetch(getControlUrl("/api/control/status"));
    const json = await response.json();
    if (json.modules) {
      Object.entries(json.modules).forEach(([key, value]) => {
        setModuleState(key, Boolean(value));
      });
    }
  } catch (err) {
    setModuleState("face", false, true);
    setModuleState("hand", false, true);
  }
}

function updateFaceCard(payload) {
  if (!faceBindings.status) return;
  if (payload.status_text) {
    faceBindings.status.textContent = `当前状态：${payload.status_text}`;
  }
  if (payload.direction) {
    faceBindings.direction.textContent = payload.direction.replace("LOOK_", "");
  }
  if (payload.eye) faceBindings.eye.textContent = payload.eye;
  if (payload.mouth) faceBindings.mouth.textContent = payload.mouth;
  if (payload.serial_status) faceBindings.serial.textContent = payload.serial_status;
  if (payload.last_command) faceBindings.cmd.textContent = payload.last_command;
  if (payload.voice_mode) {
    faceBindings.mode.textContent = payload.voice_mode === "voice" ? "语音模式" : "面部模式";
    faceBindings.mode.classList.toggle("alert", payload.voice_mode === "voice");
  }
}

function updateHandCard(payload) {
  if (payload.left || payload.right) renderLedColumns(payload);
  if (Array.isArray(payload.gestures) && handBindings.gestures) {
    const lines = payload.gestures.slice(-4);
    handBindings.gestures.innerHTML = "";
    lines.forEach((line) => {
      const li = document.createElement("li");
      li.textContent = line;
      handBindings.gestures.appendChild(li);
    });
  }
}

function renderLedColumns(payload) {
  if (!handBindings.ledGrid) return;
  handBindings.ledGrid.innerHTML = "";
  [
    { label: "左手", data: payload.left },
    { label: "右手", data: payload.right },
  ].forEach(({ label, data }) => {
    if (!Array.isArray(data)) return;
    const column = document.createElement("div");
    column.className = "led-column";
    const title = document.createElement("span");
    title.textContent = label;
    title.style.fontSize = "0.85rem";
    title.style.color = "var(--fg-muted)";
    column.appendChild(title);
    data.forEach((led) => {
      const cell = document.createElement("div");
      cell.className = "led-cell";
      cell.style.background = led.is_on ? led.color : "rgba(255,255,255,0.06)";
      cell.style.opacity = led.is_on ? Math.max(0.15, led.brightness / 255) : 0.2;
      if (led.selected) cell.classList.add("selected");
      column.appendChild(cell);
    });
    handBindings.ledGrid.appendChild(column);
  });
}

function relayExternalCommand(source, mappedCommand, rawPayload) {
  applyCommand(mappedCommand);
  if (source === "hand" && handBindings.badge) {
    handBindings.badge.textContent = `手势 → ${rawPayload?.action ?? mappedCommand}`;
  }
  if (source === "face" && faceBindings.cmd && rawPayload?.command) {
    faceBindings.cmd.textContent = rawPayload.command;
  }
}

const commandInput = document.getElementById("commandInput");
const commandSend = document.getElementById("commandSend");
if (commandInput && commandSend) {
  commandSend.addEventListener("click", () => {
    hub.ingest(commandInput.value);
    commandInput.value = "";
  });
  commandInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      hub.ingest(commandInput.value);
      commandInput.value = "";
    }
  });
}

if (faceStartBtn) faceStartBtn.addEventListener("click", () => callModuleControl("face", "start"));
if (faceStopBtn) faceStopBtn.addEventListener("click", () => callModuleControl("face", "stop"));
if (handStartBtn) handStartBtn.addEventListener("click", () => callModuleControl("hand", "start"));
if (handStopBtn) handStopBtn.addEventListener("click", () => callModuleControl("hand", "stop"));

const videoEl = document.getElementById('cam');
const canvasEl = document.getElementById('overlay');
const ctx = canvasEl ? canvasEl.getContext('2d') : null;

let faceLandmarker;
let handLandmarker;
let drawingUtils;
let stream;
let running = false;
let tasksReady = false;

async function ensureTasks() {
  if (tasksReady || !ctx) return;
  const vision = await FilesetResolver.forVisionTasks(
    'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@0.10.14/wasm'
  );
  faceLandmarker = await FaceLandmarker.createFromOptions(vision, {
    baseOptions: {
      modelAssetPath: 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task'
    },
    runningMode: 'VIDEO',
    numFaces: 1
  });
  handLandmarker = await HandLandmarker.createFromOptions(vision, {
    baseOptions: {
      modelAssetPath: 'https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/latest/hand_landmarker.task'
    },
    runningMode: 'VIDEO',
    numHands: 2
  });
  drawingUtils = new DrawingUtils(ctx);
  tasksReady = true;
}

async function startCamera() {
  if (stream) return;
  stream = await navigator.mediaDevices.getUserMedia({
    video: { width: 480, height: 360 },
    audio: false
  });
  videoEl.srcObject = stream;
  await videoEl.play();
}

async function processFrame() {
  if (!running || !tasksReady || !ctx) return;

  const timestamp = performance.now();
  ctx.clearRect(0, 0, canvasEl.width, canvasEl.height);

  const faceResult = faceLandmarker.detectForVideo(videoEl, timestamp);
  if (faceResult?.faceLandmarks) {
    faceResult.faceLandmarks.forEach(landmarks => {
      drawingUtils.drawConnectors(
        landmarks,
        FaceLandmarker.FACE_LANDMARKS_TESSELATION,
        { color: '#00FF7F', lineWidth: 1 }
      );
      drawingUtils.drawLandmarks(landmarks, { color: '#FFEE58', radius: 1.5 });
    });
  }

  const handResult = handLandmarker.detectForVideo(videoEl, timestamp);
  if (handResult?.landmarks) {
    handResult.landmarks.forEach((landmarks, index) => {
      drawingUtils.drawConnectors(
        landmarks,
        HandLandmarker.HAND_CONNECTIONS,
        { color: index === 0 ? '#4FC3F7' : '#FF7043', lineWidth: 2 }
      );
      drawingUtils.drawLandmarks(landmarks, { color: '#FFFFFF', radius: 2 });
    });
  }

  requestAnimationFrame(processFrame);
}

async function startBrowserML() {
  if (running || !videoEl || !canvasEl) return;
  running = true;
  try {
    await startCamera();
    await ensureTasks();
    requestAnimationFrame(processFrame);
  } catch (err) {
    console.error('浏览器端识别启动失败', err);
    running = false;
  }
}

document.getElementById('btnStartBrowserML')?.addEventListener('click', () => {
  if (!running) startBrowserML();
});

window.addEventListener("resize", () => resizeRenderer());
resizeRenderer();
connectBridge();
stopMotion();
