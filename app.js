/**
 * dragxsy - Visual Artist & Designer Portfolio
 * Powered by Google Drive Headless CMS
 * Dynamic Content API: /api/portfolio (Fallback: cms/manifest.json)
 */

let CMS_DATA = {
  categories: [],
  projects: [],
  assets: [],
  syncStatus: "loading",
  stats: {}
};

let currentFilter = "All";
let wheelInstance = null;

// Curated Creative Notes & Dispatches
const BLOG_POSTS = [
  {
    id: "post-1",
    tag: "DISPATCH 01",
    title: "Operating Between Deliberate Chaos and Dark Aesthetics",
    date: "Aug 2026",
    readTime: "4 min read",
    summary: "Why deliberate imperfection, halftone artifacts, and raw analog noise resonate stronger than sanitized minimalist vectors in modern visual culture.",
    content: `In an era of hyper-optimized UI kits and sanitized vectors, visual friction has become the ultimate luxury. When every brand looks like a clean white SaaS landing page, raw textures, brutalist grids, and deliberate grain force the human eye to pause and feel.
    
    Creating visuals across music covers and graphic apparel has taught me that true artistic memory isn't engineered through sterile symmetry—it's forged in tension. By combining disciplined typography with chaotic grit, the artwork develops an unmistakable identity that algorithms cannot fabricate.`
  },
  {
    id: "post-2",
    tag: "DISPATCH 02",
    title: "The Art of Album Cover Design in the Streaming Era",
    date: "Jul 2026",
    readTime: "5 min read",
    summary: "How a 3000x3000px digital square must communicate an entire sonic universe at both miniature scale and full print fidelity.",
    content: `A music cover is the front door to a sonic dimension. In streaming feeds where thousands of releases compete for a single thumb swipe, an album artwork must deliver instant emotional intrigue at 40x40 pixels while rewarding deep inspection at full gallery scale.
    
    My process focuses on capturing the sonic frequency of the artist—translating raw distortion, ambient reverb, or sharp electronic percussion into corresponding visual textures and typographic choices.`
  },
  {
    id: "post-3",
    tag: "DISPATCH 03",
    title: "From Digital Concept to Heavyweight Screenprint",
    date: "Jun 2026",
    readTime: "4 min read",
    summary: "Translating digital artwork into physical apparel: ink density, halftone separation, and textile storytelling.",
    content: `Apparel design is kinetic art—your canvas moves, folds, and ages with the wearer. Designing for heavyweight garments demands understanding ink absorption, color halftones, and how a graphic placement interacts with the human silhouette.`
  }
];

// Initialize Application
document.addEventListener('DOMContentLoaded', async () => {
  initThemeToggle();
  initMobileMenu();
  initExploreBioButton();
  initCurrentlyListening();
  initModals();
  initContactCard();
  initAdminDashboard();
  initLucideIcons();

  // Load dynamic CMS data
  await loadCMSData();
});

// Load CMS Data from Content API or Fallback Manifest
async function loadCMSData() {
  try {
    const resp = await fetch('/api/portfolio');
    if (resp.ok) {
      CMS_DATA = await resp.json();
      console.log('[CMS] Loaded portfolio from API:', CMS_DATA);
    } else {
      throw new Error(`API returned ${resp.status}`);
    }
  } catch (err) {
    console.warn('[CMS] API unavailable, attempting local manifest fallback:', err);
    try {
      const fallbackResp = await fetch('cms/manifest.json');
      if (fallbackResp.ok) {
        CMS_DATA = await fallbackResp.json();
        console.log('[CMS] Loaded portfolio from local manifest fallback');
      }
    } catch (e2) {
      console.error('[CMS] Fallback manifest failed:', e2);
    }
  }

  // Render CMS elements dynamically
  renderFilterButtons();
  renderPortfolioGrid(currentFilter);
  init3DWheel();
  updateAdminUI();
  initLucideIcons();
}

