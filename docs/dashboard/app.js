let allLeads = [];
let selectedLead = null;

const CATALOG_DATA = [
  {
    category: "fnb_beverage",
    title: "Coffee & Beverage Store",
    products: [
      "Paper Cup Hot 8oz / 12oz (Single Wall / Double Wall)",
      "Cup Cold PET / PP 14oz, 16oz, 22oz",
      "Cup Sleeve Kraft Bergelombang (Heat Insulator)",
      "Coaster Kertas Penyerap Embun",
      "Buku Menu Meja Hardcover Waterproof",
      "Stiker Segel Toples & Tutup Minuman (Security Seal)"
    ],
    materials: "Kraft PE Coating 280-320gsm anti-rembes, Sablon presisi 1-4 warna, Ivory 300gsm laminasi doff anti-air.",
    value_prop: "Desain estetik kekinian, tahan embun es dan panas kopi, menjaga aroma kopi tetap prima selama delivery."
  },
  {
    category: "fnb_food_resto",
    title: "Restoran & Usaha Katering",
    products: [
      "Paper Lunch Box Formed M & L (Bebas Lipat)",
      "Food Pail Kraft / Ivory Anti-Minyak",
      "Wrapping Paper Makanan Custom Logo",
      "Paper Bag Takeaway Tali Kur & Tali Kertas"
    ],
    materials: "Brown Kraft Food Grade 290gsm, Ivory Food Grade FDA Certified, Tinta kedelai ramah lingkungan.",
    value_prop: "Kemasan higienis berstandar food-grade, tidak bocor kuah atau minyak, meningkatkan kelas restoran."
  },
  {
    category: "fashion_retail",
    title: "Fashion & Retail Butik",
    products: [
      "Hangtag Pakaian Tebal (Label Tag)",
      "Thank You Card & Kartu Garansi",
      "Polymailer Cetak Logo Pengiriman",
      "Shopping Bag Eksklusif Tali Kur"
    ],
    materials: "Art Carton 360gsm/400gsm, Laminasi Doff Velvet, Hotprint Foil Emas/Perak, Emboss Logo Timbul.",
    value_prop: "Meningkatkan gengsi pakaian, membuat harga jual busana terlihat layak dihargai mahal."
  },
  {
    category: "beauty_skincare",
    title: "Kecantikan, Kosmetik & Skincare",
    products: [
      "Stiker Segel Botol Jar & Serum",
      "Box Lipat Skincare Kosmetik",
      "Brosur Panduan Perawatan Lipat 3 (Tri-Fold)"
    ],
    materials: "Vinyl Glossy White / Transparan Camel, Duplex/Ivory 310gsm + UV Spot Vernish mengkilap.",
    value_prop: "Stiker tahan gores dan tidak pudar terkena minyak atau cairan serum."
  },
  {
    category: "new_store_opening",
    title: "Grand Opening & Toko Baru",
    products: [
      "Signage Akrilik Toko & Nomor Meja",
      "Neon Box LED Custom Logo",
      "Stiker Kaca One-Way Vision",
      "Spanduk Kain Banner Outdoor",
      "X-Banner & Roll-Up Banner"
    ],
    materials: "Flexi Jerman 510gsm, Stiker Ritrama + Laminating UV, Akrilik Marga Cipta 3mm.",
    value_prop: "Pengerjaan kilat siap sebelum hari pembukaan resmi, warna tajam terbaca jelas dari jalan utama."
  },
  {
    category: "corporate_legal",
    title: "Kantor Hukum, Notaris & Korporat",
    products: [
      "Map Berkas Folder Dokumen Emboss",
      "Nota & Surat Jalan NCR 2-4 Ply",
      "ID Card PVC Magnetik + Lanyard",
      "Sertifikat & Blanko Resmi"
    ],
    materials: "Art Carton 310gsm laminasi satu sisi, Kertas NCR Carbonless, PVC tebal 0.76mm standar kartu perbankan.",
    value_prop: "Membangun citra formal kredibel, kerapian arsip dokumen penting, dan keamanan tanda tangan legal."
  }
];

async function fetchLeads() {
  try {
    const res = await fetch('/api/leads');
    if (!res.ok) throw new Error('Gagal mengambil data leads dari server.');
    allLeads = await res.json();
    renderDashboard();
  } catch (err) {
    console.error('Error fetch leads:', err);
  }
}

