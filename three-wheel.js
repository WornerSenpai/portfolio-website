/**
 * Three.js 3D Cylindrical Image Wheel
 * Inspired by sebneil.com's interactive 3D portfolio wheel
 */

class ThreeImageWheel {
  constructor(containerId, options = {}) {
    this.container = document.getElementById(containerId);
    if (!this.container) {
      console.error(`Container #${containerId} not found`);
      return;
    }

    this.options = Object.assign({
      cardWidth: 280,
      cardHeight: 380,
      radius: 780,
      cameraDistance: 1750,
      cameraHeight: 460,
      fov: 46,
      parallaxX: 80,
      parallaxY: 120,
      sensitivity: 0.0022,
      friction: 0.94,
      liftAmount: 70,
      introSpins: 3.5,
      items: []
    }, options);

    this.items = this.options.items;
    this.meshes = [];
    this.targetRot = 0;
    this.currentRot = 0;
    this.velocity = 0;
    this.isDragging = false;
    this.lastX = 0;
    this.pointer = { x: 0, y: 0 };
    this.hoveredIndex = -1;
    this.introOffset = Math.PI * 2 * this.options.introSpins;
    this.introDuration = 2.5;
    this.introStartTime = performance.now();
    this.isIntroAnimating = true;

    this.init();
  }