// Robust Light / Dark Theme Switcher
// Permanent Dark Theme Initialization
function initThemeToggle() {
  document.documentElement.classList.add('dark');
  document.documentElement.setAttribute('data-theme', 'dark');
  updateFilterButtonsTheme();
}

function updateFilterButtonsTheme() {
  const filterBtns = document.querySelectorAll('.filter-btn');
  filterBtns.forEach(btn => {
    if (btn.classList.contains('active-filter')) {
      btn.style.backgroundColor = '#00e5ff';
      btn.style.color = '#090b0e';
      btn.style.borderColor = '#00e5ff';
    } else {
      btn.style.backgroundColor = 'transparent';
      btn.style.color = 'var(--text-secondary)';
      btn.style.borderColor = 'var(--border-subtle)';
    }
  });
} else {
      btn.style.backgroundColor = 'transparent';
      btn.style.color = 'var(--text-secondary)';
      btn.style.borderColor = 'var(--border-subtle)';
    }
  });
}

// Explore Bio Down Button & Smooth Scroll Navigation
function initExploreBioButton() {
  const exploreBtn = document.getElementById('explore-bio-btn');
  const aboutSection = document.getElementById('about');

  if (exploreBtn && aboutSection) {
    exploreBtn.addEventListener('click', (e) => {
      e.preventDefault();
      aboutSection.scrollIntoView({ behavior: 'smooth' });
    });
  }

  // Handle header nav clicks
  document.querySelectorAll('header nav a, header a[href^="#"]').forEach(link => {
    link.addEventListener('click', (e) => {
      const targetId = link.getAttribute('href');
      if (targetId && targetId.startsWith('#')) {
        e.preventDefault();
        const targetEl = document.querySelector(targetId);
        if (targetEl) {
          targetEl.scrollIntoView({ behavior: 'smooth' });
        }
      }
    });
  });
}

// 3D Image Wheel Setup (Dynamic from CMS)
function init3DWheel() {
  const container = document.getElementById('three-canvas-container');
  if (!container || typeof ThreeImageWheel === 'undefined') return;

  const rawProjects = CMS_DATA.projects || [];
  const validProjects = rawProjects
    .filter(p => p.showcase3D !== false)
    .map(p => {
      let img = p.coverAssetUrl || (p.coverAsset ? (p.coverAsset.localPath || p.coverAsset.sourceUrl) : 'assets/hero.png');
      if (img.startsWith('uploads/')) {
        img = 'assets/cover-arts/project_wematch.jpg';
      }
      return {
        id: p.id,
        title: p.title,
        category: p.category,
        year: p.year || '2026',
        image: img,
        description: p.description || 'Visual direction piece',
        tags: p.tags || []
      };
    });

  container.innerHTML = '';

  wheelInstance = new ThreeImageWheel('three-canvas-container', {
    items: validProjects,
    cardWidth: 260,
    cardHeight: 360,
    radius: 680,
    cameraDistance: 1420,
    cameraHeight: 300,
    fov: 48,
    onCardHover: (item) => {
      const previewBox = document.getElementById('wheel-preview-box');
      const previewImg = document.getElementById('preview-img');
      const previewTitle = document.getElementById('preview-title');
      const previewCategory = document.getElementById('preview-category');
      const previewDesc = document.getElementById('preview-desc');

      if (item && previewBox) {
        previewBox.classList.remove('hidden-preview');
        if (previewImg) previewImg.src = item.image;
        if (previewTitle) previewTitle.textContent = item.title;
        if (previewCategory) previewCategory.textContent = `${item.category} • ${item.year}`;
        if (previewDesc) previewDesc.textContent = item.description;
      } else if (previewBox) {
        previewBox.classList.add('hidden-preview');
      }
    },
    onCardClick: (item) => {
      openProjectModal(item);
    }
  });
}

