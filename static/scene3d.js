// 3D station map: each bar is a weather station placed by latitude/longitude.
// Bar height = peak recorded max temperature, colour = risk level.
// Stations come from the database: index.html sets window.STATIONS = [[name, lat, lon, peak], ...]
var STATIONS = window.STATIONS || [];

(function () {
  var host = document.getElementById('scene3d');
  if (!host) return;
  var card = host.parentElement;
  var tip = card.querySelector('.scene-tip');

  function fallback(msg) {
    var fb = card.querySelector('.scene-fallback');
    if (fb) { fb.style.display = 'grid'; if (msg) fb.textContent = msg; }
  }
  if (typeof THREE === 'undefined') { fallback('3D view needs an internet connection to load three.js.'); return; }
  var renderer;
  try { renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true }); }
  catch (e) { fallback('Your browser does not support WebGL, so the 3D view is unavailable.'); return; }

  var COLORS = { normal: 0x2dd4bf, moderate: 0xfbbf24, high: 0xfb7a2f, extreme: 0xf43f5e };
  function risk(t) { return t >= 44 ? 'extreme' : t >= 41 ? 'high' : t >= 38 ? 'moderate' : 'normal'; }

  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  host.appendChild(renderer.domElement);

  var scene = new THREE.Scene();
  var camera = new THREE.PerspectiveCamera(38, 1, 0.1, 200);

  scene.add(new THREE.HemisphereLight(0xcfd8ff, 0x1a1020, 0.75));
  var sun = new THREE.DirectionalLight(0xffffff, 0.75);
  sun.position.set(-14, 26, 12);
  sun.castShadow = true;
  sun.shadow.mapSize.set(1024, 1024);
  var sc = sun.shadow.camera; sc.left = -20; sc.right = 20; sc.top = 20; sc.bottom = -20;
  scene.add(sun);

  var world = new THREE.Group();
  scene.add(world);

  // Base slab (a thick rounded-looking plinth)
  var LAT0 = 8, LAT1 = 34, LON0 = 68, LON1 = 97;
  var W = 26, D = 24;
  var slab = new THREE.Mesh(
    new THREE.BoxGeometry(W + 2, 0.8, D + 2),
    new THREE.MeshStandardMaterial({ color: 0x141c2c, roughness: 0.9 })
  );
  slab.position.y = -0.4;
  slab.receiveShadow = true;
  world.add(slab);

  var grid = new THREE.GridHelper(W + 2, 14, 0x34425f, 0x222c42);
  grid.position.y = 0.01;
  world.add(grid);

  function toX(lon) { return ((lon - LON0) / (LON1 - LON0) - 0.5) * W; }
  function toZ(lat) { return -((lat - LAT0) / (LAT1 - LAT0) - 0.5) * D; }

  var bars = [];
  var geo = new THREE.BoxGeometry(0.45, 1, 0.45);
  geo.translate(0, 0.5, 0);
  STATIONS.forEach(function (s, i) {
    var t = s[3], k = risk(t);
    var mat = new THREE.MeshStandardMaterial({ color: COLORS[k], roughness: 0.45, metalness: 0.1, emissive: COLORS[k], emissiveIntensity: 0.18 });
    var m = new THREE.Mesh(geo, mat);
    m.position.set(toX(s[2]), 0, toZ(s[1]));
    m.castShadow = true;
    m.userData = { name: s[0], temp: t, risk: k, h: Math.max(0.3, (t - 18) * 0.22), delay: i * 4 };
    m.scale.y = 0.001;
    world.add(m);
    bars.push(m);
  });

  // Camera orbit (drag to rotate, gentle auto-rotate)
  var yaw = -0.6, pitch = 0.78, dist = 44, auto = true, dragging = false, lx = 0, ly = 0;
  function placeCamera() {
    camera.position.set(Math.sin(yaw) * Math.cos(pitch) * dist, Math.sin(pitch) * dist, Math.cos(yaw) * Math.cos(pitch) * dist);
    camera.lookAt(0, 3, 0);
  }
  host.addEventListener('pointerdown', function (e) { dragging = true; auto = false; lx = e.clientX; ly = e.clientY; host.setPointerCapture(e.pointerId); });
  host.addEventListener('pointerup', function () { dragging = false; });
  host.addEventListener('pointermove', function (e) {
    if (dragging) {
      yaw -= (e.clientX - lx) * 0.006;
      pitch = Math.min(1.35, Math.max(0.25, pitch + (e.clientY - ly) * 0.004));
      lx = e.clientX; ly = e.clientY;
    }
    hover(e);
  });
  host.addEventListener('pointerleave', function () { if (tip) tip.style.opacity = 0; });

  // Hover tooltip
  var ray = new THREE.Raycaster(), mouse = new THREE.Vector2(), hovered = null;
  function hover(e) {
    var r = host.getBoundingClientRect();
    mouse.x = ((e.clientX - r.left) / r.width) * 2 - 1;
    mouse.y = -((e.clientY - r.top) / r.height) * 2 + 1;
    ray.setFromCamera(mouse, camera);
    var hit = ray.intersectObjects(bars)[0];
    if (hovered && (!hit || hit.object !== hovered)) { hovered.material.emissiveIntensity = 0.18; hovered = null; }
    if (hit) {
      hovered = hit.object;
      hovered.material.emissiveIntensity = 0.7;
      if (tip) {
        tip.textContent = hovered.userData.name + ' · ' + hovered.userData.temp.toFixed(1) + '°C';
        tip.style.left = (e.clientX - r.left) + 'px';
        tip.style.top = (e.clientY - r.top) + 'px';
        tip.style.opacity = 1;
      }
    } else if (tip) { tip.style.opacity = 0; }
  }

  function resize() {
    var w = host.clientWidth, h = host.clientHeight;
    renderer.setSize(w, h, false);
    camera.aspect = w / h;
    camera.updateProjectionMatrix();
  }
  window.addEventListener('resize', resize);
  resize();

  var start = performance.now();
  function frame(now) {
    var el = now - start;
    bars.forEach(function (b) {
      var p = Math.min(1, Math.max(0, (el - b.userData.delay) / 900));
      var ease = 1 - Math.pow(1 - p, 3);
      b.scale.y = Math.max(0.001, b.userData.h * ease);
    });
    if (auto) yaw += 0.0018;
    placeCamera();
    renderer.render(scene, camera);
    requestAnimationFrame(frame);
  }
  requestAnimationFrame(frame);
})();