function switchView(viewId) {
  document.querySelectorAll('.view-panel').forEach(panel => panel.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(btn => btn.classList.remove('active'));

  const activePanel = document.getElementById(viewId);
  if (activePanel) activePanel.classList.add('active');

  const activeBtn = document.querySelector(`.nav-item[data-view="${viewId}"]`);
  if (activeBtn) activeBtn.classList.add('active');

  const titles = {
    'view-dossier': 'Database Calon Customer (Anchor GMaps Makassar)',
    'view-inspector': 'Deep Content Inspector (Analisis 5 Postingan)',
    'view-pillars': 'Matriks 4 Dimensi Meta Universal',
    'view-catalog': 'Katalog Spesifikasi Teknis Cetak RUANG VISUAL'
  };
  const titleEl = document.getElementById('current-view-title');
  if (titleEl) titleEl.textContent = titles[viewId] || 'Platform Intelijen Pasar';

  if (viewId === 'view-catalog') {
    renderCatalog();
  }
}

function renderDashboard() {
  const catFilter = document.getElementById('filter-category').value;
  const tierFilter = document.getElementById('filter-tier').value;
  const searchFilter = document.getElementById('search-input').value.toLowerCase().trim();

  const filtered = allLeads.filter(lead => {
    if (catFilter !== 'all' && lead.category !== catFilter) return false;
    
    const score = lead.score || lead.pillars_total || 0;
    if (tierFilter === 'tier_high' && score < 80) return false;
    if (tierFilter === 'tier_med' && (score < 60 || score >= 80)) return false;
    if (tierFilter === 'tier_low' && score >= 60) return false;

    if (searchFilter) {
      const name = (lead.business_name || '').toLowerCase();
      const addr = (lead.address_full || '').toLowerCase();
      if (!name.includes(searchFilter) && !addr.includes(searchFilter)) return false;
    }

    return true;
  });

  // Metrics Bar
  document.getElementById('metric-total').textContent = filtered.length;
  document.getElementById('metric-hot').textContent = filtered.filter(l => (l.score || l.pillars_total || 0) >= 80).length;
  document.getElementById('metric-multichannel').textContent = filtered.filter(l => {
    const ch = l.channels || {};
    return Boolean(ch.instagram || ch.tiktok || ch.threads);
  }).length;
  document.getElementById('metric-contact').textContent = filtered.filter(l => l.whatsapp_number || l.phone_number).length;

  // Render Table
  const tbody = document.getElementById('leads-table-body');
  tbody.innerHTML = '';

  if (filtered.length === 0) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td colspan="6" style="text-align: center; color: var(--text-muted); padding: 32px;">Tidak ditemukan data calon customer yang sesuai dengan filter.</td>`;
    tbody.appendChild(tr);
    return;
  }

  filtered.forEach(lead => {
    const tr = document.createElement('tr');
    tr.onclick = () => openDrawer(lead);

    const score = lead.score || lead.pillars_total || 0;
    const isHigh = score >= 80;

    const pLeg = Math.round(((lead.score_legitimacy || 0) / 25) * 100);
    const pVel = Math.round(((lead.score_velocity || 0) / 25) * 100);
    const pTurn = Math.round(((lead.score_turnover || 0) / 30) * 100);
    const pBud = Math.round(((lead.score_budget || 0) / 20) * 100);

    const comm = lead.estimated_commercials || {};
    const tierText = comm.priority_commercial_tier || 'Tier 3 (Standard)';
    const unitsMin = (comm.est_monthly_units_min || 500).toLocaleString('id-ID');
    const unitsMax = (comm.est_monthly_units_max || 1500).toLocaleString('id-ID');
    const painPoints = lead.packaging_pain_points || [];
    const hasPainPoints = painPoints.length > 0;

    tr.innerHTML = `
      <td>
        <div class="lead-title-text">${escapeHtml(lead.business_name)}</div>
        <div class="lead-address-text">${escapeHtml(lead.address_full || 'Makassar')}</div>
      </td>
      <td>
        <span class="category-tag">${formatCategory(lead.category)}</span>
      </td>
      <td>
        <div class="maps-verified-badge">Terverifikasi Fisik</div>
        <div class="maps-rating-text">Rating ${lead.rating || '4.5'} (${lead.reviews_count || '100+'} ulasan)</div>
      </td>
      <td>
        <div class="comm-tier-badge ${tierText.includes('Tier 1') ? 'tier-1' : ''}">${escapeHtml(tierText.split(' ')[0])}</div>
        <div class="comm-units-text">${unitsMin} - ${unitsMax} unit/bln</div>
        ${hasPainPoints ? `<span class="pain-point-pill warning">${painPoints.length} Keluhan Kemasan</span>` : `<span class="pain-point-pill ok">Kemasan Stabil</span>`}
      </td>
      <td>
        <div class="table-score-wrapper">
          <div class="table-score-header">
            <span>Potensi</span>
            <span class="table-score-num ${isHigh ? 'high' : ''}">${score} / 100</span>
          </div>
          <div class="table-pillar-pills" title="Legitimasi: ${lead.score_legitimacy}/25 | Kecepatan: ${lead.score_velocity}/25 | Turnover: ${lead.score_turnover}/30 | Anggaran: ${lead.score_budget}/20">
            <div class="pillar-pill fill-cyan" style="opacity: ${pLeg > 0 ? '1' : '0.2'}"></div>
            <div class="pillar-pill fill-magenta" style="opacity: ${pVel > 0 ? '1' : '0.2'}"></div>
            <div class="pillar-pill fill-yellow" style="opacity: ${pTurn > 0 ? '1' : '0.2'}"></div>
            <div class="pillar-pill fill-key" style="opacity: ${pBud > 0 ? '1' : '0.2'}"></div>
          </div>
        </div>
      </td>
      <td style="text-align: right;">
        <button class="btn-dossier" onclick="event.stopPropagation(); openDrawerById('${lead.id}')">Lihat Dossier</button>
      </td>
    `;

    tbody.appendChild(tr);
  });
}

function openDrawerById(id) {
  const lead = allLeads.find(l => l.id === id);
  if (lead) openDrawer(lead);
}

function formatRupiahShort(val) {
  if (!val || val === 0) return 'Rp 0';
  if (val >= 1000000) {
    const jt = (val / 1000000).toFixed(1).replace('.0', '');
    return `Rp ${jt} Jt`;
  }
  if (val >= 1000) {
    const rb = (val / 1000).toFixed(0);
    return `Rp ${rb} Rb`;
  }
  return `Rp ${val}`;
}

function renderPainPointsList(painPoints) {
  const container = document.getElementById('drawer-pain-points-list');
  if (!container) return;
  container.innerHTML = '';

  if (!painPoints || painPoints.length === 0) {
    container.innerHTML = `
      <div class="pp-empty-state">
        <div class="pp-empty-title">Kemasan Terpantau Stabil</div>
        <div class="pp-empty-desc">Tidak ditemukan keluhan kerusakan atau kebocoran kemasan pada ulasan publik. Pelanggan puas dengan kondisi pengemasan saat ini.</div>
      </div>
    `;
    return;
  }

  painPoints.forEach((pp, idx) => {
    const card = document.createElement('div');
    card.className = 'pain-point-card';

    const kwBadges = (pp.detected_keywords || []).map(k => `<span class="pp-kw-badge">${escapeHtml(k)}</span>`).join(' ');

    card.innerHTML = `
      <div class="pp-card-header">
        <span class="pp-badge-alert">Keluhan #${idx + 1} &bull; Rating ${pp.rating || '-'}/5</span>
        <span class="pp-date">${escapeHtml(pp.date || 'Ulasan Terkini')}</span>
      </div>
      <div class="pp-review-text">"${escapeHtml(pp.review_text)}"</div>
      <div class="pp-keywords-row">
        <span class="pp-kw-label">Kata Kunci:</span>
        <div>${kwBadges}</div>
      </div>
      <div class="pp-angle-box">
        <div class="pp-angle-title">Sudut Pendekatan Penjualan (Sales Angle):</div>
        <div class="pp-angle-text">${escapeHtml(pp.sales_angle || 'Tawarkan solusi kemasan presisi anti-bocor RUANG VISUAL.')}</div>
      </div>
    `;
    container.appendChild(card);
  });
}

function openDrawer(lead) {
  selectedLead = lead;

  const handleInputEl = document.getElementById('link-handle-input');
  if (handleInputEl) handleInputEl.value = '';

  document.getElementById('drawer-category').textContent = formatCategory(lead.category);
  document.getElementById('drawer-title').textContent = lead.business_name;
  
  // Maps & Location
  document.getElementById('drawer-maps-name').textContent = lead.business_name;
  document.getElementById('drawer-address').textContent = lead.address_full || 'Alamat fisik belum tercatat';
  document.getElementById('drawer-rating').textContent = `Rating ${lead.rating || '4.5'}`;
  document.getElementById('drawer-reviews').textContent = `${lead.reviews_count || '100+'} Ulasan Google Maps`;

  const mapsLink = document.getElementById('drawer-maps-link');
  if (lead.channels && lead.channels.google_maps) {
    mapsLink.href = lead.channels.google_maps;
    mapsLink.style.display = 'inline-block';
  } else {
    mapsLink.style.display = 'none';
  }

  // 4 Pillars Scoring
  const totalScore = lead.score || lead.pillars_total || 0;
  document.getElementById('drawer-total-score').textContent = `${totalScore} / 100`;

  const leg = lead.score_legitimacy || 0;
  const vel = lead.score_velocity || 0;
  const turn = lead.score_turnover || 0;
  const bud = lead.score_budget || 0;

  document.getElementById('p-score-legitimacy').textContent = `${leg} / 25`;
  document.getElementById('p-fill-legitimacy').style.width = `${(leg / 25) * 100}%`;

  document.getElementById('p-score-velocity').textContent = `${vel} / 25`;
  document.getElementById('p-fill-velocity').style.width = `${(vel / 25) * 100}%`;

  document.getElementById('p-score-turnover').textContent = `${turn} / 30`;
  document.getElementById('p-fill-turnover').style.width = `${(turn / 30) * 100}%`;

  document.getElementById('p-score-budget').textContent = `${bud} / 20`;
  document.getElementById('p-fill-budget').style.width = `${(bud / 20) * 100}%`;

  // Explainable Intelligence Narrative
  document.getElementById('drawer-reason-summary').textContent = lead.reason_summary || 'Analisis 4 dimensi telah terhitung.';

  // Commercial Estimates
  const comm = lead.estimated_commercials || {};
  const commTierEl = document.getElementById('drawer-comm-tier');
  if (commTierEl) commTierEl.textContent = comm.priority_commercial_tier || 'Tier 3 (Standard)';
  const commCycleEl = document.getElementById('drawer-comm-cycle');
  if (commCycleEl) commCycleEl.textContent = `Siklus Restock: ${comm.restock_cycle_days || 30} Hari`;
  
  const minU = (comm.est_monthly_units_min || 0).toLocaleString('id-ID');
  const maxU = (comm.est_monthly_units_max || 0).toLocaleString('id-ID');
  const commUnitsEl = document.getElementById('drawer-comm-units');
  if (commUnitsEl) commUnitsEl.textContent = `${minU} - ${maxU} Unit`;

  const minV = formatRupiahShort(comm.est_monthly_value_min_idr || 0);
  const maxV = formatRupiahShort(comm.est_monthly_value_max_idr || 0);
  const commValEl = document.getElementById('drawer-comm-value');
  if (commValEl) commValEl.textContent = `${minV} - ${maxV} / Bln`;

  // Packaging Pain Points List
  renderPainPointsList(lead.packaging_pain_points || []);

  // Multi-Channel Status
  renderChannelsList(lead);

  // Inspected Posts Previews
  renderDrawerPosts(lead.top_posts || []);

  // Solution Recommendations
  const prodsList = document.getElementById('drawer-solution-products');
  prodsList.innerHTML = '';
  (lead.recommended_products || []).forEach(p => {
    const li = document.createElement('li');
    li.textContent = p;
    prodsList.appendChild(li);
  });

  document.getElementById('drawer-solution-specs').textContent = lead.materials_finishing || '-';
  document.getElementById('drawer-solution-value').textContent = lead.value_proposition || '-';

  // WhatsApp Pitch Draft
  const pitchArea = document.getElementById('drawer-pitch-text');
  const waBtn = document.getElementById('drawer-wa-button');
  if (lead.pitch_text) {
    pitchArea.value = lead.pitch_text;
    document.getElementById('drawer-wa-section').style.display = 'flex';
    if (lead.wa_link) {
      waBtn.href = lead.wa_link;
      waBtn.style.display = 'inline-block';
    } else {
      waBtn.style.display = 'none';
    }
  } else {
    document.getElementById('drawer-wa-section').style.display = 'none';
  }


  document.getElementById('overlay').style.display = 'block';
  document.getElementById('detail-drawer').classList.add('open');
}

function closeDrawer() {
  document.getElementById('overlay').style.display = 'none';
  document.getElementById('detail-drawer').classList.remove('open');
}

function renderChannelsList(lead) {
  const container = document.getElementById('drawer-channels-list');
  container.innerHTML = '';

  const channels = lead.channels || {};
  const channelDefs = [
    { key: 'google_maps', name: 'Google Maps' },
    { key: 'instagram', name: 'Instagram' },
    { key: 'tiktok', name: 'TikTok' },
    { key: 'threads', name: 'Threads' },
    { key: 'food_delivery', name: 'Food Delivery' }
  ];

  channelDefs.forEach(ch => {
    const card = document.createElement('div');
    card.className = 'channel-status-card';
    const val = channels[ch.key];
    const isLinked = Boolean(val && val.trim() !== '');

    let linkHtml = 'Belum Terhubung';
    if (isLinked) {
      let targetUrl = val.trim();
      let label = targetUrl;
      if (targetUrl.startsWith('http://') || targetUrl.startsWith('https://')) {
        label = targetUrl.length > 35 ? targetUrl.slice(0, 32) + '...' : targetUrl;
      } else if (ch.key === 'instagram') {
        const handle = targetUrl.replace(/^@/, '');
        targetUrl = `https://instagram.com/${handle}`;
        label = `@${handle}`;
      } else if (ch.key === 'tiktok') {
        const handle = targetUrl.replace(/^@/, '');
        targetUrl = `https://www.tiktok.com/@${handle}`;
        label = `@${handle}`;
      } else if (ch.key === 'threads') {
        const handle = targetUrl.replace(/^@/, '');
        targetUrl = `https://www.threads.net/@${handle}`;
        label = `@${handle}`;
      }
      linkHtml = `<a href="${encodeURI(targetUrl)}" target="_blank" rel="noopener noreferrer" style="color: #0284C7; font-weight: 600; text-decoration: underline; word-break: break-all;">${escapeHtml(label)}</a>`;
    }

    card.innerHTML = `
      <div class="channel-name">${ch.name}</div>
      <div class="channel-val ${isLinked ? '' : 'not-linked'}">
        ${linkHtml}
      </div>
    `;
    container.appendChild(card);
  });
}