// Dynamically Render Category Filter Buttons
function renderFilterButtons() {
  const container = document.getElementById('filter-container');
  if (!container) return;

  const categories = CMS_DATA.categories || [];
  
  let html = `
    <button data-filter="All" class="filter-btn active-filter px-5 py-2 rounded-full border text-xs sm:text-sm font-mono tracking-wider transition-all font-bold cursor-pointer">
      All
    </button>
  `;

  categories.forEach(cat => {
    html += `
      <button data-filter="${cat.name}" class="filter-btn px-5 py-2 rounded-full border text-xs sm:text-sm font-mono tracking-wider transition-all cursor-pointer">
        ${cat.name}
      </button>
    `;
  });

  container.innerHTML = html;

  // Re-bind click events
  const filterBtns = container.querySelectorAll('.filter-btn');
  filterBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      filterBtns.forEach(b => b.classList.remove('active-filter'));
      btn.classList.add('active-filter');
      currentFilter = btn.getAttribute('data-filter');
      renderPortfolioGrid(currentFilter);
    });
  });

  updateFilterButtonsTheme();
}

// Dynamically Render Portfolio Grid Cards
function renderPortfolioGrid(filter = 'All') {
  const grid = document.getElementById('portfolio-grid');
  const countEl = document.getElementById('project-counter');
  if (!grid) return;

  grid.innerHTML = '';
  const projects = CMS_DATA.projects || [];

  const filtered = filter === 'All'
    ? projects.filter(p => p.showInAll !== false)
    : projects.filter(p => p.category === filter || p.categorySlug === filter || (p.tags && p.tags.includes(filter)));

  if (countEl) {
    countEl.textContent = `${filtered.length} project${filtered.length === 1 ? '' : 's'}`;
  }

  filtered.forEach((item) => {
    const card = document.createElement('div');
    card.className = 'project-card group relative flex flex-col justify-between p-4 cursor-pointer';
    
    // Support coverAssetUrl, coverAsset object, or local hero fallback
    const coverImg = item.coverAssetUrl || (item.coverAsset ? (item.coverAsset.localPath || item.coverAsset.sourceUrl) : 'assets/hero.png');

    card.innerHTML = `
      <div class="relative w-full aspect-[4/3] rounded-2xl overflow-hidden bg-slate-100 dark:bg-neutral-900 mb-4 border border-[var(--border-subtle)] shadow-md">
        <img src="${coverImg}" alt="${item.title}" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500" loading="lazy" onerror="this.src='assets/hero.png'" />
        <div class="absolute inset-0 bg-gradient-to-t from-black/80 via-black/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300 flex items-end justify-between p-4">
          <span class="inline-flex items-center gap-1.5 px-3.5 py-1.5 rounded-full bg-[var(--accent-blue)] text-white dark:text-black text-xs font-bold font-mono shadow-md">
            VIEW CASE STUDY →
          </span>
          <span class="text-[10px] font-mono text-white/80 px-2 py-0.5 rounded-full bg-black/50 backdrop-blur-sm">
            ${item.year || '2026'}
          </span>
        </div>
      </div>
      <div class="flex items-start justify-between gap-2">
        <div>
          <span class="text-[10px] font-mono text-[var(--accent-blue)] uppercase tracking-wider font-bold">${item.category}</span>
          <h3 class="text-lg font-bold text-[var(--text-primary)] group-hover:text-[var(--accent-blue)] transition-colors mt-0.5">${item.title}</h3>
        </div>
        <span class="text-xs font-mono text-[var(--text-muted)]">${item.year || "2026"}</span>
      </div>
      <p class="text-xs text-[var(--text-secondary)] mt-2 line-clamp-2 leading-relaxed font-light">${item.description || 'Visual direction & design artwork'}</p>
      <div class="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-[var(--border-subtle)]">
        ${(item.tags || []).map(tag => `<span class="text-[9px] font-mono px-2 py-0.5 rounded-md bg-[var(--badge-bg)] text-[var(--text-secondary)] border border-[var(--border-subtle)] font-medium">${tag}</span>`).join('')}
      </div>
    `;

    card.addEventListener('click', () => openProjectModal(item));
    grid.appendChild(card);
  });

  updateFilterButtonsTheme();
  initLucideIcons();
}

