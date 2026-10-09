/* Ground Truth 3D: Delhi in fog, drawn from our own data. No tile server.
   The ground is Delhi's wards; landmarks and monitor masts stand at their real coordinates;
   each monitor carries a column as tall as its PM2.5 reading and a cloud of smog; dust drifts
   through the air, thicker on dirtier days. app.js talks to this module through window.GT3D. */
import * as THREE from "./vendor/three/three.module.min.js";
import { OrbitControls } from "./vendor/three/OrbitControls.js";

const LAT0 = 28.63, LON0 = 77.16;
const KX = (111320 * Math.cos((LAT0 * Math.PI) / 180)) / 100; // scene units per degree (1 unit = 100 m)
const KZ = 110540 / 100;
const xy = (lon, lat) => [(lon - LON0) * KX, (lat - LAT0) * KZ]; // shape plane: x east, y north
const FOG = 0xe8e7e4;
const STATE = { ok: 0x0ca30c, watch: 0xf2a60c, flag: 0xd03b3b, nodata: 0xa3a4a9 };
const TINT = { ok: 0xa9cdb0, watch: 0xefc867, flag: 0xe2867f, nodata: 0xcfd0d3 };
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const small = matchMedia("(max-width: 760px), (pointer: coarse)").matches; // phones and tablets start lighter
// ?capture=1 (video/capture_gif.py): no shadows, pixel ratio 1, less dust and no quality steps: alike, compact frames
const capture = new URLSearchParams(location.search).has("capture");

// a GPU-less machine draws WebGL in software; it gets the lightest scene from the start
function softwareGL(renderer) {
  const gl = renderer.getContext(), ext = gl.getExtension("WEBGL_debug_renderer_info");
  return /swiftshader|llvmpipe|softpipe|software|basic render/i.test(ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : "");
}

