import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";

const canvas = document.getElementById("dripCanvas");
const modelStatusEl = document.getElementById("modelStatus");
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

const fallbackRoot = new THREE.Group();
scene.add(fallbackRoot);

const platform = new THREE.Mesh(
  new THREE.CylinderGeometry(2, 2.2, 0.35, 64),
  new THREE.MeshStandardMaterial({ color: 0x101b3a, roughness: 0.3, metalness: 0.4 })
);
fallbackRoot.add(platform);

const deck = new THREE.Mesh(
  new THREE.CylinderGeometry(1.4, 1.5, 0.12, 48),
  new THREE.MeshStandardMaterial({ color: 0x1c315d, roughness: 0.35, metalness: 0.55 })
);
deck.position.y = 0.235;
fallbackRoot.add(deck);

const topPivot = new THREE.Group();
topPivot.position.y = 0.35;
fallbackRoot.add(topPivot);

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

const modelAnchor = new THREE.Group();
scene.add(modelAnchor);

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
const voiceStateEl = document.getElementById("voiceState");
const faceStartBtn = document.getElementById("faceStart");
const faceStopBtn = document.getElementById("faceStop");
const handStartBtn = document.getElementById("handStart");
const handStopBtn = document.getElementById("handStop");
const voiceStartBtn = document.getElementById("voiceStart");
const voiceStopBtn = document.getElementById("voiceStop");

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

const voiceBindings = {
  badge: document.getElementById("voiceBadge"),
  status: document.getElementById("voiceStatus"),
  transcript: document.getElementById("voiceTranscript"),
  command: document.getElementById("voiceCommand"),
};

function setStreamVisibility(target, running) {
  if (target === "voice") return;
  const img = target === "face" ? faceBindings.stream : handBindings.stream;
  if (!img) return;
  img.style.visibility = running ? "visible" : "hidden";
  img.style.opacity = running ? "1" : "0";
}

function focusModuleCard(target) {
  const card = target === "face"
    ? document.getElementById("faceCard")
    : target === "hand"
      ? document.getElementById("handCard")
      : document.getElementById("voiceCard");
  card?.scrollIntoView({ behavior: "smooth", block: "center" });
}

const motionState = {
  moveDir: 0,
  rotateDir: 0,
  heightOffset: 0,
  rotationOffset: 0,
  heightCm: 0,
  angleDeg: 0,
  limits: { min: 0, max: 0.55 },
  moveSpeed: 0.25,
  rotateSpeed: THREE.MathUtils.degToRad(60)
};

const motionBinding = {
  moveTarget: topPivot,
  rotateTarget: topPivot,
  baseY: topPivot.position.y,
  baseRotation: topPivot.rotation.z,
  rotationAxis: "z",
  source: "fallback",
};

const modelLoader = new GLTFLoader();
const MODEL_URL = new URL("./models/dripmotion.glb?v=20260316-named2", import.meta.url).href;
const MODEL_TARGET_NAMES = new Set(["toppart", "top_part", "top-part", "top"]);
const MOVABLE_RING_PATTERNS = [
  /^part_09_ringband$/i,
  /^part_10_ringdiscinner$/i,
  /^part_11_ringpatterna$/i,
  /^part_12_ringpatternb$/i,
  /^part_13_ringpatternc$/i,
  /^part_14_ringpatternd$/i,
  /^part_15_ringpatterne$/i,
  /^part_16_ringdiscouter$/i,
];

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

function normalizeDegrees(value) {
  return ((value % 360) + 360) % 360;
}

function updateModelStatus(text, tone = "idle") {
  if (!modelStatusEl) return;
  modelStatusEl.textContent = text;
  modelStatusEl.dataset.tone = tone;
}

function setFallbackVisible(visible) {
  fallbackRoot.visible = visible;
}

function syncMotionBinding() {
  if (!motionBinding.moveTarget || !motionBinding.rotateTarget) return;
  motionBinding.moveTarget.position.y = motionBinding.baseY + motionState.heightOffset;
  motionBinding.rotateTarget.rotation[motionBinding.rotationAxis] = motionBinding.baseRotation + motionState.rotationOffset;
  motionState.heightCm = motionState.heightOffset * 100;
  motionState.angleDeg = normalizeDegrees(THREE.MathUtils.radToDeg(motionState.rotationOffset));
}