// "Currently I'm Listening" Audio Widget
function initCurrentlyListening() {
  const playBtn = document.getElementById('music-play-btn');
  const eqBars = document.querySelectorAll('.equalizer-bar');
  let isPlaying = true;

  if (!playBtn) return;

  playBtn.addEventListener('click', () => {
    isPlaying = !isPlaying;
    eqBars.forEach(bar => {
      bar.style.animationPlayState = isPlaying ? 'running' : 'paused';
    });
    playBtn.innerHTML = isPlaying
      ? '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg>'
      : '<svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="currentColor"><polygon points="5 3 19 12 5 21 5 3"/></svg>';
  });
}

// Modals Setup
function initModals() {
  const projectModal = document.getElementById('project-modal');
  const modalCloseBtn = document.getElementById('modal-close-btn');

  if (modalCloseBtn && projectModal) {
    modalCloseBtn.addEventListener('click', () => closeModal(projectModal));
  }

  document.querySelectorAll('.modal-wrapper').forEach(modal => {
    modal.addEventListener('click', (e) => {
      if (e.target === modal || e.target.classList.contains('modal-backdrop')) {
        closeModal(modal);
      }
    });
  });

  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.modal-wrapper').forEach(m => closeModal(m));
    }
    // Secret Admin Hotkey: Ctrl + Shift + C
    if (e.ctrlKey && e.shiftKey && (e.key === 'C' || e.key === 'c')) {
      e.preventDefault();
      openModal(document.getElementById('admin-cms-modal'));
    }
  });

  const blogContainer = document.getElementById('blog-posts-list');
  if (blogContainer) {
    blogContainer.innerHTML = BLOG_POSTS.map(post => `
      <article class="p-6 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-card)] hover:border-[var(--accent-blue)] transition-all duration-300 group cursor-pointer shadow-sm" onclick="openBlogArticle('${post.id}')">
        <div class="flex items-center justify-between gap-4 mb-3">
          <span class="text-xs font-mono text-[var(--accent-blue)] tracking-widest font-bold">${post.tag}</span>
          <div class="flex items-center gap-3 text-xs font-mono text-[var(--text-muted)]">
            <span>${post.date}</span>
            <span>•</span>
            <span>${post.readTime}</span>
          </div>
        </div>
        <h3 class="text-2xl font-bold text-[var(--text-primary)] group-hover:text-[var(--accent-blue)] transition-colors mb-2">${post.title}</h3>
        <p class="text-sm text-[var(--text-secondary)] leading-relaxed font-light">${post.summary}</p>
        <div class="mt-4 flex items-center gap-1 text-xs font-mono font-bold text-[var(--accent-blue)]">
          <span>READ ENTRY</span>
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
        </div>
      </article>
    `).join('');
  }
}

function openModal(modal) {
  if (!modal) return;
  modal.classList.remove('modal-hidden');
  document.body.style.overflow = 'hidden';
  initLucideIcons();
}

function closeModal(modal) {
  if (!modal) return;
  modal.classList.add('modal-hidden');
  document.body.style.overflow = '';
}

function openProjectModal(item) {
  const modal = document.getElementById('project-modal');
  if (!modal || !item) return;

  const imgEl = document.getElementById('modal-project-img');
  const titleEl = document.getElementById('modal-project-title');
  const catEl = document.getElementById('modal-project-category');
  const yearEl = document.getElementById('modal-project-year');
  const descEl = document.getElementById('modal-project-desc');
  const tagsContainer = document.getElementById('modal-project-tags');
  const driveBtn = document.getElementById('modal-drive-link');

  const coverImg = item.coverAsset ? (item.coverAsset.localPath || item.coverAsset.sourceUrl) : (item.image || "assets/hero.png");

  if (imgEl) imgEl.src = coverImg;
  if (titleEl) titleEl.textContent = item.title;
  if (catEl) catEl.textContent = item.category;
  if (yearEl) yearEl.textContent = item.year || "2026";
  if (descEl) descEl.textContent = item.description;

  if (driveBtn) {
    driveBtn.href = item.driveUrl || "#";
    driveBtn.innerHTML = `<span>Open in Google Drive (${item.category})</span> <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M15 3h6v6"/><path d="M10 14 21 3"/><path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/></svg>`;
  }

  if (tagsContainer) {
    tagsContainer.innerHTML = (item.tags || []).map(t => `<span class="px-2.5 py-1 rounded-full bg-[var(--badge-bg)] border border-[var(--border-subtle)] text-xs font-mono text-[var(--text-secondary)]">${t}</span>`).join('');
  }

  openModal(modal);
}