function radial(inner, outer) {
  const c = document.createElement("canvas"); c.width = c.height = 128;
  const g = c.getContext("2d").createRadialGradient(64, 64, 0, 64, 64, 64);
  g.addColorStop(0, inner); g.addColorStop(1, outer);
  const ctx = c.getContext("2d"); ctx.fillStyle = g; ctx.fillRect(0, 0, 128, 128);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

function shapeFromRing(ring) {
  const s = new THREE.Shape();
  ring.forEach(([lon, lat], i) => { const [x, y] = xy(lon, lat); i ? s.lineTo(x, y) : s.moveTo(x, y); });
  return s;
}

function pointInRing(x, y, ring) {
  let inside = false;
  for (let i = 0, j = ring.length - 1; i < ring.length; j = i++) {
    const [xi, yi] = ring[i], [xj, yj] = ring[j];
    if ((yi > y) !== (yj > y) && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
  }
  return inside;
}

async function getJSON(u) { const r = await fetch(u); if (!r.ok) throw new Error(u); return r.json(); }

function buildGround(scene, wards, boundary) {
  // the land beyond Delhi, fading into fog
  const plane = new THREE.Mesh(new THREE.PlaneGeometry(6000, 6000), new THREE.MeshLambertMaterial({ color: 0xe2e1de }));
  plane.rotation.x = -Math.PI / 2; plane.receiveShadow = true; scene.add(plane);

  const mats = [0xf4f4f2, 0xf1f1ee, 0xeeeeeb].map((c) => new THREE.MeshLambertMaterial({ color: c }));
  const edge = [], merged = mats.map(() => ({ pos: [], nor: [] })); // one mesh per shade, not one per ward: 3 draw calls, not 290
  wards.features.forEach((f, i) => {
    const polys = f.geometry.type === "Polygon" ? [f.geometry.coordinates] : f.geometry.coordinates;
    for (const p of polys) {
      const shape = shapeFromRing(p[0]);
      p.slice(1).forEach((hole) => shape.holes.push(shapeFromRing(hole)));
      const g = new THREE.ExtrudeGeometry(shape, { depth: 0.5, bevelEnabled: false });
      g.rotateX(-Math.PI / 2);
      merged[i % 3].pos.push(...g.attributes.position.array); merged[i % 3].nor.push(...g.attributes.normal.array);
      g.dispose();
      p[0].forEach(([lon, lat], k) => {
        if (!k) return;
        const [x0, y0] = xy(...p[0][k - 1]), [x1, y1] = xy(lon, lat);
        edge.push(x0, 0.52, -y0, x1, 0.52, -y1);
      });
    }
  });
  merged.forEach(({ pos, nor }, k) => {
    const g = new THREE.BufferGeometry();
    g.setAttribute("position", new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute("normal", new THREE.Float32BufferAttribute(nor, 3));
    const m = new THREE.Mesh(g, mats[k]); m.receiveShadow = true; scene.add(m);
  });
  const eg = new THREE.BufferGeometry(); eg.setAttribute("position", new THREE.Float32BufferAttribute(edge, 3));
  scene.add(new THREE.LineSegments(eg, new THREE.LineBasicMaterial({ color: 0xd2d2ce })));

  const ring = boundary.features[0].geometry.type === "Polygon" ? boundary.features[0].geometry.coordinates[0] : boundary.features[0].geometry.coordinates[0][0];
  const pts = ring.map(([lon, lat]) => { const [x, y] = xy(lon, lat); return new THREE.Vector3(x, 0.7, -y); });
  const bl = new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineDashedMaterial({ color: 0x8f9095, dashSize: 3, gapSize: 2 }));
  bl.computeLineDistances(); scene.add(bl);
  return ring.map(([lon, lat]) => xy(lon, lat));
}

function buildCity(scene, ringXY, share = 1) {
  // low city blocks and a few trees, scattered inside Delhi's boundary (deterministic, so every visit looks the same)
  const xs = ringXY.map((p) => p[0]), ys = ringXY.map((p) => p[1]);
  const [x0, x1, y0, y1] = [Math.min(...xs), Math.max(...xs), Math.min(...ys), Math.max(...ys)];
  let seed = 11;
  const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  const inside = () => { for (let g = 0; g < 50; g++) { const x = x0 + rnd() * (x1 - x0), y = y0 + rnd() * (y1 - y0); if (pointInRing(x, y, ringXY)) return [x, y]; } return null; };
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), up = new THREE.Vector3(0, 1, 0);

  const nBlocks = Math.round(4200 * share), nTrees = Math.round(900 * share);
  const blocks = new THREE.InstancedMesh(new THREE.BoxGeometry(1, 1, 1), new THREE.MeshLambertMaterial({ color: 0xffffff }), nBlocks);
  const col = new THREE.Color();
  let n = 0;
  for (let i = 0; i < nBlocks; i++) {
    const p = inside(); if (!p) continue;
    const w = 0.35 + rnd() * 0.75, d = 0.35 + rnd() * 0.75, h = 0.25 + Math.pow(rnd(), 3) * 3.2;
    q.setFromAxisAngle(up, rnd() * Math.PI);
    m.compose(new THREE.Vector3(p[0], 0.5 + h / 2, -p[1]), q, new THREE.Vector3(w, h, d));
    blocks.setMatrixAt(n, m); blocks.setColorAt(n, col.setHSL(0.1, 0.04, 0.86 + rnd() * 0.08)); n++;
  }
  blocks.count = n; blocks.castShadow = true; blocks.receiveShadow = true; scene.add(blocks);

  const trees = new THREE.InstancedMesh(new THREE.ConeGeometry(0.45, 1.6, 7), new THREE.MeshLambertMaterial({ color: 0xa7b0a3 }), nTrees);
  n = 0;
  for (let i = 0; i < nTrees; i++) {
    const p = inside(); if (!p) continue;
    const s = 0.6 + rnd() * 0.7;
    m.compose(new THREE.Vector3(p[0], 0.5 + 0.8 * s, -p[1]), q.identity(), new THREE.Vector3(s, s, s));
    trees.setMatrixAt(n++, m);
  }
  trees.count = n; trees.castShadow = true; scene.add(trees);
}

function buildLandmarks(scene) {
  const stone = new THREE.MeshStandardMaterial({ color: 0xb4b5b8, roughness: 0.95 });
  const put = (obj, lon, lat) => { const [x, y] = xy(lon, lat); obj.position.set(x, 0.5, -y); obj.scale.setScalar(2); obj.traverse((o) => { o.castShadow = o.receiveShadow = true; }); scene.add(obj); };

  // Qutub Minar: five tapering storeys with balconies
  const qm = new THREE.Group(); let y = 0, r = 1.5;
  for (let i = 0; i < 5; i++) {
    const h = [7, 5.5, 4.5, 3.2, 3][i], r2 = r * 0.82;
    const seg = new THREE.Mesh(new THREE.CylinderGeometry(r2, r, h, 20), stone); seg.position.y = y + h / 2; qm.add(seg);
    const bal = new THREE.Mesh(new THREE.CylinderGeometry(r2 + 0.35, r2 + 0.35, 0.3, 20), stone); bal.position.y = y + h; qm.add(bal);
    y += h; r = r2;
  }
  const cap = new THREE.Mesh(new THREE.SphereGeometry(r * 0.9, 12, 8, 0, Math.PI * 2, 0, Math.PI / 2), stone); cap.position.y = y + 0.15; qm.add(cap);
  put(qm, 77.1855, 28.5245);

  // India Gate: two piers, the arch lintel, attic and a shallow dome
  const ig = new THREE.Group();
  [-4.2, 4.2].forEach((x) => { const p = new THREE.Mesh(new THREE.BoxGeometry(3.4, 11, 3.2), stone); p.position.set(x, 5.5, 0); ig.add(p); });
  const lin = new THREE.Mesh(new THREE.BoxGeometry(11.8, 2.6, 3.2), stone); lin.position.y = 12.3; ig.add(lin);
  const att = new THREE.Mesh(new THREE.BoxGeometry(9.5, 1.6, 2.6), stone); att.position.y = 14.4; ig.add(att);
  const dome = new THREE.Mesh(new THREE.SphereGeometry(1.6, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), stone); dome.position.y = 15.2; ig.add(dome);
  put(ig, 77.2295, 28.6129);

  // Lotus Temple: two rings of petals around a base
  const lt = new THREE.Group();
  const base = new THREE.Mesh(new THREE.CylinderGeometry(7.5, 8, 0.8, 27), stone); base.position.y = 0.4; lt.add(base);
  const petal = new THREE.SphereGeometry(2.6, 16, 12, 0, Math.PI, 0, Math.PI);
  [[9, 4.8, 0.95, 0.5], [9, 2.4, 1.25, 0]].forEach(([n, rad, sy, off]) => {
    for (let i = 0; i < n; i++) {
      const a = ((i + off) / n) * Math.PI * 2, p = new THREE.Mesh(petal, stone);
      p.scale.set(0.7, sy * 2.2, 0.55); p.position.set(Math.cos(a) * rad, 2.8 * sy, Math.sin(a) * rad);
      p.rotation.y = -a; p.rotation.z = -0.28 * (rad > 3 ? 1 : 0.4); lt.add(p);
    }
  });
  put(lt, 77.2588, 28.5535);
}

// Every part of every monitor is one InstancedMesh, so 52 monitors cost 7 draw calls, not ~470: on a phone each
// WebGL call is what costs. Glows and smog are camera-facing quads, turned to the camera before each frame.
function buildMonitors(scene, stations, reading) {
  const steel = new THREE.MeshStandardMaterial({ color: 0x2f3033, roughness: 0.6, metalness: 0.3 });
  const box = new THREE.MeshStandardMaterial({ color: 0x3e3f43, roughness: 0.7 });
  const flat = (map, opacity) => new THREE.MeshBasicMaterial({ map, transparent: true, opacity, depthWrite: false });
  const tint = (opacity, side) => new THREE.MeshLambertMaterial({ transparent: true, opacity, side, depthWrite: false });
  const n = stations.length, quad = new THREE.PlaneGeometry(1, 1);
  const inst = (geo, mat, count, shadow = false) => {
    const im = new THREE.InstancedMesh(geo, mat, count); im.count = 0; im.frustumCulled = false; im.castShadow = shadow; scene.add(im); return im;
  };
  const poles = inst(new THREE.CylinderGeometry(0.16, 0.22, 7, 8), steel, n, true);
  const boxes = inst(new THREE.BoxGeometry(1.6, 1.2, 0.9), box, n, true);
  const leds = inst(new THREE.SphereGeometry(0.34, 12, 8), new THREE.MeshBasicMaterial(), n);
  const glows = inst(quad, flat(radial("rgba(255,255,255,1)", "rgba(255,255,255,0)"), 0.5), n);
  const cols = inst(new THREE.CylinderGeometry(1.9, 1.9, 1, 28, 1, true), tint(0.55, THREE.DoubleSide), n);
  const caps = inst(new THREE.CircleGeometry(1.9, 28).rotateX(-Math.PI / 2), tint(0.8), n);
  // smog: brown puffs, each with its own opacity (an instanced attribute, multiplied in after the texture)
  const smogGeo = quad.clone(), smogAlpha = new THREE.InstancedBufferAttribute(new Float32Array(n * 3), 1);
  smogGeo.setAttribute("alpha", smogAlpha);
  const smogMat = flat(radial("rgba(118,106,90,0.55)", "rgba(118,106,90,0)"), 1);
  smogMat.onBeforeCompile = (sh) => {
    sh.vertexShader = "attribute float alpha;\nvarying float vAlpha;\n" + sh.vertexShader.replace("#include <begin_vertex>", "#include <begin_vertex>\nvAlpha = alpha;");
    sh.fragmentShader = "varying float vAlpha;\n" + sh.fragmentShader.replace("#include <map_fragment>", "#include <map_fragment>\ndiffuseColor.a *= vAlpha;");
  };
  const smog = inst(smogGeo, smogMat, n * 3);
  const m = new THREE.Matrix4(), q = new THREE.Quaternion(), at = new THREE.Vector3(), size = new THREE.Vector3(), c = new THREE.Color();
  const put = (im, x, y, z, color = null, sx = 1, sy = 1) => {
    m.compose(at.set(x, y, z), q.identity(), size.set(sx, sy, sx)); im.setMatrixAt(im.count, m);
    if (color != null) im.setColorAt(im.count, c.set(color));
    return im.count++;
  };
  const faces = []; // [mesh, index, x, y, z, width, height] for every camera-facing quad
  const tops = new Map(), ids = [];
  for (const s of stations) {
    const [x, y] = xy(s.lon, s.lat), z = -y;
    ids.push(s.id);
    put(poles, x, 4, z); put(boxes, x, 6.7, z); put(leds, x, 7.8, z, STATE[s.status]);
    faces.push([glows, put(glows, x, 7.8, z, STATE[s.status]), x, 7.8, z, 2.6, 2.6]);
    const pm = reading(s);
    if (pm != null) {
      const h = Math.max(pm, 4) * 0.34;
      put(cols, x, 8.5 + h / 2, z, TINT[s.status], 1, h); put(caps, x, 8.5 + h, z, TINT[s.status]);
      // smog: layered clouds, wider and thicker where the reading is higher
      for (let k = 0; k < 3; k++) {
        const w = 30 + pm * 0.55 + k * 12, i = put(smog, 0, 0, 0);
        smogAlpha.setX(i, Math.min(0.75, 0.2 + pm / 260) * (1 - k * 0.2));
        faces.push([smog, i, x + (k - 1) * 4, 4.5 + k * 5, z + (k % 2) * 3, w, w * 0.45]);
      }
      tops.set(s.id, new THREE.Vector3(x, 0.5 + 8 + h + 1.2, z));
    } else tops.set(s.id, new THREE.Vector3(x, 9, z));
  }
  const face = (camera) => {
    for (const [im, i, x, y, z, w, h] of faces) { m.compose(at.set(x, y, z), camera.quaternion, size.set(w, h, 1)); im.setMatrixAt(i, m); }
    glows.instanceMatrix.needsUpdate = smog.instanceMatrix.needsUpdate = true;
  };
  return { tops, pickables: [poles, boxes], ids, face };
}

function buildDust(scene, median, cap) {
  let n = Math.round(Math.min(cap, 2500 + median * 45));
  const pos = new Float32Array(n * 3), vel = new Float32Array(n * 3), jitter = new Float32Array(n * 2);
  // the drift: a gentle easterly by default; setWind turns it to the real wind (x east, z south)
  let wind = { x: 0.02, z: 0 };
  for (let i = 0; i < n; i++) {
    pos[i * 3] = (Math.random() - 0.5) * 700; pos[i * 3 + 1] = 1 + Math.random() * 70; pos[i * 3 + 2] = (Math.random() - 0.5) * 760;
    jitter[i * 2] = 0.5 + Math.random(); jitter[i * 2 + 1] = (Math.random() - 0.5) * 0.01;
    vel[i * 3] = wind.x * jitter[i * 2]; vel[i * 3 + 1] = (Math.random() - 0.4) * 0.008; vel[i * 3 + 2] = wind.z * jitter[i * 2] + jitter[i * 2 + 1];
  }
  // embers on the horizon in the fires' direction (data/fires.json): a few hundred warm points far out,
  // low to the ground, flickering; cheap enough for a phone (one Points object)
  let embers = null;
  const setFires = (doc) => {
    if (embers) { scene.remove(embers); embers.geometry.dispose(); embers = null; }
    if (!doc || !doc.count || doc.bearing_deg == null) return;
    const m = Math.min(300, 20 + Math.round(doc.count / 2));
    const p = new Float32Array(m * 3);
    const to = doc.bearing_deg * Math.PI / 180;  // bearing clockwise from north; x east, z south
    for (let i = 0; i < m; i++) {
      const spread = (Math.random() - 0.5) * 0.9, r = 520 + Math.random() * 160;
      p[i * 3] = Math.sin(to + spread) * r; p[i * 3 + 1] = 0.6 + Math.random() * 6; p[i * 3 + 2] = -Math.cos(to + spread) * r;
    }
    const eg = new THREE.BufferGeometry(); eg.setAttribute("position", new THREE.BufferAttribute(p, 3));
    embers = new THREE.Points(eg, new THREE.PointsMaterial({ size: 3.2, map: radial("rgba(255,140,40,1)", "rgba(255,90,20,0)"), color: 0xff8a3c,
      transparent: true, opacity: 0.85, depthWrite: false, sizeAttenuation: true, fog: false }));
    scene.add(embers);
  };
  const flicker = (t) => { if (embers) embers.material.opacity = 0.65 + 0.2 * Math.sin(t / 380); };

  const setWind = (fromDeg, kmh) => {
    if (fromDeg == null || kmh == null) return;
    // blows towards fromDeg + 180; speed on screen from 0.3 (calm) to 3 (a strong wind) times the default drift
    const to = ((fromDeg + 180) % 360) * Math.PI / 180, k = Math.min(3, Math.max(0.3, kmh / 10)) * 0.02;
    wind = { x: Math.sin(to) * k, z: -Math.cos(to) * k };
    for (let i = 0; i < n; i++) { vel[i * 3] = wind.x * jitter[i * 2]; vel[i * 3 + 2] = wind.z * jitter[i * 2] + jitter[i * 2 + 1]; }
  };
  const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  const dot = radial("rgba(100,92,80,1)", "rgba(100,92,80,0)");
  const pts = new THREE.Points(g, new THREE.PointsMaterial({ size: 1.1, map: dot, color: 0x6e6457, transparent: true, opacity: 0.55, depthWrite: false, sizeAttenuation: true }));
  scene.add(pts);
  const step = () => {
    for (let i = 0; i < n; i++) {
      pos[i * 3] += vel[i * 3]; pos[i * 3 + 1] += vel[i * 3 + 1]; pos[i * 3 + 2] += vel[i * 3 + 2];
      if (pos[i * 3] > 350) pos[i * 3] = -350; else if (pos[i * 3] < -350) pos[i * 3] = 350;
      if (pos[i * 3 + 2] > 380) pos[i * 3 + 2] = -380; else if (pos[i * 3 + 2] < -380) pos[i * 3 + 2] = 380;
      if (pos[i * 3 + 1] > 72 || pos[i * 3 + 1] < 0.5) vel[i * 3 + 1] *= -1;
    }
    g.attributes.position.needsUpdate = true;
  };
  const resize = (k) => { n = Math.floor(n * k); g.setDrawRange(0, n); pts.visible = n > 0; };
  return { step, resize, setWind, setFires, flicker, get on() { return n > 0 || !!embers; } };
}

async function init(container, { stations, reading, makeMarker, onPick, onBackgroundClick }) {
  const [wards, boundary] = await Promise.all([getJSON("geo/delhi_wards.json"), getJSON("geo/delhi_boundary.json")]);
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(FOG);
  scene.fog = new THREE.Fog(FOG, 180, 820);

  const renderer = new THREE.WebGLRenderer({ antialias: true });
  const soft = softwareGL(renderer), light = soft || small, shadows = !light && !capture;
  let dirty = true; // something changed that needs a redraw
  renderer.setPixelRatio(Math.min(devicePixelRatio, soft || capture ? 1 : small ? 1.5 : 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.shadowMap.enabled = shadows; renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  container.appendChild(renderer.domElement);
  renderer.domElement.setAttribute("aria-hidden", "true");

  const camera = new THREE.PerspectiveCamera(38, 1, 1, 4000);
  camera.position.set(-120, 150, 235);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.target.set(10, 0, 10); controls.enableDamping = true; controls.dampingFactor = 0.06;
  controls.minDistance = 60; controls.maxDistance = 900; controls.minPolarAngle = 0.25; controls.maxPolarAngle = 1.36;
  controls.enableZoom = false; controls.autoRotateSpeed = 0.35; controls.update();

  scene.add(new THREE.HemisphereLight(0xf7f7f8, 0xcfcfca, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 1.5);
  sun.position.set(-220, 320, 160); sun.castShadow = shadows;
  Object.assign(sun.shadow.camera, { left: -380, right: 380, top: 380, bottom: -380, near: 10, far: 1200 });
  sun.shadow.mapSize.set(2048, 2048); sun.shadow.bias = -0.0005; scene.add(sun);

  // built in slices with a breath between them, so the page stays responsive while the city goes up
  const breathe = () => new Promise((r) => setTimeout(r));
  const ringXY = buildGround(scene, wards, boundary);
  await breathe();
  buildCity(scene, ringXY, light ? 0.45 : 1);
  await breathe();
  buildLandmarks(scene);
  const { tops, pickables, ids, face } = buildMonitors(scene, stations, reading);
  const vals = stations.map(reading).filter((v) => v != null).sort((a, b) => a - b);
  const dust = buildDust(scene, vals.length ? vals[Math.floor(vals.length / 2)] : 40, soft || capture ? 0 : small ? 3000 : 9000);

  // when frames average over 33 ms for 2 s, give up one thing at a time, cheapest loss first
  const stepsDown = [
    () => { renderer.shadowMap.enabled = false; sun.castShadow = false; },
    () => dust.resize(0.5),
    () => { renderer.setPixelRatio(1); size(); },
    () => dust.resize(0),
  ].slice(soft || capture ? 4 : small ? 1 : 0);
  let slow = { t: 0, n: 0 };
  const pace = (dt) => {
    if (!stepsDown.length || dt > 1000) return; // a long gap is a hidden tab, not a slow frame
    slow.t += dt; slow.n++;
    if (slow.t < 2000) return;
    if (slow.t / slow.n > 33) { stepsDown.shift()(); dirty = true; }
    slow = { t: 0, n: 0 };
  };

  // HTML markers (the site's own status icons), kept above each monitor
  const layer = document.createElement("div"); layer.className = "gt3d-markers"; container.appendChild(layer);
  const marks = new Map();
  for (const s of stations) { const el = makeMarker(s); layer.appendChild(el); marks.set(s.id, el); }

  const size = () => { const w = container.clientWidth, h = container.clientHeight; renderer.setSize(w, h, false); camera.aspect = w / h; camera.updateProjectionMatrix(); dirty = true; };
  new ResizeObserver(size).observe(container); size();

  // click on the scene: a monitor, or the background
  const ray = new THREE.Raycaster(), ndc = new THREE.Vector2(); let down = null;
  renderer.domElement.addEventListener("pointerdown", (e) => { down = [e.clientX, e.clientY]; controls.autoRotate = false; tween = null; });
  renderer.domElement.addEventListener("pointerup", (e) => {
    if (!down || Math.hypot(e.clientX - down[0], e.clientY - down[1]) > 5) return;
    const r = renderer.domElement.getBoundingClientRect();
    ndc.set(((e.clientX - r.left) / r.width) * 2 - 1, -((e.clientY - r.top) / r.height) * 2 + 1);
    ray.setFromCamera(ndc, camera);
    const hit = ray.intersectObjects(pickables, false)[0];
    if (hit) onPick(ids[hit.instanceId]); else onBackgroundClick();
  });

  // rAF itself stops in a hidden tab; off screen we skip the work, and a still scene with no dust isn't redrawn
  let tween = null, visible = true, immersive = false, first = true, last = 0;
  new IntersectionObserver(([en]) => { visible = en.isIntersecting; last = 0; }).observe(container);
  const v = new THREE.Vector3();
  const loop = (now) => {
    requestAnimationFrame(loop);
    if (!visible && !immersive) return;
    if (last) pace(now - last);
    last = now;
    const moving = !!tween;
    if (tween) {
      const t = Math.min(1, (performance.now() - tween.t0) / tween.ms), e = t < 0.5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2;
      controls.target.lerpVectors(tween.fromT, tween.toT, e); camera.position.lerpVectors(tween.fromC, tween.toC, e);
      if (t >= 1) tween = null;
    }
    const changed = controls.update();
    const drifting = !reduced && dust.on;
    if (drifting) { dust.step(); dust.flicker(performance.now()); }
    if (!(moving || changed || drifting || dirty)) { last = 0; return; }
    dirty = false;
    face(camera);
    renderer.render(scene, camera);
    const w = container.clientWidth, h = container.clientHeight;
    for (const [id, el] of marks) {
      v.copy(tops.get(id)).project(camera);
      const behind = v.z > 1, x = (v.x * 0.5 + 0.5) * w, y = (-v.y * 0.5 + 0.5) * h;
      el.style.transform = `translate(${x}px, ${y}px) translate(-50%, -50%)`;
      el.style.opacity = behind ? 0 : String(Math.max(0.25, Math.min(1, 1.6 - camera.position.distanceTo(tops.get(id)) / 700)));
      el.style.pointerEvents = behind ? "none" : "auto";
    }
    if (first) { first = false; window.dispatchEvent(new CustomEvent("gt3d:ready")); }
  };
  // compiling every shader at the first draw held the page for about 2 s; compile them in the background first
  await renderer.compileAsync(scene, camera).catch(() => {});
  loop();

  return {
    focus(id, close = true) {
      const p = tops.get(id); if (!p) return;
      const toT = new THREE.Vector3(p.x, 0, p.z);
      const dir = camera.position.clone().sub(controls.target).normalize();
      const dist = close ? (immersive ? 120 : 190) : camera.position.distanceTo(controls.target);
      const toC = toT.clone().add(dir.multiplyScalar(dist)); toC.y = Math.max(toC.y, immersive ? 60 : 90);
      tween = { t0: performance.now(), ms: reduced ? 1 : 1500, fromT: controls.target.clone(), toT, fromC: camera.position.clone(), toC };
      controls.autoRotate = false;
    },
    setImmersive(on) {
      immersive = on; controls.enableZoom = on; controls.autoRotate = on && !reduced;
      if (on) {
        const toT = controls.target.clone(), toC = toT.clone().add(new THREE.Vector3(-95, 75, 150));
        tween = { t0: performance.now(), ms: reduced ? 1 : 2200, fromT: controls.target.clone(), toT, fromC: camera.position.clone(), toC };
      } else {
        tween = { t0: performance.now(), ms: reduced ? 1 : 1200, fromT: controls.target.clone(), toT: new THREE.Vector3(10, 0, 10), fromC: camera.position.clone(), toC: new THREE.Vector3(-120, 150, 235) };
      }
    },
    select(id) { for (const [k, el] of marks) el.classList.toggle("sel", k === id); },
    setWind(fromDeg, kmh) { dust.setWind(fromDeg, kmh); dirty = true; },
    setFires(doc) { dust.setFires(doc); dirty = true; },
  };
}

window.GT3D = { init };
window.dispatchEvent(new CustomEvent("gt3d:loaded"));