function bindMotionTargets(moveTarget, rotateTarget, source, rotationAxis = "z") {
  if (!moveTarget || !rotateTarget) return;
  motionBinding.moveTarget = moveTarget;
  motionBinding.rotateTarget = rotateTarget;
  motionBinding.baseY = moveTarget.position.y;
  motionBinding.baseRotation = rotateTarget.rotation[rotationAxis];
  motionBinding.rotationAxis = rotationAxis;
  motionBinding.source = source;
  syncMotionBinding();
}

function normalizeLoadedModel(root) {
  // 当前导出的 GLB 在 Web 里呈现为上下颠倒，先整体翻转再归一化。
  root.rotation.x = Math.PI;
  root.updateMatrixWorld(true);

  const initialBox = new THREE.Box3().setFromObject(root);
  const initialSize = initialBox.getSize(new THREE.Vector3());
  const maxDim = Math.max(initialSize.x, initialSize.y, initialSize.z, 0.001);
  const scale = 2.6 / maxDim;
  root.scale.setScalar(scale);
  root.updateMatrixWorld(true);

  const scaledBox = new THREE.Box3().setFromObject(root);
  const scaledCenter = scaledBox.getCenter(new THREE.Vector3());
  root.position.x -= scaledCenter.x;
  root.position.z -= scaledCenter.z;
  root.position.y -= scaledBox.min.y;
  root.updateMatrixWorld(true);
}

function findMotionTarget(root) {
  let matched = null;
  root.traverse((node) => {
    if (matched) return;
    const normalized = String(node.name || "").trim().toLowerCase();
    if (MODEL_TARGET_NAMES.has(normalized)) {
      matched = node;
      return;
    }
    if (normalized.includes("top") && (normalized.includes("part") || normalized.includes("head"))) {
      matched = node;
    }
  });
  return matched;
}

function collectNamedMovableNodes(root) {
  const nodes = [];
  root.traverse((node) => {
    if (!node?.name || !node.parent || node === root) return;
    if (MOVABLE_RING_PATTERNS.some((pattern) => pattern.test(node.name))) {
      nodes.push(node);
    }
  });
  return nodes;
}

function collectHeuristicMovableNodes(root) {
  const overallBox = new THREE.Box3().setFromObject(root);
  const overallSize = overallBox.getSize(new THREE.Vector3());
  const overallCenter = overallBox.getCenter(new THREE.Vector3());
  const nodes = [];

  root.traverse((node) => {
    if (!node?.isMesh || !node.parent) return;
    const box = new THREE.Box3().setFromObject(node);
    const size = box.getSize(new THREE.Vector3());
    const center = box.getCenter(new THREE.Vector3());
    const widthRatio = size.x / Math.max(overallSize.x, 0.001);
    const heightRatio = size.y / Math.max(overallSize.y, 0.001);
    const nearlyCentered = Math.abs(center.x - overallCenter.x) < overallSize.x * 0.12;
    const largeRoundPiece = widthRatio > 0.7 && heightRatio > 0.7;
    const thinEnough = size.z < overallSize.z * 0.2;
    if (nearlyCentered && largeRoundPiece && thinEnough) {
      nodes.push(node);
    }
  });

  return nodes;
}

function createMovableAssembly(root) {
  let nodes = collectNamedMovableNodes(root);
  if (nodes.length === 0) {
    nodes = collectHeuristicMovableNodes(root);
  }
  if (nodes.length === 0) {
    return null;
  }

  const assembly = new THREE.Group();
  assembly.name = "TopPartRuntime";
  const pivotBox = new THREE.Box3();
  nodes.forEach((node) => pivotBox.expandByObject(node));
  const pivotCenter = pivotBox.getCenter(new THREE.Vector3());
  assembly.position.copy(pivotCenter);
  root.add(assembly);
  root.updateMatrixWorld(true);
  nodes.forEach((node) => {
    assembly.attach(node);
  });
  assembly.updateMatrixWorld(true);
  return { assembly, count: nodes.length };
}

