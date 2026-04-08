import * as THREE from "three";
import { OrbitControls } from "three/addons/controls/OrbitControls.js";
import { GLTFLoader } from "three/addons/loaders/GLTFLoader.js";
import { FBXLoader } from "three/addons/loaders/FBXLoader.js";

const canvas = document.getElementById("dripCanvas");
const modelStatusEl = document.getElementById("modelStatus");

canvas.addEventListener("webglcontextlost", (e) => {
  e.preventDefault();
  console.warn("[DripMotion] WebGL 上下文丢失，等待恢复...");
  if (modelStatusEl) {
    modelStatusEl.textContent = "3D 渲染：WebGL 上下文丢失——请关闭多余标签页后刷新";
    modelStatusEl.dataset.tone = "error";
  }
}, false);

canvas.addEventListener("webglcontextrestored", () => {
  console.log("[DripMotion] WebGL 上下文已恢复");
  if (modelStatusEl) {
    modelStatusEl.textContent = "3D 渲染：WebGL 上下文已恢复，重新加载模型...";
    modelStatusEl.dataset.tone = "warn";
  }
  loadExternalModel();
}, false);

const renderer = new THREE.WebGLRenderer({
  canvas,
  antialias: false,
  alpha: true,
  powerPreference: "default",
  failIfMajorPerformanceCaveat: false,
  precision: "mediump",
});
renderer.setPixelRatio(1);
// 强制将模型视图底色设为米白杏色，避免被默认清屏色覆盖
renderer.setClearColor(0xefe0c8, 1);

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
  new THREE.MeshStandardMaterial({ color: 0xe8d2b3, roughness: 0.78, metalness: 0.08 })
);
fallbackRoot.add(platform);

