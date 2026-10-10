/* The October 2025 story, as an illustration: a water tanker sprays the air at a monitor's inlet, the dust
   settles right there and the reading drops, while the monitors a few hundred metres away still read the
   real air. Then the neighbours check notices. Same fog, dust and masts as scene3d.js; all numbers are
   illustrative. Plays only while on screen. With reduced motion, or on a machine drawing WebGL without a GPU,
   it opens on the end state and waits for Play. */
import * as THREE from "./vendor/three/three.module.min.js";

const FOG = 0xe8e7e4, DUST = new THREE.Color(0x6e6457), FOGC = new THREE.Color(FOG);
const OK = 0x0ca30c, FLAG = 0xd03b3b;
const LOOP = 18;
const T = window.GT_I18N ? window.GT_I18N.t : (s) => s; // Hindi when it is on (i18n.js)
const STEPS = [
  [0, "Before", "The monitor and the monitors around it agree: about 310 µg/m³ PM2.5."],
  [3.5, "The tanker", "A water tanker pulls up next to the monitor."],
  [6.5, "The spray", "The spray settles the dust right at the monitor's inlet. Its reading falls to about 120."],
  [11.5, "The air", "A few hundred metres away, nothing changed. The monitors there still read about 300."],
  [14, "Ground Truth", "Ground Truth compares it with its neighbours. The numbers don't add up."],
];
const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
const clamp = (x, a = 0, b = 1) => Math.min(b, Math.max(a, x));
const ease = (x) => { x = clamp(x); return x * x * (3 - 2 * x); };
const span = (t, a, b) => ease((t - a) / (b - a));

function radial(inner, outer) {
  const c = document.createElement("canvas"); c.width = c.height = 64;
  const ctx = c.getContext("2d"), g = ctx.createRadialGradient(32, 32, 0, 32, 32, 32);
  g.addColorStop(0, inner); g.addColorStop(1, outer); ctx.fillStyle = g; ctx.fillRect(0, 0, 64, 64);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

function mast(scene, x, z, glowTex) {
  const steel = new THREE.MeshStandardMaterial({ color: 0x2f3033, roughness: 0.6, metalness: 0.3 });
  const box = new THREE.MeshStandardMaterial({ color: 0x3e3f43, roughness: 0.7 });
  const g = new THREE.Group(); g.position.set(x, 0, z);
  const pole = new THREE.Mesh(new THREE.CylinderGeometry(0.09, 0.12, 5.6, 8), steel); pole.position.y = 2.8; g.add(pole);
  const sb = new THREE.Mesh(new THREE.BoxGeometry(1.1, 0.8, 0.7), box); sb.position.y = 5.2; g.add(sb);
  const inlet = new THREE.Mesh(new THREE.CylinderGeometry(0.12, 0.12, 0.7, 8), steel); inlet.position.set(0.25, 5.95, 0); g.add(inlet);
  const cap = new THREE.Mesh(new THREE.CylinderGeometry(0.28, 0.2, 0.18, 12), steel); cap.position.set(0.25, 6.35, 0); g.add(cap);
  const ledMat = new THREE.MeshBasicMaterial({ color: OK });
  const led = new THREE.Mesh(new THREE.SphereGeometry(0.16, 12, 8), ledMat); led.position.set(-0.3, 5.9, 0); g.add(led);
  const glow = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex, color: OK, transparent: true, opacity: 0.55, depthWrite: false }));
  glow.scale.set(1.4, 1.4, 1); glow.position.copy(led.position); g.add(glow);
  scene.add(g);
  return { ledMat, glow, top: new THREE.Vector3(x, 7.4, z), inlet: new THREE.Vector3(x + 0.25, 6.3, z) };
}

