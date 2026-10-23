/**
 * Income × Housing Dashboard — Frontend Client
 */

(function () {
  'use strict';

  // ──────────────── State ────────────────
  const state = {
    tab: 1,
    year: 2566,
    y0: 2554,
    y1: 2566,
    region: null,
    area: 0,
    pt: 1,
    metric: 'income',
    grain: 'yearly',
    theme: document.documentElement.getAttribute('data-theme') || 'dark',
    meta: null,
    tabData: null,
    tableViews: {}, // chartKey -> boolean
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
    }
    params.set('theme', state.theme);
    const newUrl = `${window.location.pathname}?${params.toString()}`;
    window.history.replaceState({}, '', newUrl);
  }

  // ──────────────── Theme ────────────────
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
        fetchTabData();
      });
    }
  }

  function applyTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('ihd-theme', theme);
    const toggleBtn = document.getElementById('theme-toggle-btn');
    if (toggleBtn) {
      toggleBtn.innerHTML = theme === 'dark' ? '☀️' : '🌙';
      toggleBtn.setAttribute('aria-label', theme === 'dark' ? 'สลับเป็นโหมดสว่าง' : 'สลับเป็นโหมดมืด');
    }
  }

  // ──────────────── API ────────────────
  async function fetchMeta() {
    try {
      const res = await fetch('/api/meta');
      if (!res.ok) throw new Error('Failed to load meta');
      state.meta = await res.json();
      renderYearChips();
      renderFilterControls();
      renderAsOfBadge();
    } catch (err) {
      console.error(err);
    }
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
      badge.textContent = `ข้อมูลล่าสุด: รายได้ สสช. ${state.meta.as_of.income_latest_wave} · ดัชนีบ้าน ธปท. ${state.meta.as_of.hpi_latest_month}`;
    }
  }

  function renderYearChips() {
    const container = document.getElementById('year-chips');
    if (!container || !state.meta) return;

    container.innerHTML = '';
    const years = state.tab === 2 ? state.meta.hpi_years : state.meta.income_years;

    years.forEach((y) => {
      const chip = document.createElement('button');
      chip.className = `year-chip ${state.year === y ? 'active' : ''}`;
      chip.textContent = y;
      chip.onclick = () => {
        state.year = y;
        updateUrl();
        renderYearChips();
        fetchTabData();
      };
      container.appendChild(chip);
    });
  }

  function renderFilterControls() {
    const container = document.getElementById('filter-toolbar');
    if (!container || !state.meta) return;

    container.innerHTML = '';

    // Tab 1 controls: Area & Metric
    if (state.tab === 1) {
      // Area Select
      const areaGroup = document.createElement('div');
      areaGroup.className = 'filter-group';
      areaGroup.innerHTML = `
        <label class="filter-label">ประเภทเขต:</label>
        <select class="filter-select" id="area-select">
          ${state.meta.area_types.map((a) => `<option value="${a.area_type_id}" ${state.area === a.area_type_id ? 'selected' : ''}>${a.name_th}</option>`).join('')}
        </select>
      `;
      container.appendChild(areaGroup);
      areaGroup.querySelector('#area-select').onchange = (e) => {
        state.area = parseInt(e.target.value, 10);
        updateUrl();
        fetchTabData();
      };

      // Metric Select for Choropleth
      const metricGroup = document.createElement('div');
      metricGroup.className = 'filter-group';
      metricGroup.innerHTML = `
        <label class="filter-label">ตัวชี้วัดแผนที่:</label>
        <select class="filter-select" id="metric-select">
          <option value="income" ${state.metric === 'income' ? 'selected' : ''}>ระดับรายได้ (บาท)</option>
          <option value="index" ${state.metric === 'index' ? 'selected' : ''}>ดัชนีรายได้ (2554=100)</option>
          <option value="transfer" ${state.metric === 'transfer' ? 'selected' : ''}>สัดส่วนเงินโอน (%)</option>
        </select>
      `;
      container.appendChild(metricGroup);
      metricGroup.querySelector('#metric-select').onchange = (e) => {
        state.metric = e.target.value;
        updateUrl();
        fetchTabData();
      };
    }

    // Tab 2 & 3 controls: Property Type
    if (state.tab === 2 || state.tab === 3) {
      const ptGroup = document.createElement('div');
      ptGroup.className = 'filter-group';
      ptGroup.innerHTML = `
        <label class="filter-label">ประเภทบ้าน:</label>
        <select class="filter-select" id="pt-select">
          ${state.meta.property_types.map((p) => `<option value="${p.property_type_id}" ${state.pt === p.property_type_id ? 'selected' : ''}>${p.name_th}</option>`).join('')}
        </select>
      `;
      container.appendChild(ptGroup);
      ptGroup.querySelector('#pt-select').onchange = (e) => {
        state.pt = parseInt(e.target.value, 10);
        updateUrl();
        fetchTabData();
      };
    }

    // Tab 2 Grain: Yearly / Monthly
    if (state.tab === 2) {
      const grainGroup = document.createElement('div');
      grainGroup.className = 'filter-group';
      grainGroup.innerHTML = `
        <label class="filter-label">ความละเอียดแนวโน้ม:</label>
        <select class="filter-select" id="grain-select">
          <option value="yearly" ${state.grain === 'yearly' ? 'selected' : ''}>รายปี</option>
          <option value="monthly" ${state.grain === 'monthly' ? 'selected' : ''}>รายเดือน</option>
        </select>
      `;
      container.appendChild(grainGroup);
      grainGroup.querySelector('#grain-select').onchange = (e) => {
        state.grain = e.target.value;
        updateUrl();
        fetchTabData();
      };
    }
  }

  function renderActiveFilterChips() {
    const container = document.getElementById('active-filter-chips');
    if (!container || !state.meta) return;

    container.innerHTML = '';

    // Year chip
    const yearChip = document.createElement('span');
    yearChip.className = 'chip chip-blue';
    yearChip.innerHTML = `ปี: ${state.year}`;
    container.appendChild(yearChip);

    // Region chip (if selected)
    if (state.region !== null) {
      const regionInfo = state.meta.regions.find((r) => r.region_id === state.region);
      const chip = document.createElement('span');
      chip.className = 'chip chip-orange';
      chip.innerHTML = `ภาค: ${regionInfo ? regionInfo.short_th : state.region} <button class="chip-remove" title="ล้างภาค">&times;</button>`;
      chip.querySelector('.chip-remove').onclick = () => {
        state.region = null;
        updateUrl();
        fetchTabData();
      };
      container.appendChild(chip);
    }
  }

  function renderDashboard() {
    if (!state.tabData) return;
    const data = state.tabData;

    renderActiveFilterChips();

    // Headline
    const headlineEl = document.getElementById('headline-text');
    if (headlineEl) headlineEl.textContent = data.headline;

    // KPIs
    const kpiContainer = document.getElementById('kpi-container');
    if (kpiContainer) {
      kpiContainer.innerHTML = '';
      data.kpis.forEach((kpi) => {
        const card = document.createElement('div');
        card.className = 'kpi-card';
        let deltaHtml = '';
        if (kpi.delta) {
          const dirClass = kpi.delta.direction === 'up' ? 'delta-up' : 'delta-down';
          const icon = kpi.delta.direction === 'up' ? '▲' : '▼';
          deltaHtml = `<span class="kpi-delta ${dirClass}">${icon} ${kpi.delta.value}${kpi.delta.unit} (${kpi.delta.vs})</span>`;
        }
        card.innerHTML = `
          <div class="kpi-header">
            <span class="kpi-label">${kpi.label}</span>
            ${deltaHtml}
          </div>
          <div class="kpi-value-row">
            <span class="kpi-value tabular-nums">${typeof kpi.value === 'number' ? kpi.value.toLocaleString('th-TH') : kpi.value}</span>
            <span class="kpi-unit">${kpi.unit}</span>
          </div>
        `;
        kpiContainer.appendChild(card);
      });

      // Ring card
      if (data.ring) {
        const ringCard = document.createElement('div');
        ringCard.className = 'ring-card';
        ringCard.innerHTML = `
          <span class="ring-value tabular-nums">${typeof data.ring.value === 'number' ? data.ring.value + '%' : data.ring.value}</span>
          <span class="ring-label">${data.ring.label}</span>
        `;
        kpiContainer.appendChild(ringCard);
      }
    }

    // Charts
    const chartsContainer = document.getElementById('charts-container');
    if (chartsContainer) {
      chartsContainer.innerHTML = '';
      Object.entries(data.charts).forEach(([key, chart]) => {
        const card = document.createElement('div');
        card.className = `chart-card ${key === 'trend' || key === 'price_to_income' ? 'chart-card-full' : ''}`;
        card.id = `chart-card-${key}`;

        // Header
        const header = document.createElement('div');
        header.className = 'chart-header';
        header.innerHTML = `
          <h3 class="chart-title">${chart.figure.layout.title ? chart.figure.layout.title.text : ''}</h3>
          <div class="chart-actions">
            <button class="btn-tool" id="btn-summary-${key}" title="สรุปข้อค้นพบ">✦ สรุป</button>
            <button class="btn-tool" id="btn-table-${key}" title="สลับดูตาราง">▤ ตาราง</button>
            <a class="btn-tool" href="/api/export/${state.tab}/${key}.csv?${new URLSearchParams(window.location.search).toString()}" download title="ดาวน์โหลด CSV">⤓ CSV</a>
          </div>
        `;
        card.appendChild(header);

        // Summary Panel (collapsible)
        const summaryPanel = document.createElement('div');
        summaryPanel.className = 'summary-panel';
        summaryPanel.id = `summary-${key}`;
        const isSummaryOpen = sessionStorage.getItem(`summary-${key}`) !== 'false';
        if (!isSummaryOpen) summaryPanel.style.display = 'none';

        summaryPanel.innerHTML = `
          <div class="summary-headline">${chart.summary.headline}</div>
          ${chart.summary.bullets && chart.summary.bullets.length ? `<ul class="summary-bullets">${chart.summary.bullets.map((b) => `<li>${b}</li>`).join('')}</ul>` : ''}
          ${chart.summary.caution ? `<div class="summary-caution">⚠️ ${chart.summary.caution}</div>` : ''}
        `;
        card.appendChild(summaryPanel);

        // Notice for empty / unavailable series
        if (chart.empty) {
          const emptyNotice = document.createElement('div');
          emptyNotice.className = 'empty-notice';
          emptyNotice.textContent = chart.empty;
          card.appendChild(emptyNotice);
        }

        // Plotly container
        const plotDiv = document.createElement('div');
        plotDiv.className = 'plotly-container';
        plotDiv.id = `plot-${key}`;
        card.appendChild(plotDiv);

        // Table container
        const tableDiv = document.createElement('div');
        tableDiv.className = `table-container ${state.tableViews[key] ? 'active' : ''}`;
        tableDiv.id = `table-${key}`;
        if (state.tableViews[key]) plotDiv.style.display = 'none';

        if (chart.table) {
          tableDiv.innerHTML = `
            <table class="data-table">
              <thead>
                <tr>${chart.table.columns.map((c) => `<th>${c}</th>`).join('')}</tr>
              </thead>
              <tbody>
                ${chart.table.rows.map((row) => `<tr>${row.map((cell) => `<td>${cell !== null ? cell : '-'}</td>`).join('')}</tr>`).join('')}
              </tbody>
            </table>
          `;
        }
        card.appendChild(tableDiv);

        chartsContainer.appendChild(card);

        // Button events
        const summaryBtn = header.querySelector(`#btn-summary-${key}`);
        summaryBtn.onclick = () => {
          const isVisible = summaryPanel.style.display !== 'none';
          summaryPanel.style.display = isVisible ? 'none' : 'flex';
          sessionStorage.setItem(`summary-${key}`, !isVisible);
          summaryBtn.classList.toggle('active', !isVisible);
        };
        summaryBtn.classList.toggle('active', isSummaryOpen);

        const tableBtn = header.querySelector(`#btn-table-${key}`);
        tableBtn.onclick = () => {
          const isTable = tableDiv.classList.toggle('active');
          state.tableViews[key] = isTable;
          plotDiv.style.display = isTable ? 'none' : 'block';
          tableBtn.classList.toggle('active', isTable);
          if (!isTable) {
            Plotly.Plots.resize(plotDiv);
          }
        };
        tableBtn.classList.toggle('active', !!state.tableViews[key]);

        // Draw Plotly
        const config = {
          displaylogo: false,
          responsive: true,
          modeBarButtonsToRemove: ['lasso2d', 'select2d'],
        };
        Plotly.react(plotDiv, chart.figure.data, chart.figure.layout, config);

        // Attach Click Handlers for Interactive Cross-filtering
        plotDiv.on('plotly_click', (eventData) => {
          if (!eventData || !eventData.points || !eventData.points.length) return;
          const pt = eventData.points[0];

          // 1. Choropleth click -> location is region_id
          if (pt.location !== undefined) {
            const clickedId = parseInt(pt.location, 10);
            state.region = state.region === clickedId ? null : clickedId;
            updateUrl();
            fetchTabData();
            return;
          }

          // 2. Line or Scatter or Bar click -> x is year, or region name
          if (pt.x !== undefined) {
            const xVal = parseInt(pt.x, 10);
            if (!isNaN(xVal) && xVal >= 2554 && xVal <= 2568) {
              state.year = xVal;
              updateUrl();
              renderYearChips();
              fetchTabData();
              return;
            }
          }

          // 3. Region name click on bar / treemap
          if (pt.label) {
            const regObj = state.meta.regions.find((r) => r.short_th === pt.label);
            if (regObj) {
              state.region = state.region === regObj.region_id ? null : regObj.region_id;
              updateUrl();
              fetchTabData();
              return;
            }
          }
        });
      });
    }

    // Right Drawer Insights
    const insightsList = document.getElementById('insights-list');
    if (insightsList && data.insights) {
      insightsList.innerHTML = '';
      data.insights.forEach((item) => {
        const li = document.createElement('li');
        li.className = 'insights-item';
        li.textContent = item;
        insightsList.appendChild(li);
      });
    }

    // Notes
    const notesContainer = document.getElementById('notes-list');
    if (notesContainer && data.notes) {
      notesContainer.innerHTML = data.notes.map((n) => `<div>• ${n}</div>`).join('');
    }
  }

  // ──────────────── Tab Switching ────────────────
  function initTabs() {
    const tabs = document.querySelectorAll('.nav-item[data-tab]');
    tabs.forEach((tabBtn) => {
      tabBtn.addEventListener('click', () => {
        const targetTab = parseInt(tabBtn.getAttribute('data-tab'), 10);
        if (targetTab === state.tab) return;
        state.tab = targetTab;
        tabs.forEach((t) => t.classList.toggle('active', parseInt(t.getAttribute('data-tab'), 10) === state.tab));

        // Update Tab Title in UI
        const tabNames = {
          1: '1 · รายได้ครัวเรือน (สสช.)',
          2: '2 · ดัชนีราคาบ้าน (ธปท.)',
          3: '3 · รายได้ vs ราคาบ้าน (เปรียบเทียบ)',
        };
        const titleEl = document.getElementById('tab-title');
        if (titleEl) titleEl.textContent = tabNames[state.tab];

        updateUrl();
        renderYearChips();
        renderFilterControls();
        fetchTabData();
      });
    });

    // Clear filters button
    const clearBtn = document.getElementById('clear-filters-btn');
    if (clearBtn) {
      clearBtn.addEventListener('click', () => {
        state.region = null;
        state.area = 0;
        state.pt = 1;
        state.metric = 'income';
        state.grain = 'yearly';
        state.year = 2566;
        state.y0 = 2554;
        state.y1 = 2566;
        updateUrl();
        renderYearChips();
        renderFilterControls();
        fetchTabData();
      });
    }
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