const deck = new THREE.Mesh(
  new THREE.CylinderGeometry(1.4, 1.5, 0.12, 48),
  new THREE.MeshStandardMaterial({ color: 0xf2e3cc, roughness: 0.65, metalness: 0.05 })
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

// 默认不显示内置演示模型
fallbackRoot.visible = false;

const modelAnchor = new THREE.Group();
scene.add(modelAnchor);

const floor = new THREE.Mesh(
  new THREE.CircleGeometry(4, 80),
  new THREE.MeshBasicMaterial({ color: 0xead8bc, transparent: true, opacity: 0.92 })
);
floor.rotation.x = -Math.PI / 2;
floor.position.y = -0.2;
scene.add(floor);

const modelBoundsHelper = new THREE.Box3Helper(new THREE.Box3(), 0xffb347);
modelBoundsHelper.visible = false;
scene.add(modelBoundsHelper);

const statusText = document.getElementById("statusText");
const heightValue = document.getElementById("heightValue");
const angleValue = document.getElementById("angleValue");
const bridgeStatusEl = document.getElementById("bridgeStatus");
const faceStateEl = document.getElementById("faceState");
const handStateEl = document.getElementById("handState");
const voiceStateEl = document.getElementById("voiceState");
const faceStartBtn = document.getElementById("faceStart");
const faceStopBtn = document.getElementById("faceStop");
const faceTempoToggleBtn = document.getElementById("faceTempoToggle");
const handStartBtn = document.getElementById("handStart");
const handStopBtn = document.getElementById("handStop");
const voiceStartBtn = document.getElementById("voiceStart");
const voiceStopBtn = document.getElementById("voiceStop");
const partPrevBtn = document.getElementById("partPrev");
const partNextBtn = document.getElementById("partNext");
const partRingOnlyBtn = document.getElementById("partRingOnly");
const partShowAllBtn = document.getElementById("partShowAll");
const partBodyOnlyBtn = document.getElementById("partBodyOnly");
const partDebugStatusEl = document.getElementById("partDebugStatus");

const faceBindings = {
  direction: document.getElementById("faceDirection"),
  eye: document.getElementById("faceEye"),
  mouth: document.getElementById("faceMouth"),
  serial: document.getElementById("faceSerial"),
  cmd: document.getElementById("faceCommand"),
  mode: document.getElementById("faceMode"),
  stream: document.getElementById("faceStream"),
  gestures: document.getElementById("faceGestureList"),
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

// 为RingA\RingB\RingC\RingD稍立独立的运动状态
const ringStates = {};
["A", "B", "C", "D"].forEach((ring) => {
  ringStates[ring] = {
    moveDir: 0,
    rotateDir: 0,
    heightOffset: 0,
    rotationOffset: 0,
    heightCm: 0,
    angleDeg: 0,
    baseMoveSpeed: 0.45,
    baseRotateSpeed: THREE.MathUtils.degToRad(60),
    tempoMode: "normal",
    // 初始值会在模型加载后按模型尺寸自适应覆盖
    limits: { min: -0.35, max: 0.35 },
    moveSpeed: 0.45,
    rotateSpeed: THREE.MathUtils.degToRad(60),
    expressionRotateDir: 1,
    expressionRotateAccum: 0,
  };
});

const motionBinding = {
  moveTarget: topPivot,
  rotateTarget: topPivot,
  baseY: topPivot.position.y,
  baseRotation: topPivot.rotation.z,
  rotationAxis: "z",
  source: "fallback",
};

// 人RingA\RingB\RingC\RingD\u7684惬子运动绑定
const ringBindings = {};
["A", "B", "C", "D"].forEach((ring) => {
  ringBindings[ring] = {
    moveTarget: null,
    rotateTarget: null,
    baseMoveY: 0,
    baseY: 0,
    baseRotation: 0,
    rotationAxis: "z",
    source: "ring-" + ring.toLowerCase(),
  };
});

const flowerState = {
  openness: 0,
  target: 0,
  speed: 1.1,
  nodes: [],
};

const flowerRuntimeConfig = {
  manualNodeNames: [],
};

// RingA~D 上下起伏参数（世界坐标）
const RING_WORLD_UP_LIFT_FACTOR = 0.06;
const RING_WORLD_DOWN_LIFT_FACTOR = 0.02;
const RING_WORLD_UP_LIFT_MIN = 0.03;
const RING_WORLD_UP_LIFT_MAX = 0.2;
const RING_WORLD_DOWN_LIFT_MIN = 0.008;
const RING_WORLD_DOWN_LIFT_MAX = 0.06;
const RING_LIFT_SPEED_FACTOR = 1.5;

let lastLoadedModelRoot = null;

const modelLoader = new GLTFLoader();
const fbxLoader = new FBXLoader();
const FORCE_DEBUG_MODEL_MATERIAL = false;
const FORCE_WIREFRAME_OVERLAY = false;
const FORCE_POINTS_OVERLAY = false;
const MODEL_CANDIDATES = [
  // 当前模型（用户指定）
  "./models/chaifen.fbx?v=20260324-chaifen-current",
];
const MODEL_TARGET_NAMES = new Set(["toppart", "top_part", "top-part", "top", "ringa", "ringb", "ringc", "ringd"]);
const RING_MODULE_NAMES = ["RingA", "RingB", "RingC", "RingD"];
// 新模型优先按 RingA~RingD 精确绑定，旧模型仍可匹配 Part_09/10/16
const MOVABLE_RING_PATTERNS = [
  /^ringa$/i,
  /^ringb$/i,
  /^ringc$/i,
  /^ringd$/i,
  /^part_09_ringband$/i,
  /^part_10_ringdiscinner$/i,
  /^part_16_ringdiscouter$/i,
];
const PART_NODE_ORDER = [
  // 新分层结构
  "RingA",
  "RingB",
  "RingC",
  "RingD",
  "Flower",
  "Component",
];
const RING_PART_NAMES = new Set([
  "RingA",
  "RingB",
  "RingC",
  "RingD",
]);

// 手动指定花瓣节点名（最可靠）
const FLOWER_PART_NAMES = [
  "Flower",
  "flower",
  "FLOWER",
];

// 未手动指定时，按名字模式自动识别
const FLOWER_NAME_PATTERNS = [
  /petal/i,
  /flower/i,
  /center_flower|central_flower|center/i,
  /huaban|hua_ban|花瓣/i,
  /^part_1[1-5]_bodypattern/i,
];

const partDebugState = {
  entries: [],
  mode: "all",
  uiBound: false,
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

function normalizeDegrees(value) {
  return ((value % 360) + 360) % 360;
}

function updateModelStatus(text, tone = "idle") {
  if (!modelStatusEl) return;
  modelStatusEl.textContent = text;
  modelStatusEl.dataset.tone = tone;
}

function updatePartDebugStatus(text) {
  if (!partDebugStatusEl) return;
  partDebugStatusEl.textContent = text;
}

function setFallbackVisible(visible) {
  fallbackRoot.visible = visible;
}

function getDisplayFileName(modelUrl) {
  try {
    const name = new URL(modelUrl, window.location.href).pathname.split("/").pop() || "unknown.glb";
    return name.split("?")[0];
  } catch {
    return String(modelUrl || "unknown.glb");
  }
}

function countRenderableMeshes(root) {
  let meshCount = 0;
  root?.traverse((node) => {
    if (node?.isMesh) meshCount += 1;
  });
  return meshCount;
}

function enforceMeshVisibility(root) {
  root?.traverse((node) => {
    if (!node?.isMesh) return;
    node.visible = true;
    node.frustumCulled = false;
    if (node.geometry) {
      node.geometry.computeBoundingBox();
      node.geometry.computeBoundingSphere();
    }
  });
}

function addWireframeOverlay(root) {
  root?.traverse((node) => {
    if (!node?.isMesh || !node.geometry) return;
    const wireGeo = new THREE.WireframeGeometry(node.geometry);
    const wireMat = new THREE.LineBasicMaterial({
      color: 0xfff36b,
      transparent: false,
      depthTest: false,
      depthWrite: false,
      toneMapped: false,
    });
    const lines = new THREE.LineSegments(wireGeo, wireMat);
    lines.frustumCulled = false;
    lines.renderOrder = 999;
    node.add(lines);
  });
}

function addPointsOverlay(root) {
  root?.traverse((node) => {
    if (!node?.isMesh || !node.geometry?.attributes?.position) return;
    const pointsMat = new THREE.PointsMaterial({
      color: 0x00ffd0,
      size: 2.2,
      sizeAttenuation: true,
      transparent: false,
      depthTest: false,
      depthWrite: false,
      toneMapped: false,
    });
    const points = new THREE.Points(node.geometry, pointsMat);
    points.frustumCulled = false;
    points.renderOrder = 1000;
    node.add(points);
  });
}

function applyDebugMaterial(root) {
  root?.traverse((node) => {
    if (!node?.isMesh) return;
    node.material = new THREE.MeshNormalMaterial({
      side: THREE.DoubleSide,
      transparent: false,
      opacity: 1,
      depthTest: true,
      depthWrite: true,
    });
  });
}

function syncMotionBinding() {
  if (!motionBinding.moveTarget || !motionBinding.rotateTarget) return;
  motionBinding.moveTarget.position.y = motionBinding.baseY + motionState.heightOffset;
  motionBinding.rotateTarget.rotation[motionBinding.rotationAxis] = motionBinding.baseRotation + motionState.rotationOffset;
  motionState.heightCm = motionState.heightOffset * 100;
  motionState.angleDeg = normalizeDegrees(THREE.MathUtils.radToDeg(motionState.rotationOffset));
}

function syncRingMotionBinding(ring) {
  const binding = ringBindings[ring];
  if (!binding || !binding.moveTarget || !binding.rotateTarget) return;
  
  const state = ringStates[ring];
  if (!state) return;

  // 上下位移施加在 moveTarget 上，保证位移与旋转可叠加且效果稳定可见。
  binding.moveTarget.position.y = binding.baseMoveY + state.heightOffset;
  binding.rotateTarget.position.y = binding.baseY;
  binding.rotateTarget.rotation[binding.rotationAxis] = binding.baseRotation + state.rotationOffset;
  state.heightCm = state.heightOffset * 100;
  state.angleDeg = normalizeDegrees(THREE.MathUtils.radToDeg(state.rotationOffset));
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

function applyFlowerPose() {
  if (!flowerState.nodes.length) return;
  const t = clamp(flowerState.openness, 0, 1);

  flowerState.nodes.forEach((entry) => {
    const { node, basePosition, baseRotation, baseScale } = entry;
    if (!node) return;

    // 当前实现：花朵完全禁用变换，保持在初始位置
    // 待确认真正的控制方式后再启用
    node.position.copy(basePosition);
    node.rotation.copy(baseRotation);
    node.scale.copy(baseScale);
  });
}

function clearFlowerRig() {
  flowerState.nodes.forEach((entry) => {
    const { node, basePosition, baseRotation, baseScale } = entry;
    if (!node) return;
    node.position.copy(basePosition);
    node.rotation.copy(baseRotation);
    node.scale.copy(baseScale);
  });
  flowerState.nodes = [];
  flowerState.openness = 0;
  flowerState.target = 0;
}

function collectNodeNames(root) {
  const names = [];
  root?.traverse((node) => {
    if (node?.name) names.push(node.name);
  });
  return [...new Set(names)].sort();
}

function getObjectByNameLoose(root, name) {
  if (!root || !name) return null;
  const direct = root.getObjectByName(name);
  if (direct) return direct;
  const target = String(name).toLowerCase();
  let matched = null;
  root.traverse((node) => {
    if (matched || !node?.name) return;
    if (String(node.name).toLowerCase() === target) {
      matched = node;
    }
  });
  return matched;
}

function collectFlowerNodesByName(root, names) {
  const found = [];
  names.forEach((name) => {
    const node = getObjectByNameLoose(root, name);
    if (node?.isObject3D) found.push(node);
  });
  return found;
}

function collectFlowerNodesByPattern(root) {
  const found = [];
  root?.traverse((node) => {
    const n = String(node?.name || "");
    if (!n) return;
    if (FLOWER_NAME_PATTERNS.some((p) => p.test(n))) {
      found.push(node);
    }
  });
  return found;
}

function setupFlowerRig(root) {
  clearFlowerRig();
  if (!root) return;
  const picked = [];
  const manualNames = flowerRuntimeConfig.manualNodeNames.length
    ? flowerRuntimeConfig.manualNodeNames
    : FLOWER_PART_NAMES;
  const usingExplicitNames = manualNames.length > 0;

  if (manualNames.length) {
    picked.push(...collectFlowerNodesByName(root, manualNames));
  }

  if (!picked.length && usingExplicitNames) {
    console.warn("[DripMotion] 手动配置的花瓣节点未命中", manualNames);
    const allNames = collectNodeNames(root);
    console.log("[DripMotion] 当前可用节点名:", allNames);
    updateStatus("花朵开合：固定花瓣节点未命中，已切换自动候选");
  }

  if (!picked.length) {
    picked.push(...collectFlowerNodesByPattern(root));
  }

  if (!picked.length) {
    const box = new THREE.Box3().setFromObject(root);
    const center = box.getCenter(new THREE.Vector3());
    const size = box.getSize(new THREE.Vector3());

    const candidates = [];
    root.traverse((node) => {
      if (!node?.isMesh) return;
      const nbox = new THREE.Box3().setFromObject(node);
      const ncenter = nbox.getCenter(new THREE.Vector3());
      const dx = ncenter.x - center.x;
      const dz = ncenter.z - center.z;
      const radial = Math.hypot(dx, dz);
      const nearCenter = radial < Math.max(size.x, size.z) * 0.28;
      const upperHalf = ncenter.y > center.y - size.y * 0.08;
      if (nearCenter && upperHalf) {
        candidates.push({ node, radial });
      }
    });
    candidates.sort((a, b) => a.radial - b.radial);
    candidates.slice(0, 6).forEach((x) => picked.push(x.node));
  }

  if (!picked.length) {
    console.warn("[DripMotion] 未识别到可开合花朵节点");
    updateStatus("花朵开合：未识别到花瓣节点（可在控制台设置）");
    return;
  }

  flowerState.nodes = picked.map((node, index) => ({
    node,
    basePosition: node.position.clone(),
    baseRotation: node.rotation.clone(),
    baseScale: node.scale.clone(),
    phase: (index / Math.max(1, picked.length)) * Math.PI * 2,
  }));

  flowerState.openness = 0;
  flowerState.target = 0;
  applyFlowerPose();
  // 保持花朵可见
  flowerState.nodes.forEach(({ node }) => {
    if (node) node.visible = true;
  });
  console.log(`[DripMotion] 花朵节点已绑定：${flowerState.nodes.length} 个`, flowerState.nodes.map((x) => x.node.name));
  console.log("[DripMotion] 提示：在控制台执行 dripDebug.listNodeNames() 查看所有节点名");
  console.log("[DripMotion] 提示：执行 dripDebug.setFlowerNodes(['nodename']) 手动指定花朵节点");
}

function initFlowerDebugApi() {
  const api = {
    listNodeNames() {
      if (!lastLoadedModelRoot) {
        console.warn("[DripMotion] 当前没有已加载模型");
        return [];
      }
      const names = collectNodeNames(lastLoadedModelRoot);
      console.log("[DripMotion] 节点名列表:", names);
      return names;
    },
    setFlowerNodes(names) {
      if (!Array.isArray(names)) {
        console.warn("[DripMotion] setFlowerNodes 需要数组参数");
        return;
      }
      flowerRuntimeConfig.manualNodeNames = names.filter(Boolean).map((x) => String(x).trim());
      if (!lastLoadedModelRoot) return;
      setupFlowerRig(lastLoadedModelRoot);
      console.log("[DripMotion] 已更新花瓣节点映射:", flowerRuntimeConfig.manualNodeNames);
    },
    clearFlowerNodes() {
      flowerRuntimeConfig.manualNodeNames = [];
      if (!lastLoadedModelRoot) return;
      setupFlowerRig(lastLoadedModelRoot);
      console.log("[DripMotion] 已清除手动花瓣节点映射");
    },
  };

  window.dripDebug = {
    ...(window.dripDebug || {}),
    ...api,
  };
}

function setFlowerTarget(next, statusLabel) {
  if (!flowerState.nodes.length) {
    updateStatus("花朵开合：未识别到可控节点");
    return;
  }
  flowerState.target = clamp(next, 0, 1);
  if (statusLabel) updateStatus(statusLabel);
}

function initRingDebugApi() {
  const api = {
    ringStates() {
      console.log("=== Ring States ===");
      ["A", "B", "C", "D"].forEach((ring) => {
        const state = ringStates[ring];
        console.log(
          `Ring${ring}: moveDir=${state.moveDir}, rotateDir=${state.rotateDir}, ` +
          `heightOffset=${state.heightOffset.toFixed(3)}, rotationOffset=${(state.rotationOffset * 180 / Math.PI).toFixed(1)}°, ` +
          `limits=[${state.limits.min}, ${state.limits.max}]`
        );
      });
      return ringStates;
    },
    ringBindings() {
      console.log("=== Ring Bindings ===");
      ["A", "B", "C", "D"].forEach((ring) => {
        const binding = ringBindings[ring];
        console.log(
          `Ring${ring}: ` +
          `moveTarget=${binding.moveTarget ? binding.moveTarget.name : "null"}, ` +
          `rotateTarget=${binding.rotateTarget ? binding.rotateTarget.name : "null"}, ` +
          `baseY=${binding.baseY?.toFixed(3) || "null"}, ` +
          `baseRotation=${binding.baseRotation?.toFixed(3) || "null"}`
        );
      });
      return ringBindings;
    },
    testRingMove(ring, direction) {
      console.log(`[Ring Debug] 测试 Ring${ring} ${direction > 0 ? "向上" : "向下"} 移动`);
      startRingMove(ring, direction);
      console.log(`[Ring Debug] state.moveDir set to ${direction}`);
      return ringStates[ring];
    },
    testRingRotate(ring, direction) {
      console.log(`[Ring Debug] 测试 Ring${ring} ${direction > 0 ? "左转" : "右转"}`);
      startRingRotate(ring, direction);
      return ringStates[ring];
    },
    stopRing(ring) {
      stopRingMotion(ring);
      console.log(`[Ring Debug] Ring${ring} 已停止`);
      return ringStates[ring];
    },
  };
  
  window.dripDebug = {
    ...(window.dripDebug || {}),
    ...api,
  };
  
  console.log("[DripMotion] Ring Debug API ready. Use dripDebug.ringStates() / dripDebug.ringBindings() / dripDebug.testRingMove(ring, dir)");
}

function normalizeLoadedModel(root, flipX = false) {
  // GLB 导出坐标系倒置需要翻转；FBX 从 Blender 导出已是正向，不翻转。
  if (flipX) {
    root.rotation.x = Math.PI;
  }
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

// FBX 材质统一转换为“做旧古铜”风格
function convertFBXMaterials(root) {
  const hashName = (name) => {
    let h = 0;
    const s = String(name || "mesh");
    for (let i = 0; i < s.length; i += 1) h = ((h << 5) - h + s.charCodeAt(i)) | 0;
    return Math.abs(h);
  };

  const buildBronzeColor = (nodeName) => {
    const h = hashName(nodeName);
    const hue = 0.075 + (h % 8) / 320; // 铜棕色相，带轻微差异
    const sat = 0.42 + (h % 4) * 0.025;
    const light = 0.28 + (h % 5) * 0.022;
    return new THREE.Color().setHSL(hue, Math.min(0.56, sat), Math.min(0.40, light));
  };

  const applyPatina = (base, nodeName) => {
    const h = hashName(nodeName);
    const patina = new THREE.Color().setHSL(0.47, 0.22, 0.24 + (h % 3) * 0.03); // 轻微铜绿
    return base.clone().lerp(patina, 0.12 + (h % 3) * 0.02);
  };

  root.traverse((node) => {
    if (!node.isMesh) return;
    const oldMats = Array.isArray(node.material) ? node.material : [node.material];
    const newMats = oldMats.map((m) => {
      if (!m) return m;

      const sourceColor = m.color ? m.color.clone() : new THREE.Color(0xffffff);
      const bronzeBase = buildBronzeColor(node.name);
      const mixed = sourceColor.clone().lerp(bronzeBase, m.map ? 0.45 : 0.78);
      const resolvedColor = applyPatina(mixed, node.name);

      const side = m.side ?? THREE.DoubleSide;
      const transparent = m.transparent ?? false;
      const opacity = m.opacity ?? 1;
      const map = m.map ?? null;
      const normalMap = m.normalMap ?? null;
      const emissiveMap = m.emissiveMap ?? null;

      const std = new THREE.MeshStandardMaterial({
        color: resolvedColor,
        roughness: 0.58,
        metalness: 0.68,
        side,
        transparent,
        opacity,
      });
      if (map) std.map = map;
      if (normalMap) std.normalMap = normalMap;
      std.emissive = new THREE.Color(0x140d08);
      std.emissiveIntensity = 0.32;
      if (emissiveMap) std.emissiveMap = emissiveMap;
      return std;
    });
    node.material = Array.isArray(node.material) ? newMats : newMats[0];
    const assigned = Array.isArray(node.material) ? node.material : [node.material];
    assigned.forEach((mat) => {
      if (mat) mat.needsUpdate = true;
    });
  });
}

function detectRingLayer(node) {
  let current = node;
  while (current) {
    const n = String(current.name || "").toLowerCase();
    if (/ringa|part_10|ringdiscinner|inner/.test(n)) return "innerA";
    if (/ringb|part_09|ringband|band|mid/.test(n)) return "innerB";
    if (/ringc|part_16|ringdiscouter|outer/.test(n)) return "outerC";
    if (/ringd|outermost/.test(n)) return "outerD";
    current = current.parent;
  }
  return null;
}

function detectModelPartBucket(node) {
  let current = node;
  while (current) {
    const n = String(current.name || "").toLowerCase();
    if (n.includes("ringa")) return "ringA";
    if (n.includes("ringb")) return "ringB";
    if (n.includes("ringc")) return "ringC";
    if (n.includes("ringd")) return "ringD";
    if (n.includes("flower")) return "flower";
    if (n.includes("component")) return "component";
    current = current.parent;
  }
  return null;
}

function applyLayeredRingBronze(root) {
  const palette = {
    innerA: {
      color: new THREE.Color(0x4a2f21),
      emissive: new THREE.Color(0x1a110c),
      roughness: 0.7,
      metalness: 0.52,
    },
    innerB: {
      color: new THREE.Color(0x6a412a),
      emissive: new THREE.Color(0x23150d),
      roughness: 0.62,
      metalness: 0.62,
    },
    outerC: {
      color: new THREE.Color(0x8b5a3b),
      emissive: new THREE.Color(0x2a1a10),
      roughness: 0.48,
      metalness: 0.72,
    },
    outerD: {
      color: new THREE.Color(0xa9754f),
      emissive: new THREE.Color(0x2f1f13),
      roughness: 0.44,
      metalness: 0.78,
    },
    ringA: {
      color: new THREE.Color(0x6c4a2f),
      emissive: new THREE.Color(0x1c120b),
      roughness: 0.66,
      metalness: 0.58,
    },
    ringB: {
      color: new THREE.Color(0x855636),
      emissive: new THREE.Color(0x24160d),
      roughness: 0.58,
      metalness: 0.64,
    },
    ringC: {
      color: new THREE.Color(0xa06943),
      emissive: new THREE.Color(0x2a190f),
      roughness: 0.5,
      metalness: 0.7,
    },
    ringD: {
      color: new THREE.Color(0xbd8354),
      emissive: new THREE.Color(0x311f13),
      roughness: 0.45,
      metalness: 0.76,
    },
    flower: {
      color: new THREE.Color(0xd8b47f),
      emissive: new THREE.Color(0x2a2014),
      roughness: 0.55,
      metalness: 0.24,
    },
    component: {
      color: new THREE.Color(0xebe0cf),
      emissive: new THREE.Color(0x1a1610),
      roughness: 0.72,
      metalness: 0.06,
    },
  };

  root.traverse((node) => {
    if (!node?.isMesh) return;
    const bucketByName = detectModelPartBucket(node);
    const layer = detectRingLayer(node);
    const spec = palette[bucketByName] || palette[layer];
    if (!spec) return;

    const mats = Array.isArray(node.material) ? node.material : [node.material];
    const upgraded = mats.map((mat) => {
      if (!mat) return mat;

      let target = mat;
      if (!mat.isMeshStandardMaterial) {
        target = new THREE.MeshStandardMaterial({
          map: mat.map ?? null,
          normalMap: mat.normalMap ?? null,
          transparent: mat.transparent ?? false,
          opacity: mat.opacity ?? 1,
          side: mat.side ?? THREE.DoubleSide,
        });
      }

      target.color.copy(spec.color);
      target.emissive.copy(spec.emissive);
      target.emissiveIntensity = 0.36;
      target.roughness = spec.roughness;
      target.metalness = spec.metalness;
      target.needsUpdate = true;
      return target;
    });

    node.material = Array.isArray(node.material) ? upgraded : upgraded[0];
  });
}

function focusCameraOnObject(object3d, padding = 1.35) {
  const box = new THREE.Box3().setFromObject(object3d);
  if (box.isEmpty()) return;

  const size = box.getSize(new THREE.Vector3());
  const center = box.getCenter(new THREE.Vector3());
  const maxDim = Math.max(size.x, size.y, size.z, 0.001);
  if (!Number.isFinite(maxDim) || maxDim <= 0) return;

  const fov = THREE.MathUtils.degToRad(camera.fov);
  const fitDistance = (maxDim * padding) / (2 * Math.tan(fov / 2));
  const direction = new THREE.Vector3(1, 0.72, 1.18).normalize();
  const nextPos = center.clone().add(direction.multiplyScalar(fitDistance));

  camera.position.copy(nextPos);
  camera.near = Math.max(0.01, fitDistance / 100);
  camera.far = Math.max(50, fitDistance * 20);
  camera.updateProjectionMatrix();

  controls.target.copy(center);
  controls.update();
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

  // 优先精确使用 RingA~RingD，避免把 Flower/Component 纳入可动集合
  const exactRingNodes = RING_MODULE_NAMES
    .map((name) => getObjectByNameLoose(root, name))
    .filter((node) => node?.isObject3D);
  if (exactRingNodes.length >= 2) {
    return exactRingNodes;
  }

  return nodes;
}

function collectHeuristicMovableNodes(root) {
  const overallBox = new THREE.Box3().setFromObject(root);
  const overallSize = overallBox.getSize(new THREE.Vector3());
  const overallCenter = overallBox.getCenter(new THREE.Vector3());
  const nodes = [];

  root.traverse((node) => {
    if (!node?.isMesh || !node.parent) return;
    const nodeName = String(node.name || "").toLowerCase();
    if (nodeName.includes("flower") || nodeName.includes("component")) return;

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

function createRingAssembly(root, ringName) {
  // 获取指定圆环的节点
  const ringNode = getObjectByNameLoose(root, ringName);
  if (!ringNode || !ringNode.isObject3D) {
    return null;
  }

  const assembly = new THREE.Group();
  assembly.name = `${ringName}RunTime_Assembly`;
  
  // 计算圆环的中心位置
  const box = new THREE.Box3().setFromObject(ringNode);
  const centerWorld = box.getCenter(new THREE.Vector3());
  const centerLocal = root.worldToLocal(centerWorld.clone());
  
  assembly.position.copy(centerLocal);
  root.add(assembly);
  root.updateMatrixWorld(true);
  
  // 将圆环节点附加到 assembly
  assembly.attach(ringNode);
  assembly.updateMatrixWorld(true);
  
  return { assembly, count: 1 };
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
  const pivotCenterWorld = pivotBox.getCenter(new THREE.Vector3());
  const pivotCenterLocal = root.worldToLocal(pivotCenterWorld.clone());
  assembly.position.copy(pivotCenterLocal);
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
  const rootCenterWorld = rootBox.getCenter(new THREE.Vector3());
  const moveWorld = new THREE.Vector3();
  moveTarget.getWorldPosition(moveWorld);
  const rootCenterLocal = root.worldToLocal(rootCenterWorld.clone());
  const moveLocal = root.worldToLocal(moveWorld.clone());

  const pivot = new THREE.Group();
  pivot.name = "OrbitPivotRuntime";
  pivot.position.set(rootCenterLocal.x, moveLocal.y, rootCenterLocal.z);
  root.add(pivot);
  root.updateMatrixWorld(true);
  pivot.attach(moveTarget);
  pivot.updateMatrixWorld(true);
  return pivot;
}

function createModelCenterPivot(root, parent) {
  const rootBox = new THREE.Box3().setFromObject(root);
  const centerWorld = rootBox.getCenter(new THREE.Vector3());
  const parentLocalCenter = parent.worldToLocal(centerWorld.clone());

  const pivot = new THREE.Group();
  pivot.name = "ModelCenterPivotRuntime";
  pivot.position.copy(parentLocalCenter);
  parent.add(pivot);
  parent.updateMatrixWorld(true);
  pivot.attach(root);
  pivot.updateMatrixWorld(true);
  return pivot;
}

function bindPerRingMotionTargets(root) {
  // 为每个圆环（A/B/C/D）创建独立的 moveTarget 和 rotateTarget
  const rootBox = new THREE.Box3().setFromObject(root);
  const rootCenterLocal = root.worldToLocal(rootBox.getCenter(new THREE.Vector3()));
  const rootSize = rootBox.getSize(new THREE.Vector3());
  // 上下分离：上移幅度更大，下移幅度更小（先算世界坐标，再换算 root 局部坐标）
  const desiredWorldUpLift = clamp(
    rootSize.y * RING_WORLD_UP_LIFT_FACTOR,
    RING_WORLD_UP_LIFT_MIN,
    RING_WORLD_UP_LIFT_MAX
  );
  const desiredWorldDownLift = clamp(
    rootSize.y * RING_WORLD_DOWN_LIFT_FACTOR,
    RING_WORLD_DOWN_LIFT_MIN,
    RING_WORLD_DOWN_LIFT_MAX
  );
  const rootScaleY = Math.max(Math.abs(root.scale.y || 0), 1e-6);
  const upLiftLocal = desiredWorldUpLift / rootScaleY;
  const downLiftLocal = desiredWorldDownLift / rootScaleY;

  let successCount = 0;
  RING_MODULE_NAMES.forEach((ringFullName) => {
    // 提取单字母键 (RingA → A, RingB → B, etc)
    const ring = ringFullName.charAt(ringFullName.length - 1);

    const ringNode = getObjectByNameLoose(root, ringFullName);
    if (!ringNode || !ringNode.isObject3D) {
      console.warn(`[Ring Binding] 找不到圆环节点: ${ringFullName}`);
      return;
    }

    // 创建 moveTarget assembly（包装 ringNode）
    const moveTarget = new THREE.Group();
    moveTarget.name = `${ringFullName}MoveTarget`;
    
    // 计算 ringNode 的中心位置
    const box = new THREE.Box3().setFromObject(ringNode);
    const centerWorld = box.getCenter(new THREE.Vector3());
    
    // assembly 定位到圆环中心
    moveTarget.position.copy(root.worldToLocal(centerWorld.clone()));
    root.add(moveTarget);
    root.updateMatrixWorld(true);
    
    // 将 ringNode 附加到 moveTarget
    moveTarget.attach(ringNode);
    root.updateMatrixWorld(true);
    
    // 创建旋转枢轴（rotateTarget）
    const rotateTarget = new THREE.Group();
    rotateTarget.name = `${ringFullName}RotatePivot`;
    
    // 枢轴位置：模型中心
    rotateTarget.position.copy(rootCenterLocal);
    root.add(rotateTarget);
    root.updateMatrixWorld(true);

    // 将 moveTarget 附加到枢轴
    rotateTarget.attach(moveTarget);
    root.updateMatrixWorld(true);

    // 记录旋转枢轴在 root 下的初始高度，供上下起伏使用
    const basePivotY = rotateTarget.position.y;

    // 保存到 ringBindings（使用单字母键）
    ringBindings[ring].moveTarget = moveTarget;
    ringBindings[ring].rotateTarget = rotateTarget;
    ringBindings[ring].baseMoveY = moveTarget.position.y;
    ringBindings[ring].baseY = basePivotY;
    ringBindings[ring].baseRotation = 0; // 初始旋转为 0
    ringBindings[ring].rotationAxis = "y";

    // 为该环设置自适应上下起伏参数
    if (ringStates[ring]) {
      // 当前按钮方向为翻转映射：moveUp -> dir -1, moveDown -> dir +1
      // 因此：上移幅度对应 limits.min 的绝对值；下移幅度对应 limits.max
      ringStates[ring].limits.min = -upLiftLocal;
      ringStates[ring].limits.max = downLiftLocal;
      ringStates[ring].baseMoveSpeed = Math.max(upLiftLocal, downLiftLocal) * RING_LIFT_SPEED_FACTOR;
      ringStates[ring].baseRotateSpeed = THREE.MathUtils.degToRad(60);
      ringStates[ring].moveSpeed = ringStates[ring].baseMoveSpeed;
      ringStates[ring].rotateSpeed = ringStates[ring].baseRotateSpeed;
    }

    successCount++;
    console.log(
      `[Ring Binding] ${ringFullName}(${ring}) 已绑定 - pivotY: ${basePivotY.toFixed(3)}, ` +
      `worldUp=${desiredWorldUpLift.toFixed(3)}, worldDown=${desiredWorldDownLift.toFixed(3)}, ` +
      `localUp=${upLiftLocal.toFixed(3)}, localDown=${downLiftLocal.toFixed(3)}, ` +
      `moveSpeed=${(Math.max(upLiftLocal, downLiftLocal) * RING_LIFT_SPEED_FACTOR).toFixed(3)}, ` +
      `rootScaleY=${rootScaleY.toExponential(2)}, pivot: ${rotateTarget.name}`
    );
  });

  // 返回成功绑定的环数（4 = 全部成功）
  return successCount;
}

function buildPartRegistry(root) {
  const entries = [];
  const missing = [];
  PART_NODE_ORDER.forEach((name) => {
    const node = getObjectByNameLoose(root, name);
    if (!node) {
      missing.push(name);
      return;
    }
    entries.push({
      name,
      node,
      isRing: RING_PART_NAMES.has(name),
    });
  });
  partDebugState.entries = entries;
  const found = entries.length;
  const ringFound = entries.filter((e) => e.isRing).length;
  const bodyFound = found - ringFound;
  updatePartDebugStatus(
    `部件节点：静态模块 ${bodyFound} 个 | 圆环组 ${ringFound} 个（RingA + RingB + RingC + RingD）` +
    (missing.length ? `，缺失 ${missing.join(", ")}` : "")
  );
}

function applyPartDebugView() {
  const entries = partDebugState.entries;
  if (!entries.length) return;

  entries.forEach((entry) => {
    if (partDebugState.mode === "all") {
      entry.node.visible = true;
    } else if (partDebugState.mode === "ring") {
      entry.node.visible = entry.isRing;
    } else if (partDebugState.mode === "body") {
      entry.node.visible = !entry.isRing;
    }
  });

  const ringCount = entries.filter((e) => e.isRing).length;
  const bodyCount = entries.length - ringCount;
  if (partDebugState.mode === "ring") {
    updatePartDebugStatus(`部件节点：仅显示圆环组（${ringCount} 个节点：RingA、RingB、RingC、RingD）`);
  } else if (partDebugState.mode === "body") {
    updatePartDebugStatus(`部件节点：仅显示静态模块（${bodyCount} 个节点，Flower 与 Component 不参与环运动）`);
  } else {
    updatePartDebugStatus(`部件节点：显示全部 — 静态模块 ${bodyCount} 个 | 圆环组 ${ringCount} 个`);
  }
}

function bindPartDebugUI() {
  if (partDebugState.uiBound) return;
  partDebugState.uiBound = true;

  partBodyOnlyBtn?.addEventListener("click", () => {
    if (!partDebugState.entries.length) return;
    partDebugState.mode = "body";
    applyPartDebugView();
  });

  partRingOnlyBtn?.addEventListener("click", () => {
    if (!partDebugState.entries.length) return;
    partDebugState.mode = "ring";
    applyPartDebugView();
  });

  partShowAllBtn?.addEventListener("click", () => {
    if (!partDebugState.entries.length) return;
    partDebugState.mode = "all";
    applyPartDebugView();
  });
}

async function loadExternalModel() {
  // 不显示内置模拟模型，只加载真实模型
  setFallbackVisible(false);

  let lastError = null;
  for (const candidate of MODEL_CANDIDATES) {
    const modelUrl = new URL(candidate, import.meta.url).href;
    const fileName = getDisplayFileName(modelUrl);
    const isFBX = /\.fbx(\?|$)/i.test(modelUrl);

    // 不做 HEAD 预探测，直接加载以减少等待时间

    updateModelStatus(`3D 模型：正在加载 ${fileName} …`, "warn");
    try {
      let modelRoot;
      if (isFBX) {
        // FBXLoader 直接返回 THREE.Group
        modelRoot = await fbxLoader.loadAsync(modelUrl);
      } else {
        // GLTFLoader 返回 gltf 对象，场景在 gltf.scene
        const gltf = await modelLoader.loadAsync(modelUrl);
        modelRoot = gltf.scene;
      }

      const meshCount = countRenderableMeshes(modelRoot);
      if (meshCount === 0) {
        throw new Error(`模型 ${fileName} 不包含可渲染 Mesh`);
      }

      // 打印所有节点名，方便在浏览器控制台查看模型结构
      const nodeNames = [];
      modelRoot.traverse((n) => { if (n.name) nodeNames.push(n.name); });
      console.log("[DripMotion] 模型节点列表:", nodeNames);
      console.log(`[DripMotion] 已加载模型 ${fileName}（${isFBX ? "FBX" : "GLB"}），mesh 数量：${meshCount}`);

      // 坐标系修正：GLB 以及部分 FBX（如 chaifen / ImageToStl.com_999）需要绕 X 轴翻转
      const needsFlipX = !isFBX || /imagetostl\.com_999\.fbx|chaifen\.fbx/i.test(fileName);
      normalizeLoadedModel(modelRoot, needsFlipX);

      // 先把模型挂到场景并显示一帧，减少“加载完成后还要等待处理”的体感延迟
      modelAnchor.clear();
      modelAnchor.add(modelRoot);
      lastLoadedModelRoot = modelRoot;
      setFallbackVisible(false);
      modelBoundsHelper.visible = false;
      focusCameraOnObject(modelRoot);
      updateModelStatus(`3D 模型：已加载 ${fileName}，正在初始化材质与控制…`, "warn");

      // 让浏览器先渲染出模型，再做后处理（材质、绑定、调试）
      await new Promise((resolve) => requestAnimationFrame(resolve));

      if (isFBX) {
        // FBX 材质转换为 MeshStandardMaterial，修复白色显示问题
        convertFBXMaterials(modelRoot);
      }

      // 圆盘内-中-外三层应用不同深浅的做旧古铜色
      applyLayeredRingBronze(modelRoot);

      modelRoot.traverse((node) => {
        if (node.isMesh) {
          node.castShadow = true;
          node.receiveShadow = true;
        }
      });
      enforceMeshVisibility(modelRoot);
      if (FORCE_DEBUG_MODEL_MATERIAL) {
        applyDebugMaterial(modelRoot);
      }
      if (FORCE_WIREFRAME_OVERLAY) {
        addWireframeOverlay(modelRoot);
      }
      if (FORCE_POINTS_OVERLAY) {
        addPointsOverlay(modelRoot);
      }

      // 首先尝试绑定独立的 4 个环（A/B/C/D）
      const ringBindingSuccess = bindPerRingMotionTargets(modelRoot);
      
      if (ringBindingSuccess === 4) {
        // 成功绑定了全部 4 个环，使用独立控制模式
        updateModelStatus(`3D 模型：已加载 ${fileName}，4 个独立圆环已启用`, "ok");
      } else {
        // 未成功绑定所有环，回退到全局 assembly 模式
        const extracted = createMovableAssembly(modelRoot);
        if (extracted) {
          const orbitPivot = createOrbitPivot(modelRoot, extracted.assembly);
          bindMotionTargets(extracted.assembly, orbitPivot, "external-ring", "y");
          updateModelStatus(`3D 模型：已加载 ${fileName}，圆圈部件已启用（${extracted.count} 个子节点）`, "ok");
        } else {
          const controlledNode = findMotionTarget(modelRoot);
          if (controlledNode) {
            const orbitPivot = createOrbitPivot(modelRoot, controlledNode);
            bindMotionTargets(controlledNode, orbitPivot, "external", "y");
            updateModelStatus(`3D 模型：已加载 ${fileName}，控制节点：${controlledNode.name}`, "ok");
          } else {
            const centerPivot = createModelCenterPivot(modelRoot, modelAnchor);
            bindMotionTargets(modelRoot, centerPivot, "external-root", "y");
            updateModelStatus(`3D 模型：已加载 ${fileName}，未拆分出圆圈部件，当前围绕模型中心旋转`, "warn");
          }
        }
      }

      buildPartRegistry(modelRoot);
      bindPartDebugUI();
      partDebugState.mode = "all";
      applyPartDebugView();
      setupFlowerRig(modelRoot);
      return;
    } catch (error) {
      lastError = error;
      console.warn(`[DripMotion] 模型加载失败：${fileName}，尝试下一个候选文件`, error);
    }
  }

  console.error("[DripMotion] 外部 3D 模型加载失败", lastError);
  modelAnchor.clear();
  setFallbackVisible(false);
  modelBoundsHelper.visible = false;
  clearFlowerRig();
  lastLoadedModelRoot = null;
  updateModelStatus("3D 模型：chaifen.fbx 加载失败，请检查文件或网络", "error");
}

function updateStatus(text) {
  if (statusText) statusText.textContent = text;
  if (heightValue) heightValue.textContent = `${motionState.heightCm.toFixed(1)} cm`;
  if (angleValue) angleValue.textContent = `${motionState.angleDeg.toFixed(0)}°`;
}

function updateMotionStatus() {
  const moveLabel = motionState.moveDir > 0 ? "上升" : motionState.moveDir < 0 ? "下降" : "停止";
  const rotateLabel = motionState.rotateDir > 0 ? "左转" : motionState.rotateDir < 0 ? "右转" : "停止";

  if (motionState.moveDir === 0 && motionState.rotateDir === 0) {
    updateStatus("圆环组 - 停止");
    return;
  }

  updateStatus(`圆环组 - 竖向${moveLabel} | 水平${rotateLabel}`);
}

function startMove(dir) {
  motionState.moveDir = dir;
  updateMotionStatus();
}

function startRotate(dir) {
  motionState.rotateDir = dir;
  updateMotionStatus();
}

function stopMotion(label = "圆环组 - 停止") {
  motionState.moveDir = 0;
  motionState.rotateDir = 0;
  updateStatus(label);
}

function startRingMove(ring, dir) {
  const state = ringStates[ring];
  if (!state) {
    console.warn(`[Ring Move] Ring${ring} state not found!`);
    return;
  }
  state.moveDir = dir;
  console.log(`[Ring Move] Ring${ring} moveDir=${dir}, heightOffset=${state.heightOffset.toFixed(3)}, limits=[${state.limits.min}, ${state.limits.max}]`);
  updateStatus(`Ring${ring} - ${dir > 0 ? "上升中" : "下降中"}`);
}

function startRingRotate(ring, dir) {
  const state = ringStates[ring];
  if (!state) {
    console.warn(`[Ring Rotate] Ring${ring} state not found!`);
    return;
  }
  state.rotateDir = dir;
  console.log(`[Ring Rotate] Ring${ring} rotateDir=${dir}`);
  updateStatus(`Ring${ring} - ${dir > 0 ? "左转中" : "右转中"}`);
}

function stopRingMotion(ring, label = null) {
  const state = ringStates[ring];
  if (!state) return;
  state.moveDir = 0;
  state.rotateDir = 0;
  updateStatus(label || `Ring${ring} - 停止`);
}

function applyRingCommand(ring, action) {
  switch (action) {
    case "moveUp":
      // 模型在当前坐标系下为翻转状态，上下控制方向取反
      startRingMove(ring, -1);
      break;
    case "moveDown":
      // 模型在当前坐标系下为翻转状态，上下控制方向取反
      startRingMove(ring, 1);
      break;
    case "rotateLeft":
      startRingRotate(ring, 1);
      break;
    case "rotateRight":
      startRingRotate(ring, -1);
      break;
    case "stop":
      stopRingMotion(ring);
      break;
    default:
      break;
  }
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
    // case "flowerOpen":
    //   setFlowerTarget(1, "中间花朵 - 打开中");
    //   break;
    // case "flowerClose":
    //   setFlowerTarget(0, "中间花朵 - 闭合中");
    //   break;
    default:
      break;
  }
}

function stepPhysics(delta) {
  // === GLOBAL MOTION (legacy, kept for backwards compatibility) ===
  if (motionState.moveDir !== 0) {
    const offset = motionState.moveDir * motionState.moveSpeed * delta;
    motionState.heightOffset = clamp(motionState.heightOffset + offset, motionState.limits.min, motionState.limits.max);
    const reachedTop = motionState.heightOffset >= motionState.limits.max && motionState.moveDir > 0;
    const reachedBottom = motionState.heightOffset <= motionState.limits.min && motionState.moveDir < 0;
    if (reachedTop || reachedBottom) {
      motionState.moveDir = 0;
      if (reachedTop) {
        updateStatus(motionState.rotateDir === 0 ? "圆环组 - 达到最高点" : "圆环组 - 达到最高点，继续旋转");
      }
      if (reachedBottom) {
        updateStatus(motionState.rotateDir === 0 ? "圆环组 - 达到最低点" : "圆环组 - 达到最低点，继续旋转");
      }
    }
  }

  if (motionState.rotateDir !== 0) {
    motionState.rotationOffset += motionState.rotateDir * motionState.rotateSpeed * delta;
  }

  syncMotionBinding();

  // === PER-RING MOTION (new independent control) ===
  if (faceExpressionControlEnabled) {
    applyExpressionRhythmToAllRings(delta);
  } else {
    for (const ring of ["A", "B", "C", "D"]) {
      const state = ringStates[ring];
      if (!state) continue;

      // Update height offset (move up/down)
      if (state.moveDir !== 0) {
        const offset = state.moveDir * state.moveSpeed * delta;
        state.heightOffset = clamp(state.heightOffset + offset, state.limits.min, state.limits.max);
        const reachedTop = state.heightOffset >= state.limits.max && state.moveDir > 0;
        const reachedBottom = state.heightOffset <= state.limits.min && state.moveDir < 0;
        if (reachedTop || reachedBottom) {
          state.moveDir = 0;
          if (reachedTop) {
            updateStatus(state.rotateDir === 0 ? `Ring${ring} - 达到最高点` : `Ring${ring} - 达到最高点，继续旋转`);
          }
          if (reachedBottom) {
            updateStatus(state.rotateDir === 0 ? `Ring${ring} - 达到最低点` : `Ring${ring} - 达到最低点，继续旋转`);
          }
        }
      }

      // Update rotation offset (rotate left/right)
      if (state.rotateDir !== 0) {
        state.rotationOffset += state.rotateDir * state.rotateSpeed * delta;
      }

      // Sync with 3D binding for this ring
      syncRingMotionBinding(ring);
    }
  }

  // === FLOWER ANIMATION ===
  if (flowerState.nodes.length) {
    const diff = flowerState.target - flowerState.openness;
    if (Math.abs(diff) > 0.0001) {
      const step = Math.min(Math.abs(diff), flowerState.speed * delta);
      flowerState.openness += Math.sign(diff) * step;
      applyFlowerPose();

      if (Math.abs(flowerState.target - flowerState.openness) < 0.005) {
        flowerState.openness = flowerState.target;
        applyFlowerPose();
        if (flowerState.target >= 0.99) updateStatus("中间花朵 - 已打开");
        if (flowerState.target <= 0.01) updateStatus("中间花朵 - 已闭合");
      }
    }
  }
}

function renderLoop() {
  requestAnimationFrame(renderLoop);
  const delta = clock.getDelta();
  resizeRenderer();
  stepPhysics(delta);
  controls.update();
  renderer.render(scene, camera);
}

const buttons = document.querySelectorAll(".control-btn");
buttons.forEach((btn) => {
  btn.addEventListener("click", () => {
    const command = btn.dataset.command;
    const ring = btn.dataset.ring;  // RingA/B/C/D，如果没有则为 null
    if (ring && ["A", "B", "C", "D"].includes(ring)) {
      applyRingCommand(ring, command);
    } else {
      applyCommand(command);
    }
  });
});

const FACE_COMMAND_MAP = {
  LOOK_LEFT: "rotateLeft",
  LOOK_RIGHT: "rotateRight",
  LOOK_UP: "moveUp",
  LOOK_DOWN: "moveDown",
  DEFAULT: "stop",
  CLOSE_EYES: "moveDown",
  OPEN_EYES: "moveUp",
  OPEN_MOUTH: "moveUp",
  CLOSE_MOUTH: "stop",
};

const FACE_RING_COMMANDS = {
  SELECT_RING_A: "A",
  SELECT_RING_B: "B",
  SELECT_RING_C: "C",
  SELECT_RING_D: "D",
};

let activeFaceRing = null;
let activeFaceBehavior = "等待检测";
let activeFaceExpression = "平静";
let activeFaceTempo = "normal";
let faceExpressionControlEnabled = false;
let faceRhythmClockSec = 0;

renderLoop();

const FACE_TEMPO_LABELS = {
  normal: "正常",
  happy: "欢快",
  fast: "快速",
  slow: "缓慢",
  surprise: "旋转加快",
  angry: "强力旋转",
};

const FACE_TEMPO_FACTORS = {
  normal: 1.0,
  happy: 1.2,
  fast: 1.8,
  slow: 0.65,
  surprise: 1.15,
  angry: 0.9,
};

const FACE_TEMPO_ROTATE_BOOSTS = {
  normal: 1.0,
  happy: 1.15,
  fast: 1.55,
  slow: 0.75,
  surprise: 1.8,
  angry: 2.0,
};

function faceActionLabel(command) {
  const labels = {
    LOOK_LEFT: "左转",
    LOOK_RIGHT: "右转",
    LOOK_UP: "上移",
    LOOK_DOWN: "下移",
    OPEN_EYES: "上移",
    CLOSE_EYES: "下移",
    OPEN_MOUTH: "上移",
    CLOSE_MOUTH: "停止",
    DEFAULT: "停止",
  };
  return labels[command] || "等待检测";
}

function applyFaceTempoToRing(ring, tempoMode) {
  const state = ringStates[ring];
  if (!state) return;
  const factor = FACE_TEMPO_FACTORS[tempoMode] ?? 1.0;
  const rotateBoost = FACE_TEMPO_ROTATE_BOOSTS[tempoMode] ?? 1.0;
  if (typeof state.baseMoveSpeed !== "number") {
    state.baseMoveSpeed = state.moveSpeed;
  }
  if (typeof state.baseRotateSpeed !== "number") {
    state.baseRotateSpeed = state.rotateSpeed;
  }
  state.tempoMode = tempoMode;
  state.moveSpeed = state.baseMoveSpeed * factor;
  state.rotateSpeed = state.baseRotateSpeed * factor * rotateBoost;
}

function applyActiveFaceTempo() {
  if (faceExpressionControlEnabled) return;
  if (!activeFaceRing || !["A", "B", "C", "D"].includes(activeFaceRing)) return;
  applyFaceTempoToRing(activeFaceRing, faceExpressionControlEnabled ? activeFaceTempo : "normal");
}

function resetAllRingsToHome(statusText = null) {
  for (const ring of ["A", "B", "C", "D"]) {
    const state = ringStates[ring];
    if (!state) continue;
    state.moveDir = 0;
    state.rotateDir = 0;
    state.heightOffset = 0;
    state.rotationOffset = 0;
    state.expressionRotateDir = 1;
    state.expressionRotateAccum = 0;
    state.tempoMode = "normal";
    if (typeof state.baseMoveSpeed === "number") {
      state.moveSpeed = state.baseMoveSpeed;
    }
    if (typeof state.baseRotateSpeed === "number") {
      state.rotateSpeed = state.baseRotateSpeed;
    }
    syncRingMotionBinding(ring);
  }
  if (statusText) {
    updateStatus(statusText);
  }
}

function getFaceRhythmProfile(expression) {
  const map = {
    平静: {
      freq: 1.0, amp: 0.16, rotateDeg: 12, pulse: 0.05, sharp: 0.0, stagger: 0.6,
      bobFreq: 0.95, bobAmp: 0.04, bobPunch: 0.012, bobBias: 0.0,
      choreoAmp: 0.42, choreoSpeed: 0.75,
    },
    抿嘴微笑: {
      freq: 1.7, amp: 0.24, rotateDeg: 20, pulse: 0.10, sharp: 0.15, stagger: 0.9,
      bobFreq: 1.45, bobAmp: 0.085, bobPunch: 0.03, bobBias: 0.012,
      choreoAmp: 0.62, choreoSpeed: 1.0,
    },
    咧嘴大笑: {
      freq: 2.7, amp: 0.40, rotateDeg: 34, pulse: 0.22, sharp: 0.35, stagger: 1.15,
      bobFreq: 2.1, bobAmp: 0.14, bobPunch: 0.07, bobBias: 0.04,
      choreoAmp: 0.78, choreoSpeed: 1.35,
    },
    惊讶: {
      freq: 3.4, amp: 0.30, rotateDeg: 44, pulse: 0.30, sharp: 0.45, stagger: 1.6,
      bobFreq: 3.25, bobAmp: 0.18, bobPunch: 0.12, bobBias: 0.10,
      choreoAmp: 0.90, choreoSpeed: 1.7,
    },
    愤怒: {
      freq: 2.15, amp: 0.36, rotateDeg: 58, pulse: 0.26, sharp: 0.7, stagger: 1.9,
      bobFreq: 2.45, bobAmp: 0.12, bobPunch: 0.13, bobBias: -0.04,
      choreoAmp: 0.78, choreoSpeed: 1.45,
    },
  };
  return map[expression] || map.平静;
}

function smoothStep01(x) {
  const t = clamp(x, 0, 1);
  return t * t * (3 - 2 * t);
}

function sequentialRingWave(normalizedCycle, ring, upOrder, downOrder) {
  // 一个循环：按 upOrder 逐个上移，再按 downOrder 逐个下移。
  const c = ((normalizedCycle % 1) + 1) % 1;
  const stepPos = c * 8;
  const seg = Math.floor(stepPos);
  const p = stepPos - seg;

  if (seg < 4) {
    const idx = upOrder.indexOf(ring);
    if (idx < 0) return -1;
    if (idx < seg) return 1;
    if (idx === seg) return -1 + 2 * smoothStep01(p);
    return -1;
  }

  const downSeg = seg - 4;
  const idx = downOrder.indexOf(ring);
  if (idx < 0) return 1;
  if (idx < downSeg) return -1;
  if (idx === downSeg) return 1 - 2 * smoothStep01(p);
  return 1;
}

function applyExpressionRhythmToAllRings(delta) {
  faceRhythmClockSec += delta;
  const t = faceRhythmClockSec;
  const profile = getFaceRhythmProfile(activeFaceExpression);
  const phases = { A: 0, B: 1.17, C: 2.34, D: 3.51 };
  const normalizedCycle = (t * profile.choreoSpeed) % 1;
  const pairOsc = Math.sin(normalizedCycle * Math.PI * 2);

  for (const ring of ["A", "B", "C", "D"]) {
    const state = ringStates[ring];
    if (!state) continue;

    const phase = phases[ring] * profile.stagger;
    const baseWave = Math.sin(t * profile.freq + phase);
    const subWave = Math.sin(t * profile.freq * 2.1 + phase * 0.6);
    const pulseWave = Math.max(0, Math.sin(t * profile.freq * 1.35 + phase * 1.4));
    const sharpWave = Math.sign(baseWave) * Math.pow(Math.abs(baseWave), Math.max(0.01, 1 - profile.sharp));
    // 上下律动按表情配置：不同情绪对应不同快慢与轻重。
    const bobWave = Math.sin(t * profile.bobFreq + phase * 0.75);
    const bobPulse = Math.max(0, Math.sin(t * profile.bobFreq * 1.85 + phase * 1.1));
    const emotionBob = bobWave * profile.bobAmp + bobPulse * profile.bobPunch + profile.bobBias;

    let desiredSpinDir = 1;
    let choreoMotion = 0;

    if (activeFaceExpression === "抿嘴微笑") {
      // AC 左转，BD 右转；ABCD 逐个上移，再 DCBA 逐个下降。
      desiredSpinDir = ring === "A" || ring === "C" ? 1 : -1;
      choreoMotion = sequentialRingWave(normalizedCycle, ring, ["A", "B", "C", "D"], ["D", "C", "B", "A"]);
    } else if (activeFaceExpression === "咧嘴大笑") {
      // AC 右转，BD 左转；AC 与 BD 反向同步上下。
      desiredSpinDir = ring === "A" || ring === "C" ? -1 : 1;
      choreoMotion = (ring === "A" || ring === "C") ? pairOsc : -pairOsc;
    } else if (activeFaceExpression === "惊讶") {
      // AB 左转，CD 右转；AD 与 BC 反向同步上下。
      desiredSpinDir = ring === "A" || ring === "B" ? 1 : -1;
      choreoMotion = (ring === "A" || ring === "D") ? pairOsc : -pairOsc;
    } else if (activeFaceExpression === "愤怒") {
      // ABCD 同向左转；AC 与 BD 反向同步上下。
      desiredSpinDir = 1;
      choreoMotion = (ring === "A" || ring === "C") ? pairOsc : -pairOsc;
    } else {
      // 平静等默认：轻微同相上下。
      desiredSpinDir = 1;
      choreoMotion = Math.sin(normalizedCycle * Math.PI * 2 + phase * 0.35) * 0.45;
    }

    let heightNorm = sharpWave * profile.amp + subWave * profile.pulse * 0.35 + pulseWave * profile.pulse * 0.65 + emotionBob + choreoMotion * profile.choreoAmp;
    if (activeFaceExpression === "惊讶") heightNorm += 0.12;
    heightNorm = clamp(heightNorm, -0.95, 0.95);

    const ringRange = Math.min(Math.abs(state.limits.min), Math.abs(state.limits.max));
    const usableRange = Math.max(0.03, ringRange * 0.9);

    state.moveDir = 0;
    state.rotateDir = 0;
    state.heightOffset = clamp(heightNorm * usableRange, state.limits.min, state.limits.max);

    // 旋转策略：每个环必须先完整转一圈（360°）后才允许切换方向。
    if (state.expressionRotateDir !== desiredSpinDir && state.expressionRotateAccum >= Math.PI * 2) {
      state.expressionRotateDir = desiredSpinDir;
      state.expressionRotateAccum = 0;
    }

    const rotateSpeedRad = THREE.MathUtils.degToRad(profile.rotateDeg);
    const deltaAngle = state.expressionRotateDir * rotateSpeedRad * delta;
    state.rotationOffset += deltaAngle;
    state.expressionRotateAccum += Math.abs(deltaAngle);

    syncRingMotionBinding(ring);
  }
}

function setFaceExpressionControlEnabled(enabled) {
  faceExpressionControlEnabled = Boolean(enabled);
  faceRhythmClockSec = 0;
  if (faceTempoToggleBtn) {
    faceTempoToggleBtn.textContent = faceExpressionControlEnabled ? "表情控制：开启" : "表情控制：关闭";
    // 清除停止样式，启用时使用正常样式，禁用时恢复停止样式
    faceTempoToggleBtn.classList.toggle("module-btn--stop", !faceExpressionControlEnabled);
    // 添加视觉反馈：启用时添加活跃状态
    faceTempoToggleBtn.classList.toggle("module-btn--active", faceExpressionControlEnabled);
  }

  if (faceExpressionControlEnabled) {
    activeFaceRing = null;
    activeFaceBehavior = "表情节奏模式（全环联动）";
    resetAllRingsToHome("表情节奏模式：全环归位完成");
  } else {
    activeFaceBehavior = "选环动作模式";
    resetAllRingsToHome("已退出表情节奏模式");
  }

  applyActiveFaceTempo();
  renderFaceGestureInfo();
}

function renderFaceGestureInfo() {
  if (!faceBindings.gestures) return;
  const ringText = faceExpressionControlEnabled ? "全环联动" : (activeFaceRing ? `Ring${activeFaceRing}` : "--");
  const behaviorText = activeFaceBehavior || "等待检测";
  const expressionText = activeFaceExpression || "平静";
  const tempoText = FACE_TEMPO_LABELS[activeFaceTempo] || "正常";
  const controlText = faceExpressionControlEnabled ? "开启" : "关闭";
  const modeText = faceExpressionControlEnabled ? "表情节奏模式" : "选环动作模式";
  faceBindings.gestures.innerHTML = "";
  [
    `当前模式：${modeText}`,
    `当前环：${ringText}`,
    `当前行为：${behaviorText}`,
    `当前表情：${expressionText}`,
    `当前节奏：${tempoText}`,
    `表情控制：${controlText}`,
  ].forEach((line) => {
    const li = document.createElement("li");
    li.textContent = line;
    faceBindings.gestures.appendChild(li);
  });
}

const HAND_COMMAND_MAP = {
  moveUp: "moveUp",
  moveDown: "moveDown",
  rotateLeft: "rotateLeft",
  rotateRight: "rotateRight",
  flowerOpen: "flowerOpen",
  flowerClose: "flowerClose",
  openFlower: "flowerOpen",
  closeFlower: "flowerClose",
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
  if (target === "face" && faceTempoToggleBtn) {
    faceTempoToggleBtn.disabled = !running;
  }
  setStreamVisibility(target, running);

  if (target === "face" && !running) {
    activeFaceBehavior = "等待检测";
    activeFaceExpression = "平静";
    activeFaceTempo = "normal";
    setFaceExpressionControlEnabled(false);
    renderFaceGestureInfo();
  }
}

let bridgeRetryDelayMs = 1000;
let bridgeReconnectTimer = null;
let bridgeSocket = null;
let bridgeConnecting = false;
let activeBridgeHost = window.location.hostname || "127.0.0.1";
const BRIDGE_PORT = 5051;
const QUERY = new URLSearchParams(window.location.search);
const ENABLE_BRIDGE = QUERY.get("standalone") !== "1" && QUERY.get("bridge") !== "off";
const ENABLE_VOICE_AI = QUERY.get("voiceai") !== "off";
const AUTO_START_ON_PAGE_OPEN = false;
const DEFAULT_MODULE_ON_OPEN = "face";
let bridgeBootstrapDone = false;
let lastVoiceAiTranscript = "";
let voiceAiRequestBusy = false;
let voiceAiRunToken = 0;

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
  if (typeof event.data !== "string") return;
  const raw = event.data.trim();
  if (!raw || !raw.startsWith("{")) return;
  try {
    const data = JSON.parse(raw);
    handleBridgeEvent(data);
  } catch {
    // Ignore heartbeat/non-JSON noise from bridge endpoint.
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
      const faceCommand = message.payload?.command;
      if (faceBindings.cmd && faceCommand) {
        faceBindings.cmd.textContent = faceCommand;
      }

      // 表情节奏模式下，禁用“选环 + 单环动作”链路。
      if (faceExpressionControlEnabled) {
        activeFaceBehavior = "表情节奏模式（全环联动）";
        renderFaceGestureInfo();
        return;
      }

      const ringFromFace = FACE_RING_COMMANDS[message.payload?.command];
      if (ringFromFace) {
        activeFaceRing = ringFromFace;
        activeFaceBehavior = `选中 Ring${ringFromFace}`;
        applyActiveFaceTempo();
        renderFaceGestureInfo();
        if (faceBindings.cmd) {
          faceBindings.cmd.textContent = `SELECT_RING_${ringFromFace}`;
        }
        if (faceBindings.badge) {
          faceBindings.badge.textContent = `面部选环 → Ring${ringFromFace}`;
        }
        return;
      }

      const next = FACE_COMMAND_MAP[message.payload?.command];
      if (message.payload?.command) {
        activeFaceBehavior = faceActionLabel(message.payload.command);
        renderFaceGestureInfo();
      }
      if (next) {
        if (activeFaceRing && ["A", "B", "C", "D"].includes(activeFaceRing)) {
          applyRingCommand(activeFaceRing, next);
        } else {
          relayExternalCommand("face", next, message.payload);
        }
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
      const ring = message.payload?.ring || message.payload?.meta?.ring;
      if (message.payload?.action === "selectRing") {
        if (handBindings.badge) {
          handBindings.badge.textContent = ring ? `手势选环 → Ring${ring}` : "手势选环";
        }
        return;
      }
      const next = HAND_COMMAND_MAP[message.payload?.action];
      if (next) {
        if (handBindings.badge) {
          handBindings.badge.textContent = ring
            ? `手势 → Ring${ring}:${message.payload?.action}`
            : `手势 → ${message.payload?.action}`;
        }
        if (ring && ["A", "B", "C", "D"].includes(ring)) {
          applyRingCommand(ring, next);
        } else {
          relayExternalCommand("hand", next, message.payload);
        }
      }
    }
    return;
  }

  if (message.channel === "voice") {
    if (message.type === "status") {
      const payload = message.payload || {};
      updateVoiceCard(payload);
      maybeRunVoiceAi(payload);
    }
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
    const isNetworkError = err instanceof TypeError;
    if (isNetworkError) {
      console.warn("控制模块失败：bridge 服务未连接（127.0.0.1:5051）");
    } else {
      console.error("控制模块失败", err);
    }
    setModuleState(target, false, true);
    updateBridgeStatus(
      isNetworkError
        ? "桥接服务：连接失败，请先启动 bridge（127.0.0.1:5051）"
        : "桥接服务：无法连接后端控制接口",
      "error"
    );
  }
}

function getControlUrl(path) {
  const protocol = window.location.protocol.startsWith("http")
    ? window.location.protocol
    : "http:";
  return `${protocol}//${activeBridgeHost}:${BRIDGE_PORT}${path}`;
}

function sleepMs(ms) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

function shouldRunVoiceAi(payload) {
  if (!ENABLE_VOICE_AI || !payload) return false;
  if (!payload.available) return false;
  const transcript = String(payload.transcript || "").trim();
  if (transcript.length < 4) return false;
  if (transcript === lastVoiceAiTranscript) return false;
  if (/等待唤醒|唤醒词/i.test(payload.status_text || "")) return false;
  return true;
}

async function requestVoiceAiPlan(transcript) {
  const response = await fetch(getControlUrl("/api/ai/voice-plan"), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text: transcript }),
  });
  const json = await response.json();
  if (!response.ok || json.status !== "ok" || !json.plan) {
    throw new Error("voice_ai_plan_failed");
  }
  return json;
}

async function executeVoiceMotionPlan(result, transcript) {
  const token = ++voiceAiRunToken;
  const plan = result?.plan || {};
  const steps = Array.isArray(plan.steps) ? plan.steps : [];
  if (!steps.length) return;

  if (voiceBindings.badge) {
    voiceBindings.badge.textContent = result.engine === "llm" ? "AI编排中" : "规则编排中";
    voiceBindings.badge.classList.add("alert");
  }
  if (voiceBindings.command) {
    voiceBindings.command.textContent = plan.summary || "已生成动作序列";
  }

  updateStatus(`语音AI执行：${transcript.slice(0, 16)}${transcript.length > 16 ? "..." : ""}`);

  for (const step of steps) {
    if (token !== voiceAiRunToken) return;
    const ring = typeof step.ring === "string" ? step.ring : null;
    const action = typeof step.action === "string" ? step.action : "stop";
    const durationMs = Number.isFinite(step.durationMs) ? Math.max(200, Number(step.durationMs)) : 900;

    if (ring && ["A", "B", "C", "D"].includes(ring)) {
      applyRingCommand(ring, action);
      await sleepMs(durationMs);
      if (token !== voiceAiRunToken) return;
      if (action !== "stop") stopRingMotion(ring, `Ring${ring} - 停止`);
      continue;
    }

    applyCommand(action);
    await sleepMs(durationMs);
    if (token !== voiceAiRunToken) return;
    if (action !== "stop") applyCommand("stop");
  }

  if (voiceBindings.badge) {
    voiceBindings.badge.textContent = "监听中";
    voiceBindings.badge.classList.remove("alert");
  }
}

async function maybeRunVoiceAi(payload) {
  if (!shouldRunVoiceAi(payload) || voiceAiRequestBusy) return;
  const transcript = String(payload.transcript || "").trim();
  voiceAiRequestBusy = true;
  lastVoiceAiTranscript = transcript;

  try {
    const result = await requestVoiceAiPlan(transcript);
    await executeVoiceMotionPlan(result, transcript);
  } catch (err) {
    console.warn("语音 AI 编排失败，已跳过", err);
    if (voiceBindings.badge) {
      voiceBindings.badge.textContent = "AI失败";
      voiceBindings.badge.classList.add("alert");
    }
  } finally {
    voiceAiRequestBusy = false;
  }
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
  if (payload.status_text && faceBindings.status) {
    faceBindings.status.textContent = `当前状态：${payload.status_text}`;
  }
  if (payload.direction && faceBindings.direction) {
    faceBindings.direction.textContent = payload.direction.replace("LOOK_", "");
  }
  if (payload.eye && faceBindings.eye) faceBindings.eye.textContent = payload.eye;
  if (payload.mouth && faceBindings.mouth) faceBindings.mouth.textContent = payload.mouth;
  if (payload.serial_status && faceBindings.serial) faceBindings.serial.textContent = payload.serial_status;
  if (payload.last_command && faceBindings.cmd) faceBindings.cmd.textContent = payload.last_command;
  if (typeof payload.expression === "string") {
    const normalizedExpression = payload.expression === "难过抽泣" ? "平静" : payload.expression;
    activeFaceExpression = normalizedExpression;
    const normalizedTempo = payload.tempo === "slow" ? "normal" : payload.tempo;
    const nextTempo = normalizedTempo && FACE_TEMPO_FACTORS[normalizedTempo] ? normalizedTempo : "normal";
    activeFaceTempo = nextTempo;
    applyActiveFaceTempo();
  }
  if (faceBindings.mode) {
    faceBindings.mode.textContent = payload.calibrated ? "已校准" : "校准中";
    faceBindings.mode.classList.toggle("alert", !payload.calibrated);
  }
  renderFaceGestureInfo();
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
  if (!handBindings.gestures) return;

  const lines = Array.isArray(payload.gestures)
    ? payload.gestures.filter((line) => typeof line === "string" && line.trim().length > 0)
    : [];

  const left = payload.left_status || {};
  const right = payload.right_status || {};

  const leftGesture = typeof left.ring_gesture === "string" ? left.ring_gesture : "not_detected";
  const leftActive = typeof left.active_ring === "string" ? left.active_ring : "A";
  const rightDirection = typeof right.index_direction === "string" ? right.index_direction : "not_detected";

  const fallbackLines = [
    `Left Ring Gesture: ${leftGesture}`,
    `Left Active Ring: ${leftActive}`,
    `Right Index Direction: ${rightDirection}`,
  ];

  const renderLines = lines.length > 0 ? lines.slice(-4) : fallbackLines;

  handBindings.gestures.innerHTML = "";
  renderLines.forEach((line) => {
    const li = document.createElement("li");
    li.textContent = line;
    handBindings.gestures.appendChild(li);
  });
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
if (faceTempoToggleBtn) {
  faceTempoToggleBtn.addEventListener("click", () => {
    setFaceExpressionControlEnabled(!faceExpressionControlEnabled);
  });
}
if (handStartBtn) handStartBtn.addEventListener("click", () => callModuleControl("hand", "start"));
if (handStopBtn) handStopBtn.addEventListener("click", () => callModuleControl("hand", "stop"));
if (voiceStartBtn) voiceStartBtn.addEventListener("click", () => callModuleControl("voice", "start"));
if (voiceStopBtn) voiceStopBtn.addEventListener("click", () => callModuleControl("voice", "stop"));

window.addEventListener("resize", () => resizeRenderer());
resizeRenderer();
syncMotionBinding();
initFlowerDebugApi();
initRingDebugApi();
loadExternalModel();
connectBridge();
stopMotion();
setStreamVisibility("face", false);
setStreamVisibility("hand", false);