function tanker(scene) {
  const g = new THREE.Group();
  const dark = new THREE.MeshStandardMaterial({ color: 0x3a3b3e, roughness: 0.7 });
  const tankM = new THREE.MeshStandardMaterial({ color: 0xd6d7d9, roughness: 0.5, metalness: 0.2 });
  const glass = new THREE.MeshStandardMaterial({ color: 0x9aa0a6, roughness: 0.2, metalness: 0.4 });
  const chassis = new THREE.Mesh(new THREE.BoxGeometry(7.4, 0.4, 2.1), dark); chassis.position.y = 0.8; g.add(chassis);
  const cab = new THREE.Mesh(new THREE.BoxGeometry(1.8, 1.9, 2.1), dark); cab.position.set(2.8, 1.95, 0); g.add(cab);
  const win = new THREE.Mesh(new THREE.BoxGeometry(0.05, 0.75, 1.8), glass); win.position.set(3.72, 2.4, 0); g.add(win);
  const tank = new THREE.Mesh(new THREE.CylinderGeometry(1.0, 1.0, 5.0, 24), tankM); tank.rotation.z = Math.PI / 2; tank.position.set(-0.9, 2.05, 0); g.add(tank);
  for (const x of [-3.15, 1.35]) { const end = new THREE.Mesh(new THREE.CylinderGeometry(1.02, 1.02, 0.08, 24), dark); end.rotation.z = Math.PI / 2; end.position.set(x, 2.05, 0); g.add(end); }
  const wheelG = new THREE.CylinderGeometry(0.45, 0.45, 0.35, 16);
  for (const x of [-2.6, -1.4, 2.6]) for (const z of [-1.05, 1.05]) { const w = new THREE.Mesh(wheelG, dark); w.rotation.x = Math.PI / 2; w.position.set(x, 0.45, z); g.add(w); }
  // the spray nozzle on the rear of the tank, aimed at the pavement side
  const nozzle = new THREE.Mesh(new THREE.CylinderGeometry(0.07, 0.1, 0.9, 8), dark); nozzle.position.set(-2.6, 3.25, -0.5); nozzle.rotation.x = -0.9; g.add(nozzle);
  g.position.set(-60, 0, 5.2);
  scene.add(g);
  return { g, nozzleLocal: new THREE.Vector3(-2.6, 3.55, -0.85) };
}

function street(scene) {
  const ground = new THREE.Mesh(new THREE.PlaneGeometry(400, 400), new THREE.MeshLambertMaterial({ color: 0xe2e1de }));
  ground.rotation.x = -Math.PI / 2; scene.add(ground);
  const road = new THREE.Mesh(new THREE.PlaneGeometry(400, 7.5), new THREE.MeshLambertMaterial({ color: 0xcfcfcc }));
  road.rotation.x = -Math.PI / 2; road.position.set(0, 0.01, 5.2); scene.add(road);
  const kerb = new THREE.Mesh(new THREE.BoxGeometry(400, 0.18, 0.3), new THREE.MeshLambertMaterial({ color: 0xf1f1ee }));
  kerb.position.set(0, 0.09, 1.4); scene.add(kerb);
  const dashM = new THREE.MeshBasicMaterial({ color: 0xf4f4f2 });
  for (let x = -120; x < 120; x += 6) { const d = new THREE.Mesh(new THREE.PlaneGeometry(2.6, 0.18), dashM); d.rotation.x = -Math.PI / 2; d.position.set(x, 0.02, 5.2); scene.add(d); }
  // low city blocks and trees behind the pavement, fading into fog
  const mats = [0xf4f4f2, 0xf1f1ee, 0xeeeeeb].map((c) => new THREE.MeshLambertMaterial({ color: c }));
  const treeM = new THREE.MeshLambertMaterial({ color: 0xa7b0a3 });
  let seed = 7; const rnd = () => ((seed = (seed * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 70; i++) {
    const x = (rnd() - 0.5) * 140, z = -6 - rnd() * 70;
    if (Math.abs(x - 34) < 6 && Math.abs(z + 24) < 6) continue; // keep the neighbour mast clear
    const w = 3 + rnd() * 6, d = 3 + rnd() * 6, h = 2 + rnd() * 9;
    const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, d), mats[i % 3]); b.position.set(x, h / 2, z); scene.add(b);
  }
  for (let i = 0; i < 40; i++) {
    const x = (rnd() - 0.5) * 120, z = -3 - rnd() * 50;
    const t = new THREE.Mesh(new THREE.ConeGeometry(0.7, 2.6, 7), treeM); t.position.set(x, 1.3, z); scene.add(t);
  }
  for (let x = -40; x <= 40; x += 9) { if (Math.abs(x) < 4) continue; const t = new THREE.Mesh(new THREE.ConeGeometry(0.6, 2.4, 7), treeM); t.position.set(x, 1.2, -1.6); scene.add(t); }
}