// Replaced by dynamic openBlogArticle
function _old_openBlogArticle(id) {
  const post = BLOG_POSTS.find(p => p.id === id);
  if (!post) return;

  const modal = document.getElementById('article-modal');
  if (!modal) return;

  document.getElementById('article-modal-tag').textContent = post.tag;
  document.getElementById('article-modal-date').textContent = `${post.date} • ${post.readTime}`;
  document.getElementById('article-modal-title').textContent = post.title;
  document.getElementById('article-modal-content').innerHTML = post.content.split('\n\n').map(p => `<p class="mb-4 leading-relaxed font-light">${p}</p>`).join('');

  openModal(modal);
}

// Contact Hub & Interactive Action Modals
function initContactCard() {
  const shareBtn = document.getElementById('btn-share-idea');
  const bookBtn = document.getElementById('btn-book-call');
  const ideaModal = document.getElementById('share-idea-modal');
  const bookModal = document.getElementById('book-call-modal');

  if (shareBtn && ideaModal) {
    shareBtn.addEventListener('click', () => openModal(ideaModal));
  }

  if (bookBtn && bookModal) {
    bookBtn.addEventListener('click', () => openModal(bookModal));
  }

  // Idea Form Submission
  const ideaForm = document.getElementById('idea-form');
  if (ideaForm) {
    ideaForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const feedback = document.getElementById('idea-form-feedback');
      if (feedback) {
        feedback.classList.remove('hidden');
        feedback.innerHTML = `<span class="text-[var(--accent-blue)] font-bold">✓ Message sent!</span> dragxsy will respond shortly.`;
      }
      setTimeout(() => {
        closeModal(ideaModal);
        ideaForm.reset();
        if (feedback) feedback.classList.add('hidden');
      }, 1800);
    });
  }

  // Calendar Booking Simulation
  const calendarSlots = document.querySelectorAll('.cal-slot');
  calendarSlots.forEach(slot => {
    slot.addEventListener('click', () => {
      calendarSlots.forEach(s => {
        s.classList.remove('bg-[var(--accent-blue)]', 'text-white', 'dark:text-black', 'font-bold');
        s.classList.add('bg-[var(--badge-bg)]', 'text-[var(--text-primary)]');
      });
      slot.classList.remove('bg-[var(--badge-bg)]', 'text-[var(--text-primary)]');
      slot.classList.add('bg-[var(--accent-blue)]', 'text-white', 'dark:text-black', 'font-bold');
      const bookFeedback = document.getElementById('book-slot-feedback');
      if (bookFeedback) {
        bookFeedback.textContent = `Selected: ${slot.getAttribute('data-slot')} (Creative Discovery)`;
      }
    });
  });

  const confirmBookBtn = document.getElementById('confirm-booking-btn');
  if (confirmBookBtn) {
    confirmBookBtn.addEventListener('click', () => {
      const bookFeedback = document.getElementById('book-slot-feedback');
      if (bookFeedback) {
        bookFeedback.innerHTML = `<span class="text-[var(--accent-blue)] font-bold">✓ Session booked!</span> Confirmation details sent.`;
      }
      setTimeout(() => {
        closeModal(bookModal);
      }, 1800);
    });
  }
}