function createOrbitPivot(root, moveTarget) {
  const rootBox = new THREE.Box3().setFromObject(root);
  const rootCenter = rootBox.getCenter(new THREE.Vector3());
  const moveWorld = new THREE.Vector3();
  moveTarget.getWorldPosition(moveWorld);

  const pivot = new THREE.Group();
  pivot.name = "OrbitPivotRuntime";
  pivot.position.set(rootCenter.x, moveWorld.y, rootCenter.z);
  root.add(pivot);
  root.updateMatrixWorld(true);
  pivot.attach(moveTarget);
  pivot.updateMatrixWorld(true);
  return pivot;
}

async function loadExternalModel() {
  updateModelStatus("3D 模型：正在加载 dripmotion.glb …", "warn");
  try {
    const gltf = await modelLoader.loadAsync(MODEL_URL);
    const modelRoot = gltf.scene;

    // 先打印所有节点名，方便在浏览器控制台查看模型结构
    const nodeNames = [];
    modelRoot.traverse((n) => { if (n.name) nodeNames.push(n.name); });
    console.log("[DripMotion] 模型节点列表:", nodeNames);

    normalizeLoadedModel(modelRoot);
    modelRoot.traverse((node) => {
      if (node.isMesh) {
        node.castShadow = true;
        node.receiveShadow = true;
      }
    });

    modelAnchor.clear();
    modelAnchor.add(modelRoot);
    setFallbackVisible(false);   // 只要文件加载成功，就隐藏内置模型

    const extracted = createMovableAssembly(modelRoot);
    if (extracted) {
      const orbitPivot = createOrbitPivot(modelRoot, extracted.assembly);
      bindMotionTargets(extracted.assembly, orbitPivot, "external-ring", "y");
      updateModelStatus(`3D 模型：已加载 GLB，圆圈部件已启用（${extracted.count} 个子节点）`, "ok");
    } else {
      const controlledNode = findMotionTarget(modelRoot);
      if (controlledNode) {
        const orbitPivot = createOrbitPivot(modelRoot, controlledNode);
        bindMotionTargets(controlledNode, orbitPivot, "external", "y");
        updateModelStatus(`3D 模型：已加载 GLB，控制节点：${controlledNode.name}`, "ok");
      } else {
        bindMotionTargets(modelRoot, modelRoot, "external-root", "y");
        updateModelStatus("3D 模型：已加载 GLB，未拆分出圆圈部件，当前控制整体", "warn");
      }
    }
  } catch (error) {
    console.warn("[DripMotion] 外部 3D 模型加载失败，回退到内置演示模型", error);
    modelAnchor.clear();
    setFallbackVisible(true);
    bindMotionTargets(topPivot, topPivot, "fallback");
    updateModelStatus("3D 模型：加载失败，当前使用内置演示模型", "warn");
  }
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
    motionState.heightOffset = clamp(motionState.heightOffset + offset, motionState.limits.min, motionState.limits.max);
    const reachedTop = motionState.heightOffset >= motionState.limits.max && motionState.moveDir > 0;
    const reachedBottom = motionState.heightOffset <= motionState.limits.min && motionState.moveDir < 0;
    if (reachedTop) stopMotion("上表面部件 - 达到最高点");
    if (reachedBottom) stopMotion("上表面部件 - 达到最低点");
  }

  if (motionState.rotateDir !== 0) {
    motionState.rotationOffset += motionState.rotateDir * motionState.rotateSpeed * delta;
  }

  syncMotionBinding();
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

function updateBridgeStatus(text, tone = "idle") {
  if (!bridgeStatusEl) return;
  bridgeStatusEl.textContent = text;
  bridgeStatusEl.dataset.tone = tone;
}

function moduleLabel(target) {
  if (target === "face") return "面部";
  if (target === "hand") return "手势";
  return "语音";
}

function setModuleState(target, running, error = false) {
  const el = target === "face" ? faceStateEl : target === "hand" ? handStateEl : voiceStateEl;
  if (!el) return;
  el.textContent = `${moduleLabel(target)}：${running ? "运行中" : "未启动"}`;
  el.classList.remove("chip--active", "chip--idle", "chip--error");
  if (error) {
    el.classList.add("chip", "chip--error");
  } else if (running) {
    el.classList.add("chip", "chip--active");
  } else {
    el.classList.add("chip", "chip--idle");
  }

  const startBtn = target === "face" ? faceStartBtn : target === "hand" ? handStartBtn : voiceStartBtn;
  const stopBtn = target === "face" ? faceStopBtn : target === "hand" ? handStopBtn : voiceStopBtn;
  if (startBtn) startBtn.disabled = running;
  if (stopBtn) stopBtn.disabled = !running;
  setStreamVisibility(target, running);
}