function dust(scene) {
  const n = 5200, base = new Float32Array(n * 3), pos = new Float32Array(n * 3), col = new Float32Array(n * 3), spd = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    base[i * 3] = (Math.random() - 0.5) * 100; base[i * 3 + 1] = 0.3 + Math.random() * 15; base[i * 3 + 2] = -50 + Math.random() * 66;
    spd[i] = 0.25 + Math.random() * 0.5;
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(pos, 3)); g.setAttribute("color", new THREE.BufferAttribute(col, 3));
  const pts = new THREE.Points(g, new THREE.PointsMaterial({ size: 0.4, map: radial("rgba(255,255,255,1)", "rgba(255,255,255,0)"), vertexColors: true, transparent: true, opacity: 0.7, depthWrite: false }));
  pts.frustumCulled = false; // positions move every frame; the first bounding sphere would be wrong
  scene.add(pts);
  const c = new THREE.Color();
  // clear: 0..1, how far the spray has settled the dust around the inlet
  return (time, clear, at) => {
    for (let i = 0; i < n; i++) {
      let x = base[i * 3] + time * spd[i]; x = ((x + 50) % 100 + 100) % 100 - 50;
      const y0 = base[i * 3 + 1] + Math.sin(time * 0.4 + i) * 0.25, z = base[i * 3 + 2];
      const d = Math.hypot(x - at.x, (y0 - at.y) * 0.8, z - at.z);
      const k = clear * Math.pow(clamp(1 - d / 8.5), 0.6);
      pos[i * 3] = x; pos[i * 3 + 1] = Math.max(0.15, y0 - k * 3); pos[i * 3 + 2] = z;
      c.copy(DUST).lerp(FOGC, k * 0.97); col[i * 3] = c.r; col[i * 3 + 1] = c.g; col[i * 3 + 2] = c.b;
    }
    g.attributes.position.needsUpdate = true; g.attributes.color.needsUpdate = true;
  };
}

function water(scene) {
  const n = 1400, pos = new Float32Array(n * 3).fill(-100), vel = new Float32Array(n * 3), age = new Float32Array(n).fill(9);
  const g = new THREE.BufferGeometry(); g.setAttribute("position", new THREE.BufferAttribute(pos, 3));
  const pts = new THREE.Points(g, new THREE.PointsMaterial({ size: 0.34, color: 0x7fb0dd, transparent: true, opacity: 0.9, depthWrite: false }));
  pts.frustumCulled = false;
  scene.add(pts);
  let next = 0;
  return (dt, emitting, from, to) => {
    if (emitting) {
      const dir = to.clone().sub(from); const dist = dir.length(); dir.normalize();
      for (let k = 0; k < Math.round(dt * 520); k++) {
        const i = next; next = (next + 1) % n;
        pos[i * 3] = from.x; pos[i * 3 + 1] = from.y; pos[i * 3 + 2] = from.z;
        const s = dist * (1.05 + Math.random() * 0.35);
        vel[i * 3] = dir.x * s + (Math.random() - 0.5) * 1.6; vel[i * 3 + 1] = dir.y * s + 4.2 + (Math.random() - 0.5) * 1.2; vel[i * 3 + 2] = dir.z * s + (Math.random() - 0.5) * 1.6;
        age[i] = 0;
      }
    }
    for (let i = 0; i < n; i++) {
      if (age[i] > 1.6) { pos[i * 3 + 1] = -100; continue; }
      age[i] += dt; vel[i * 3 + 1] -= 9.8 * dt;
      pos[i * 3] += vel[i * 3] * dt; pos[i * 3 + 1] += vel[i * 3 + 1] * dt; pos[i * 3 + 2] += vel[i * 3 + 2] * dt;
      if (pos[i * 3 + 1] < 0.05) age[i] = 9;
    }
    g.attributes.position.needsUpdate = true;
  };
}