// Admin CMS Modal Controls & Live Sync Trigger
function initAdminDashboard() {
  const syncBtn = document.getElementById('admin-sync-btn');
  if (syncBtn) {
    syncBtn.addEventListener('click', async () => {
      syncBtn.disabled = true;
      syncBtn.innerHTML = `<span>Synchronizing Drive...</span>`;
      try {
        const resp = await fetch('/api/sync', { method: 'POST' });
        const res = await resp.json();
        if (res.success) {
          syncBtn.innerHTML = `<span>✓ Sync Complete!</span>`;
          await loadCMSData();
        } else {
          syncBtn.innerHTML = `<span>⚠ Sync Error</span>`;
        }
      } catch (err) {
        console.error('[CMS] Sync request error:', err);
        syncBtn.innerHTML = `<span>⚠ Sync Failed</span>`;
      } finally {
        setTimeout(() => {
          syncBtn.disabled = false;
          syncBtn.innerHTML = `<span>Sync Google Drive Now</span>`;
        }, 2000);
      }
    });
  }
}

function updateAdminUI() {
  const statusEl = document.getElementById('admin-sync-status');
  const lastSyncEl = document.getElementById('admin-last-sync');
  const catCountEl = document.getElementById('admin-cat-count');
  const projCountEl = document.getElementById('admin-proj-count');
  const logsContainer = document.getElementById('admin-logs-list');

  if (statusEl) statusEl.textContent = CMS_DATA.syncStatus || "synced";
  if (lastSyncEl) lastSyncEl.textContent = CMS_DATA.lastSyncedAt ? new Date(CMS_DATA.lastSyncedAt).toLocaleString() : "Never";
  if (catCountEl) catCountEl.textContent = (CMS_DATA.categories || []).length;
  if (projCountEl) projCountEl.textContent = (CMS_DATA.projects || []).length;

  if (logsContainer && CMS_DATA.syncLogs) {
    logsContainer.innerHTML = CMS_DATA.syncLogs.slice(0, 15).map(log => `
      <div class="p-2.5 rounded-lg bg-black/40 border border-white/5 flex items-center justify-between text-xs font-mono">
        <div class="flex items-center gap-2">
          <span class="px-1.5 py-0.5 rounded text-[10px] font-bold bg-[var(--accent-blue)]/20 text-[var(--accent-blue)]">${log.type}</span>
          <span class="text-[var(--text-primary)]">${log.item}</span>
        </div>
        <span class="text-[var(--text-muted)] text-[10px]">${log.timestamp}</span>
      </div>
    `).join('');
  }
}

function initLucideIcons() {
  if (window.lucide && typeof window.lucide.createIcons === 'function') {
    window.lucide.createIcons();
  }
}

// Global helpers
window.openModal = openModal;
window.closeModal = closeModal;
window.openBlogArticle = openBlogArticle;
window.openProjectModal = openProjectModal;
window.closeModalById = (id) => closeModal(document.getElementById(id));

// Dynamic Blog Posts Rendering
function renderBlogPosts() {
  const blogContainer = document.getElementById('blog-posts-list');
  if (!blogContainer) return;

  const posts = (CMS_DATA.posts && CMS_DATA.posts.length > 0) ? CMS_DATA.posts : [];

  if (posts.length === 0) {
    blogContainer.innerHTML = `
      <div class="col-span-full py-12 text-center text-xs font-mono text-[var(--text-muted)]">
        No dispatches published yet. Add articles via the Mobile CMS.
      </div>
    `;
    return;
  }

  blogContainer.innerHTML = posts.map(post => `
    <article class="p-6 rounded-2xl border border-[var(--border-subtle)] bg-[var(--bg-card)] hover:border-[var(--accent-blue)] transition-all duration-300 group cursor-pointer shadow-sm" onclick="openBlogArticle('${post.id}')">
      <div class="flex items-center justify-between gap-4 mb-3">
        <span class="text-xs font-mono text-[var(--accent-blue)] tracking-widest font-bold">${post.tag || 'DISPATCH'}</span>
        <div class="flex items-center gap-3 text-xs font-mono text-[var(--text-muted)]">
          <span>${post.date || ''}</span>
          <span>•</span>
          <span>${post.readTime || '4 min read'}</span>
        </div>
      </div>
      <h3 class="text-2xl font-bold text-[var(--text-primary)] group-hover:text-[var(--accent-blue)] transition-colors mb-2">${post.title}</h3>
      <p class="text-sm text-[var(--text-secondary)] leading-relaxed font-light">${post.summary || ''}</p>
      <div class="mt-4 flex items-center gap-1 text-xs font-mono font-bold text-[var(--accent-blue)]">
        <span>READ ENTRY</span>
        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
      </div>
    </article>
  `).join('');
}

