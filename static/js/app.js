/**
 * Income × Housing Dashboard — Frontend Client v2
 */

(function () {
  'use strict';

  // ──────────────── State (Single Client Store) ────────────────
  const state = {
    tab: 1,
    year: 2568,
    y0: 2554,
    y1: 2568,
    region: null,
    area: 0,
    pt: 1,
    metric: 'income',
    grain: 'yearly',
    cagr_view: 'by_region',
    theme: document.documentElement.getAttribute('data-theme') || 'dark',
    meta: null,
    tabData: null,
  };

  let fetchTimeout = null;

  const REGION_COLORS = {
    0: '#8FA0BC',
    1: '#2F6BFF',
    2: '#18B8D8',
    3: '#8B7CF6',
    4: '#F5A524',
    5: '#FF7A1A',
  };

  // ──────────────── SVG Lucide Icons (Inline, No Emojis) ────────────────
  const ICONS = {
    wallet: `<svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 7V4a1 1 0 0 0-1-1H5a2 2 0 0 0 0 4h15a1 1 0 0 1 1 1v4h-3a2 2 0 0 0 0 4h3a1 1 0 0 0 1-1v-2a1 1 0 0 0-1-1"/><path d="M3 5v14a2 2 0 0 0 2 2h15a1 1 0 0 0 1-1v-4"/></svg>`,
    house: `<svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M15 21v-8a1 1 0 0 0-1-1h-4a1 1 0 0 0-1 1v8"/><path d="M3 10a2 2 0 0 1 .709-1.528l7-5.999a2 2 0 0 1 2.582 0l7 5.999A2 2 0 0 1 21 10v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/></svg>`,
    scale: `<svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="m16 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="m2 16 3-8 3 8c-.87.65-1.92 1-3 1s-2.13-.35-3-1Z"/><path d="M7 21h10"/><path d="M12 3v18"/><path d="M3 7h2c2 0 5-1 7-2 2 1 5 2 7 2h2"/></svg>`,
    info: `<svg class="nav-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="10"/><path d="M12 16v-4"/><path d="M12 8h.01"/></svg>`,
    sun: `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="12" r="4"/><path d="M12 2v2"/><path d="M12 20v2"/><path d="m4.93 4.93 1.41 1.41"/><path d="m17.66 17.66 1.41 1.41"/><path d="M2 12h2"/><path d="M20 12h2"/><path d="m6.34 17.66-1.41 1.41"/><path d="m19.07 4.93-1.41 1.41"/></svg>`,
    moon: `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z"/></svg>`,
    rotateCcw: `<svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/></svg>`,
    trendingUp: `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="22 7 13.5 15.5 8.5 10.5 2 17"/><polyline points="16 7 22 7 22 13"/></svg>`,
    trendingDown: `<svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="22 17 13.5 8.5 8.5 13.5 2 7"/><polyline points="16 17 22 17 22 11"/></svg>`,
    barChart: `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><line x1="12" y1="20" x2="12" y2="10"/><line x1="18" y1="20" x2="18" y2="4"/><line x1="6" y1="20" x2="6" y2="16"/></svg>`,
    activity: `<svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.75" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/></svg>`,
  };

  // ──────────────── URL Sync ────────────────
  function readUrlParams() {
    const params = new URLSearchParams(window.location.search);
    if (params.has('tab')) state.tab = parseInt(params.get('tab'), 10);
    if (params.has('year')) state.year = parseInt(params.get('year'), 10);
    if (params.has('y0')) state.y0 = parseInt(params.get('y0'), 10);
    if (params.has('y1')) state.y1 = parseInt(params.get('y1'), 10);
    if (params.has('region')) state.region = params.get('region') === '' ? null : parseInt(params.get('region'), 10);
    if (params.has('area')) state.area = parseInt(params.get('area'), 10);
    if (params.has('pt')) state.pt = parseInt(params.get('pt'), 10);
    if (params.has('metric')) state.metric = params.get('metric');
    if (params.has('grain')) state.grain = params.get('grain');
    if (params.has('cagr_view')) state.cagr_view = params.get('cagr_view');
    if (params.has('theme')) state.theme = params.get('theme');
  }

  function updateUrl() {
    const params = new URLSearchParams();
    params.set('tab', state.tab);
    params.set('year', state.year);
    params.set('y0', state.y0);
    params.set('y1', state.y1);
    if (state.region !== null) params.set('region', state.region);
    if (state.tab === 1) {
      params.set('area', state.area);
      params.set('metric', state.metric);
    }
    if (state.tab === 2 || state.tab === 3) {
      params.set('pt', state.pt);
    }
    if (state.tab === 2) {
      params.set('grain', state.grain);
      params.set('metric', state.metric);
    }
    if (state.tab === 3) {
      params.set('cagr_view', state.cagr_view);
    }
    params.set('theme', state.theme);
    window.history.replaceState({}, '', `${window.location.pathname}?${params.toString()}`);
  }

  function hasNonDefaultFilters() {
    if (state.region !== null) return true;
    if (state.year !== 2568) return true;
    if (state.y0 !== 2554 || state.y1 !== 2568) return true;
    if (state.tab === 1 && (state.area !== 0 || state.metric !== 'income')) return true;
    if (state.tab === 2 && (state.pt !== 1 || state.grain !== 'yearly' || state.metric !== 'hpi')) return true;
    if (state.tab === 3 && (state.pt !== 1 || state.cagr_view !== 'by_region')) return true;
    return false;
  }

  // ──────────────── Theme Handling ────────────────
  function initTheme() {
    const saved = localStorage.getItem('ihd-theme');
    if (saved) {
      state.theme = saved;
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: light)').matches) {
      state.theme = 'light';
    } else {
      state.theme = 'dark';
    }
    applyTheme(state.theme);

    const toggleBtn = document.getElementById('theme-toggle-btn');
    if (toggleBtn) {
      toggleBtn.addEventListener('click', () => {
        state.theme = state.theme === 'dark' ? 'light' : 'dark';
        applyTheme(state.theme);
        updateUrl();
        queueFetch();
      });
    }
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('ihd-theme', theme);
    const toggleBtn = document.getElementById('theme-toggle-btn');
    if (toggleBtn) {
      toggleBtn.innerHTML = theme === 'dark' ? ICONS.sun : ICONS.moon;
      toggleBtn.setAttribute('aria-label', theme === 'dark' ? 'สลับเป็นโหมดสว่าง' : 'สลับเป็นโหมดมืด');
    }
  }

  // ──────────────── API Fetching ────────────────
  async function fetchMeta() {
    try {
      const res = await fetch('/api/meta');
      if (!res.ok) throw new Error('Failed to load meta');
      state.meta = await res.json();
      renderAsOfBadge();
      renderControlBar();
    } catch (err) {
      console.error(err);
    }
  }

  function queueFetch() {
    if (fetchTimeout) clearTimeout(fetchTimeout);
    fetchTimeout = setTimeout(fetchTabData, 100);
  }

  async function fetchTabData() {
    const params = new URLSearchParams();
    params.set('year', state.year);
    params.set('y0', state.y0);
    params.set('y1', state.y1);
    if (state.region !== null) params.set('region', state.region);
    params.set('area', state.area);
    params.set('pt', state.pt);
    params.set('metric', state.metric);
    params.set('grain', state.grain);
    params.set('cagr_view', state.cagr_view);
    params.set('theme', state.theme);

    try {
      const res = await fetch(`/api/tab/${state.tab}?${params.toString()}`);
      if (!res.ok) {
        const errData = await res.json();
        alert(errData.detail || 'เกิดข้อผิดพลาดในการดึงข้อมูล');
        return;
      }
      state.tabData = await res.json();
      renderDashboard();
    } catch (err) {
      console.error('Fetch error:', err);
    }
  }

  // ──────────────── Render Methods ────────────────
  function renderAsOfBadge() {
    const badge = document.getElementById('as-of-badge');
    if (badge && state.meta && state.meta.as_of) {
      badge.textContent = `ข้อมูลล่าสุด: สสช. ${state.meta.as_of.income_latest_wave} · ธปท. ${state.meta.as_of.hpi_latest_month}`;
    }
  }

  function renderControlBar() {
    const container = document.getElementById('control-bar');
    if (!container || !state.meta) return;

    container.innerHTML = '';

    const leftCol = document.createElement('div');
    leftCol.className = 'control-bar-left';

    // 1. Region Radio Chips with color dots
    const regionGroup = document.createElement('div');
    regionGroup.className = 'control-group';
    regionGroup.innerHTML = `
      <span class="control-label">ภูมิภาค:</span>
      <div class="region-chips" role="radiogroup">
        <button class="region-chip ${state.region === null ? 'active' : ''}" data-region="null" role="radio" aria-checked="${state.region === null}">
          <span class="region-dot" style="background-color: ${REGION_COLORS[0]}"></span>
          <span>ทั้งประเทศ</span>
        </button>
        ${state.meta.regions.filter(r => r.region_id > 0).map(r => `
          <button class="region-chip ${state.region === r.region_id ? 'active' : ''}" data-region="${r.region_id}" role="radio" aria-checked="${state.region === r.region_id}" style="${state.region === r.region_id ? `background-color: ${REGION_COLORS[r.region_id]}26; border-color: ${REGION_COLORS[r.region_id]}` : ''}">
            <span class="region-dot" style="background-color: ${REGION_COLORS[r.region_id]}"></span>
            <span>${r.short_th}</span>
          </button>
        `).join('')}
      </div>
    `;
    leftCol.appendChild(regionGroup);

    regionGroup.querySelectorAll('.region-chip').forEach(btn => {
      btn.onclick = () => {
        const targetReg = btn.dataset.region === 'null' ? null : parseInt(btn.dataset.region, 10);
        state.region = (state.region === targetReg && targetReg !== null) ? null : targetReg;
        updateUrl();
        renderControlBar();
        queueFetch();
      };
    });

    // 2. Year Selection
    if (state.tab === 1 || state.tab === 2) {
      const yearGroup = document.createElement('div');
      yearGroup.className = 'control-group';
      const years = state.tab === 1 ? state.meta.income_years : state.meta.hpi_years;
      yearGroup.innerHTML = `
        <span class="control-label">ปี:</span>
        <div class="year-chips-scroll">
          ${years.map(y => `
            <button class="year-chip-btn ${state.year === y ? 'active' : ''}" data-year="${y}">${y}</button>
          `).join('')}
        </div>
      `;
      leftCol.appendChild(yearGroup);

      yearGroup.querySelectorAll('.year-chip-btn').forEach(btn => {
        btn.onclick = () => {
          state.year = parseInt(btn.dataset.year, 10);
          updateUrl();
          renderControlBar();
          queueFetch();
        };
      });
    } else if (state.tab === 3) {
      // Tab 3: Year Range (Start & End)
      const rangeGroup = document.createElement('div');
      rangeGroup.className = 'control-group';
      rangeGroup.innerHTML = `
        <span class="control-label">ช่วงปี:</span>
        <select class="control-select" id="y0-select">
          ${state.meta.income_years.map(y => `<option value="${y}" ${state.y0 === y ? 'selected' : ''}>${y}</option>`).join('')}
        </select>
        <span style="color: var(--text-muted); font-size: 0.85rem;">→</span>
        <select class="control-select" id="y1-select">
          ${state.meta.income_years.map(y => `<option value="${y}" ${state.y1 === y ? 'selected' : ''}>${y}</option>`).join('')}
        </select>
      `;
      leftCol.appendChild(rangeGroup);

      rangeGroup.querySelector('#y0-select').onchange = (e) => {
        const val = parseInt(e.target.value, 10);
        if (val >= state.y1) {
          alert('ปีเริ่มต้นต้องน้อยกว่าปีสิ้นสุด');
          e.target.value = state.y0;
          return;
        }
        state.y0 = val;
        updateUrl();
        queueFetch();
      };
      rangeGroup.querySelector('#y1-select').onchange = (e) => {
        const val = parseInt(e.target.value, 10);
        if (val <= state.y0) {
          alert('ปีสิ้นสุดต้องมากกว่าปีเริ่มต้น');
          e.target.value = state.y1;
          return;
        }
        state.y1 = val;
        updateUrl();
        queueFetch();
      };
    }

    // 3. Tab-Specific Controls
    if (state.tab === 1) {
      // Area Select
      const areaGroup = document.createElement('div');
      areaGroup.className = 'control-group';
      areaGroup.innerHTML = `
        <span class="control-label">เขต:</span>
        <select class="control-select" id="area-select">
          ${state.meta.area_types.map(a => `<option value="${a.area_type_id}" ${state.area === a.area_type_id ? 'selected' : ''}>${a.name_th}</option>`).join('')}
        </select>
      `;
      leftCol.appendChild(areaGroup);
      areaGroup.querySelector('#area-select').onchange = (e) => {
        state.area = parseInt(e.target.value, 10);
        updateUrl();
        queueFetch();
      };
    } else if (state.tab === 2 || state.tab === 3) {
      // Property Type Select
      const ptGroup = document.createElement('div');
      ptGroup.className = 'control-group';
      ptGroup.innerHTML = `
        <span class="control-label">ประเภทบ้าน:</span>
        <select class="control-select" id="pt-select">
          ${state.meta.property_types.map(p => `<option value="${p.property_type_id}" ${state.pt === p.property_type_id ? 'selected' : ''}>${p.name_th}</option>`).join('')}
        </select>
      `;
      leftCol.appendChild(ptGroup);
      ptGroup.querySelector('#pt-select').onchange = (e) => {
        state.pt = parseInt(e.target.value, 10);
        updateUrl();
        queueFetch();
      };
    }

    container.appendChild(leftCol);

    // Right Column: Clear Filters Ghost Button
    if (hasNonDefaultFilters()) {
      const clearBtn = document.createElement('button');
      clearBtn.className = 'btn-ghost-clear';
      clearBtn.innerHTML = `${ICONS.rotateCcw} <span>ล้างตัวกรอง</span>`;
      clearBtn.onclick = () => {
        state.region = null;
        state.area = 0;
        state.pt = 1;
        state.metric = state.tab === 2 ? 'hpi' : 'income';
        state.grain = 'yearly';
        state.cagr_view = 'by_region';
        state.year = 2568;
        state.y0 = 2554;
        state.y1 = 2568;
        updateUrl();
        renderControlBar();
        queueFetch();
      };
      container.appendChild(clearBtn);
    }
  }

  function renderDashboard() {
    if (!state.tabData) return;
    const data = state.tabData;

    // Status Line
    const statusLineEl = document.getElementById('tab-status-line');
    if (statusLineEl && data.status_line) {
      statusLineEl.textContent = data.status_line;
    }

    // ──────────────── Render 4 KPI Cards ────────────────
    const kpiContainer = document.getElementById('kpi-container');
    if (kpiContainer && data.kpis) {
      kpiContainer.innerHTML = '';
      data.kpis.forEach((kpi, idx) => {
        const card = document.createElement('div');
        card.className = 'kpi-card';

        let chipHtml = '';
        if (kpi.delta) {
          const isUp = kpi.delta.direction === 'up';
          const icon = isUp ? ICONS.trendingUp : ICONS.trendingDown;
          const cls = isUp ? 'kpi-chip-positive' : 'kpi-chip-negative';
          chipHtml = `
            <div class="kpi-delta-row">
              <span class="kpi-chip ${cls}">${icon} <span>${kpi.delta.value}${kpi.delta.unit} (${kpi.delta.vs})</span></span>
            </div>
          `;
        } else if (kpi.status) {
          let cls = 'kpi-chip-neutral';
          let icon = '';
          if (kpi.status === 'harder') {
            cls = 'kpi-chip-negative';
            icon = ICONS.trendingUp;
          } else if (kpi.status === 'easier') {
            cls = 'kpi-chip-positive';
            icon = ICONS.trendingDown;
          }
          chipHtml = `
            <div class="kpi-delta-row">
              <span class="kpi-chip ${cls}">${icon} <span>${kpi.unit}</span></span>
            </div>
          `;
        }

        const iconBox = idx === 0 ? ICONS.wallet : (idx === 1 ? ICONS.activity : (idx === 2 ? ICONS.house : ICONS.scale));

        card.innerHTML = `
          <div class="kpi-top">
            <div class="kpi-icon-box">${iconBox}</div>
            <span class="kpi-label">${kpi.label}</span>
          </div>
          <div class="kpi-value-row">
            <span class="kpi-value tabular-nums">${typeof kpi.value === 'number' ? kpi.value.toLocaleString('th-TH') : kpi.value}</span>
          </div>
          ${kpi.subline ? `<div class="kpi-subline">${kpi.subline}</div>` : `<div class="kpi-unit">${kpi.unit}</div>`}
          ${chipHtml}
        `;
        kpiContainer.appendChild(card);
      });
    }

    // ──────────────── Render Charts (Tabs 1 & 2 vs Tab 3) ────────────────
    const chartsContainer = document.getElementById('charts-container');
    if (!chartsContainer) return;

    chartsContainer.innerHTML = '';

    if (state.tab === 1 || state.tab === 2) {
      renderTab1OrTab2Charts(chartsContainer, data);
    } else if (state.tab === 3) {
      renderTab3Charts(chartsContainer, data);
    }

    // Notes list
    const notesContainer = document.getElementById('notes-list');
    if (notesContainer && data.notes) {
      notesContainer.innerHTML = data.notes.map(n => `<div>• ${n}</div>`).join('');
    }
  }

  // ──────────────── Tabs 1 & 2 Charts Rendering ────────────────
  function renderTab1OrTab2Charts(container, data) {
    const grid = document.createElement('div');
    grid.className = 'main-charts-grid';

    // Left Column: Map Card
    const mapCard = document.createElement('div');
    mapCard.className = 'chart-card';
    mapCard.id = 'map-card';

    const mapTitle = state.tab === 1 ? 'แผนที่รายได้เฉลี่ยรายภาค' : 'แผนที่ดัชนีราคาบ้านรายภาค';
    let mapSegmentedHtml = '';
    if (state.tab === 1) {
      mapSegmentedHtml = `
        <div class="segmented-control" id="map-metric-control">
          <button class="segmented-btn ${state.metric === 'income' ? 'active' : ''}" data-metric="income">รายได้</button>
          <button class="segmented-btn ${state.metric === 'index' ? 'active' : ''}" data-metric="index">ดัชนี</button>
          <button class="segmented-btn ${state.metric === 'transfer' ? 'active' : ''}" data-metric="transfer">เงินโอน</button>
        </div>
      `;
    } else {
      mapSegmentedHtml = `
        <div class="segmented-control" id="map-metric-control">
          <button class="segmented-btn ${state.metric === 'hpi' ? 'active' : ''}" data-metric="hpi">ดัชนี</button>
          <button class="segmented-btn ${state.metric === 'yoy' ? 'active' : ''}" data-metric="yoy">YoY</button>
          <button class="segmented-btn ${state.metric === 'cagr' ? 'active' : ''}" data-metric="cagr">CAGR</button>
        </div>
      `;
    }

    const choroObj = data.charts.choropleth;
    mapCard.innerHTML = `
      <div class="chart-header">
        <h3 class="chart-title">${mapTitle}</h3>
        ${mapSegmentedHtml}
      </div>
      <div class="chart-read-guide">${choroObj.read_guide || ''}</div>
      <div class="plotly-container" id="plot-choropleth"></div>
      <div class="chart-note">${choroObj.note || ''}</div>
    `;
    grid.appendChild(mapCard);

    // Right Column: Stack of Line Trend and Heatmap
    const rightStack = document.createElement('div');
    rightStack.className = 'charts-right-stack';

    // 1. Line Trend Card
    const trendCard = document.createElement('div');
    trendCard.className = 'chart-card';
    const trendTitle = state.tab === 1 ? 'แนวโน้มรายได้ตามปี' : 'แนวโน้มดัชนีราคาบ้าน';
    let trendSegmentedHtml = '';
    if (state.tab === 1) {
      trendSegmentedHtml = `
        <div class="segmented-control" id="trend-metric-control">
          <button class="segmented-btn ${state.metric === 'income' ? 'active' : ''}" data-metric="income">บาท</button>
          <button class="segmented-btn ${state.metric === 'index' ? 'active' : ''}" data-metric="index">ดัชนี</button>
        </div>
      `;
    } else {
      trendSegmentedHtml = `
        <div class="segmented-control" id="trend-grain-control">
          <button class="segmented-btn ${state.grain === 'yearly' ? 'active' : ''}" data-grain="yearly">รายปี</button>
          <button class="segmented-btn ${state.grain === 'monthly' ? 'active' : ''}" data-grain="monthly">รายเดือน</button>
        </div>
      `;
    }

    const trendObj = data.charts.trend;
    trendCard.innerHTML = `
      <div class="chart-header">
        <h3 class="chart-title">${trendTitle}</h3>
        ${trendSegmentedHtml}
      </div>
      <div class="chart-read-guide">${trendObj.read_guide || ''}</div>
      <div class="plotly-container" id="plot-trend"></div>
      <div class="chart-note">${trendObj.note || ''}</div>
    `;
    rightStack.appendChild(trendCard);

    // 2. Heatmap Card
    const heatmapCard = document.createElement('div');
    heatmapCard.className = 'chart-card';
    const heatmapTitle = state.tab === 1 ? 'ช่องว่างเมือง-ชนบท (%)' : 'อัตราเปลี่ยนแปลงรายปี (YoY %)';
    const heatmapObj = data.charts.heatmap;
    heatmapCard.innerHTML = `
      <div class="chart-header">
        <h3 class="chart-title">${heatmapTitle}</h3>
      </div>
      <div class="chart-read-guide">${heatmapObj.read_guide || ''}</div>
      <div class="plotly-container" id="plot-heatmap"></div>
      <div class="chart-note">${heatmapObj.note || ''}</div>
    `;
    rightStack.appendChild(heatmapCard);

    grid.appendChild(rightStack);
    container.appendChild(grid);

    // Bottom Full Width: Treemap (Tab 1 only)
    if (state.tab === 1 && data.charts.treemap) {
      const treemapCard = document.createElement('div');
      treemapCard.className = 'chart-card chart-card-full';
      const treeObj = data.charts.treemap;
      treemapCard.innerHTML = `
        <div class="chart-header">
          <h3 class="chart-title">สัดส่วนแหล่งที่มาของรายได้</h3>
        </div>
        <div class="chart-read-guide">${treeObj.read_guide || ''}</div>
        <div class="plotly-container" id="plot-treemap"></div>
        <div class="treemap-legend">
          <span class="treemap-legend-item"><span class="treemap-legend-dot" style="background-color: #2F6BFF"></span> จากการทำงาน</span>
          <span class="treemap-legend-item"><span class="treemap-legend-dot" style="background-color: #5B8CFF"></span> เงินโอน/สวัสดิการ</span>
          <span class="treemap-legend-item"><span class="treemap-legend-dot" style="background-color: #8FB0FF"></span> ไม่เป็นตัวเงิน</span>
          <span class="treemap-legend-item"><span class="treemap-legend-dot" style="background-color: #D6E6FF"></span> อื่น ๆ (ทรัพย์สิน + ไม่ประจำ)</span>
        </div>
        <div class="chart-note">${treeObj.note || ''}</div>
      `;
      container.appendChild(treemapCard);
    }

    // Attach segmented controls events
    const mapSeg = container.querySelector('#map-metric-control');
    if (mapSeg) {
      mapSeg.querySelectorAll('button').forEach(btn => {
        btn.onclick = () => {
          state.metric = btn.dataset.metric;
          updateUrl();
          queueFetch();
        };
      });
    }

    const trendSeg = container.querySelector('#trend-metric-control');
    if (trendSeg) {
      trendSeg.querySelectorAll('button').forEach(btn => {
        btn.onclick = () => {
          state.metric = btn.dataset.metric;
          updateUrl();
          queueFetch();
        };
      });
    }

    const grainSeg = container.querySelector('#trend-grain-control');
    if (grainSeg) {
      grainSeg.querySelectorAll('button').forEach(btn => {
        btn.onclick = () => {
          state.grain = btn.dataset.grain;
          updateUrl();
          queueFetch();
        };
      });
    }

    // Render Plotly Figures with reactive cross-filtering
    renderPlotly('plot-choropleth', choroObj.figure, true);
    renderPlotly('plot-trend', trendObj.figure, false);
    renderPlotly('plot-heatmap', heatmapObj.figure, false);
    if (state.tab === 1 && data.charts.treemap) {
      renderPlotly('plot-treemap', data.charts.treemap.figure, false);
    }
  }

  // ──────────────── Tab 3 Charts Rendering ────────────────
  function renderTab3Charts(container, data) {
    // 1. Hero Price-to-Income Line Chart
    const heroCard = document.createElement('div');
    heroCard.className = 'chart-card chart-card-full';
    const heroObj = data.charts.hero;
    heroCard.innerHTML = `
      <div class="chart-header">
        <h3 class="chart-title">ดัชนีราคาบ้าน ÷ ดัชนีรายได้</h3>
      </div>
      <div class="chart-read-guide">${heroObj.read_guide || ''}</div>
      <div class="plotly-container" id="plot-hero"></div>
      <div class="chart-note">${heroObj.note || ''}</div>
    `;
    container.appendChild(heroCard);

    // 2. CAGR Comparison Chart
    const cagrCard = document.createElement('div');
    cagrCard.className = 'chart-card chart-card-full';
    const cagrObj = data.charts.cagr;
    cagrCard.innerHTML = `
      <div class="chart-header">
        <h3 class="chart-title">การเติบโตเฉลี่ยสะสมต่อปี (CAGR)</h3>
        <div class="segmented-control" id="cagr-view-control">
          <button class="segmented-btn ${state.cagr_view === 'by_region' ? 'active' : ''}" data-view="by_region">แยกตามภาค</button>
          <button class="segmented-btn ${state.cagr_view === 'by_type' ? 'active' : ''}" data-view="by_type">แยกตามประเภทบ้าน</button>
        </div>
      </div>
      <div class="chart-read-guide">${cagrObj.read_guide || ''}</div>
      <div class="plotly-container" id="plot-cagr"></div>
      <div class="chart-note">${cagrObj.note || ''}</div>
    `;
    container.appendChild(cagrCard);

    const cagrSeg = cagrCard.querySelector('#cagr-view-control');
    if (cagrSeg) {
      cagrSeg.querySelectorAll('button').forEach(btn => {
        btn.onclick = () => {
          state.cagr_view = btn.dataset.view;
          updateUrl();
          queueFetch();
        };
      });
    }

    renderPlotly('plot-hero', heroObj.figure, false);
    renderPlotly('plot-cagr', cagrObj.figure, false);
  }

  // ──────────────── Plotly Rendering & Click Handlers ────────────────
  function renderPlotly(divId, figure, isMap = false) {
    const el = document.getElementById(divId);
    if (!el || !figure) return;

    const config = {
      displayModeBar: false,
      displaylogo: false,
      responsive: true,
      scrollZoom: isMap,
    };

    Plotly.react(el, figure.data, figure.layout, config);

    // Attach click event for cross-filtering
    el.on('plotly_click', (eventData) => {
      if (!eventData || !eventData.points || !eventData.points.length) return;
      const pt = eventData.points[0];

      // 1. Map Click: location = region_id
      if (pt.location !== undefined) {
        const clickedId = parseInt(pt.location, 10);
        state.region = state.region === clickedId ? null : clickedId;
        updateUrl();
        renderControlBar();
        queueFetch();
        return;
      }

      // 2. Treemap Click: label contains region or ID
      if (pt.label) {
        const cleanLabel = pt.label.replace(/<b>|<\/b>/g, '').split(' · ')[0];
        const regObj = state.meta.regions.find(r => r.short_th === cleanLabel || r.name_th === cleanLabel);
        if (regObj) {
          state.region = state.region === regObj.region_id ? null : regObj.region_id;
          updateUrl();
          renderControlBar();
          queueFetch();
          return;
        }
      }

      // 3. Heatmap Click: pt.x = year, pt.y = region name
      if (pt.x !== undefined && pt.y !== undefined && isNaN(parseInt(pt.y, 10))) {
        const clickedYear = parseInt(pt.x, 10);
        const regObj = state.meta.regions.find(r => r.short_th === pt.y);
        if (!isNaN(clickedYear)) state.year = clickedYear;
        if (regObj) {
          state.region = regObj.region_id === 0 ? null : regObj.region_id;
        }
        updateUrl();
        renderControlBar();
        queueFetch();
        return;
      }

      // 4. Bar or Line Click in Tab 3 or Trend
      if (pt.x !== undefined) {
        const xStr = String(pt.x).replace(/<b>|<\/b>/g, '');
        // Year click on line trend
        const xNum = parseInt(xStr, 10);
        if (!isNaN(xNum) && xNum >= 2554 && xNum <= 2568) {
          state.year = xNum;
          updateUrl();
          renderControlBar();
          queueFetch();
          return;
        }

        // Region bar click in CAGR
        if (xStr.includes('ภาพรวม') || xStr.includes('ทั้งประเทศ')) {
          state.region = null;
          updateUrl();
          renderControlBar();
          queueFetch();
          return;
        }

        const regObj = state.meta.regions.find(r => r.short_th === xStr);
        if (regObj) {
          state.region = regObj.region_id === 0 ? null : regObj.region_id;
          updateUrl();
          renderControlBar();
          queueFetch();
          return;
        }

        // Property type bar click in CAGR by type
        const ptObj = state.meta.property_types.find(p => p.name_th === xStr);
        if (ptObj) {
          state.pt = ptObj.property_type_id;
          updateUrl();
          renderControlBar();
          queueFetch();
          return;
        }
      }
    });
  }

  // ──────────────── Tab Switching ────────────────
  function initTabs() {
    const tabs = document.querySelectorAll('.nav-item[data-tab]');
    tabs.forEach(tabBtn => {
      tabBtn.addEventListener('click', () => {
        const targetTab = parseInt(tabBtn.getAttribute('data-tab'), 10);
        if (targetTab === state.tab) return;
        state.tab = targetTab;
        tabs.forEach(t => t.classList.toggle('active', parseInt(t.getAttribute('data-tab'), 10) === state.tab));

        const tabTitles = {
          1: '1 · รายได้ครัวเรือน (สสช.)',
          2: '2 · ดัชนีราคาบ้าน (ธปท.)',
          3: '3 · รายได้ vs ราคาบ้าน (เปรียบเทียบ)',
        };
        const titleEl = document.getElementById('tab-title');
        if (titleEl) titleEl.textContent = tabTitles[state.tab];

        updateUrl();
        renderControlBar();
        queueFetch();
      });
    });
  }

  // ──────────────── Init ────────────────
  window.addEventListener('DOMContentLoaded', async () => {
    initTheme();
    readUrlParams();
    initTabs();
    await fetchMeta();
    await fetchTabData();
  });
})();
