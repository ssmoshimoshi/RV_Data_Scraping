let allLeads = [];
let selectedLead = null;
let currentPage = 1;
const LEADS_PER_PAGE = 25;
let currentOutreachFilter = 'all';

const CATALOG_DATA = [
  {
    category: "advertising",
    title: "1. Reklame & Promosi Visual",
    products: [
      "Neon Box LED Acrylic Custom Logo",
      "Signage Akrilik Toko & Nomor Meja",
      "Huruf Timbul (Channel Letter) Stainless / Galvanis",
      "Banner Outdoor Flexi Jerman 510gsm High-Res",
      "X-Banner, Roll-Up Banner & Tripod Display",
      "Stiker Kaca One-Way Vision & Sandblast Printing"
    ],
    materials: "Flexi Jerman 510gsm, Akrilik Marga Cipta 3mm, LED Samsung Waterproof, Rangka Holo Galvanis anti-karat.",
    value_prop: "Pengerjaan presisi tahan cuaca ekstrem Makassar, pencahayaan merata, visibilitas maksimal dari jalan utama."
  },
  {
    category: "custom_merch",
    title: "2. Merchandise & Souvenir Promosi",
    products: [
      "Tumbler Stainless Grafir Laser & UV Print",
      "Mug Keramik Coating Sublimasi Anti-Pudar",
      "Flashdisk Kartu PVC Cetak Full Color",
      "Payung Lipat Sablon Logo Korporat",
      "Pin Enamel Logam & Gantungan Kunci Karet",
      "Notebook Agenda Eksklusif Hardcover Emboss"
    ],
    materials: "Stainless Steel SUS304 Food Grade, UV Curable Ink Jepang tahan gores, Kulit sintetis premium.",
    value_prop: "Membangun loyalitas merek pelanggan dengan souvenir berkualitas tinggi yang awet digunakan bertahun-tahun."
  },
  {
    category: "apparel",
    title: "3. Konveksi & Sablon Tekstil",
    products: [
      "Kaos Komunitas & Event Cotton Combed 24s/30s",
      "Kemeja PDH / PDL Drill Bordir Komputer Presisi",
      "Polo Shirt Lacoste Pique Bordir Monogram",
      "Jaket Hoodie & Bomber Custom Bordir",
      "Apron Barista / Chef Canvas Waterproof",
      "Tote Bag Canvas Tebal Sablon Plastisol"
    ],
    materials: "Cotton Combed 100% reaktif adem, Kain American / Japan Drill original, Benang bordir polyester tahan luntur.",
    value_prop: "Jahitan rantai standar distro, pola potong nyaman di badan, warna sablon dan bordir tahan cuci puluhan kali."
  },
  {
    category: "office_school",
    title: "4. Institusi, Sekolah & Kantor",
    products: [
      "Map Berkas Folder Dokumen Tebal Emboss / Foil",
      "Nota & Surat Jalan NCR Carbonless 2 - 4 Ply",
      "ID Card PVC Magnetik / RFID Standar Perbankan",
      "Tali Lanyard Tissue 2cm Print Sublim Full Color",
      "Sertifikat & Ijazah Kertas Linen / Concorde Berhologram",
      "Buku Agenda Tahunan, Kalender Meja & Kalender Dinding"
    ],
    materials: "Art Carton 310gsm laminasi doff/glossy, Kertas NCR original tidak tembus buram, PVC tebal 0.76mm standar ATM.",
    value_prop: "Membangun citra formal kredibel, kerapian arsip dokumen penting, dan standarisasi identitas staf profesional."
  },
  {
    category: "label_sticker",
    title: "5. Labeling Produk & Stiker Kemasan",
    products: [
      "Stiker Vinyl Waterproof Doff / Glossy Cetak Tajam",
      "Stiker Transparan Camel Anti-Air Khusus Botol",
      "Stiker Roll Kemasan Otomatis (Mesin Labeler)",
      "Stiker Segel Toples & Tutup Minuman (Security Seal)",
      "Stiker Hologram Pengaman Produk Anti-Pemalsuan",
      "Stiker Kraft Cokelat Estetik Eco-Friendly"
    ],
    materials: "Bahan Vinyl Ritrama / Camel sintetis tahan beku kulkas, Lem super kuat food grade, Laminasi dingin anti-minyak.",
    value_prop: "Daya rekat kuat tidak mudah lepas terkena embun es atau minyak, potongan kiss-cut rapi siap diaplikasikan kilat."
  },
  {
    category: "fnb_beverage",
    title: "Sektor: Coffee & Beverage Store",
    products: [
      "Paper Cup Hot 8oz / 12oz (Single Wall & Double Wall)",
      "Cup Cold PET / PP Tebal 14oz, 16oz, 22oz Sablon Tajam",
      "Cup Sleeve Kraft Bergelombang (Heat Insulator)",
      "Coaster Kertas Penyerap Embun Es",
      "Buku Menu Meja Hardcover Waterproof Anti-Noda",
      "Stiker Segel Tutup Minuman Higienis"
    ],
    materials: "Kraft PE Coating 290-320gsm anti-rembes, Sablon food-grade presisi, Ivory 300gsm laminasi doff tahan percikan air.",
    value_prop: "Desain estetik modern, tahan embun es dan panas kopi, menjaga keamanan minuman saat pengantaran kurir online."
  },
  {
    category: "fnb_food_resto",
    title: "Sektor: Restoran & Usaha Katering",
    products: [
      "Paper Lunch Box Formed M & L (Bebas Lipat Siap Pakai)",
      "Food Pail Kraft / Ivory Anti-Minyak & Anti-Bocor",
      "Wrapping Paper Makanan Custom Cetak Pola Logo",
      "Paper Bag Takeaway Kraft Tali Kur & Tali Pipih",
      "Buku Menu Hardcover Eksklusif Tahan Minyak"
    ],
    materials: "Brown Kraft Food Grade 290gsm FDA Certified, Ivory Food Grade, Tinta nabati ramah lingkungan.",
    value_prop: "Kemasan higienis standar sertifikasi makanan, tidak bocor kuah santan atau minyak rendang, menaikkan kelas kuliner."
  },
  {
    category: "fashion_retail",
    title: "Sektor: Fashion & Retail Butik",
    products: [
      "Hangtag Pakaian Tebal (Label Merek Premium)",
      "Thank You Card & Kartu Petunjuk Perawatan Busana",
      "Polymailer Cetak Logo Identitas Pengiriman Paket",
      "Shopping Bag Kertas Ivory Eksklusif Tali Kur",
      "Label Woven & Pita Satin Jahit Leher"
    ],
    materials: "Art Carton 360gsm/400gsm, Laminasi Doff Velvet Beludru, Hotprint Foil Emas/Perak, Emboss Logo Timbul.",
    value_prop: "Meningkatkan gengsi pakaian, membuat harga jual busana tampak bernilai tinggi dan eksklusif di mata pembeli."
  },
  {
    category: "beauty_skincare",
    title: "Sektor: Kecantikan, Kosmetik & Skincare",
    products: [
      "Stiker Segel Botol Dropper, Jar Krim & Serum",
      "Box Kemasan Lipat Skincare Ivory Cetak Spot UV",
      "Brosur Panduan Pemakaian Lipat 3 (Tri-Fold Brosur)",
      "Pouch Kosmetik Custom Bahan Spunbound / Kanvas"
    ],
    materials: "Vinyl Glossy White / Transparan Camel, Ivory 310gsm + UV Spot Vernish mengkilap, Tahan tumpahan kimia ringan.",
    value_prop: "Label tidak melar atau terkelupas saat terkena minyak serum wajah, desain elegan mencerminkan standar klinis."
  },
  {
    category: "corporate_legal",
    title: "Sektor: Kantor Hukum, Notaris & Korporat",
    products: [
      "Map Berkas Folder Dokumen Emboss Lambang Resmi",
      "Nota & Kuitansi NCR Carbonless 2-4 Rangkap",
      "ID Card Staf Magnetik & Lanyard Tenun Berkualitas",
      "Kop Surat & Amplop Resmi Segel Kering"
    ],
    materials: "Art Carton 310gsm laminasi satu sisi, Kertas HVS 100gsm impor, PVC padat 0.76mm standar kartu identitas.",
    value_prop: "Menegaskan legitimasi dan reputasi formal kantor, menjamin kerahasiaan berkas klien dengan folder berstandar tinggi."
  },
  {
    category: "education",
    title: "Sektor: Institusi Pendidikan & Kampus",
    products: [
      "Buku Agenda Wisuda & Buku Tahunan Siswa Hardcover",
      "Map Ijazah Folio Hotprint Foil Emas Sudut Siku",
      "Kartu Pelajar / Mahasiswa Kartu Pintar RFID",
      "Spanduk Penerimaan Peserta Didik Baru (PPDB)",
      "Brosur Program Studi & Formulir Pendaftaran NCR"
    ],
    materials: "ASE Kulit Sintetis tebal 0.8mm + Busa siku emas, Kertas Art Paper 150gsm full color, Flexi outdoor 440gsm.",
    value_prop: "Paket lengkap pengadaan institusi pendidikan dengan jaminan ketepatan waktu sebelum kalender akademik dimulai."
  },
  {
    category: "event_community",
    title: "Sektor: Event Organizer & Komunitas",
    products: [
      "Gelang Tiket Masuk Wristband Tyvek / Vinyl Barcode",
      "ID Card Panitia & Peserta + Tali Lanyard Cetak Dua Sisi",
      "Backdrop Panggung Photobooth Jumbo Seamless",
      "Goodie Bag Spunbond / Kanvas Sablon Souvenir",
      "Plakat Akrilik Penghargaan & Medali Logam Cor"
    ],
    materials: "Kertas sintetis Tyvek anti-sobek tahan air, Akrilik 5mm cutting laser presisi, Flexi korindo 440gsm high-res.",
    value_prop: "Kecepatan produksi kilat siap kirim H-3 acara, manajemen kontrol akses tiket yang aman anti-pemalsuan."
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

function switchDrawerTab(tabId) {
  document.querySelectorAll('.drawer-tab-btn').forEach(btn => btn.classList.remove('active'));
  document.querySelectorAll('.drawer-tab-content').forEach(content => content.classList.remove('active'));

  const targetContent = document.getElementById(tabId);
  if (targetContent) targetContent.classList.add('active');

  const btnMap = {
    'tab-outreach': 'tab-btn-outreach',
    'tab-intel': 'tab-btn-intel',
    'tab-reviews': 'tab-btn-reviews',
    'tab-channels': 'tab-btn-channels'
  };
  const activeBtn = document.getElementById(btnMap[tabId]);
  if (activeBtn) activeBtn.classList.add('active');
}

function setOutreachFilter(status) {
  currentOutreachFilter = status;
  const selectEl = document.getElementById('filter-outreach');
  if (selectEl) selectEl.value = status;
  updatePipelinePillActive(status);
  currentPage = 1;
  renderDashboard();
}

function updatePipelinePillActive(status) {
  document.querySelectorAll('.pipeline-pill').forEach(btn => {
    if (btn.getAttribute('data-status') === status) {
      btn.classList.add('active');
    } else {
      btn.classList.remove('active');
    }
  });
}

function changePage(delta) {
  currentPage += delta;
  renderDashboard();
}

function getLeadPillarKey(lead) {
  if (lead.primary_service_pillar) {
    const p = String(lead.primary_service_pillar).toLowerCase();
    if (p.includes('advert') || p.includes('reklame')) return 'advertising';
    if (p.includes('merch') || p.includes('souvenir')) return 'custom_merch';
    if (p.includes('apparel') || p.includes('konveksi') || p.includes('sablon')) return 'apparel';
    if (p.includes('office') || p.includes('school') || p.includes('kantor') || p.includes('sekolah')) return 'office_school';
    if (p.includes('label') || p.includes('sticker') || p.includes('kemasan')) return 'label_sticker';
    return p;
  }
  const sector = String(lead.target_sector || lead.category || '').toLowerCase();
  if (sector.includes('education') || sector.includes('corporate') || sector.includes('legal') || sector.includes('notaris')) {
    return 'office_school';
  }
  if (sector.includes('fashion') || sector.includes('retail_apparel') || sector.includes('apparel')) {
    return 'apparel';
  }
  if (sector.includes('event')) {
    return 'custom_merch';
  }
  if (sector.includes('opening') || sector.includes('store') || sector.includes('advertising')) {
    return 'advertising';
  }
  return 'label_sticker';
}

function formatPillar(key) {
  const map = {
    advertising: '1. Reklame & Promosi Visual',
    custom_merch: '2. Merchandise & Souvenir',
    apparel: '3. Konveksi & Sablon Tekstil',
    office_school: '4. Institusi, Kantor & Sekolah',
    label_sticker: '5. Labeling & Kemasan Produk'
  };
  return map[key] || 'Promosi & Cetak';
}

function getLeadTier(lead) {
  if (lead.priority_tier && /^Tier [A-D]$/i.test(lead.priority_tier.trim())) {
    return lead.priority_tier.trim().toUpperCase();
  }
  const score = Number(lead.lead_score || lead.score || lead.pillars_total || 0);
  if (score >= 80) return 'Tier A';
  if (score >= 65) return 'Tier B';
  if (score >= 50) return 'Tier C';
  return 'Tier D';
}

function renderDashboard() {
  const countAll = allLeads.length;
  const countUncontacted = allLeads.filter(l => (l.outreach_status || 'Belum Dihubungi') === 'Belum Dihubungi').length;
  const countContacted = allLeads.filter(l => l.outreach_status === 'Dihubungi').length;
  const countInterested = allLeads.filter(l => l.outreach_status === 'Tertarik').length;
  const countClosing = allLeads.filter(l => l.outreach_status === 'Closing').length;
  const countIrrelevant = allLeads.filter(l => l.outreach_status === 'Tidak Relevan').length;

  const elAll = document.getElementById('pipe-count-all');
  if (elAll) elAll.textContent = countAll;
  const elUn = document.getElementById('pipe-count-uncontacted');
  if (elUn) elUn.textContent = countUncontacted;
  const elCon = document.getElementById('pipe-count-contacted');
  if (elCon) elCon.textContent = countContacted;
  const elInt = document.getElementById('pipe-count-interested');
  if (elInt) elInt.textContent = countInterested;
  const elClo = document.getElementById('pipe-count-closing');
  if (elClo) elClo.textContent = countClosing;
  const elIrr = document.getElementById('pipe-count-irrelevant');
  if (elIrr) elIrr.textContent = countIrrelevant;

  const catFilter = (document.getElementById('filter-category') || {}).value || 'all';
  const pillarFilter = (document.getElementById('filter-pillar') || {}).value || 'all';
  const tierFilter = (document.getElementById('filter-tier') || {}).value || 'all';
  const outreachSelect = document.getElementById('filter-outreach');
  const outreachFilter = outreachSelect ? outreachSelect.value : currentOutreachFilter;
  const searchFilter = (document.getElementById('search-input') || {}).value ? document.getElementById('search-input').value.toLowerCase().trim() : '';

  const filtered = allLeads.filter(lead => {
    // Sektor Filter
    if (catFilter !== 'all') {
      const sec = (lead.target_sector || lead.category || '').toLowerCase();
      if (sec !== catFilter.toLowerCase()) return false;
    }

    // 5 Pilar Layanan Filter
    if (pillarFilter !== 'all') {
      const pKey = getLeadPillarKey(lead);
      if (pKey !== pillarFilter) return false;
    }

    // Tier Filter (Tier A, Tier B, Tier C, Tier D)
    if (tierFilter !== 'all') {
      const tier = getLeadTier(lead);
      if (tier !== tierFilter) return false;
    }

    // Outreach Status Filter
    const st = lead.outreach_status || 'Belum Dihubungi';
    if (outreachFilter !== 'all' && st !== outreachFilter) return false;

    // Search Filter
    if (searchFilter) {
      const name = (lead.business_name || '').toLowerCase();
      const addr = (lead.address_full || '').toLowerCase();
      const cluster = (lead.sales_cluster || '').toLowerCase();
      const dist = (lead.district_area || '').toLowerCase();
      const wa = (lead.whatsapp_number || lead.phone_number || '').toLowerCase();
      if (!name.includes(searchFilter) && !addr.includes(searchFilter) && !cluster.includes(searchFilter) && !dist.includes(searchFilter) && !wa.includes(searchFilter)) {
        return false;
      }
    }

    return true;
  });

  // Metrics Bar
  document.getElementById('metric-total').textContent = filtered.length;
  document.getElementById('metric-hot').textContent = filtered.filter(l => {
    const tier = getLeadTier(l);
    return tier === 'Tier A' || tier === 'Tier B';
  }).length;
  document.getElementById('metric-multichannel').textContent = filtered.filter(l => {
    const ch = l.channels || {};
    return Boolean(ch.instagram || ch.tiktok || ch.threads || (l.platforms && l.platforms.length > 1));
  }).length;
  document.getElementById('metric-contact').textContent = filtered.filter(l => Boolean(l.whatsapp_number || l.phone_number)).length;

  // Pagination calculations
  const totalPages = Math.ceil(filtered.length / LEADS_PER_PAGE) || 1;
  if (currentPage > totalPages) currentPage = totalPages;
  if (currentPage < 1) currentPage = 1;

  const startIdx = (currentPage - 1) * LEADS_PER_PAGE;
  const endIdx = Math.min(startIdx + LEADS_PER_PAGE, filtered.length);
  const pageItems = filtered.slice(startIdx, endIdx);

  const countInfoEl = document.getElementById('leads-count-info');
  if (countInfoEl) {
    countInfoEl.textContent = filtered.length > 0
      ? `Menampilkan ${startIdx + 1} - ${endIdx} dari ${filtered.length} calon customer`
      : 'Menampilkan 0 calon customer';
  }

  const pageIndicatorEl = document.getElementById('page-indicator');
  if (pageIndicatorEl) {
    pageIndicatorEl.textContent = `Halaman ${currentPage} / ${totalPages}`;
  }

  const prevBtn = document.getElementById('btn-page-prev');
  if (prevBtn) prevBtn.disabled = currentPage <= 1;

  const nextBtn = document.getElementById('btn-page-next');
  if (nextBtn) nextBtn.disabled = currentPage >= totalPages;

  // Render Table Body
  const tbody = document.getElementById('leads-table-body');
  tbody.innerHTML = '';

  if (filtered.length === 0) {
    const tr = document.createElement('tr');
    tr.innerHTML = `<td colspan="6" style="text-align: center; color: var(--text-muted); padding: 36px;">Tidak ditemukan data calon customer yang sesuai dengan kriteria filter saat ini.</td>`;
    tbody.appendChild(tr);
    return;
  }

  pageItems.forEach(lead => {
    const tr = document.createElement('tr');
    tr.onclick = () => openDrawer(lead);

    const score = Number(lead.lead_score || lead.score || lead.pillars_total || 0);
    const isHigh = score >= 80;

    const pLeg = Math.round(((lead.score_legitimacy || 0) / 25) * 100);
    const pVel = Math.round(((lead.score_velocity || 0) / 25) * 100);
    const pTurn = Math.round(((lead.score_turnover || 0) / 30) * 100);
    const pBud = Math.round(((lead.score_budget || 0) / 20) * 100);

    const pillarKey = getLeadPillarKey(lead);
    const pillarName = formatPillar(pillarKey);
    const tierName = getLeadTier(lead);
    const tierClass = tierName.toLowerCase().replace(' ', '-');

    const comm = lead.estimated_commercials || {};
    const unitsMin = (comm.est_monthly_units_min || 500).toLocaleString('id-ID');
    const unitsMax = (comm.est_monthly_units_max || 1500).toLocaleString('id-ID');
    const painPoints = lead.packaging_pain_points || lead.service_pain_points || [];
    const hasPainPoints = painPoints.length > 0;

    const clusterText = lead.sales_cluster || lead.district_area || 'Makassar Kota';

    const statusText = lead.outreach_status || 'Belum Dihubungi';
    let statusBadgeClass = 'uncontacted';
    if (statusText === 'Dihubungi') statusBadgeClass = 'contacted';
    else if (statusText === 'Tertarik') statusBadgeClass = 'interested';
    else if (statusText === 'Closing') statusBadgeClass = 'closing';
    else if (statusText === 'Tidak Relevan') statusBadgeClass = 'irrelevant';

    const notes = lead.outreach_notes || lead.sales_notes || '';
    const notesSnippet = notes
      ? `<div style="font-size: 11px; color: var(--text-muted); margin-top: 4px; font-style: italic; max-width: 150px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="${escapeHtml(notes)}">${escapeHtml(notes)}</div>`
      : '';

    const waDisplay = lead.whatsapp_number
      ? `<div class="wa-verified-tag">
          <svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="20 6 9 17 4 12"/></svg>
          <span>WA: ${escapeHtml(lead.whatsapp_number)}</span>
         </div>`
      : (lead.phone_number ? `<div style="font-size: 11px; color: var(--text-muted); margin-top: 3px;">Tel: ${escapeHtml(lead.phone_number)}</div>` : '');

    tr.innerHTML = `
      <td>
        <div class="lead-title-text">${escapeHtml(lead.business_name)}</div>
        <div class="lead-address-text">${escapeHtml(lead.address_full || 'Makassar')}</div>
        <div class="maps-rating-text" style="margin-top: 4px;">Rating ${lead.rating || '4.5'} (${lead.reviews_count || 0} ulasan GMaps)</div>
        ${waDisplay}
      </td>
      <td>
        <div style="display: flex; flex-direction: column; gap: 4px; align-items: flex-start;">
          <span class="category-tag">${escapeHtml(formatCategory(lead.target_sector || lead.category))}</span>
          <span class="pillar-badge ${pillarKey}">${escapeHtml(pillarName)}</span>
        </div>
      </td>
      <td>
        <div style="display: flex; flex-direction: column; gap: 4px; align-items: flex-start;">
          <span class="tier-tag ${tierClass}">${escapeHtml(tierName)}</span>
          <span class="status-badge ${statusBadgeClass}">${escapeHtml(statusText)}</span>
        </div>
        ${notesSnippet}
      </td>
      <td>
        <div class="comm-tier-badge ${tierClass === 'tier-a' ? 'tier-1' : ''}">${escapeHtml(clusterText)}</div>
        <div class="comm-units-text">${unitsMin} - ${unitsMax} unit/bln</div>
        ${hasPainPoints ? `<span class="pain-point-pill warning">${painPoints.length} Keluhan Mutu</span>` : `<span class="pain-point-pill ok">Mutu Terjaga</span>`}
      </td>
      <td>
        <div class="table-score-wrapper">
          <div class="table-score-header">
            <span>Potensi</span>
            <span class="table-score-num ${isHigh ? 'high' : ''}">${score} / 100</span>
          </div>
          <div class="table-pillar-pills" title="Legitimasi: ${lead.score_legitimacy || 0}/25 | Kecepatan: ${lead.score_velocity || 0}/25 | Turnover: ${lead.score_turnover || 0}/30 | Anggaran: ${lead.score_budget || 0}/20">
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
  const lead = allLeads.find(l => l.id === id || l.entity_id === id);
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
        <div class="pp-empty-title">Kemasan & Mutu Percetakan Terpantau Stabil</div>
        <div class="pp-empty-desc">Tidak ditemukan keluhan kerusakan kemasan atau keterlambatan cetak pada ulasan publik. Konsumen puas dengan mutu pengemasan saat ini.</div>
      </div>
    `;
    return;
  }

  painPoints.forEach((pp, idx) => {
    const card = document.createElement('div');
    card.className = 'pain-point-card';

    const kws = pp.detected_keywords || pp.keywords || [];
    const kwBadges = kws.map(k => `<span class="pp-kw-badge">${escapeHtml(k)}</span>`).join(' ');
    const reviewSnippet = pp.review_text || pp.snippet || pp.text || 'Ulasan pelanggan terkait mutu fisik kemasan.';
    const salesAngle = pp.sales_angle || 'Tawarkan solusi cetak presisi dan kemasan berstandar mutu RUANG VISUAL.';

    card.innerHTML = `
      <div class="pp-card-header">
        <span class="pp-badge-alert">Keluhan #${idx + 1} &bull; Rating ${pp.rating || '-'}/5</span>
        <span class="pp-date">${escapeHtml(pp.date || 'Ulasan Terkini')}</span>
      </div>
      <div class="pp-review-text">"${escapeHtml(reviewSnippet)}"</div>
      <div class="pp-keywords-row">
        <span class="pp-kw-label">Kata Kunci:</span>
        <div>${kwBadges || '<span class="pp-kw-badge">Mutu Cetak</span>'}</div>
      </div>
      <div class="pp-angle-box">
        <div class="pp-angle-title">Sudut Pendekatan Penjualan (Sales Angle):</div>
        <div class="pp-angle-text">${escapeHtml(salesAngle)}</div>
      </div>
    `;
    container.appendChild(card);
  });
}

function renderReviewSnippets(snippets) {
  const container = document.getElementById('drawer-review-snippets-list');
  if (!container) return;
  container.innerHTML = '';

  if (!snippets || snippets.length === 0) {
    container.innerHTML = `
      <div style="font-size: 12px; color: var(--text-muted); padding: 14px; background: #f8fafc; border-radius: 6px; border: 1px solid var(--border-subtle); line-height: 1.5;">
        Belum ada sampel teks ulasan langsung yang diimpor ke profil dossier ini. Data ulasan agregat Google Maps tetap aktif.
      </div>
    `;
    return;
  }

  snippets.forEach((item, idx) => {
    const div = document.createElement('div');
    div.className = 'review-snippet-item';
    
    let text = '';
    let author = 'Pelanggan Google Maps';
    let rating = '5.0';
    let date = '';

    if (typeof item === 'string') {
      text = item;
    } else if (typeof item === 'object') {
      text = item.text || item.snippet || item.comment || '';
      author = item.author_name || item.author || author;
      rating = item.rating ? `${item.rating}.0` : rating;
      date = item.date || item.relative_time || '';
    }

    div.innerHTML = `
      <div class="review-snippet-meta">
        <span class="review-snippet-author">${escapeHtml(author)}</span>
        <span class="review-snippet-stars">Rating ${rating}</span>
        ${date ? `<span class="review-snippet-date">${escapeHtml(date)}</span>` : ''}
      </div>
      <div class="review-snippet-text">"${escapeHtml(text)}"</div>
    `;
    container.appendChild(div);
  });
}

function openDrawer(lead) {
  selectedLead = lead;

  // Reset Input handle
  const handleInputEl = document.getElementById('link-handle-input');
  if (handleInputEl) handleInputEl.value = '';

  // Header meta badges
  const sectorName = formatCategory(lead.target_sector || lead.category);
  const pillarKey = getLeadPillarKey(lead);
  const pillarName = formatPillar(pillarKey);
  const tierName = getLeadTier(lead);

  const secBadge = document.getElementById('drawer-sector-badge');
  if (secBadge) secBadge.textContent = sectorName;

  const pilBadge = document.getElementById('drawer-pillar-badge');
  if (pilBadge) {
    pilBadge.textContent = pillarName;
    pilBadge.className = `drawer-badge-pill pillar pillar-badge ${pillarKey}`;
  }

  const tierBadge = document.getElementById('drawer-tier-badge');
  if (tierBadge) {
    tierBadge.textContent = tierName;
    tierBadge.className = `drawer-badge-pill tier tier-tag ${tierName.toLowerCase().replace(' ', '-')}`;
  }

  document.getElementById('drawer-title').textContent = lead.business_name || 'Detail Calon Customer';

  // TAB 1: Kontak & Lokasi
  const waTextEl = document.getElementById('drawer-wa-number-text');
  if (waTextEl) {
    if (lead.whatsapp_number) {
      const isVal = lead.is_active_verified || lead.is_wa_valid;
      waTextEl.textContent = `WhatsApp: ${lead.whatsapp_number} ${isVal ? '(Terverifikasi Aktif)' : ''}`;
    } else if (lead.phone_number) {
      waTextEl.textContent = `Telepon Bisnis: ${lead.phone_number}`;
    } else {
      waTextEl.textContent = 'WhatsApp: Belum Tercatat';
    }
  }

  const clusterEl = document.getElementById('drawer-cluster');
  if (clusterEl) {
    clusterEl.textContent = `Cluster Rute: ${lead.sales_cluster || lead.district_area || 'Makassar Kota'}`;
  }

  const addrEl = document.getElementById('drawer-address');
  if (addrEl) {
    addrEl.textContent = lead.address_full || 'Alamat fisik belum tercatat';
  }

  const ratingEl = document.getElementById('drawer-rating');
  if (ratingEl) {
    ratingEl.textContent = `Rating ${lead.rating || '4.5'}`;
  }

  const revEl = document.getElementById('drawer-reviews');
  if (revEl) {
    revEl.textContent = `${lead.reviews_count || 0} Ulasan GMaps`;
  }

  const mapsLink = document.getElementById('drawer-maps-link');
  if (mapsLink) {
    const gmapsUrl = (lead.channels && lead.channels.google_maps)
      ? lead.channels.google_maps
      : (lead.google_maps_place_id ? `https://maps.google.com/?cid=${lead.google_maps_place_id}` : '');
    if (gmapsUrl) {
      mapsLink.href = gmapsUrl;
      mapsLink.style.display = 'inline-block';
    } else {
      mapsLink.style.display = 'none';
    }
  }

  // Pitch & WhatsApp Button
  const pitchArea = document.getElementById('drawer-pitch-text');
  const waBtn = document.getElementById('drawer-wa-button');
  const copyToast = document.getElementById('drawer-copy-feedback');
  if (copyToast) copyToast.style.display = 'none';

  const pitchText = lead.pitch_text || lead.whatsapp_pitch || '';
  if (pitchArea) pitchArea.value = pitchText;

  const waSection = document.getElementById('drawer-wa-section');
  if (pitchText) {
    if (waSection) waSection.style.display = 'flex';
    const waLink = lead.wa_link || (lead.whatsapp_number ? `https://wa.me/${lead.whatsapp_number}?text=${encodeURIComponent(pitchText)}` : '');
    if (waBtn) {
      if (waLink) {
        waBtn.href = waLink;
        waBtn.style.display = 'inline-block';
      } else {
        waBtn.style.display = 'none';
      }
    }
  } else {
    if (waSection) waSection.style.display = 'none';
  }

  // Outreach Status & Notes
  const outreachSelect = document.getElementById('drawer-outreach-select');
  const outreachNotes = document.getElementById('drawer-outreach-notes');
  const outreachFeedback = document.getElementById('drawer-outreach-feedback');
  const outreachTimestamp = document.getElementById('drawer-outreach-timestamp');

  if (outreachSelect) outreachSelect.value = lead.outreach_status || 'Belum Dihubungi';
  if (outreachNotes) outreachNotes.value = lead.outreach_notes || lead.sales_notes || '';
  if (outreachFeedback) outreachFeedback.style.display = 'none';

  if (outreachTimestamp) {
    if (lead.contacted_at) {
      const d = new Date(lead.contacted_at);
      const formatted = isNaN(d.getTime()) ? lead.contacted_at : d.toLocaleString('id-ID', {
        day: 'numeric',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      });
      outreachTimestamp.textContent = `Terakhir dihubungi: ${formatted}`;
      outreachTimestamp.style.display = 'block';
    } else {
      outreachTimestamp.style.display = 'none';
    }
  }

  // TAB 2: Intelijen & Order
  const totalScore = Number(lead.lead_score || lead.score || lead.pillars_total || 0);
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

  document.getElementById('drawer-reason-summary').textContent = lead.reason_summary || 'Perhitungan skor didasarkan pada formula 4 dimensi Meta Universal: Legitimasi, Kecepatan, Turnover, dan Anggaran.';

  // Commercial Estimates
  const comm = lead.estimated_commercials || {};
  const commTierEl = document.getElementById('drawer-comm-tier');
  if (commTierEl) commTierEl.textContent = tierName;
  const commCycleEl = document.getElementById('drawer-comm-cycle');
  if (commCycleEl) commCycleEl.textContent = `Siklus: ${comm.restock_cycle_days || 30} Hari`;

  const minU = (comm.est_monthly_units_min || 500).toLocaleString('id-ID');
  const maxU = (comm.est_monthly_units_max || 1500).toLocaleString('id-ID');
  const commUnitsEl = document.getElementById('drawer-comm-units');
  if (commUnitsEl) commUnitsEl.textContent = `${minU} - ${maxU} Unit`;

  const orderVal = comm.est_monthly_value_min_idr || lead.est_order_value_idr || 0;
  const commValEl = document.getElementById('drawer-comm-value');
  if (commValEl) commValEl.textContent = formatRupiahShort(orderVal);

  // Recommendations
  const prodsList = document.getElementById('drawer-solution-products');
  prodsList.innerHTML = '';
  let recs = lead.recommended_products || [];
  if (typeof recs === 'string') {
    recs = recs.split(',').map(s => s.trim()).filter(Boolean);
  }
  if (!Array.isArray(recs) || recs.length === 0) {
    recs = ['Kemasan & Media Promosi Standar RUANG VISUAL'];
  }
  recs.forEach(p => {
    const li = document.createElement('li');
    li.textContent = p;
    prodsList.appendChild(li);
  });

  document.getElementById('drawer-solution-specs').textContent = lead.materials_finishing || 'Standar spesifikasi material RUANG VISUAL sesuai jenis usaha.';
  document.getElementById('drawer-solution-value').textContent = lead.value_proposition || 'Kualitas cetak presisi, pengiriman tepat waktu di area Makassar, dan harga bersahabat.';

  // TAB 3: Ulasan & Mutu
  const tab3RatingEl = document.getElementById('drawer-tab3-rating');
  if (tab3RatingEl) tab3RatingEl.textContent = `${lead.rating || '4.5'} / 5.0`;
  const tab3RevCountEl = document.getElementById('drawer-tab3-reviews-count');
  if (tab3RevCountEl) tab3RevCountEl.textContent = `Berdasarkan ${lead.reviews_count || 0} ulasan Google Maps`;

  const tab3MapsLink = document.getElementById('drawer-tab3-maps-link');
  if (tab3MapsLink) {
    const gmapsUrl = (lead.channels && lead.channels.google_maps)
      ? lead.channels.google_maps
      : (lead.google_maps_place_id ? `https://maps.google.com/?cid=${lead.google_maps_place_id}` : '');
    if (gmapsUrl) {
      tab3MapsLink.href = gmapsUrl;
      tab3MapsLink.style.display = 'inline-block';
    } else {
      tab3MapsLink.style.display = 'none';
    }
  }

  renderPainPointsList(lead.packaging_pain_points || lead.service_pain_points || []);

  let rawSnippets = lead.review_snippets || lead.review_snippets_json || lead.review_samples || [];
  if (typeof rawSnippets === 'string') {
    try { rawSnippets = JSON.parse(rawSnippets); } catch (e) { rawSnippets = []; }
  }
  renderReviewSnippets(rawSnippets);

  // TAB 4: Jejak Multi-Kanal
  renderChannelsList(lead);
  renderDrawerPosts(lead.top_posts || []);

  // Default active tab: Tab 1 (Kontak & Pitch)
  switchDrawerTab('tab-outreach');

  // Open modal
  document.getElementById('overlay').style.display = 'block';
  document.getElementById('detail-drawer').classList.add('open');
}

async function copyWhatsAppPitch() {
  const pitchArea = document.getElementById('drawer-pitch-text');
  const feedback = document.getElementById('drawer-copy-feedback');
  if (!pitchArea || !pitchArea.value) return;

  try {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      await navigator.clipboard.writeText(pitchArea.value);
    } else {
      pitchArea.select();
      document.execCommand('copy');
    }
    if (feedback) {
      feedback.style.display = 'inline-block';
      setTimeout(() => {
        if (feedback) feedback.style.display = 'none';
      }, 3000);
    }
  } catch (err) {
    console.error('Gagal menyalin teks pitch:', err);
  }
}

async function saveLeadOutreachStatus() {
  if (!selectedLead) return;
  const statusSelect = document.getElementById('drawer-outreach-select');
  const notesInput = document.getElementById('drawer-outreach-notes');
  const feedback = document.getElementById('drawer-outreach-feedback');
  const outreachTimestamp = document.getElementById('drawer-outreach-timestamp');

  const newStatus = statusSelect.value;
  const newNotes = notesInput.value.trim();

  try {
    const res = await fetch('/api/leads/update-status', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        lead_id: selectedLead.id || selectedLead.entity_id,
        status: newStatus,
        notes: newNotes
      })
    });

    if (!res.ok) throw new Error('Gagal menyimpan status penjangkauan');
    await res.json();

    selectedLead.outreach_status = newStatus;
    selectedLead.outreach_notes = newNotes;
    selectedLead.sales_notes = newNotes;

    const idx = allLeads.findIndex(l => (l.id === selectedLead.id || l.entity_id === selectedLead.id));
    if (idx !== -1) {
      allLeads[idx].outreach_status = newStatus;
      allLeads[idx].outreach_notes = newNotes;
      allLeads[idx].sales_notes = newNotes;
    }

    if (newStatus === 'Dihubungi' || newStatus === 'Closing') {
      const nowIso = new Date().toISOString();
      selectedLead.contacted_at = nowIso;
      if (idx !== -1) allLeads[idx].contacted_at = nowIso;
      if (outreachTimestamp) {
        outreachTimestamp.textContent = 'Terakhir dihubungi: Baru saja';
        outreachTimestamp.style.display = 'block';
      }
    }

    if (feedback) {
      feedback.textContent = 'Status penjangkauan berhasil diperbarui.';
      feedback.style.color = '#0284C7';
      feedback.style.display = 'block';
      setTimeout(() => { if (feedback) feedback.style.display = 'none'; }, 3000);
    }

    renderDashboard();
  } catch (err) {
    console.error('Error saving outreach status:', err);
    if (feedback) {
      feedback.textContent = 'Gagal menyimpan status penjangkauan.';
      feedback.style.color = '#E11D48';
      feedback.style.display = 'block';
    }
  }
}