function openBlogArticle(id) {
  const posts = (CMS_DATA.posts && CMS_DATA.posts.length > 0) ? CMS_DATA.posts : [];
  const post = posts.find(p => p.id === id);
  if (!post) return;

  const modal = document.getElementById('article-modal');
  if (!modal) return;

  const tagEl = document.getElementById('article-modal-tag');
  const dateEl = document.getElementById('article-modal-date');
  const titleEl = document.getElementById('article-modal-title');
  const contentEl = document.getElementById('article-modal-content');

  if (tagEl) tagEl.textContent = post.tag || 'DISPATCH';
  if (dateEl) dateEl.textContent = `${post.date || ''} • ${post.readTime || '4 min read'}`;
  if (titleEl) titleEl.textContent = post.title;
  if (contentEl) {
    contentEl.innerHTML = (post.content || '').split('\n\n').map(p => `<p class="mb-4 leading-relaxed font-light">${p.replace(/\n/g, '<br>')}</p>`).join('');
  }

  openModal(modal);
}


// Responsive Mobile Navigation Menu Handler
function initMobileMenu() {
  const menuBtn = document.getElementById('mobile-menu-btn');
  const drawer = document.getElementById('mobile-nav-drawer');
  const barsIcon = document.getElementById('menu-icon-bars');
  const closeIcon = document.getElementById('menu-icon-close');
  const navLinks = document.querySelectorAll('.mobile-nav-link');

  if (!menuBtn || !drawer) return;

  function toggleMenu() {
    const isOpen = drawer.classList.contains('menu-open');
    if (isOpen) {
      closeMenu();
    } else {
      openMenu();
    }
  }

  function openMenu() {
    drawer.classList.add('menu-open');
    if (barsIcon) barsIcon.classList.add('hidden');
    if (closeIcon) closeIcon.classList.remove('hidden');
    document.body.style.overflow = 'hidden';
    initLucideIcons();
  }

  function closeMenu() {
    drawer.classList.remove('menu-open');
    if (barsIcon) barsIcon.classList.remove('hidden');
    if (closeIcon) closeIcon.classList.add('hidden');
    document.body.style.overflow = '';
    initLucideIcons();
  }

  window.closeMobileMenu = closeMenu;

  menuBtn.addEventListener('click', toggleMenu);

  navLinks.forEach(link => {
    link.addEventListener('click', () => {
      closeMenu();
    });
  });

  // Close on Escape key
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape' && drawer.classList.contains('menu-open')) {
      closeMenu();
    }
  });
}


// Full-Screen High-Resolution Lightbox Viewer
function openFullscreenLightbox(imgUrl) {
  const lightbox = document.getElementById('fullscreen-lightbox');
  const fullImg = document.getElementById('lightbox-full-img');
  if (!lightbox || !fullImg) return;

  fullImg.src = imgUrl || '';
  lightbox.classList.remove('opacity-0', 'pointer-events-none');
  lightbox.classList.add('opacity-100', 'pointer-events-auto');
  document.body.style.overflow = 'hidden';
  initLucideIcons();
}

function closeFullscreenLightbox() {
  const lightbox = document.getElementById('fullscreen-lightbox');
  if (!lightbox) return;

  lightbox.classList.remove('opacity-100', 'pointer-events-auto');
  lightbox.classList.add('opacity-0', 'pointer-events-none');
  document.body.style.overflow = '';
}