function renderDrawerPosts(posts) {
  const container = document.getElementById('drawer-posts-list');
  container.innerHTML = '';

  if (!posts || posts.length === 0) {
    container.innerHTML = `
      <div style="font-size: 12px; color: var(--text-muted); background: #F8FAFC; padding: 14px; border-radius: 6px; border: 1px solid var(--border-subtle);">
        Konten sosial belum diinspeksi. Hubungkan akun Instagram atau TikTok di atas untuk menarik 5 postingan terpopuler secara otomatis.
      </div>
    `;
    return;
  }

  posts.forEach((post, idx) => {
    const item = document.createElement('div');
    item.className = 'drawer-post-item';

    const tagsHtml = (post.tags || []).map(t => `<span class="post-tag-badge">${escapeHtml(t)}</span>`).join(' ');

    item.innerHTML = `
      <div class="dpi-top">
        <span>Konten #${idx + 1} &bull; ${post.date}</span>
        <div>${tagsHtml}</div>
      </div>
      <div class="dpi-caption">${escapeHtml(post.caption)}</div>
      <div class="dpi-stats">
        <span>Views: ${post.views.toLocaleString()}</span>
        <span>Likes: ${post.likes.toLocaleString()}</span>
        <span>Komentar: ${post.comments.toLocaleString()}</span>
        <span>ER: ${post.engagement_rate}%</span>
      </div>
    `;
    container.appendChild(item);
  });
}