function closeDrawer() {
  document.getElementById('overlay').style.display = 'none';
  document.getElementById('detail-drawer').classList.remove('open');
}

function renderChannelsList(lead) {
  const container = document.getElementById('drawer-channels-list');
  if (!container) return;
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
    const val = channels[ch.key] || (ch.key === 'instagram' ? lead.instagram_handle : (ch.key === 'tiktok' ? lead.tiktok_handle : ''));
    const isLinked = Boolean(val && String(val).trim() !== '');

    let linkHtml = 'Belum Terhubung';
    if (isLinked) {
      let targetUrl = String(val).trim();
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
  if (!container) return;
  container.innerHTML = '';

  if (!posts || posts.length === 0) {
    container.innerHTML = `
      <div style="font-size: 12px; color: var(--text-muted); background: #F8FAFC; padding: 14px; border-radius: 6px; border: 1px solid var(--border-subtle); line-height: 1.5;">
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
        <span>Konten #${idx + 1} &bull; ${escapeHtml(post.date || 'Terkini')}</span>
        <div>${tagsHtml}</div>
      </div>
      <div class="dpi-caption">${escapeHtml(post.caption || '')}</div>
      <div class="dpi-stats">
        <span>Views: ${(post.views || 0).toLocaleString()}</span>
        <span>Likes: ${(post.likes || 0).toLocaleString()}</span>
        <span>Komentar: ${(post.comments || 0).toLocaleString()}</span>
        <span>ER: ${post.engagement_rate || 0}%</span>
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
        lead_id: selectedLead.id || selectedLead.entity_id,
        platform: platform,
        handle_or_url: handleInput
      })
    });

    if (!res.ok) throw new Error('Gagal menghubungkan kanal sosial.');
    const result = await res.json();

    const updatedLead = result.lead;
    const idx = allLeads.findIndex(l => (l.id === updatedLead.id || l.entity_id === updatedLead.id));
    if (idx !== -1) {
      allLeads[idx] = updatedLead;
    }

    selectedLead = updatedLead;
    document.getElementById('link-handle-input').value = '';

    renderDashboard();
    openDrawer(updatedLead);

    alert(`Kanal ${platform} berhasil dihubungkan.`);
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
    document.getElementById('ins-result-views').textContent = (data.total_views || 0).toLocaleString();
    document.getElementById('ins-result-eng').textContent = `${data.avg_engagement_rate || 0}%`;
    document.getElementById('ins-result-signals').textContent = `${data.packaging_intent_posts || 0} Konten`;

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
            <span>${escapeHtml(post.date || '')}</span>
          </div>
          <div class="post-caption">${escapeHtml(post.caption || '')}</div>
          <div class="post-stats-row">
            <span>Views: ${(post.views || 0).toLocaleString()}</span>
            <span>Likes: ${(post.likes || 0).toLocaleString()}</span>
            <span>Komentar: ${(post.comments || 0).toLocaleString()}</span>
          </div>
          <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 6px;">
            <span style="font-size: 11px; font-weight: 700; color: var(--text-muted);">ER: ${post.engagement_rate || 0}%</span>
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
      <span class="cat-badge">${escapeHtml(formatPillar(cat.category) !== 'Promosi & Cetak' ? formatPillar(cat.category) : formatCategory(cat.category))}</span>
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
  if (!cat) return 'Umum';
  const map = {
    fnb_beverage: 'Coffee & Beverage',
    fnb_food_resto: 'Food & Restoran',
    fnb_hospitality: 'Hotel & Hospitality',
    fashion_retail: 'Fashion & Butik',
    retail_apparel: 'Retail & Pakaian',
    beauty_skincare: 'Beauty & Skincare',
    new_store_opening: 'Grand Opening',
    corporate_legal: 'Notaris & Korporat',
    education: 'Institusi Pendidikan',
    event_community: 'Event & Komunitas',
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
const catSelect = document.getElementById('filter-category');
if (catSelect) {
  catSelect.addEventListener('change', () => {
    currentPage = 1;
    renderDashboard();
  });
}

const pillarSelect = document.getElementById('filter-pillar');
if (pillarSelect) {
  pillarSelect.addEventListener('change', () => {
    currentPage = 1;
    renderDashboard();
  });
}

const tierSelect = document.getElementById('filter-tier');
if (tierSelect) {
  tierSelect.addEventListener('change', () => {
    currentPage = 1;
    renderDashboard();
  });
}

const outreachSelect = document.getElementById('filter-outreach');
if (outreachSelect) {
  outreachSelect.addEventListener('change', (e) => {
    currentOutreachFilter = e.target.value;
    updatePipelinePillActive(currentOutreachFilter);
    currentPage = 1;
    renderDashboard();
  });
}

const searchInput = document.getElementById('search-input');
if (searchInput) {
  searchInput.addEventListener('input', () => {
    currentPage = 1;
    renderDashboard();
  });
}

const exportCsvBtn = document.getElementById('btn-export-csv');
if (exportCsvBtn) {
  exportCsvBtn.addEventListener('click', () => {
    window.location.href = '/api/export/csv';
  });
}

const exportCsvFullBtn = document.getElementById('btn-export-csv-full');
if (exportCsvFullBtn) {
  exportCsvFullBtn.addEventListener('click', () => {
    window.location.href = '/api/export/csv-full';
  });
}

// Initial Load
fetchLeads();