function init(stage) {
  const $ = (s) => document.querySelector(s);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  const gl = renderer.getContext(), info = gl.getExtension("WEBGL_debug_renderer_info");
  const soft = /swiftshader|llvmpipe|softpipe|software|basic render/i.test(info ? gl.getParameter(info.UNMASKED_RENDERER_WEBGL) : "");
  renderer.setPixelRatio(Math.min(devicePixelRatio, soft ? 1 : matchMedia("(max-width: 760px)").matches ? 1.5 : 1.75));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.domElement.setAttribute("aria-hidden", "true");
  stage.prepend(renderer.domElement);

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(FOG);
  scene.fog = new THREE.Fog(FOG, 24, 95);
  scene.add(new THREE.HemisphereLight(0xffffff, 0xd8d6d2, 1.6));
  const sun = new THREE.DirectionalLight(0xffffff, 1.2); sun.position.set(-20, 30, 15); scene.add(sun);

  const glowTex = radial("rgba(255,255,255,1)", "rgba(255,255,255,0)");
  street(scene);
  const me = mast(scene, 0, -0.4, glowTex);
  const nb = mast(scene, 34, -24, glowTex);
  const truck = tanker(scene);
  const stepDust = dust(scene);
  const stepWater = water(scene);
  const mist = new THREE.Sprite(new THREE.SpriteMaterial({ map: radial("rgba(255,255,255,0.9)", "rgba(255,255,255,0)"), transparent: true, opacity: 0, depthWrite: false }));
  mist.scale.set(11, 7, 1); mist.position.set(-0.8, 4.2, 1.2); scene.add(mist);
  const smogTex = radial("rgba(118,106,90,0.55)", "rgba(118,106,90,0)");
  const haze = [];
  let hs = 11; const hr = () => ((hs = (hs * 16807) % 2147483647) / 2147483647);
  for (let i = 0; i < 26; i++) {
    const sp = new THREE.Sprite(new THREE.SpriteMaterial({ map: smogTex, transparent: true, depthWrite: false, opacity: 0 }));
    const p = i < 6 ? new THREE.Vector3((hr() - 0.5) * 7, 2 + hr() * 5, (hr() - 0.5) * 5) : new THREE.Vector3((hr() - 0.5) * 80, 2 + hr() * 10, -45 + hr() * 55);
    const size = i < 6 ? 6 + hr() * 4 : 14 + hr() * 16;
    sp.scale.set(size, size * 0.55, 1); sp.position.copy(p); scene.add(sp);
    haze.push({ sp, base: i < 6 ? 0.5 : 0.28 + hr() * 0.2, near: clamp(1 - p.distanceTo(new THREE.Vector3(0, 5, 0)) / 9) });
  }
  const lineG = new THREE.BufferGeometry().setFromPoints([me.top, nb.top]);
  const lineM = new THREE.LineDashedMaterial({ color: 0x4f5156, dashSize: 0.8, gapSize: 0.6, transparent: true, opacity: 0 });
  const line = new THREE.Line(lineG, lineM); line.computeLineDistances(); scene.add(line);

  const camera = new THREE.PerspectiveCamera(36, 1, 0.5, 400);
  const target = new THREE.Vector3(5, 3.4, -6);
  const tagMe = $("#sp-me"), tagNb = $("#sp-nb"), vMe = $("#sp-me-v"), vNb = $("#sp-nb-v"), flagEl = $("#sp-flag");
  const cap = $("#sp-caption"), steps = [...document.querySelectorAll("#sp-steps button")], toggle = $("#spray-toggle");

  function resize() {
    const w = stage.clientWidth, h = stage.clientHeight;
    renderer.setSize(w, h, false); camera.aspect = w / h;
    camera.fov = w < 640 ? 50 : 36; camera.updateProjectionMatrix();
  }
  new ResizeObserver(resize).observe(stage); resize();

  const v = new THREE.Vector3();
  function place(el, p) {
    v.copy(p).project(camera);
    el.style.transform = `translate(${((v.x + 1) / 2) * stage.clientWidth}px, ${((1 - v.y) / 2) * stage.clientHeight}px) translate(-50%, -100%)`;
  }

  // It plays by itself from step 1 each time it scrolls into view. With "reduce motion" on (Windows' "animation
  // effects" off sets it, often without people knowing) it still plays, once, without the camera sway, and rests on
  // the last step. Pause is always there, and a visitor's Pause is kept.
  let t = 0, lastStep = -1, playing = true, held = false, visible = false, last = performance.now();
  const setPlaying = (on) => { playing = on; toggle.textContent = T(on ? "Pause" : "Play"); toggle.setAttribute("aria-pressed", String(!on)); };
  function frame(dt, draw = true) {
    // where the tanker is: drives in, parks next to the monitor, drives off
    const x = t < 3.5 ? -60 : t < 6.5 ? -60 + 63.2 * span(t, 3.5, 6.5) : t < 15.5 ? 3.2 : 3.2 + 60 * span(t, 15.5, 18);
    truck.g.position.x = x;
    const spraying = t > 6.6 && t < 14;
    const clear = t < 16.8 ? span(t, 6.8, 11) : 1 - span(t, 16.8, 18);
    const nozzle = truck.nozzleLocal.clone().add(truck.g.position);
    stepWater(dt, spraying, nozzle, me.inlet.clone().add(new THREE.Vector3(0, -0.8, 0)));
    stepDust(t, clear, me.inlet);
    mist.material.opacity = 0.45 * (spraying ? span(t, 6.6, 8) : clear * 0.6);
    for (const h of haze) h.sp.material.opacity = h.base * (1 - clear * Math.min(1, h.near * 1.6));

    const flagged = t >= 14 && t < 17.6;
    const fl = flagged ? span(t, 14, 14.8) : 0;
    me.ledMat.color.setHex(fl > 0.5 ? FLAG : OK); me.glow.material.color.setHex(fl > 0.5 ? FLAG : OK);
    lineM.opacity = t >= 11.5 && t < 17.6 ? 0.9 * span(t, 11.5, 12.5) : 0;

    // the camera breathes a little, so it reads as a place, not a diagram
    const sway = reduced ? 0 : Math.sin(t * 0.35) * 1.6;
    camera.position.set(-12 + sway, 10.5, 19); camera.lookAt(target);

    const reading = Math.round(310 - 192 * clear + (reduced ? 0 : Math.sin(t * 2.1) * 2));
    vMe.textContent = reading; vNb.textContent = Math.round(302 + (reduced ? 0 : Math.sin(t * 1.3) * 3));
    tagMe.classList.toggle("low", clear > 0.5); flagEl.hidden = !flagged;
    place(tagMe, me.top); place(tagNb, nb.top);

    const step = STEPS.reduce((k, [s], i) => (t >= s ? i : k), 0);
    if (step !== lastStep) {
      lastStep = step; cap.innerHTML = `<b>${step + 1} · ${T(STEPS[step][1])}.</b> ${T(STEPS[step][2])}`;
      steps.forEach((b, i) => { b.setAttribute("aria-current", String(i === step)); b.classList.toggle("done", i < step); });
    }
    stage.classList.toggle("blink", t > 17.6);
    if (draw) renderer.render(scene, camera);
  }

  function loop(now) {
    const dt = Math.min(0.05, (now - last) / 1000); last = now;
    // the full-screen 3D map (html.lock) covers this; no point drawing both
    if (visible && playing && !document.documentElement.classList.contains("lock")) {
      if (reduced && t + dt >= LOOP - 0.5) { seek(15); setPlaying(false); } // once through, then rest on the end
      else { t = (t + dt) % LOOP; frame(dt); }
    }
    requestAnimationFrame(loop);
  }
  // jump to a step: run the simulation forward to it, so the dust and the water are where they'd be
  function seek(to) {
    t = 0; for (let s = 0; s < to; s += 1 / 30) { t = s; frame(1 / 30, false); } // simulate only: drawing 450 frames without a GPU took a minute
    t = to; frame(1 / 30);
  }
  steps.forEach((b, i) => b.addEventListener("click", () => { seek(STEPS[i][0] + (i === 2 ? 4.6 : 0.4)); }));
  toggle.addEventListener("click", () => {
    held = playing; // a visitor's Pause sticks; Play after the end starts the story again
    if (!playing && t >= 14.9) seek(0);
    setPlaying(!playing);
  });
  // coming into view (a third of it on screen) starts the story from the beginning, unless the visitor paused it
  new IntersectionObserver(([en]) => {
    const was = visible;
    visible = en.isIntersecting;
    if (visible && !was && !held) { seek(0); setPlaying(true); }
  }, { threshold: 0.35 }).observe(stage);
  // shaders compile in the background (it held the page at the first draw), then the first frame and the loop
  renderer.compileAsync(scene, camera).catch(() => {}).then(() => {
    if (!playing) { toggle.textContent = T("Play"); toggle.setAttribute("aria-pressed", "true"); seek(15); } else frame(0);
    requestAnimationFrame(loop);
  });
  window.__spray = { seek, get t() { return t; } }; // for the capture scripts
}

const stage = document.getElementById("spray-stage");
if (stage) {
  try {
    if (!document.createElement("canvas").getContext("webgl2")) throw new Error("no WebGL2");
    init(stage);
  } catch (e) {
    stage.classList.add("nogl");
    document.getElementById("sp-caption").innerHTML = STEPS.map(([, k, s], i) => `<b>${i + 1} · ${T(k)}.</b> ${T(s)}`).join("<br>");
  }
}
