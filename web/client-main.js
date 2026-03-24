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

// 默认不显示内置演示模型，避免外部模型加载时出现“先闪一下试用版”
fallbackRoot.visible = false;

const modelAnchor = new THREE.Group();
scene.add(modelAnchor);

const floor = new THREE.Mesh(
  new THREE.CircleGeometry(4, 80),
  new THREE.MeshBasicMaterial({ color: 0x0a152f, transparent: true, opacity: 0.8 })
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

const flowerState = {
  openness: 0,
  target: 0,
  speed: 1.1,
  nodes: [],
};

const flowerRuntimeConfig = {
  manualNodeNames: [],
};

let lastLoadedModelRoot = null;

const modelLoader = new GLTFLoader();
const fbxLoader = new FBXLoader();
const FORCE_DEBUG_MODEL_MATERIAL = false;
const FORCE_WIREFRAME_OVERLAY = false;
const FORCE_POINTS_OVERLAY = false;
const MODEL_CANDIDATES = [
  // 当前模型（用户指定）
  "./models/chaifen.fbx?v=20260324-chaifen-current",
  // FBX 优先（用户指定文件）
  "./models/ImageToStl.com_999.fbx?v=20260317-fbx-user",
  "./models/model_999.fbx?v=20260317-fbx",
  // GLB 备用
  "./models/model_999.glb?v=20260316-model999b",
  "./models/ImageToStl.com_999.glb?v=20260316-model999",
  "./models/dripmotion.glb?v=20260316-named4",
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
    const { node, basePosition, baseRotation, baseScale, phase } = entry;
    if (!node) return;

    const radial = 0.045 * t;
    const tilt = 0.34 * t;

    node.position.copy(basePosition);
    node.position.x += Math.cos(phase) * radial;
    node.position.z += Math.sin(phase) * radial;
    node.position.y += 0.012 * t;

    node.rotation.copy(baseRotation);
    node.rotation.x = baseRotation.x - tilt;

    node.scale.set(
      baseScale.x * (1 + 0.20 * t),
      baseScale.y * (1 - 0.08 * t),
      baseScale.z * (1 + 0.20 * t)
    );
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
  console.log(`[DripMotion] 花朵开合节点已绑定：${flowerState.nodes.length} 个`, flowerState.nodes.map((x) => x.node.name));
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
  };

  root.traverse((node) => {
    if (!node?.isMesh) return;
    const layer = detectRingLayer(node);
    if (!layer) return;

    const spec = palette[layer];
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
  // 加载外部模型期间保持内置模型隐藏，避免先闪出试用模型
  setFallbackVisible(false);

  let lastError = null;
  for (const candidate of MODEL_CANDIDATES) {
    const modelUrl = new URL(candidate, import.meta.url).href;
    const fileName = getDisplayFileName(modelUrl);
    const isFBX = /\.fbx(\?|$)/i.test(modelUrl);

    // 先用 HEAD 检查文件是否存在，避免为缺失文件报错
    if (isFBX) {
      try {
        const probe = await fetch(modelUrl, { method: "HEAD" });
        if (!probe.ok) {
          console.log(`[DripMotion] FBX 候选文件不存在 (${probe.status})，跳过：${fileName}`);
          continue;
        }
      } catch {
        console.log(`[DripMotion] FBX 候选文件无法访问，跳过：${fileName}`);
        continue;
      }
    }

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

      // 你的 ImageToStl.com_999.fbx 需要翻转；其余 FBX 通常不需要翻转
      const needsFlipX = !isFBX || /imagetostl\.com_999\.fbx/i.test(fileName);
      normalizeLoadedModel(modelRoot, needsFlipX);

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

      modelAnchor.clear();
      modelAnchor.add(modelRoot);
      lastLoadedModelRoot = modelRoot;
      setFallbackVisible(false);
      modelBoundsHelper.visible = false;

      focusCameraOnObject(modelRoot);

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

  console.error("[DripMotion] 外部 3D 模型加载失败，回退到内置演示模型", lastError);
  modelAnchor.clear();
  setFallbackVisible(true);
  modelBoundsHelper.visible = false;
  bindMotionTargets(topPivot, topPivot, "fallback");
  clearFlowerRig();
  lastLoadedModelRoot = null;
  updateModelStatus("3D 模型：候选文件均加载失败，当前使用内置演示模型", "warn");
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
    case "flowerOpen":
      setFlowerTarget(1, "中间花朵 - 打开中");
      break;
    case "flowerClose":
      setFlowerTarget(0, "中间花朵 - 闭合中");
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
initFlowerDebugApi();
loadExternalModel();
connectBridge();
stopMotion();
setStreamVisibility("face", false);
setStreamVisibility("hand", false);