  init() {
    const width = this.container.clientWidth || window.innerWidth;
    const height = this.container.clientHeight || window.innerHeight;

    // Scene
    this.scene = new THREE.Scene();

    // Camera
    this.camera = new THREE.PerspectiveCamera(this.options.fov, width / height, 10, 8000);
    this.camera.position.set(0, this.options.cameraHeight, this.options.cameraDistance);
    this.camera.lookAt(0, 0, 0);

    // Renderer
    this.renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true, powerPreference: "high-performance" });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    this.renderer.setSize(width, height);
    if (THREE.SRGBColorSpace) {
      this.renderer.outputColorSpace = THREE.SRGBColorSpace;
    }
    this.container.appendChild(this.renderer.domElement);

    // Group for all cards
    this.wheelGroup = new THREE.Group();
    this.scene.add(this.wheelGroup);

    // Lighting
    const ambientLight = new THREE.AmbientLight(0xffffff, 1.4);
    this.scene.add(ambientLight);

    const dirLight = new THREE.DirectionalLight(0xffffff, 0.9);
    dirLight.position.set(0, 1000, 1000);
    this.scene.add(dirLight);

    // Raycaster for hover & clicks
    this.raycaster = new THREE.Raycaster();
    this.mouse = new THREE.Vector2(-999, -999);

    // Create cards
    this.createCards();

    // Bind events
    this.bindEvents();

    // Start animation loop
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

    const geometry = new THREE.ShapeGeometry(shape, 24);
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

  createCardTexture(item, index) {
    if (item.image) {
      const loader = new THREE.TextureLoader();
      const texture = loader.load(
        item.image,
        () => {
          if (this.renderer) this.renderer.render(this.scene, this.camera);
        },
        undefined,
        (err) => {
          console.warn(`Failed to load texture ${item.image}`, err);
        }
      );
      if (THREE.SRGBColorSpace) texture.colorSpace = THREE.SRGBColorSpace;
      texture.minFilter = THREE.LinearFilter;
      return texture;
    }

    const canvas = document.createElement('canvas');
    canvas.width = 512;
    canvas.height = 700;
    const ctx = canvas.getContext('2d');

    const grad = ctx.createLinearGradient(0, 0, 512, 700);
    const colors = [
      ['#1a1c23', '#0e1014'],
      ['#232128', '#121016'],
      ['#1b2420', '#0a140f'],
      ['#24201b', '#140f0a']
    ];
    const c = colors[index % colors.length];
    grad.addColorStop(0, c[0]);
    grad.addColorStop(1, c[1]);
    ctx.fillStyle = grad;
    ctx.fillRect(0, 0, 512, 700);

    ctx.strokeStyle = 'rgba(255, 255, 255, 0.15)';
    ctx.lineWidth = 4;
    ctx.strokeRect(12, 12, 488, 676);

    ctx.fillStyle = '#00e5ff';
    ctx.font = 'bold 24px monospace';
    ctx.fillText(`0${index + 1} // ARCHIVE`, 35, 60);

    ctx.fillStyle = '#ffffff';
    ctx.font = 'bold 40px sans-serif';
    const words = (item.title || `PROJECT ${index + 1}`).split(' ');
    let line = '';
    let y = 160;
    for (let w of words) {
      if (ctx.measureText(line + w).width > 420) {
        ctx.fillText(line, 35, y);
        line = w + ' ';
        y += 50;
      } else {
        line += w + ' ';
      }
    }
    ctx.fillText(line, 35, y);

    ctx.fillStyle = '#9ca3af';
    ctx.font = '22px sans-serif';
    ctx.fillText(item.category || 'Visual Direction', 35, y + 45);

    const texture = new THREE.CanvasTexture(canvas);
    if (THREE.SRGBColorSpace) texture.colorSpace = THREE.SRGBColorSpace;
    return texture;
  }

  createCards() {
    const total = this.items.length;
    const geometry = this.createRoundedCardGeometry(this.options.cardWidth, this.options.cardHeight, 16);

    for (let i = 0; i < total; i++) {
      const item = this.items[i];
      const texture = this.createCardTexture(item, i);

      const material = new THREE.MeshStandardMaterial({
        map: texture,
        side: THREE.DoubleSide,
        roughness: 0.25,
        metalness: 0.1
      });

      const mesh = new THREE.Mesh(geometry, material);
      const angle = (i / total) * Math.PI * 2;
      
      mesh.userData = {
        index: i,
        item: item,
        angle: angle,
        sinA: Math.sin(angle),
        cosA: Math.cos(angle),
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

      // Check if inside canvas bounds for hover detection
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
        const rotDelta = (deltaX / Math.max(rect.width, 1)) * (Math.PI * 1.8);
        this.targetRot += rotDelta;
        this.velocity = rotDelta;
      }
    };

    const onUp = () => {
      this.isDragging = false;
    };

    // Wheel Event: On landing page, scroll rotates 3D cylinder without scrolling page
    const onWindowWheel = (e) => {
      const scrollY = window.scrollY || document.documentElement.scrollTop;
      // If user is at or near the top landing hero section
      if (scrollY <= 50) {
        e.preventDefault(); // Prevent page from scrolling down
        const delta = Math.abs(e.deltaX) > Math.abs(e.deltaY) ? e.deltaX : e.deltaY;
        const rotationAmount = delta * this.options.sensitivity;
        this.targetRot -= rotationAmount;
        this.velocity = -rotationAmount * 0.4;
      }
    };

    const onClick = (e) => {
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

    // Bind non-passive wheel event on window to capture scroll on landing page
    window.addEventListener('wheel', onWindowWheel, { passive: false });
    el.addEventListener('click', onClick);

    window.addEventListener('resize', () => {
      const w = el.clientWidth || window.innerWidth;
      const h = el.clientHeight || window.innerHeight;
      this.camera.aspect = w / h;
      this.camera.updateProjectionMatrix();
      this.renderer.setSize(w, h);
    });
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

    // Inertia & lerping
    if (!this.isDragging) {
      this.targetRot += this.velocity;
      this.velocity *= this.options.friction;
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

    // Update camera parallax
    const targetCamX = -this.pointer.x * this.options.parallaxX;
    const targetCamY = this.options.cameraHeight + this.pointer.y * this.options.parallaxY;
    this.camera.position.x += (targetCamX - this.camera.position.x) * 0.05;
    this.camera.position.y += (targetCamY - this.camera.position.y) * 0.05;
    this.camera.lookAt(0, 0, 0);

    // Update cards positions along cylindrical perimeter
    const radius = this.options.radius;
    const total = this.meshes.length;

    for (let i = 0; i < total; i++) {
      const mesh = this.meshes[i];
      const baseAngle = mesh.userData.angle;
      const angle = baseAngle + effectiveRot;

      const sinA = Math.sin(angle);
      const cosA = Math.cos(angle);

      // Lift animation on hover
      const isHovered = (i === this.hoveredIndex);
      mesh.userData.targetLift = isHovered ? this.options.liftAmount : 0;
      mesh.userData.lift += (mesh.userData.targetLift - mesh.userData.lift) * 0.15;

      // Position in 3D circle
      mesh.position.x = sinA * radius;
      mesh.position.z = cosA * radius;
      mesh.position.y = mesh.userData.lift;

      // Tangent rotation to face outward
      mesh.rotation.y = angle + Math.PI / 2;
      mesh.rotation.x = isHovered ? -0.1 : 0;
    }

    this.renderer.render(this.scene, this.camera);
  }
}

window.ThreeImageWheel = ThreeImageWheel;