async function submitChannelLink() {
  if (!selectedLead) return;

  const platform = document.getElementById('link-platform-select').value;
  const handleInput = document.getElementById('link-handle-input').value.trim();

  if (!handleInput) {
    alert('Harap masukkan username atau link akun media sosial terlebih dahulu.');
    return;
  }

  try {
    const res = await fetch('/api/leads/link-channel', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lead_id: selectedLead.id,
        platform: platform,
        handle_or_url: handleInput
      })
    });

    if (!res.ok) throw new Error('Gagal menghubungkan kanal sosial.');
    const result = await res.json();

    // Update in local state
    const updatedLead = result.lead;
    const idx = allLeads.findIndex(l => l.id === updatedLead.id);
    if (idx !== -1) {
      allLeads[idx] = updatedLead;
    }

    selectedLead = updatedLead;
    document.getElementById('link-handle-input').value = '';

    renderDashboard();
    openDrawer(updatedLead);

    alert(`Kanal ${platform} berhasil dihubungkan dan 5 konten terpopuler telah ditarik ke profil dossier.`);
  } catch (err) {
    console.error('Error link channel:', err);
    alert('Terjadi kesalahan saat menghubungkan kanal sosial.');
  }
}

async function runStandaloneInspection() {
  const platform = document.getElementById('inspect-platform').value;
  const handleInput = document.getElementById('inspect-handle').value.trim();

  if (!handleInput) {
    alert('Harap masukkan username atau URL profil akun.');
    return;
  }

  try {
    const res = await fetch('/api/inspect-content', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        platform: platform,
        handle: handleInput
      })
    });

    if (!res.ok) throw new Error('Gagal melakukan inspeksi konten.');
    const data = await res.json();

    document.getElementById('ins-result-handle').textContent = `${data.handle} (${data.platform})`;
    document.getElementById('ins-result-views').textContent = data.total_views.toLocaleString();
    document.getElementById('ins-result-eng').textContent = `${data.avg_engagement_rate}%`;
    document.getElementById('ins-result-signals').textContent = `${data.packaging_intent_posts} Konten`;

    const grid = document.getElementById('inspector-posts-grid');
    grid.innerHTML = '';

    if (!data.posts || data.posts.length === 0) {
      grid.innerHTML = `
        <div style="font-size: 13px; color: var(--text-muted); background: #F8FAFC; padding: 18px; border-radius: 6px; border: 1px solid var(--border-subtle); text-align: center; width: 100%; grid-column: 1 / -1;">
          Status: <strong>${escapeHtml(data.status || 'Belum diinspeksi')}</strong>. Belum ada konten media yang ditarik untuk akun ini.
        </div>
      `;
    } else {
      data.posts.forEach((post, i) => {
        const card = document.createElement('div');
        card.className = 'post-card';
        const tags = (post.tags || []).map(t => `<span class="post-tag-badge">${escapeHtml(t)}</span>`).join(' ');

        card.innerHTML = `
          <div class="post-meta-top">
            <span>Postingan #${i + 1}</span>
            <span>${post.date}</span>
          </div>
          <div class="post-caption">${escapeHtml(post.caption)}</div>
          <div class="post-stats-row">
            <span>Views: ${post.views.toLocaleString()}</span>
            <span>Likes: ${post.likes.toLocaleString()}</span>
            <span>Komentar: ${post.comments.toLocaleString()}</span>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px;">
            <span style="font-size: 11px; font-weight: 700; color: var(--text-muted);">ER: ${post.engagement_rate}%</span>
            <div>${tags}</div>
          </div>
        `;
        grid.appendChild(card);
      });
    }

    document.getElementById('inspector-results').style.display = 'block';
  } catch (err) {
    console.error('Error standalone inspection:', err);
    alert('Terjadi kesalahan saat melakukan inspeksi konten.');
  }
}

