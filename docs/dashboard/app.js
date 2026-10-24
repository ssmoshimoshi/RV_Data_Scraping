let allLeads = [];

async function fetchLeads() {
  try {
    const res = await fetch('/api/leads');
    if (!res.ok) throw new Error('Failed to load leads API');
    allLeads = await res.json();
    renderDashboard();
  } catch (err) {
    console.error('Error fetching leads:', err);
  }
}

function renderDashboard() {
  const catFilter = document.getElementById('filter-category').value;
  const platformFilter = document.getElementById('filter-platform').value;
  const searchFilter = document.getElementById('search-input').value.toLowerCase();

  const filtered = allLeads.filter(lead => {
    if (catFilter !== 'all' && lead.category !== catFilter) return false;
    if (platformFilter !== 'all' && lead.platform !== platformFilter) return false;
    if (searchFilter && !lead.business_name.toLowerCase().includes(searchFilter) && !(lead.address_full || '').toLowerCase().includes(searchFilter)) {
      return false;
    }
    return true;
  });

  // Update Metrics
  document.getElementById('metric-total').textContent = filtered.length;
  document.getElementById('metric-hot').textContent = filtered.filter(l => l.score >= 80).length;
  document.getElementById('metric-wa').textContent = filtered.filter(l => l.whatsapp_number).length;
  document.getElementById('metric-products').textContent = filtered.filter(l => (l.recommended_products || []).length > 0).length;

  // Clear Columns
  const cols = {
    new_lead: document.getElementById('list-new_lead'),
    ready_to_pitch: document.getElementById('list-ready_to_pitch'),
    outreach: document.getElementById('list-outreach'),
    won_deal: document.getElementById('list-won_deal')
  };

  const counts = {
    new_lead: 0,
    ready_to_pitch: 0,
    outreach: 0,
    won_deal: 0
  };

  Object.values(cols).forEach(col => col.innerHTML = '');

  filtered.forEach(lead => {
    let colKey = 'new_lead';
    if (lead.status === 'won_deal') {
      colKey = 'won_deal';
    } else if (['sample_box_requested', 'quotation_sent'].includes(lead.status)) {
      colKey = 'outreach';
    } else if (lead.status === 'ready_to_pitch') {
      colKey = 'ready_to_pitch';
    }

    counts[colKey]++;

    const card = document.createElement('div');
    card.className = 'lead-card';
    card.onclick = () => openDrawer(lead);

    const isHigh = lead.score >= 80;
    const prods = (lead.recommended_products || []).slice(0, 2).join(', ');

    card.innerHTML = `
      <div class="card-top">
        <span class="card-name">${escapeHtml(lead.business_name)}</span>
        <span class="score-badge ${isHigh ? 'high' : ''}">${lead.score} pts</span>
      </div>
      <div class="card-category">${formatCategory(lead.category)} &bull; ${lead.platform}</div>
      <div class="card-products">${escapeHtml(prods || 'Kebutuhan cetak terpetakan')}</div>
      <div class="card-actions">
        ${lead.wa_link ? `<a href="${lead.wa_link}" target="_blank" class="btn-wa" onclick="event.stopPropagation()">Chat WhatsApp</a>` : ''}
        <button class="btn-detail" onclick="event.stopPropagation(); openDrawerById('${lead.id}')">Detail</button>
      </div>
    `;

    cols[colKey].appendChild(card);
  });

  document.getElementById('count-new_lead').textContent = counts.new_lead;
  document.getElementById('count-ready_to_pitch').textContent = counts.ready_to_pitch;
  document.getElementById('count-outreach').textContent = counts.outreach;
  document.getElementById('count-won_deal').textContent = counts.won_deal;
}

function openDrawerById(id) {
  const lead = allLeads.find(l => l.id === id);
  if (lead) openDrawer(lead);
}

function openDrawer(lead) {
  document.getElementById('drawer-title').textContent = lead.business_name;
  document.getElementById('drawer-address').textContent = lead.address_full || 'Alamat fisik belum terdata';
  
  const prodsList = (lead.recommended_products || []).map(p => `&bull; ${p}`).join('<br>');
  document.getElementById('drawer-products').innerHTML = `
    <strong>Produk Rekomendasi:</strong><br>${prodsList || '-'}<br><br>
    <strong>Spesifikasi & Finishing:</strong><br>${escapeHtml(lead.materials_finishing || '-')}<br><br>
    <strong>Value Proposition:</strong><br>${escapeHtml(lead.value_proposition || '-')}
  `;

  document.getElementById('drawer-pitch').value = lead.pitch_text || 'Nomor WhatsApp belum tersedia untuk menyusun pitch otomatis.';
  
  const waBtn = document.getElementById('drawer-wa-btn');
  if (lead.wa_link) {
    waBtn.href = lead.wa_link;
    waBtn.style.display = 'block';
  } else {
    waBtn.style.display = 'none';
  }

  document.getElementById('overlay').style.display = 'block';
  document.getElementById('detail-drawer').classList.add('open');
}

function closeDrawer() {
  document.getElementById('overlay').style.display = 'none';
  document.getElementById('detail-drawer').classList.remove('open');
}

function formatCategory(cat) {
  const map = {
    fnb_beverage: 'Coffee & Drink',
    fnb_food_resto: 'Food & Resto',
    fashion_retail: 'Fashion & Retail',
    beauty_skincare: 'Beauty & Skincare',
    new_store_opening: 'Grand Opening',
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

document.getElementById('filter-category').addEventListener('change', renderDashboard);
document.getElementById('filter-platform').addEventListener('change', renderDashboard);
document.getElementById('search-input').addEventListener('input', renderDashboard);

fetchLeads();