window.openFullscreenLightbox = openFullscreenLightbox;
window.closeFullscreenLightbox = closeFullscreenLightbox;

// Close lightbox on backdrop click or ESC key
document.addEventListener('DOMContentLoaded', () => {
  const lightbox = document.getElementById('fullscreen-lightbox');
  if (lightbox) {
    lightbox.addEventListener('click', (e) => {
      if (e.target === lightbox) closeFullscreenLightbox();
    });
  }
  document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeFullscreenLightbox();
  });
});


// =========================================================================
// LAST.FM API REAL-TIME LISTENING INTEGRATION
// =========================================================================
const LASTFM_CONFIG = {
  apiKey: '5d430fd337f3838ff79e20caed1fe716',
  username: 'dragxsy',
  refreshIntervalMs: 25000 // Refresh every 25s
};

async function initLastFmWidget() {
  const linkEl = document.getElementById('lastfm-link');
  const imgEl = document.getElementById('lastfm-album-art');
  const iconEl = document.getElementById('lastfm-default-icon');
  const statusLabel = document.getElementById('lastfm-status-label');
  const pulseDot = document.getElementById('lastfm-pulse-dot');
  const titleEl = document.getElementById('lastfm-track-title');
  const artistEl = document.getElementById('lastfm-artist-name');
  const eqBars = document.querySelectorAll('.eq-bar');

  if (!titleEl) return;

  async function updateTrack() {
    try {
      const url = `https://ws.audioscrobbler.com/2.0/?method=user.getrecenttracks&user=${LASTFM_CONFIG.username}&api_key=${LASTFM_CONFIG.apiKey}&format=json&limit=1`;
      const resp = await fetch(url);
      if (!resp.ok) return;

      const data = await resp.json();
      const tracks = data?.recenttracks?.track;
      if (!tracks || tracks.length === 0) return;

      const track = Array.isArray(tracks) ? tracks[0] : tracks;
      const isNowPlaying = track['@attr']?.nowplaying === 'true';
      const trackName = track.name || 'Unknown Track';
      const artistName = track.artist?.['#text'] || track.artist?.name || 'Unknown Artist';
      const trackUrl = track.url || `https://www.last.fm/user/${LASTFM_CONFIG.username}`;

      // Get highest resolution album art
      let albumArt = '';
      if (track.image && Array.isArray(track.image)) {
        const largeImg = track.image.find(i => i.size === 'extralarge') || track.image.find(i => i.size === 'large') || track.image[track.image.length - 1];
        albumArt = largeImg?.['#text'] || '';
      }

      if (linkEl) linkEl.href = trackUrl;
      titleEl.textContent = trackName;
      artistEl.textContent = artistName;

      if (albumArt) {
        imgEl.src = albumArt;
        imgEl.classList.remove('hidden');
        if (iconEl) iconEl.classList.add('hidden');
      } else {
        imgEl.classList.add('hidden');
        if (iconEl) iconEl.classList.remove('hidden');
      }

      if (isNowPlaying) {
        if (statusLabel) statusLabel.textContent = 'CURRENTLY LISTENING';
        if (pulseDot) {
          pulseDot.className = 'w-2 h-2 rounded-full bg-emerald-500 animate-pulse';
        }
        eqBars.forEach(b => b.classList.add('eq-playing'));
      } else {
        if (statusLabel) statusLabel.textContent = 'RECENTLY PLAYED';
        if (pulseDot) {
          pulseDot.className = 'w-2 h-2 rounded-full bg-[var(--accent-blue)]';
        }
        eqBars.forEach(b => b.classList.remove('eq-playing'));
      }
    } catch (err) {
      console.warn('Last.fm fetch error:', err);
    }
  }

  // Initial fetch
  await updateTrack();

  // Polling interval
  setInterval(updateTrack, LASTFM_CONFIG.refreshIntervalMs);
}

// Attach to DOM load
document.addEventListener('DOMContentLoaded', () => {
  initLastFmWidget();
});