let bridgeRetryDelayMs = 1000;
let bridgeReconnectTimer = null;
let bridgeSocket = null;
let bridgeConnecting = false;
let activeBridgeHost = window.location.hostname || "127.0.0.1";
const BRIDGE_PORT = 5051;
const QUERY = new URLSearchParams(window.location.search);
const ENABLE_BRIDGE = QUERY.get("standalone") !== "1" && QUERY.get("bridge") !== "off";
const AUTO_START_ON_PAGE_OPEN = false;
const DEFAULT_MODULE_ON_OPEN = "face";
let bridgeBootstrapDone = false;

function setBridgeButtonsEnabled(enabled) {
  [faceStartBtn, faceStopBtn, handStartBtn, handStopBtn, voiceStartBtn, voiceStopBtn].forEach((btn) => {
    if (btn) btn.disabled = !enabled;
  });
}

function bridgeHostCandidates() {
  const currentHost = window.location.hostname;
  const list = [currentHost, "127.0.0.1", "localhost"].filter(Boolean);
  return [...new Set(list)];
}

async function probeBridge(host, timeoutMs = 1200) {
  const controller = new AbortController();
  const timer = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    const response = await fetch(`http://${host}:${BRIDGE_PORT}/health`, {
      method: "GET",
      cache: "no-store",
      signal: controller.signal,
    });
    return response.ok;
  } catch {
    return false;
  } finally {
    window.clearTimeout(timer);
  }
}

async function resolveBridgeHost() {
  if (await probeBridge(activeBridgeHost)) return activeBridgeHost;
  for (const host of bridgeHostCandidates()) {
    if (host === activeBridgeHost) continue;
    if (await probeBridge(host)) return host;
  }
  return null;
}

function scheduleBridgeReconnect() {
  if (bridgeReconnectTimer) return;
  bridgeReconnectTimer = window.setTimeout(() => {
    bridgeReconnectTimer = null;
    connectBridge();
  }, bridgeRetryDelayMs);
  bridgeRetryDelayMs = Math.min(15000, Math.floor(bridgeRetryDelayMs * 1.7));
}

async function connectBridge() {
  if (!ENABLE_BRIDGE) {
    updateBridgeStatus("桥接服务：已关闭（独立模式）", "idle");
    setBridgeButtonsEnabled(false);
    return;
  }
  if (bridgeConnecting) return;
  if (bridgeSocket && (bridgeSocket.readyState === WebSocket.OPEN || bridgeSocket.readyState === WebSocket.CONNECTING)) {
    return;
  }
  if (!("WebSocket" in window)) {
    updateBridgeStatus("桥接服务：浏览器不支持 WebSocket", "error");
    return;
  }

  bridgeConnecting = true;
  const resolvedHost = await resolveBridgeHost();
  bridgeConnecting = false;
  if (!resolvedHost) {
    updateBridgeStatus("桥接服务：未启动，等待连接...", "warn");
    scheduleBridgeReconnect();
    return;
  }

  activeBridgeHost = resolvedHost;
  const protocol = window.location.protocol === "https:" ? "wss" : "ws";
  const socket = new WebSocket(`${protocol}://${activeBridgeHost}:${BRIDGE_PORT}/ws`);
  bridgeSocket = socket;
  socket.addEventListener("open", () => {
    bridgeRetryDelayMs = 1000;
    updateBridgeStatus("桥接服务：已连接", "ok");
    refreshModuleStatus();
    ensureBackendAutoStart();
  });
  socket.addEventListener("close", () => {
    bridgeSocket = null;
    updateBridgeStatus("桥接服务：断开，重连中...", "warn");
    scheduleBridgeReconnect();
  });
  socket.addEventListener("error", () => {
    bridgeSocket = null;
    updateBridgeStatus("桥接服务：连接异常", "error");
    scheduleBridgeReconnect();
  });
  socket.addEventListener("message", handleBridgeMessage);
}