function renderCatalog() {
  const grid = document.getElementById('catalog-grid');
  if (!grid || grid.children.length > 0) return;

  CATALOG_DATA.forEach(cat => {
    const card = document.createElement('div');
    card.className = 'catalog-card';

    const prodsHtml = cat.products.map(p => `<li>${escapeHtml(p)}</li>`).join('');

    card.innerHTML = `
      <span class="cat-badge">${formatCategory(cat.category)}</span>
      <h3 class="cat-title">${escapeHtml(cat.title)}</h3>
      
      <div class="cat-sublabel">Produk Kemasan &amp; Cetak Utama</div>
      <ul class="cat-prods-list">${prodsHtml}</ul>

      <div class="cat-sublabel">Spesifikasi Material &amp; Finishing</div>
      <div class="cat-desc">${escapeHtml(cat.materials)}</div>

      <div class="cat-sublabel">Value Proposition RUANG VISUAL</div>
      <div class="cat-desc">${escapeHtml(cat.value_prop)}</div>
    `;
    grid.appendChild(card);
  });
}

function formatCategory(cat) {
  const map = {
    fnb_beverage: 'Coffee & Beverage',
    fnb_food_resto: 'Food & Restoran',
    fashion_retail: 'Fashion & Butik',
    beauty_skincare: 'Beauty & Skincare',
    new_store_opening: 'Grand Opening',
    corporate_legal: 'Notaris & Korporat',
    event_service: 'Event & Organizer',
    general_commercial: 'Commercial Business'
  };
  return map[cat] || cat;
}

function escapeHtml(str) {
  if (!str) return '';
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

// Event Listeners
document.getElementById('filter-category').addEventListener('change', renderDashboard);
document.getElementById('filter-tier').addEventListener('change', renderDashboard);
document.getElementById('search-input').addEventListener('input', renderDashboard);
document.getElementById('btn-export-csv').addEventListener('click', () => {
  window.location.href = '/api/export/csv';
});

// Initial Load
fetchLeads();
