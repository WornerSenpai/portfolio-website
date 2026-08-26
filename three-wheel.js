/**
 * Three.js 3D Cylindrical Image Wheel
 * High-performance interactive 3D portfolio wheel for dragxsy
 */

class ThreeImageWheel {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.error(`Container #${containerId} not found`);
      return;
    }

    this.options = Object.assign({
      cardWidth: 260,
      cardHeight: 350,
      radius: 650,
      cameraDistance: 1380,
      cameraHeight: 280,
      fov: 48,
      parallaxX: 60,
      parallaxY: 80,
      sensitivity: 0.0025,
      friction: 0.94,
      liftAmount: 50,
      introSpins: 2.5,
      items: []
    }, options);

    let rawItems = this.options.items || [];
    if (rawItems.length === 0) {
      // Default archive fallback items
      rawItems = [
        { id: "1", title: "Visual Direction Vol 1", category: "Cover Arts", image: "assets/project_wematch.jpg", year: "2026" },
        { id: "2", title: "Poster Typography 02", category: "Posters", image: "assets/project_jab.jpg", year: "2026" },
        { id: "3", title: "Motion Visual Sequence", category: "Music Videos", image: "assets/project_galland.jpg", year: "2026" },
        { id: "4", title: "Apparel Editorial Zine", category: "Promotional", image: "assets/project_bequant.jpg", year: "2026" },
        { id: "5", title: "Tactile Sound Cover", category: "Cover Arts", image: "assets/project_trois_rois.jpg", year: "2026" },
        { id: "6", title: "Graphic Screenprint", category: "Apparel", image: "assets/project_free_handise.jpg", year: "2026" }
      ];
    }

    // Ensure cylinder has enough cards (at least 12 cards) for a full 360-degree wheel
    this.items = [];
    while (this.items.length < 12) {
      this.items = this.items.concat(rawItems);
    }
    if (this.items.length > 20) {
      this.items = this.items.slice(0, 20);
    }

    this.meshes = [];
    this.targetRot = 0;
    this.currentRot = 0;
    this.velocity = 0.0015; // subtle idle rotation
    this.isDragging = false;
    this.lastX = 0;
    this.pointer = { x: 0, y: 0 };
    this.hoveredIndex = -1;
    this.introOffset = Math.PI * 2 * this.options.introSpins;
    this.introDuration = 2.0;
    this.introStartTime = performance.now();
    this.isIntroAnimating = true;

    this.init();
  }

  init() {
    const width = this.container.clientWidth || window.innerWidth;
    const height = this.container.clientHeight || window.innerHeight;

    // 1. Scene
    this.scene = new THREE.Scene();

    // 2. Camera
    this.camera = new THREE.PerspectiveCamera(this.options.fov, width / height, 10, 8000);
    this.camera.position.set(0, this.options.cameraHeight, this.options.cameraDistance);
    this.camera.lookAt(0, 0, 0);

    // 3. WebGL Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(width, height);
    if (THREE.SRGBColorSpace) {
      this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    }
    this.container.innerHTML = '';
    this.container.appendChild(this.renderer.domElement);

    // 4. Wheel Group
    this.wheelGroup = new THREE.Group();
    this.scene.add(this.wheelGroup);

    // 5. Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 1.6);
    this.scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0x00e5ff, 0.8);
    dirLight.position.set(0, 800, 1000);
    this.scene.add(dirLight);

    const dirLight2 = new THREE.DirectionalLight(0xffffff, 0.9);
    dirLight2.position.set(0, -500, 800);
    this.scene.add(dirLight2);

    // 6. Raycasting
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2(-999, -999);

    // 7. Build Cards
    this.createCards();

    // 8. Bind Events
    this.bindEvents();

    // 9. Animation Loop
    this.animate = this.animate.bind(this);
    requestAnimationFrame(this.animate);
  }

  createRoundedCardGeometry(w, h, r = 16) {
    const shape = new THREE.Shape();
    const x = -w / 2;
    const y = -h / 2;
    shape.moveTo(x + r, y);
    shape.lineTo(x + w - r, y);
    shape.quadraticCurveTo(x + w, y, x + w, y + r);
    shape.lineTo(x + w, y + h - r);
    shape.quadraticCurveTo(x + w, y + h, x + w - r, y + h);
    shape.lineTo(x + r, y + h);
    shape.quadraticCurveTo(x, y + h, x, y + h - r);
    shape.lineTo(x, y + r);
    shape.quadraticCurveTo(x, y, x + r, y);

    const geometry = new THREE.ShapeGeometry(shape, 20);
    const pos = geometry.attributes.position;
    const uvs = [];
    for (let i = 0; i < pos.count; i++) {
      const px = pos.getX(i);
      const py = pos.getY(i);
      uvs.push((px - x) / w, (py - y) / h);
    }
    geometry.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
    return geometry;
  }

  createFallbackCanvas(item, index) {
    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 700;
    const ctx = canvas.getContext('2d');

    // Background gradient
    const grad = ctx.createLinearGradient(0, 0, 512, 700);
    grad.addColorStop(0, '#161b24');
    grad.addColorStop(1, '#090b0e');
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 512, 700);

    // Border
    ctx.strokeStyle = 'rgba(0, 229, 255, 0.35)';
    ctx.lineWidth = 6;
    ctx.strokeRect(10, 10, 492, 680);

    // Tag
    ctx.fillStyle = '#00e5ff';
    ctx.font = 'bold 26px monospace';
    ctx.fillText(`0${(index % 9) + 1} // ${item.category || 'ARTWORK'}`, 35, 60);

    // Title
    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 38px sans-serif';
    const words = (item.title || 'Portfolio Piece').split(' ');
    let line = '';
    let y = 140;
    for (let w of words) {
      if (ctx.measureText(line + w).width > 440) {
        ctx.fillText(line, 35, y);
        line = w + ' ';
        y += 48;
      } else {
        line += w + ' ';
      }
    }
    ctx.fillText(line, 35, y);

    // Subtitle
    ctx.fillStyle = '#94a3b8';
    ctx.font = '22px monospace';
    ctx.fillText(`${item.year || '2026'} • dragxsy studio`, 35, y + 45);

    const texture = new THREE.CanvasTexture(canvas);
    if (THREE.SRGBColorSpace) texture.colorSpace = THREE.SRGBColorSpace;
    return texture;
  }

  createCards() {
    const total = this.items.length;
    const geometry = this.createRoundedCardGeometry(this.options.cardWidth, this.options.cardHeight, 16);
    const textureLoader = new THREE.TextureLoader();

    for (let i = 0; i < total; i++) {
      const item = this.items[i];
      const fallbackTexture = this.createFallbackCanvas(item, i);

      const material = new THREE.MeshStandardMaterial({
        map: fallbackTexture,
        side: THREE.DoubleSide,
        roughness: 0.2,
        metalness: 0.1
      });

      // If item has image, load and replace fallback texture
      if (item.image) {
        let imageSrc = item.image;
        if (!imageSrc.startsWith('http') && !imageSrc.startsWith('data:') && !imageSrc.startsWith('/')) {
          imageSrc = imageSrc;
        }

        textureLoader.load(
          imageSrc,
          (loadedTex) => {
            if (THREE.SRGBColorSpace) loadedTex.colorSpace = THREE.SRGBColorSpace;
            loadedTex.minFilter = THREE.LinearFilter;
            material.map = loadedTex;
            material.needsUpdate = true;
          },
          undefined,
          () => {
            // keep fallback texture if image fails
          }
        );
      }

      const mesh = new THREE.Mesh(geometry, material);
      const angle = (i / total) * Math.PI * 2;

      mesh.userData = {
        index: i,
        item: item,
        angle: angle,
        lift: 0,
        targetLift: 0
      };

      this.wheelGroup.add(mesh);
      this.meshes.push(mesh);
    }
  }

  bindEvents() {
    const el = this.container;

    const onDown = (e) => {
      this.isDragging = true;
      this.lastX = e.clientX ?? (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
      this.velocity = 0;
    };

    const onMove = (e) => {
      const clientX = e.clientX ?? (e.touches && e.touches[0] ? e.touches[0].clientX : 0);
      const clientY = e.clientY ?? (e.touches && e.touches[0] ? e.touches[0].clientY : 0);

      const rect = el.getBoundingClientRect();

      if (clientX >= rect.left && clientX <= rect.right && clientY >= rect.top && clientY <= rect.bottom) {
        this.pointer.x = ((clientX - rect.left) / rect.width) * 2 - 1;
        this.pointer.y = -(((clientY - rect.top) / rect.height) * 2 - 1);
        this.mouse.x = this.pointer.x;
        this.mouse.y = this.pointer.y;
      } else {
        this.mouse.x = -999;
        this.mouse.y = -999;
      }

      if (this.isDragging) {
        const deltaX = clientX - this.lastX;
        this.lastX = clientX;
        const rotDelta = (deltaX / Math.max(rect.width, 1)) * (Math.PI * 1.6);
        this.targetRot += rotDelta;
        this.velocity = rotDelta;
      }
    };

    const onUp = () => {
      this.isDragging = false;
    };

    const onClick = () => {
      if (Math.abs(this.velocity) > 0.008) return;
      if (this.hoveredIndex !== -1 && this.options.onCardClick) {
        this.options.onCardClick(this.items[this.hoveredIndex]);
      }
    };

    el.addEventListener('mousedown', onDown);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);

    el.addEventListener('touchstart', onDown, { passive: true });
    window.addEventListener('touchmove', onMove, { passive: true });
    window.addEventListener('touchend', onUp);

    el.addEventListener('click', onClick);

    const updateResponsiveCamera = () => {
      const w = el.clientWidth || window.innerWidth;
      const h = el.clientHeight || window.innerHeight;

      if (w < 768) {
        const aspectFactor = Math.max(h / w, 1.4);
        this.camera.position.z = this.options.cameraDistance * (aspectFactor * 0.75);
        this.camera.position.y = this.options.cameraHeight * 0.75;
      } else if (w < 1024) {
        this.camera.position.z = this.options.cameraDistance * 1.05;
        this.camera.position.y = this.options.cameraHeight * 0.9;
      } else {
        this.camera.position.z = this.options.cameraDistance;
        this.camera.position.y = this.options.cameraHeight;
      }

      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(w, h);
    };

    updateResponsiveCamera();
    window.addEventListener('resize', updateResponsiveCamera);
  }

  animate() {
    requestAnimationFrame(this.animate);

    const now = performance.now();

    // Intro spinning animation
    if (this.isIntroAnimating) {
      const elapsed = (now - this.introStartTime) / 1000;
      const t = Math.min(elapsed / this.introDuration, 1);
      const ease = 1 - Math.pow(1 - t, 3);
      this.introOffset = (Math.PI * 2 * this.options.introSpins) * (1 - ease);
      if (t >= 1) {
        this.isIntroAnimating = false;
        this.introOffset = 0;
      }
    }

    // Inertia & subtle idle spin
    if (!this.isDragging) {
      this.targetRot += this.velocity;
      this.velocity *= this.options.friction;
      if (Math.abs(this.velocity) < 0.0002) {
        this.velocity = 0.0008; // smooth idle drift
      }
    }
    this.currentRot += (this.targetRot - this.currentRot) * 0.08;

    const effectiveRot = this.currentRot + this.introOffset;

    // Raycasting for card hover
    this.raycaster.setFromCamera(this.mouse, this.camera);
    const intersects = this.raycaster.intersectObjects(this.meshes);

    let newHoveredIndex = -1;
    if (intersects.length > 0) {
      const hit = intersects[0].object;
      newHoveredIndex = hit.userData.index;
    }

    if (newHoveredIndex !== this.hoveredIndex) {
      this.hoveredIndex = newHoveredIndex;
      if (this.options.onCardHover) {
        this.options.onCardHover(this.hoveredIndex !== -1 ? this.items[this.hoveredIndex] : null);
      }
    }

    // Camera parallax
    const targetCamX = -this.pointer.x * this.options.parallaxX;
    const targetCamY = this.options.cameraHeight + this.pointer.y * this.options.parallaxY;
    this.camera.position.x += (targetCamX - this.camera.position.x) * 0.05;
    this.camera.position.y += (targetCamY - this.camera.position.y) * 0.05;
    this.camera.lookAt(0, 0, 0);

    // Position cards around cylinder
    const radius = this.options.radius;
    const total = this.meshes.length;

    for (let i = 0; i < total; i++) {
      const mesh = this.meshes[i];
      const baseAngle = mesh.userData.angle;
      const angle = baseAngle + effectiveRot;

      const sinA = Math.sin(angle);
      const cosA = Math.cos(angle);

      const isHovered = (i === this.hoveredIndex);
      mesh.userData.targetLift = isHovered ? this.options.liftAmount : 0;
      mesh.userData.lift += (mesh.userData.targetLift - mesh.userData.lift) * 0.15;

      mesh.position.x = sinA * radius;
      mesh.position.z = cosA * radius;
      mesh.position.y = mesh.userData.lift;

      mesh.rotation.y = angle + Math.PI / 2;
      mesh.rotation.x = isHovered ? -0.1 : 0;
    }

    this.renderer.render(this.scene, this.camera);
  }
}

window.ThreeImageWheel = ThreeImageWheel;