async function ensureBackendAutoStart() {
  if (!AUTO_START_ON_PAGE_OPEN || bridgeBootstrapDone) return;
  bridgeBootstrapDone = true;
  await callModuleControl(DEFAULT_MODULE_ON_OPEN, "start");
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
    return;
  }

  if (message.channel === "voice") {
    if (message.type === "status") updateVoiceCard(message.payload || {});
    if (message.type === "command") {
      if (voiceBindings.command && message.payload?.command) {
        voiceBindings.command.textContent = message.payload.command;
      }
      if (voiceBindings.badge) {
        voiceBindings.badge.textContent = "识别中";
      }
    }
    return;
  }
  if (message.channel === "system" && message.type === "module") {
    const { target, running } = message.payload || {};
    if (target) setModuleState(target, Boolean(running));
  }
}

async function callModuleControl(target, action) {
  if (!ENABLE_BRIDGE) {
    updateBridgeStatus("桥接服务：独立模式下不可控制后端模块", "warn");
    return;
  }
  try {
    const response = await fetch(getControlUrl("/api/control"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ target, action }),
    });
    const json = await response.json();
    if (!response.ok || json.status !== "ok") {
      setModuleState(target, false, true);
      updateBridgeStatus("桥接服务：控制请求失败", "error");
    } else {
      if (json.modules) {
        Object.entries(json.modules).forEach(([key, value]) => {
          setModuleState(key, Boolean(value));
        });
      }

      const running = Boolean(json.modules?.[target]);
      if (action === "start" && running) {
        focusModuleCard(target);
        const cn = moduleLabel(target);
        updateBridgeStatus(`桥接服务：${cn}识别已启动`, "ok");
      }
    }
  } catch (err) {
    console.warn("控制模块失败", err);
    setModuleState(target, false, true);
    updateBridgeStatus("桥接服务：无法连接后端控制接口", "error");
  }
}

function getControlUrl(path) {
  const protocol = window.location.protocol.startsWith("http")
    ? window.location.protocol
    : "http:";
  return `${protocol}//${activeBridgeHost}:${BRIDGE_PORT}${path}`;
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
    setModuleState("voice", false, true);
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
  if (faceBindings.mode) {
    faceBindings.mode.textContent = payload.calibrated ? "已校准" : "校准中";
    faceBindings.mode.classList.toggle("alert", !payload.calibrated);
  }
}

function updateVoiceCard(payload) {
  if (voiceBindings.status && payload.status_text) {
    voiceBindings.status.textContent = `当前状态：${payload.status_text}`;
  }
  if (voiceBindings.transcript) {
    voiceBindings.transcript.textContent = payload.transcript || "--";
  }
  if (voiceBindings.command && payload.last_command) {
    voiceBindings.command.textContent = payload.last_command;
  }
  if (voiceBindings.badge) {
    if (!payload.available) {
      voiceBindings.badge.textContent = "未启用";
      voiceBindings.badge.classList.remove("alert");
    } else if (payload.awake) {
      voiceBindings.badge.textContent = "已唤醒";
      voiceBindings.badge.classList.add("alert");
    } else {
      voiceBindings.badge.textContent = "监听中";
      voiceBindings.badge.classList.remove("alert");
    }
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

if (faceStartBtn) faceStartBtn.addEventListener("click", () => callModuleControl("face", "start"));
if (faceStopBtn) faceStopBtn.addEventListener("click", () => callModuleControl("face", "stop"));
if (handStartBtn) handStartBtn.addEventListener("click", () => callModuleControl("hand", "start"));
if (handStopBtn) handStopBtn.addEventListener("click", () => callModuleControl("hand", "stop"));
if (voiceStartBtn) voiceStartBtn.addEventListener("click", () => callModuleControl("voice", "start"));
if (voiceStopBtn) voiceStopBtn.addEventListener("click", () => callModuleControl("voice", "stop"));

window.addEventListener("resize", () => resizeRenderer());
resizeRenderer();
syncMotionBinding();
loadExternalModel();
connectBridge();
stopMotion();
setStreamVisibility("face", false);
setStreamVisibility("hand", false);
