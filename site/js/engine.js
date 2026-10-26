/**
 * Income × Housing Dashboard — Pure JavaScript Engine for Static Site
 * Replaces FastAPI backend; generates identical KPI calculations and Plotly JSON specs.
 */

(function (root, factory) {
  if (typeof module === 'object' && module.exports) {
    module.exports = factory();
  } else {
    root.DashboardEngine = factory();
  }
}(typeof self !== 'undefined' ? self : this, function () {
  'use strict';

  let DB = null;

  const FONT_FAMILY = 'Anuphan, Noto Sans Thai, Sarabun, system-ui, sans-serif';

  const REGION_COLORS = {
    dark: {
      'กทม.+ปริมณฑล': '#5B8CFF',
      'กลาง': '#3CCBE8',
      'เหนือ': '#A99DFF',
      'อีสาน': '#FFC04D',
      'ใต้': '#FF8A3D',
      'ทั่วประเทศ': '#8FA0BC',
    },
    light: {
      'กทม.+ปริมณฑล': '#2F6BFF',
      'กลาง': '#18B8D8',
      'เหนือ': '#8B7CF6',
      'อีสาน': '#F5A524',
      'ใต้': '#FF7A1A',
      'ทั่วประเทศ': '#8FA0BC',
    },
  };

  const INCOME_SOURCE_COLORS = {
    dark: {
      'จากการทำงาน': '#3B63D9',
      'เงินโอน/สวัสดิการ': '#5B8CFF',
      'ไม่เป็นตัวเงิน': '#8FB0FF',
      'อื่น ๆ': '#2A3A5E',
      'ทรัพย์สิน': '#8FA0BC',
      'ไม่ประจำ': '#4B5563',
    },
    light: {
      'จากการทำงาน': '#173DA8',
      'เงินโอน/สวัสดิการ': '#2F6BFF',
      'ไม่เป็นตัวเงิน': '#85B2FF',
      'อื่น ๆ': '#D6E6FF',
      'ทรัพย์สิน': '#93C5FD',
      'ไม่ประจำ': '#BFDBFE',
    },
  };

  const SEMANTIC_COLORS = {
    dark: {
      income: '#5B8CFF',
      housing: '#FF8A3D',
      positive: '#34D399',
      negative: '#F87171',
      neutral: '#8FA0BC',
    },
    light: {
      income: '#2F6BFF',
      housing: '#FF7A1A',
      positive: '#0E9F6E',
      negative: '#E5484D',
      neutral: '#5E6C84',
    },
  };

  const CHOROPLETH_INCOME_SCALE = [
    [0.0, '#EAF2FF'],
    [0.5, '#2F6BFF'],
    [1.0, '#0F2A75'],
  ];

  const CHOROPLETH_HOUSING_SCALE = [
    [0.0, '#FFF1E6'],
    [0.5, '#FF8A3D'],
    [1.0, '#B3470A'],
  ];

  const HEATMAP_GAP_SCALE = [
    [0.0, '#EAF2FF'],
    [0.5, '#2F6BFF'],
    [1.0, '#0F2A75'],
  ];

  function get_heatmap_yoy_scale(theme) {
    const zeroColor = theme === 'dark' ? '#1F2937' : '#F3F4F6';
    return [
      [0.0, '#14B8A6'],
      [0.5, zeroColor],
      [1.0, '#B3470A'],
    ];
  }

  const TOKENS = {
    dark: {
      surface: '#111827',
      surface_2: '#1A2336',
      border: 'rgba(255,255,255,0.08)',
      text: '#EAF0FA',
      text_muted: '#8FA0BC',
      grid: 'rgba(120,140,170,0.18)',
    },
    light: {
      surface: '#FFFFFF',
      surface_2: '#F1F5FB',
      border: 'rgba(11,27,52,0.08)',
      text: '#0B1B34',
      text_muted: '#5E6C84',
      grid: 'rgba(120,140,170,0.18)',
    },
  };

  const REGION_LABEL_COORDS = {
    1: { lon: 100.40, lat: 13.60 },
    2: { lon: 100.20, lat: 15.20 },
    3: { lon: 99.40, lat: 17.71 },
    4: { lon: 103.17, lat: 16.29 },
    5: { lon: 99.48, lat: 8.32 },
  };

  function regionColor(short_th, theme) {
    const palette = REGION_COLORS[theme] || REGION_COLORS.dark;
    return palette[short_th] || '#8FA0BC';
  }

  function regionDash(is_national) {
    return is_national ? 'dash' : 'solid';
  }

  function getBaseLayout(theme) {
    const t = TOKENS[theme] || TOKENS.dark;
    return {
      paper_bgcolor: 'rgba(0,0,0,0)',
      plot_bgcolor: 'rgba(0,0,0,0)',
      title: { text: '' },
      font: {
        family: FONT_FAMILY,
        color: t.text_muted,
        size: 12.5,
      },
      xaxis: {
        gridcolor: 'rgba(0,0,0,0)',
        showgrid: false,
        zeroline: false,
        showline: false,
        tickfont: { family: FONT_FAMILY, color: t.text_muted, size: 12 },
      },
      yaxis: {
        gridcolor: t.grid,
        showgrid: true,
        zeroline: false,
        showline: false,
        tickfont: { family: FONT_FAMILY, color: t.text_muted, size: 12 },
        tickformat: ',.0f',
      },
      hoverlabel: {
        bgcolor: t.surface,
        bordercolor: t.text_muted,
        font: { family: FONT_FAMILY, color: t.text, size: 12.5 },
      },
      margin: { l: 16, r: 16, t: 8, b: 28 },
      separators: ',.',
      showlegend: false,
    };
  }

  // ──────────────── Metric Helpers ────────────────
  function roundVal(v, dec = 2) {
    if (v === null || v === undefined || isNaN(v)) return null;
    const factor = Math.pow(10, dec);
    return Math.round((v + Number.EPSILON) * factor) / factor;
  }

  function cagr_pct(v0, v1, years) {
    if (!years || !v0 || years <= 0 || v0 <= 0 || v1 <= 0) return null;
    const c = Math.pow(v1 / v0, 1.0 / years) - 1.0;
    return roundVal(c * 100, 2);
  }

  function pct_change(v0, v1) {
    if (!v0 || v0 === 0) return null;
    return roundVal(100.0 * (v1 / v0 - 1.0), 1);
  }

  // ──────────────── Engine Core ────────────────
  function init(data) {
    DB = data;
  }

  function isReady() {
    return DB !== null && DB.meta !== undefined;
  }

  function getMeta() {
    return DB ? DB.meta : null;
  }

  function getGeoJson() {
    return DB ? DB.geojson : null;
  }

  // ──────────────── Tab 1 Calculations & Charts ────────────────
  function handleTab1(params) {
    const year = params.year || 2568;
    const area = params.area !== undefined ? params.area : 0;
    const region = (params.region !== undefined && params.region !== null && params.region !== '') ? parseInt(params.region, 10) : null;
    const theme = params.theme || 'dark';
    const metric = params.metric || 'income';
    const t = TOKENS[theme] || TOKENS.dark;
    const gj = getGeoJson();

    const regInfo = region !== null ? DB.meta.regions.find(r => r.region_id === region) : null;
    const scope = regInfo ? regInfo.short_th : 'ทั่วประเทศ';
    const areaInfo = DB.meta.area_types.find(a => a.area_type_id === area);
    const areaName = areaInfo ? areaInfo.name_th : 'รวมทุกเขต';

    const status_line = `${scope} · ปี ${year} · ${areaName}`;

    // Target Region ID for KPIs (0 for national if region is null)
    const targetRid = region !== null ? region : 0;

    const targetRow = DB.income.find(r => r.year_be === year && r.region_id === targetRid && r.area_type_id === area);
    const baseRow = DB.income.find(r => r.year_be === 2554 && r.region_id === targetRid && r.area_type_id === area);

    const incomeVal = targetRow ? targetRow.monthly_income : 0;
    const baseIncomeVal = baseRow ? baseRow.monthly_income : 0;

    const isBaseYear = (year === 2554);
    const deltaVal = !isBaseYear ? pct_change(baseIncomeVal, incomeVal) : null;
    const yearsSpan = year - 2554;
    const incomeCagr = yearsSpan > 0 ? cagr_pct(baseIncomeVal, incomeVal, yearsSpan) : null;

    const transferPct = (targetRow && targetRow.monthly_income)
      ? roundVal(100.0 * targetRow.current_transfer / targetRow.monthly_income, 1)
      : 0;

    // Urban-Rural Gap: 100 * (urban - rural) / rural
    const urbanRow = DB.income.find(r => r.year_be === year && r.region_id === targetRid && r.area_type_id === 1);
    const ruralRow = DB.income.find(r => r.year_be === year && r.region_id === targetRid && r.area_type_id === 2);
    let gapPct = null;
    if (urbanRow && ruralRow && ruralRow.monthly_income) {
      gapPct = roundVal(100.0 * (urbanRow.monthly_income - ruralRow.monthly_income) / ruralRow.monthly_income, 1);
    }

    const kpis = [
      {
        id: 'income',
        label: 'รายได้เฉลี่ย',
        value: Math.round(incomeVal),
        unit: 'บาท/เดือน',
        delta: deltaVal !== null ? {
          value: Math.abs(deltaVal),
          unit: '%',
          vs: '2554',
          direction: deltaVal >= 0 ? 'up' : 'down',
        } : null,
      },
      {
        id: 'cagr',
        label: `CAGR 2554→${year}`,
        value: incomeCagr !== null ? roundVal(incomeCagr, 2) : '—',
        unit: incomeCagr !== null ? '%/ปี' : '(ปีฐาน)',
        delta: (incomeCagr !== null && !isBaseYear) ? {
          value: roundVal(Math.abs(incomeCagr), 2),
          unit: '%',
          vs: '2554',
          direction: incomeCagr >= 0 ? 'up' : 'down',
        } : null,
      },
      {
        id: 'transfer',
        label: 'สัดส่วนเงินโอน/สวัสดิการ',
        value: transferPct,
        unit: '% ของรายได้',
        delta: null,
      },
      {
        id: 'gap',
        label: 'ช่องว่างเมือง-ชนบท',
        value: gapPct !== null ? gapPct : '—',
        unit: '%',
        subline: (urbanRow && ruralRow)
          ? `ในเขต ${Math.round(urbanRow.monthly_income).toLocaleString()} ÷ นอกเขต ${Math.round(ruralRow.monthly_income).toLocaleString()} บาท`
          : undefined,
        delta: null,
      },
    ];

    // ──────────────── Chart 1A: Choropleth ────────────────
    const choroData = DB.meta.regions
      .filter(r => r.region_id > 0)
      .map(r => {
        const row = DB.income.find(i => i.year_be === year && i.region_id === r.region_id && i.area_type_id === area);
        const bRow = DB.income.find(i => i.year_be === 2554 && i.region_id === r.region_id && i.area_type_id === area);
        let val = 0;
        if (metric === 'income') {
          val = row ? row.monthly_income : 0;
        } else if (metric === 'index') {
          val = (row && bRow && bRow.monthly_income) ? roundVal(100.0 * row.monthly_income / bRow.monthly_income, 1) : 100.0;
        } else if (metric === 'transfer') {
          val = (row && row.monthly_income) ? roundVal(100.0 * row.current_transfer / row.monthly_income, 1) : 0;
        }
        return {
          region_id: r.region_id,
          code: r.code,
          short_th: r.short_th,
          value: val,
        };
      });

    const metricLabel = metric === 'income' ? 'รายได้' : (metric === 'index' ? 'ดัชนีรายได้' : 'สัดส่วนเงินโอน');
    const unitLabel = metric === 'income' ? 'บาท/เดือน' : (metric === 'index' ? '(2554=100)' : '%');

    const choroLocs = choroData.map(r => r.region_id);
    const choroVals = choroData.map(r => r.value);
    const choroCustom = choroData.map(r => `${r.short_th}<br>${r.value.toLocaleString(undefined, { maximumFractionDigits: 1 })} ${unitLabel}<br>${areaName} · ปี ${year}`);

    const choroTraces = [
      {
        type: 'choroplethmap',
        geojson: gj,
        locations: choroLocs,
        z: choroVals,
        featureidkey: 'properties.region_id',
        colorscale: CHOROPLETH_INCOME_SCALE,
        customdata: choroCustom,
        hovertemplate: '%{customdata}<extra></extra>',
        marker: { line: { color: t.border, width: 0.5 }, opacity: 0.85 },
        colorbar: {
          orientation: 'h',
          x: 0.03,
          y: 0.03,
          xanchor: 'left',
          yanchor: 'bottom',
          thickness: 10,
          outlinewidth: 0,
          tickfont: { family: FONT_FAMILY, color: t.text_muted, size: 11 },
          tickformat: ',.0f',
          title: { text: '' },
        },
      },
    ];

    if (region && choroLocs.includes(region)) {
      const selRow = choroData.find(r => r.region_id === region);
      choroTraces.push({
        type: 'choroplethmap',
        geojson: gj,
        locations: [region],
        z: [selRow ? selRow.value : 0],
        featureidkey: 'properties.region_id',
        colorscale: CHOROPLETH_INCOME_SCALE,
        showscale: false,
        marker: { line: { color: t.text, width: 3 }, opacity: 0.9 },
        hoverinfo: 'skip',
      });
    }

    const lblLons = [], lblLats = [], lblTexts = [];
    choroData.forEach(r => {
      const coords = REGION_LABEL_COORDS[r.region_id];
      if (coords) {
        lblLons.push(coords.lon);
        lblLats.push(coords.lat);
        lblTexts.push(`<b>${r.short_th}</b><br>${r.value.toLocaleString(undefined, { maximumFractionDigits: 0 })}`);
      }
    });

    choroTraces.push({
      type: 'scattermap',
      mode: 'text',
      lon: lblLons,
      lat: lblLats,
      text: lblTexts,
      textfont: { family: FONT_FAMILY, size: 12, color: t.text },
      hoverinfo: 'skip',
    });

    const choroLayout = getBaseLayout(theme);
    Object.assign(choroLayout, {
      height: 560,
      margin: { l: 0, r: 0, t: 0, b: 0 },
      map: {
        style: theme === 'dark' ? 'carto-darkmatter' : 'carto-positron',
        center: { lat: 13.0, lon: 101.2 },
        zoom: 4.6,
      },
    });

    // ──────────────── Chart 1B: Trend Line ────────────────
    const trendTraces = [];
    const yKey = metric === 'income' ? 'monthly_income' : 'income_index';
    const hoverFmt = metric === 'income' ? '%{y:,.0f} บาท' : '%{y:.1f}';

    DB.meta.regions.forEach(reg => {
      const isNational = reg.is_national;
      const rid = reg.region_id;
      const isSelected = (region !== null && region === rid) || (region === null && isNational);
      const hasAnySelected = region !== null && region > 0;

      let opacity = 1.0;
      let lineWidth = 2.5;
      if (hasAnySelected && !isSelected) {
        opacity = 0.3;
        lineWidth = 1.5;
      } else if (isSelected) {
        opacity = 1.0;
        lineWidth = 3.5;
      }

      const rows = DB.income
        .filter(i => i.region_id === rid && i.area_type_id === area)
        .sort((a, b) => a.year_be - b.year_be);

      const bRow = rows.find(r => r.year_be === 2554);
      const bInc = bRow ? bRow.monthly_income : 1;

      const xs = rows.map(r => String(r.year_be));
      const ys = rows.map(r => metric === 'income' ? r.monthly_income : (100.0 * r.monthly_income / bInc));

      const color = regionColor(reg.short_th, theme);
      const fillMode = (isSelected && !isNational) ? 'tozeroy' : 'none';

      trendTraces.push({
        type: 'scatter',
        x: xs,
        y: ys,
        mode: 'lines+markers',
        name: reg.short_th,
        line: {
          color: color,
          dash: regionDash(isNational),
          width: lineWidth,
        },
        fill: fillMode,
        fillcolor: theme === 'light' ? 'rgba(47, 107, 255, 0.08)' : 'rgba(91, 140, 255, 0.08)',
        opacity: opacity,
        marker: { size: 5, line: { color: t.surface, width: 2 } },
        customdata: Array(xs.length).fill(rid),
        hovertemplate: `${reg.short_th}: ${hoverFmt}<extra></extra>`,
      });

      if (rows.length > 0) {
        trendTraces.push({
          type: 'scatter',
          x: [xs[xs.length - 1]],
          y: [ys[ys.length - 1]],
          mode: 'text',
          name: reg.short_th,
          customdata: [rid],
          text: [`  ${reg.short_th}`],
          textposition: 'middle right',
          textfont: { family: FONT_FAMILY, size: 11, color: color },
          hoverinfo: 'skip',
          showlegend: false,
          opacity: opacity,
        });
      }
    });

    const trendLayout = getBaseLayout(theme);
    Object.assign(trendLayout, {
      margin: { l: 48, r: 60, t: 8, b: 28 },
      xaxis: {
        ...trendLayout.xaxis,
        type: 'category',
        showspikes: true,
        spikethickness: 1,
        spikecolor: t.grid,
        spikemode: 'across',
      },
      yaxis: {
        ...trendLayout.yaxis,
        title: { text: '' },
      },
      height: 320,
      hovermode: 'x unified',
    });

    // ──────────────── Chart 1C: Heatmap (Urban-Rural Gap) ────────────────
    const regionOrder = ['กทม.+ปริมณฑล', 'กลาง', 'เหนือ', 'อีสาน', 'ใต้', 'ทั่วประเทศ'];
    const yCategories = [...regionOrder].reverse();
    const xYears = DB.meta.income_years.map(String);

    const gapLookup = {};
    DB.meta.regions.forEach(reg => {
      DB.meta.income_years.forEach(yr => {
        const u = DB.income.find(i => i.year_be === yr && i.region_id === reg.region_id && i.area_type_id === 1);
        const r = DB.income.find(i => i.year_be === yr && i.region_id === reg.region_id && i.area_type_id === 2);
        if (u && r && r.monthly_income) {
          const g = roundVal(100.0 * (u.monthly_income - r.monthly_income) / r.monthly_income, 1);
          gapLookup[`${reg.short_th}_${yr}`] = g;
        }
      });
    });

    const zHeat = [];
    const textHeat = [];
    yCategories.forEach(regName => {
      const rowZ = [];
      const rowT = [];
      xYears.forEach(yr => {
        const val = gapLookup[`${regName}_${yr}`];
        rowZ.push(val !== undefined ? val : null);
        rowT.push(val !== undefined && val !== null ? `${Math.round(val)}%` : '');
      });
      zHeat.push(rowZ);
      textHeat.push(rowT);
    });

    const heatShapes = [
      {
        type: 'line',
        x0: -0.5,
        x1: xYears.length - 0.5,
        y0: 0.5,
        y1: 0.5,
        line: { color: t.text_muted, width: 1, dash: 'dot' },
      },
    ];

    const yrStr = String(year);
    if (xYears.includes(yrStr)) {
      const colIdx = xYears.indexOf(yrStr);
      heatShapes.push({
        type: 'rect',
        x0: colIdx - 0.48,
        x1: colIdx + 0.48,
        y0: -0.48,
        y1: yCategories.length - 0.52,
        line: { color: t.text, width: 2 },
        fillcolor: 'rgba(0,0,0,0)',
      });
    }

    if (region !== null) {
      const targetRegObj = DB.meta.regions.find(r => r.region_id === region);
      if (targetRegObj && yCategories.includes(targetRegObj.short_th)) {
        const rowIdx = yCategories.indexOf(targetRegObj.short_th);
        heatShapes.push({
          type: 'rect',
          x0: -0.48,
          x1: xYears.length - 0.52,
          y0: rowIdx - 0.48,
          y1: rowIdx + 0.48,
          line: { color: t.text, width: 2 },
          fillcolor: 'rgba(0,0,0,0)',
        });
      }
    }

    const heatLayout = getBaseLayout(theme);
    Object.assign(heatLayout, {
      margin: { l: 48, r: 48, t: 8, b: 28 },
      xaxis: { ...heatLayout.xaxis, type: 'category' },
      yaxis: { ...heatLayout.yaxis, type: 'category', showgrid: true },
      height: 280,
      shapes: heatShapes,
    });

    const heatFigure = {
      data: [
        {
          type: 'heatmap',
          z: zHeat,
          x: xYears,
          y: yCategories,
          text: textHeat,
          texttemplate: '%{text}',
          textfont: { family: FONT_FAMILY, size: 11.5 },
          colorscale: HEATMAP_GAP_SCALE,
          zmin: 0,
          zmax: 65,
          xgap: 4,
          ygap: 4,
          hovertemplate: '%{y} ปี %{x}<br>ช่องว่าง: %{z:.1f}%<extra></extra>',
          colorbar: {
            thickness: 10,
            outlinewidth: 0,
            tickfont: { family: FONT_FAMILY, color: t.text_muted, size: 10 },
            title: { text: '' },
          },
        },
      ],
      layout: heatLayout,
    };

    // ──────────────── Chart 1D: Treemap (Income Breakdown) ────────────────
    const sourceColors = INCOME_SOURCE_COLORS[theme];
    let treemapFigure = null;

    if (region !== null) {
      // Single region mode
      const rRow = DB.income.find(i => i.year_be === year && i.region_id === region && i.area_type_id === area);
      if (rRow) {
        const tot = rRow.monthly_income;
        const s1 = roundVal(100.0 * rRow.from_work / tot, 1);
        const s2 = roundVal(100.0 * rRow.current_transfer / tot, 1);
        const s3 = roundVal(100.0 * rRow.nonmoney_income / tot, 1);
        const s4 = roundVal(100.0 * rRow.property_income / tot, 1);
        const s5 = roundVal(100.0 - (s1 + s2 + s3 + s4), 1);

        const leaves = [
          { name: 'จากการทำงาน', amount: rRow.from_work, share: s1 },
          { name: 'เงินโอน/สวัสดิการ', amount: rRow.current_transfer, share: s2 },
          { name: 'ไม่เป็นตัวเงิน', amount: rRow.nonmoney_income, share: s3 },
          { name: 'ทรัพย์สิน', amount: rRow.property_income, share: s4 },
          { name: 'ไม่ประจำ', amount: rRow.noncur_m_income, share: s5 },
        ];

        const tLabels = leaves.map(l => l.name);
        const tParents = leaves.map(() => '');
        const tValues = leaves.map(l => l.amount);
        const tTexts = leaves.map(l => `${l.name}<br>${l.amount.toLocaleString(undefined, { maximumFractionDigits: 0 })} บาท (${l.share.toFixed(1)}%)`);
        const tCustom = leaves.map(l => [l.share, l.name]);
        const tColors = leaves.map(l => sourceColors[l.name] || sourceColors['อื่น ๆ']);

        const treeLayout = getBaseLayout(theme);
        Object.assign(treeLayout, {
          height: 440,
          margin: { l: 4, r: 4, t: 4, b: 4 },
          uniformtext: { minsize: 11, mode: 'hide' },
        });

        treemapFigure = {
          data: [
            {
              type: 'treemap',
              labels: tLabels,
              parents: tParents,
              values: tValues,
              text: tTexts,
              customdata: tCustom,
              textinfo: 'text',
              hoverinfo: 'text',
              marker: { colors: tColors },
              textfont: { family: FONT_FAMILY, size: 13 },
              root_color: 'rgba(0,0,0,0)',
              pathbar: { visible: false },
            },
          ],
          layout: treeLayout,
        };
      }
    } else {
      // Multi-region mode (5 regions)
      const tLabels = [];
      const tParents = [];
      const tValues = [];
      const tTexts = [];
      const tCustom = [];
      const tColors = [];

      DB.meta.regions.filter(r => r.region_id > 0).forEach(reg => {
        const rRow = DB.income.find(i => i.year_be === year && i.region_id === reg.region_id && i.area_type_id === area);
        if (rRow) {
          const tot = rRow.monthly_income;
          const s1 = roundVal(100.0 * rRow.from_work / tot, 1);
          const s2 = roundVal(100.0 * rRow.current_transfer / tot, 1);
          const s3 = roundVal(100.0 * rRow.nonmoney_income / tot, 1);
          const s4 = roundVal(100.0 - (s1 + s2 + s3), 1);
          const otherAmt = rRow.property_income + rRow.noncur_m_income;

          const groups = [
            { name: 'จากการทำงาน', amount: rRow.from_work, share: s1 },
            { name: 'เงินโอน/สวัสดิการ', amount: rRow.current_transfer, share: s2 },
            { name: 'ไม่เป็นตัวเงิน', amount: rRow.nonmoney_income, share: s3 },
            { name: 'อื่น ๆ', amount: otherAmt, share: s4 },
          ];

          const regId = `REG_${reg.region_id}`;
          const childrenSum = groups.reduce((acc, g) => acc + g.amount, 0);

          tLabels.push(regId);
          tParents.push('');
          tValues.push(childrenSum > 0 ? childrenSum : tot);
          tTexts.push(`<b>${reg.short_th} · ${tot.toLocaleString(undefined, { maximumFractionDigits: 0 })} บาท</b>`);
          tCustom.push([100.0, reg.short_th]);
          tColors.push(t.surface_2);

          groups.forEach(g => {
            const childId = `${regId}_${g.name}`;
            tLabels.push(childId);
            tParents.push(regId);
            tValues.push(g.amount);
            tTexts.push(`${g.name}<br>${g.share.toFixed(1)}%`);
            tCustom.push([g.share, g.name]);
            tColors.push(sourceColors[g.name] || sourceColors['อื่น ๆ']);
          });
        }
      });

      const treeLayout = getBaseLayout(theme);
      Object.assign(treeLayout, {
        height: 440,
        margin: { l: 4, r: 4, t: 4, b: 4 },
        uniformtext: { minsize: 11, mode: 'hide' },
      });

      treemapFigure = {
        data: [
          {
            type: 'treemap',
            branchvalues: 'total',
            labels: tLabels,
            parents: tParents,
            values: tValues,
            text: tTexts,
            customdata: tCustom,
            textinfo: 'text',
            hoverinfo: 'text',
            marker: {
              colors: tColors,
              pad: { t: 28, l: 3, r: 3, b: 3 },
            },
            textfont: { family: FONT_FAMILY, size: 12 },
            root_color: 'rgba(0,0,0,0)',
            pathbar: { visible: false },
          },
        ],
        layout: treeLayout,
      };
    }

    return {
      status_line: status_line,
      kpis: kpis,
      charts: {
        choropleth: {
          figure: { data: choroTraces, layout: choroLayout },
          read_guide: 'สีเข้ม = รายได้สูง · คลิกภาคบนแผนที่เพื่อกรอง',
          note: 'รายได้เฉลี่ยต่อเดือนของครัวเรือน (สสช. 2554–2568)',
          empty: null,
        },
        trend: {
          figure: { data: trendTraces, layout: trendLayout },
          read_guide: 'คลิกจุดเพื่อเลือกปี · คลิกเส้นเพื่อเลือกภาค',
          note: 'สำรวจทุก 2 ปี รวม 8 รอบสำรวจ',
          empty: null,
        },
        heatmap: {
          figure: heatFigure,
          read_guide: 'สีเข้ม = ในเมืองได้มากกว่าชนบทมาก · เส้นประ = ทั้งประเทศ',
          note: 'ช่องว่าง (%) = (ในเขต − นอกเขต) ÷ นอกเขต × 100',
          empty: null,
        },
        treemap: {
          figure: treemapFigure,
          read_guide: 'แบ่งสัดส่วนตามยอดรวมของแต่ละภาค (ผลรวมเท่ากับ 100%)',
          note: 'แหล่งรายได้ 4 หมวดหลักตามแบบสำรวจ สสช.',
          empty: null,
        },
      },
      notes: [
        'รายได้เฉลี่ยต่อเดือนของครัวเรือน จากการสำรวจภาวะเศรษฐกิจและสังคมของครัวเรือน (สสช.)',
        'ข้อมูลมีเฉพาะปีสำรวจทุก 2 ปี (8 รอบ 2554–2568) ไม่เติมค่าข้ามปีที่ขาด',
        'ตัวเลขเป็นราคาตามปี (nominal) ไม่ปรับอัตราเงินเฟ้อ',
      ],
      as_of: DB.meta.as_of,
    };
  }

  // ──────────────── Tab 2 Calculations & Charts ────────────────
  function handleTab2(params) {
    const year = params.year || 2568;
    const pt = params.pt || 1;
    const region = (params.region !== undefined && params.region !== null && params.region !== '') ? parseInt(params.region, 10) : null;
    const theme = params.theme || 'dark';
    const metric = params.metric || 'hpi';
    const grain = params.grain || 'yearly';
    const t = TOKENS[theme] || TOKENS.dark;
    const gj = getGeoJson();

    const regInfo = region !== null ? DB.meta.regions.find(r => r.region_id === region) : null;
    const scope = regInfo ? regInfo.short_th : 'ทั่วประเทศ';
    const ptInfo = DB.meta.property_types.find(p => p.property_type_id === pt);
    const ptName = ptInfo ? ptInfo.name_th : 'รวมทุกประเภทที่อยู่อาศัย';

    const status_line = `${scope} · ปี ${year} · ${ptName}`;
    const targetRid = region !== null ? region : 0;

    const curAnnual = DB.hpi_annual.find(r => r.year_be === year && r.region_id === targetRid && r.property_type_id === pt);
    const baseAnnual = DB.hpi_annual.find(r => r.year_be === 2554 && r.region_id === targetRid && r.property_type_id === pt);
    const prevAnnual = DB.hpi_annual.find(r => r.year_be === year - 1 && r.region_id === targetRid && r.property_type_id === pt);

    const idxVal = curAnnual ? curAnnual.index_mean12 : 100.0;
    const baseVal = baseAnnual ? baseAnnual.index_mean12 : 100.0;
    const isBaseYear = (year === 2554);
    const yearsSpan = year - 2554;
    const cagrVal = yearsSpan > 0 ? cagr_pct(baseVal, idxVal, yearsSpan) : null;
    const yoyVal = (!isBaseYear && curAnnual && prevAnnual && prevAnnual.index_mean12)
      ? roundVal(100.0 * (curAnnual.index_mean12 / prevAnnual.index_mean12 - 1.0), 2)
      : null;

    // Fastest region from 2554 to year
    let fastestReg = null;
    let fastestGrowth = -Infinity;
    let fastestIdx = 100.0;
    DB.meta.regions.filter(r => r.region_id > 0).forEach(r => {
      const cRow = DB.hpi_annual.find(a => a.year_be === year && a.region_id === r.region_id && a.property_type_id === pt);
      const bRow = DB.hpi_annual.find(a => a.year_be === 2554 && a.region_id === r.region_id && a.property_type_id === pt);
      if (cRow && bRow && bRow.index_mean12) {
        const growth = cRow.index_mean12 / bRow.index_mean12;
        if (growth > fastestGrowth) {
          fastestGrowth = growth;
          fastestReg = r.short_th;
          fastestIdx = cRow.index_mean12;
        }
      }
    });

    const fastestCagr = (yearsSpan > 0 && fastestIdx) ? cagr_pct(100.0, fastestIdx, yearsSpan) : 0.0;

    const kpis = [
      {
        id: 'hpi',
        label: `ดัชนีราคาบ้าน ปี ${year}`,
        value: roundVal(idxVal, 1),
        unit: '(2554=100)',
        delta: null,
      },
      {
        id: 'yoy',
        label: `YoY ปี ${year}`,
        value: yoyVal !== null ? `${yoyVal >= 0 ? '+' : ''}${yoyVal.toFixed(2)}%` : '—',
        unit: yoyVal !== null ? 'เทียบปีก่อน' : '(ปีฐาน)',
        delta: null,
      },
      {
        id: 'cagr',
        label: `CAGR 2554→${year}`,
        value: cagrVal !== null ? roundVal(cagrVal, 2) : '—',
        unit: cagrVal !== null ? '%/ปี' : '(ปีฐาน)',
        delta: (cagrVal !== null && !isBaseYear) ? {
          value: roundVal(Math.abs(cagrVal), 2),
          unit: '%',
          vs: '2554',
          direction: cagrVal >= 0 ? 'up' : 'down',
        } : null,
      },
      {
        id: 'fastest',
        label: 'ภาคที่โตเร็วสุด',
        value: fastestReg || '—',
        unit: (fastestReg && fastestCagr) ? `CAGR ${fastestCagr.toFixed(2)}%/ปี` : '',
        delta: null,
      },
    ];

    let emptyNotice = null;
    if (pt === 3 && (region === 3 || region === 4)) {
      emptyNotice = 'ไม่มีข้อมูลทาวน์เฮ้าส์ของภาคนี้ในฐานข้อมูล ธปท.';
    }

    // ──────────────── Chart 2A: Choropleth ────────────────
    const choroData = [];
    DB.meta.regions.filter(r => r.region_id > 0).forEach(r => {
      const cRow = DB.hpi_annual.find(a => a.year_be === year && a.region_id === r.region_id && a.property_type_id === pt);
      const bRow = DB.hpi_annual.find(a => a.year_be === 2554 && a.region_id === r.region_id && a.property_type_id === pt);
      const pRow = DB.hpi_annual.find(a => a.year_be === year - 1 && a.region_id === r.region_id && a.property_type_id === pt);
      if (cRow) {
        let val = cRow.index_mean12;
        if (metric === 'yoy') {
          val = (pRow && pRow.index_mean12) ? roundVal(100.0 * (cRow.index_mean12 / pRow.index_mean12 - 1.0), 2) : 0.0;
        } else if (metric === 'cagr') {
          val = (bRow && yearsSpan > 0) ? (cagr_pct(bRow.index_mean12, cRow.index_mean12, yearsSpan) || 0.0) : 0.0;
        }
        choroData.push({
          region_id: r.region_id,
          code: r.code,
          short_th: r.short_th,
          value: val,
        });
      }
    });

    const presentIds = new Set(choroData.map(r => r.region_id));
    const allIds = new Set([1, 2, 3, 4, 5]);
    const missingIds = [...allIds].filter(id => !presentIds.has(id));

    const mLabel = metric === 'hpi' ? 'ดัชนี' : (metric === 'yoy' ? 'YoY' : 'CAGR');
    const uLabel = metric === 'hpi' ? '(2554=100)' : '%/ปี';

    const choroTraces = [];

    if (missingIds.length > 0) {
      const missingNames = { 3: 'เหนือ', 4: 'อีสาน' };
      const mCustom = missingIds.map(mid => `${missingNames[mid] || ''}<br>ไม่มีข้อมูล<br>${ptName}`);
      const mColor = theme === 'dark' ? '#232D3F' : '#E5E7EB';
      choroTraces.push({
        type: 'choroplethmap',
        geojson: gj,
        locations: missingIds,
        z: missingIds.map(() => 0),
        featureidkey: 'properties.region_id',
        colorscale: [[0, mColor], [1, mColor]],
        showscale: false,
        customdata: mCustom,
        hovertemplate: '%{customdata}<extra></extra>',
        marker: { line: { color: t.border, width: 0.5 }, opacity: 0.7 },
      });
    }

    if (choroData.length > 0) {
      const locs = choroData.map(r => r.region_id);
      const vals = choroData.map(r => r.value);
      const custom = choroData.map(r => `${r.short_th}<br>${mLabel} ${r.value.toLocaleString(undefined, { maximumFractionDigits: 1 })} ${uLabel}<br>${ptName} · ปี ${year}`);

      choroTraces.push({
        type: 'choroplethmap',
        geojson: gj,
        locations: locs,
        z: vals,
        featureidkey: 'properties.region_id',
        colorscale: CHOROPLETH_HOUSING_SCALE,
        customdata: custom,
        hovertemplate: '%{customdata}<extra></extra>',
        marker: { line: { color: t.border, width: 0.5 }, opacity: 0.85 },
        colorbar: {
          orientation: 'h',
          x: 0.03,
          y: 0.03,
          xanchor: 'left',
          yanchor: 'bottom',
          thickness: 10,
          outlinewidth: 0,
          tickfont: { family: FONT_FAMILY, color: t.text_muted, size: 11 },
          tickformat: metric === 'hpi' ? ',.1f' : '+,.1f',
          title: { text: '' },
        },
      });

      if (region && locs.includes(region)) {
        const sRow = choroData.find(r => r.region_id === region);
        choroTraces.push({
          type: 'choroplethmap',
          geojson: gj,
          locations: [region],
          z: [sRow ? sRow.value : 0],
          featureidkey: 'properties.region_id',
          colorscale: CHOROPLETH_HOUSING_SCALE,
          showscale: false,
          marker: { line: { color: t.text, width: 3 }, opacity: 0.9 },
          hoverinfo: 'skip',
        });
      }

      const lons = [], lats = [], texts = [];
      choroData.forEach(r => {
        const coords = REGION_LABEL_COORDS[r.region_id];
        if (coords) {
          lons.push(coords.lon);
          lats.push(coords.lat);
          texts.push(`<b>${r.short_th}</b><br>${r.value.toFixed(1)}`);
        }
      });

      choroTraces.push({
        type: 'scattermap',
        mode: 'text',
        lon: lons,
        lat: lats,
        text: texts,
        textfont: { family: FONT_FAMILY, size: 12, color: t.text },
        hoverinfo: 'skip',
      });
    }

    const choroLayout = getBaseLayout(theme);
    Object.assign(choroLayout, {
      height: 560,
      margin: { l: 0, r: 0, t: 0, b: 0 },
      map: {
        style: theme === 'dark' ? 'carto-darkmatter' : 'carto-positron',
        center: { lat: 13.0, lon: 101.2 },
        zoom: 4.6,
      },
    });

    // ──────────────── Chart 2B: Trend (Annual or Monthly) ────────────────
    const trendTraces = [];
    const trendShapes = [];
    const trendAnnotations = [];
    const isMonthly = (grain === 'monthly');

    DB.meta.regions.forEach(reg => {
      const isNational = reg.is_national;
      const rid = reg.region_id;
      const isSelected = (region !== null && region === rid) || (region === null && isNational);
      const hasAnySelected = region !== null && region > 0;

      let opacity = 1.0;
      let lineWidth = 2.5;
      if (hasAnySelected && !isSelected) {
        opacity = 0.3;
        lineWidth = 1.5;
      } else if (isSelected) {
        opacity = 1.0;
        lineWidth = 3.5;
      }

      const color = regionColor(reg.short_th, theme);
      const fillMode = (isSelected && !isNational) ? 'tozeroy' : 'none';

      let xs = [];
      let ys = [];

      if (isMonthly) {
        const rows = DB.hpi_monthly
          .filter(m => m.region_id === rid && m.property_type_id === pt)
          .sort((a, b) => a.month_id - b.month_id);
        xs = rows.map(r => `${r.year_be}-${String(r.month_no).padStart(2, '0')}`);
        ys = rows.map(r => r.index_value);
      } else {
        const rows = DB.hpi_annual
          .filter(a => a.region_id === rid && a.property_type_id === pt)
          .sort((a, b) => a.year_be - b.year_be);
        xs = rows.map(r => String(r.year_be));
        ys = rows.map(r => r.index_mean12);
      }

      if (xs.length > 0) {
        trendTraces.push({
          type: 'scatter',
          x: xs,
          y: ys,
          mode: isMonthly ? 'lines' : 'lines+markers',
          name: reg.short_th,
          line: {
            color: color,
            dash: regionDash(isNational),
            width: lineWidth,
          },
          fill: fillMode,
          fillcolor: theme === 'light' ? 'rgba(255, 122, 26, 0.08)' : 'rgba(255, 138, 61, 0.08)',
          opacity: opacity,
          marker: { size: 5, line: { color: t.surface, width: 2 } },
          customdata: Array(xs.length).fill(rid),
          hovertemplate: `${reg.short_th}: %{y:.1f}<extra></extra>`,
        });

        trendTraces.push({
          type: 'scatter',
          x: [xs[xs.length - 1]],
          y: [ys[ys.length - 1]],
          mode: 'text',
          name: reg.short_th,
          customdata: [rid],
          text: [`  ${reg.short_th}`],
          textposition: 'middle right',
          textfont: { family: FONT_FAMILY, size: 11, color: color },
          hoverinfo: 'skip',
          showlegend: false,
          opacity: opacity,
        });
      }
    });

    const trendLayout = getBaseLayout(theme);
    const trendXaxis = {
      ...trendLayout.xaxis,
      type: 'category',
      showspikes: true,
      spikethickness: 1,
      spikecolor: t.grid,
      spikemode: 'across',
      tickangle: 0,
    };

    if (isMonthly) {
      const years = DB.meta.hpi_years;
      trendXaxis.tickmode = 'array';
      trendXaxis.tickvals = years.map(y => `${y}-01`);
      trendXaxis.ticktext = years.map(String);
    }

    Object.assign(trendLayout, {
      margin: { l: 48, r: 60, t: 8, b: 32 },
      xaxis: trendXaxis,
      yaxis: {
        ...trendLayout.yaxis,
        title: { text: '' },
        tickformat: ',.0f',
      },
      height: 320,
      hovermode: 'x unified',
      shapes: trendShapes,
      annotations: trendAnnotations,
    });

    // ──────────────── Chart 2C: Heatmap (YoY %) ────────────────
    const regionOrder = ['กทม.+ปริมณฑล', 'กลาง', 'เหนือ', 'อีสาน', 'ใต้', 'ทั่วประเทศ'];
    const yCategories = [...regionOrder].reverse();
    const xYears = DB.meta.hpi_years.map(String);

    const yoyLookup = {};
    DB.meta.regions.forEach(reg => {
      DB.meta.hpi_years.forEach(yr => {
        const cur = DB.hpi_annual.find(a => a.year_be === yr && a.region_id === reg.region_id && a.property_type_id === pt);
        const prev = DB.hpi_annual.find(a => a.year_be === yr - 1 && a.region_id === reg.region_id && a.property_type_id === pt);
        if (cur && prev && prev.index_mean12) {
          yoyLookup[`${reg.short_th}_${yr}`] = roundVal(100.0 * (cur.index_mean12 / prev.index_mean12 - 1.0), 2);
        }
      });
    });

    const zHeat = [];
    const textHeat = [];
    yCategories.forEach(regName => {
      const rowZ = [];
      const rowT = [];
      xYears.forEach(yr => {
        const val = yoyLookup[`${regName}_${yr}`];
        rowZ.push(val !== undefined ? val : null);
        rowT.push(val !== undefined && val !== null ? `${Math.round(val)}%` : '');
      });
      zHeat.push(rowZ);
      textHeat.push(rowT);
    });

    const heatShapes = [
      {
        type: 'line',
        x0: -0.5,
        x1: xYears.length - 0.5,
        y0: 0.5,
        y1: 0.5,
        line: { color: t.text_muted, width: 1, dash: 'dot' },
      },
    ];

    const yrStr = String(year);
    if (xYears.includes(yrStr)) {
      const colIdx = xYears.indexOf(yrStr);
      heatShapes.push({
        type: 'rect',
        x0: colIdx - 0.48,
        x1: colIdx + 0.48,
        y0: -0.48,
        y1: yCategories.length - 0.52,
        line: { color: t.text, width: 2 },
        fillcolor: 'rgba(0,0,0,0)',
      });
    }

    if (region !== null) {
      const targetRegObj = DB.meta.regions.find(r => r.region_id === region);
      if (targetRegObj && yCategories.includes(targetRegObj.short_th)) {
        const rowIdx = yCategories.indexOf(targetRegObj.short_th);
        heatShapes.push({
          type: 'rect',
          x0: -0.48,
          x1: xYears.length - 0.52,
          y0: rowIdx - 0.48,
          y1: rowIdx + 0.48,
          line: { color: t.text, width: 2 },
          fillcolor: 'rgba(0,0,0,0)',
        });
      }
    }

    const heatLayout = getBaseLayout(theme);
    Object.assign(heatLayout, {
      margin: { l: 48, r: 48, t: 8, b: 28 },
      xaxis: { ...heatLayout.xaxis, type: 'category' },
      yaxis: { ...heatLayout.yaxis, type: 'category', showgrid: true },
      height: 280,
      shapes: heatShapes,
    });

    const heatFigure = {
      data: [
        {
          type: 'heatmap',
          z: zHeat,
          x: xYears,
          y: yCategories,
          text: textHeat,
          texttemplate: '%{text}',
          textfont: { family: FONT_FAMILY, size: 11.5 },
          colorscale: get_heatmap_yoy_scale(theme),
          zmid: 0,
          xgap: 4,
          ygap: 4,
          hovertemplate: '%{y} ปี %{x}<br>YoY: %{z:.1f}%<extra></extra>',
          colorbar: {
            thickness: 10,
            outlinewidth: 0,
            tickfont: { family: FONT_FAMILY, color: t.text_muted, size: 10 },
            title: { text: '' },
          },
        },
      ],
      layout: heatLayout,
    };

    return {
      status_line: status_line,
      kpis: kpis,
      charts: {
        choropleth: {
          figure: { data: choroTraces, layout: choroLayout },
          read_guide: 'สีเข้ม = ดัชนีสูง · สีเทา = ไม่มีข้อมูล · คลิกภาคเพื่อกรอง',
          note: 'ที่มา: ธปท. (EC_EI_008_S4 ฐาน 2554=100)',
          empty: emptyNotice,
        },
        trend: {
          figure: { data: trendTraces, layout: trendLayout },
          read_guide: 'คลิกจุดเพื่อเลือกปี · คลิกเส้นเพื่อเลือกภาค',
          note: 'เฉลี่ยเคลื่อนที่ 3 เดือน · ม.ค. 2566 เพิ่มฐานข้อมูลสถาบันการเงินเฉพาะกิจ',
          empty: emptyNotice,
        },
        heatmap: {
          figure: heatFigure,
          read_guide: 'ฟ้า = ติดลบ · ส้ม = ขยายตัว · คลิกช่องเพื่อเลือกภาคและปีพร้อมกัน',
          note: 'ดัชนีบอกการเปลี่ยนแปลง ไม่ใช่ระดับราคาบ้านเป็นบาท',
          empty: emptyNotice,
        },
      },
      notes: [
        'ดัชนีราคาที่อยู่อาศัย (2554=100) ธนาคารแห่งประเทศไทย (BoT EC_EI_008_S4)',
        'ดัชนีคำนวณด้วย Hedonic regression แบบเฉลี่ยเคลื่อนที่ 3 เดือน จากฐานข้อมูลสินเชื่อ',
        'ภาคเหนือและอีสานไม่มีชุดข้อมูลทาวน์เฮ้าส์ (ดัชนีรวมทุกประเภทจึงเท่ากับบ้านเดี่ยว)',
        'ตั้งแต่ ม.ค. 2566 เพิ่มฐานข้อมูลของสถาบันการเงินเฉพาะกิจ',
      ],
      as_of: DB.meta.as_of,
    };
  }

  // ──────────────── Tab 3 Calculations & Charts ────────────────
  function handleTab3(params) {
    const y0 = params.y0 || 2554;
    const y1 = params.y1 || 2568;
    const pt = params.pt || 1;
    const region = (params.region !== undefined && params.region !== null && params.region !== '') ? parseInt(params.region, 10) : null;
    const theme = params.theme || 'dark';
    const cagrView = params.cagr_view || 'summary';
    const t = TOKENS[theme] || TOKENS.dark;
    const colors = SEMANTIC_COLORS[theme] || SEMANTIC_COLORS.dark;

    const regInfo = region !== null ? DB.meta.regions.find(r => r.region_id === region) : null;
    const scope = regInfo ? regInfo.short_th : 'ทั่วประเทศ';
    const ptInfo = DB.meta.property_types.find(p => p.property_type_id === pt);
    const ptName = ptInfo ? ptInfo.name_th : 'รวมทุกประเภทที่อยู่อาศัย';

    const status_line = `${scope} · ${ptName} · ${y0}–${y1}`;

    // 1. Build Price-to-Income Data rebased so that y0 = 100
    // Income index per region (area_type_id = 0)
    const surveyYears = DB.meta.income_years.filter(y => y >= y0 && y <= y1);

    const ptiData = [];
    DB.meta.regions.forEach(reg => {
      const rid = reg.region_id;
      // Get base rows at y0
      const incBaseRow = DB.income.find(i => i.year_be === y0 && i.region_id === rid && i.area_type_id === 0);
      const hpiBaseRow = DB.hpi_annual.find(a => a.year_be === y0 && a.region_id === rid && a.property_type_id === pt);

      const incBase = incBaseRow ? incBaseRow.monthly_income : 1;
      const hpiBase = hpiBaseRow ? hpiBaseRow.index_mean12 : 1;

      surveyYears.forEach(yr => {
        const incRow = DB.income.find(i => i.year_be === yr && i.region_id === rid && i.area_type_id === 0);
        const hpiRow = DB.hpi_annual.find(a => a.year_be === yr && a.region_id === rid && a.property_type_id === pt);

        if (incRow && hpiRow) {
          const newInc = incBase ? (100.0 * incRow.monthly_income / incBase) : 100.0;
          const newHpi = hpiBase ? (100.0 * hpiRow.index_mean12 / hpiBase) : 100.0;
          const newPti = newInc ? (100.0 * (newHpi / 100.0) / (newInc / 100.0)) : 100.0;

          ptiData.push({
            year_be: yr,
            region_id: rid,
            code: reg.code,
            short_th: reg.short_th,
            is_national: reg.is_national,
            income_index: roundVal(newInc, 2),
            hpi_index: roundVal(newHpi, 2),
            price_to_income_index: roundVal(newPti, 2),
          });
        }
      });
    });

    const targetRid = region !== null ? region : 0;
    const targetEndRow = ptiData.find(r => r.region_id === targetRid && r.year_be === y1);

    const ptiVal = targetEndRow ? targetEndRow.price_to_income_index : 100.0;
    const hpiEnd = targetEndRow ? targetEndRow.hpi_index : 100.0;
    const incEnd = targetEndRow ? targetEndRow.income_index : 100.0;

    let statusText = 'ระดับคงที่';
    let statusDir = 'neutral';
    if (ptiVal > 100.5) {
      statusText = 'ซื้อยากขึ้น';
      statusDir = 'danger';
    } else if (ptiVal < 99.5) {
      statusText = 'ซื้อง่ายขึ้น';
      statusDir = 'success';
    }

    // CAGR Calculations for KPIs
    const incStart = DB.income.find(i => i.year_be === y0 && i.region_id === targetRid && i.area_type_id === 0);
    const incEndRow = DB.income.find(i => i.year_be === y1 && i.region_id === targetRid && i.area_type_id === 0);
    const hpiStart = DB.hpi_annual.find(a => a.year_be === y0 && a.region_id === targetRid && a.property_type_id === pt);
    const hpiEndRow = DB.hpi_annual.find(a => a.year_be === y1 && a.region_id === targetRid && a.property_type_id === pt);

    const span = y1 - y0;
    const incCagr = (incStart && incEndRow && span > 0) ? cagr_pct(incStart.monthly_income, incEndRow.monthly_income, span) : 0.0;
    const hpiCagr = (hpiStart && hpiEndRow && span > 0) ? cagr_pct(hpiStart.index_mean12, hpiEndRow.index_mean12, span) : 0.0;
    const gap = roundVal((hpiCagr || 0) - (incCagr || 0), 2);
    const gapSign = gap > 0 ? '+' : '';

    const kpis = [
      {
        id: 'pti',
        label: `ดัชนีราคา ÷ รายได้ ปี ${y1}`,
        value: roundVal(ptiVal, 1),
        unit: `(${statusText})`,
        subline: `ราคาบ้าน ${hpiEnd.toFixed(1)} ÷ รายได้ ${incEnd.toFixed(1)}`,
        status: statusDir,
        delta: null,
      },
      {
        id: 'inc_cagr',
        label: `CAGR รายได้ ${y0}→${y1}`,
        value: incCagr !== null ? roundVal(incCagr, 2) : '—',
        unit: '%/ปี',
        delta: null,
      },
      {
        id: 'hpi_cagr',
        label: `CAGR ราคาบ้าน ${y0}→${y1}`,
        value: hpiCagr !== null ? roundVal(hpiCagr, 2) : '—',
        unit: '%/ปี',
        delta: null,
      },
      {
        id: 'gap',
        label: 'ช่องว่าง CAGR (บ้าน − รายได้)',
        value: `${gapSign}${gap.toFixed(2)}`,
        unit: 'จุดเปอร์เซ็นต์',
        delta: null,
      },
    ];

    // ──────────────── Chart 3A: Hero (Price-to-Income Ratio) ────────────────
    const allPtiVals = ptiData.map(r => r.price_to_income_index);
    const minVal = allPtiVals.length > 0 ? Math.min(...allPtiVals) : 95.0;
    const maxVal = allPtiVals.length > 0 ? Math.max(...allPtiVals) : 150.0;

    const yMin = Math.min(95.0, minVal - 5.0);
    const yMax = maxVal + 10.0;

    const heroShapes = [
      {
        type: 'rect',
        xref: 'paper',
        x0: 0,
        x1: 1,
        y0: 100,
        y1: yMax,
        fillcolor: colors.housing,
        opacity: 0.07,
        line: { width: 0 },
        layer: 'below',
      },
      {
        type: 'rect',
        xref: 'paper',
        x0: 0,
        x1: 1,
        y0: yMin,
        y1: 100,
        fillcolor: colors.income,
        opacity: 0.07,
        line: { width: 0 },
        layer: 'below',
      },
      {
        type: 'line',
        xref: 'paper',
        x0: 0,
        x1: 1,
        y0: 100,
        y1: 100,
        line: { color: t.text_muted, width: 1.5, dash: 'dash' },
      },
    ];

    const heroAnnotations = [
      {
        xref: 'paper',
        x: 0.01,
        y: 100,
        text: '100 = ราคาบ้านกับรายได้โตเท่ากัน',
        showarrow: false,
        xanchor: 'left',
        yanchor: 'bottom',
        font: { family: FONT_FAMILY, size: 11, color: t.text_muted },
      },
      {
        xref: 'paper',
        x: 0.01,
        y: yMax - 2,
        text: 'ซื้อยากขึ้น (ราคาบ้านพุ่งแซงรายได้)',
        showarrow: false,
        xanchor: 'left',
        font: { family: FONT_FAMILY, size: 12, color: colors.housing, weight: 600 },
      },
      {
        xref: 'paper',
        x: 0.01,
        y: yMin + 2,
        text: 'ซื้อง่ายขึ้น (รายได้โตแซงราคาบ้าน)',
        showarrow: false,
        xanchor: 'left',
        font: { family: FONT_FAMILY, size: 12, color: colors.income, weight: 600 },
      },
    ];

    const heroTraces = [];
    DB.meta.regions.forEach(reg => {
      const isNational = reg.is_national;
      const rid = reg.region_id;
      const isSelected = (region !== null && region === rid) || (region === null && isNational);

      let color = regionColor(reg.short_th, theme);
      let width = 1.5;
      let opacity = 0.35;

      if (isSelected) {
        color = isNational ? t.text : regionColor(reg.short_th, theme);
        width = 4.0;
        opacity = 1.0;
      }

      const rows = ptiData.filter(r => r.region_id === rid).sort((a, b) => a.year_be - b.year_be);
      if (rows.length > 0) {
        const xs = rows.map(r => String(r.year_be));
        const ys = rows.map(r => r.price_to_income_index);

        const custom = rows.map(r => {
          const diff = r.price_to_income_index - 100.0;
          const s = diff > 0 ? '+' : '';
          return [reg.short_th, r.price_to_income_index, r.income_index, r.hpi_index, `${s}${diff.toFixed(1)}%`];
        });

        heroTraces.push({
          type: 'scatter',
          x: xs,
          y: ys,
          mode: 'lines+markers',
          name: reg.short_th,
          line: { color: color, width: width, dash: regionDash(isNational) },
          marker: { size: 5, line: { color: t.surface, width: 2 } },
          customdata: custom,
          hovertemplate: '<b>ปี %{x} · %{customdata[0]}</b><br>อัตราส่วนราคา÷รายได้: <b>%{customdata[1]:.1f}</b><br>ดัชนีราคาบ้าน: %{customdata[3]:.1f}<br>ดัชนีรายได้: %{customdata[2]:.1f}<br>เทียบต้นช่วง: %{customdata[4]}<extra></extra>',
          opacity: opacity,
        });

        const lastVal = ys[ys.length - 1];
        const sText = lastVal > 100 ? 'ซื้อยากขึ้น' : 'ซื้อง่ายขึ้น';
        const lblText = isSelected ? `  <b>${lastVal.toFixed(1)}</b> (${sText})` : `  ${lastVal.toFixed(1)}`;

        heroTraces.push({
          type: 'scatter',
          x: [xs[xs.length - 1]],
          y: [lastVal],
          mode: 'text',
          text: [lblText],
          textposition: 'middle right',
          textfont: { family: FONT_FAMILY, size: 11, color: color },
          hoverinfo: 'skip',
          showlegend: false,
          opacity: opacity,
        });
      }
    });

    const heroLayout = getBaseLayout(theme);
    Object.assign(heroLayout, {
      margin: { l: 48, r: 120, t: 8, b: 28 },
      xaxis: { ...heroLayout.xaxis, type: 'category' },
      yaxis: {
        ...heroLayout.yaxis,
        range: [yMin, yMax],
        title: { text: `ดัชนีราคาบ้าน ÷ ดัชนีรายได้ (ปี ${y0} = 100)` },
      },
      height: 400,
      hovermode: 'closest',
      shapes: heroShapes,
      annotations: heroAnnotations,
    });

    // ──────────────── Chart 3B: CAGR Comparison ────────────────
    const cagrTraces = [];
    let cats = [];
    let incVals = [];
    let hpiVals = [];

    if (cagrView === 'by_type') {
      if (targetRid === 3 || targetRid === 4) {
        cats = ['ภาพรวม = บ้านเดี่ยว'];
        const s = DB.hpi_annual.find(a => a.year_be === y0 && a.region_id === targetRid && a.property_type_id === 1);
        const e = DB.hpi_annual.find(a => a.year_be === y1 && a.region_id === targetRid && a.property_type_id === 1);
        const hVal = (s && e && span > 0) ? (cagr_pct(s.index_mean12, e.index_mean12, span) || 0.0) : 0.0;
        incVals = [incCagr || 0.0];
        hpiVals = [hVal];
      } else {
        DB.meta.property_types.forEach(p => {
          cats.push(p.name_th);
          incVals.push(incCagr || 0.0);
          const s = DB.hpi_annual.find(a => a.year_be === y0 && a.region_id === targetRid && a.property_type_id === p.property_type_id);
          const e = DB.hpi_annual.find(a => a.year_be === y1 && a.region_id === targetRid && a.property_type_id === p.property_type_id);
          const hVal = (s && e && span > 0) ? (cagr_pct(s.index_mean12, e.index_mean12, span) || 0.0) : 0.0;
          hpiVals.push(hVal);
        });
      }
    } else if (cagrView === 'by_region') {
      DB.meta.regions.forEach(r => {
        cats.push(r.short_th);
        const sInc = DB.income.find(i => i.year_be === y0 && i.region_id === r.region_id && i.area_type_id === 0);
        const eInc = DB.income.find(i => i.year_be === y1 && i.region_id === r.region_id && i.area_type_id === 0);
        const sHpi = DB.hpi_annual.find(a => a.year_be === y0 && a.region_id === r.region_id && a.property_type_id === pt);
        const eHpi = DB.hpi_annual.find(a => a.year_be === y1 && a.region_id === r.region_id && a.property_type_id === pt);

        const iVal = (sInc && eInc && span > 0) ? (cagr_pct(sInc.monthly_income, eInc.monthly_income, span) || 0.0) : 0.0;
        const hVal = (sHpi && eHpi && span > 0) ? (cagr_pct(sHpi.index_mean12, eHpi.index_mean12, span) || 0.0) : 0.0;

        incVals.push(iVal);
        hpiVals.push(hVal);
      });
    } else {
      // Summary mode
      cats = [`<b>${scope}</b>`];
      incVals = [incCagr || 0.0];
      hpiVals = [hpiCagr || 0.0];
    }

    cagrTraces.push({
      type: 'bar',
      x: cats,
      y: incVals,
      name: 'CAGR รายได้ครัวเรือน',
      marker: { color: colors.income, cornerradius: 6 },
      text: incVals.map(v => `${v >= 0 ? '+' : ''}${v.toFixed(2)}% ต่อปี`),
      textposition: 'outside',
      textfont: { family: FONT_FAMILY, size: 11.5, color: t.text },
      hovertemplate: '%{x}<br>รายได้: %{y:.2f}%/ปี<extra></extra>',
    });

    cagrTraces.push({
      type: 'bar',
      x: cats,
      y: hpiVals,
      name: 'CAGR ราคาบ้าน',
      marker: { color: colors.housing, cornerradius: 6 },
      text: hpiVals.map(v => `${v >= 0 ? '+' : ''}${v.toFixed(2)}% ต่อปี`),
      textposition: 'outside',
      textfont: { family: FONT_FAMILY, size: 11.5, color: t.text },
      hovertemplate: '%{x}<br>ราคาบ้าน: %{y:.2f}%/ปี<extra></extra>',
    });

    const allBarVals = [...incVals, ...hpiVals];
    const maxBar = Math.max(...allBarVals, 0);
    const minBar = Math.min(...allBarVals, 0);
    const yBarMax = maxBar > 0 ? maxBar * 1.3 : 5.0;
    const yBarMin = minBar < 0 ? minBar * 1.3 : 0.0;

    const cagrLayout = getBaseLayout(theme);
    Object.assign(cagrLayout, {
      margin: { l: 48, r: 24, t: 20, b: 28 },
      xaxis: { ...cagrLayout.xaxis, type: 'category' },
      yaxis: {
        ...cagrLayout.yaxis,
        title: { text: '%/ปี' },
        range: [yBarMin, yBarMax],
        tickformat: '+,.1f',
      },
      barmode: 'group',
      height: 340,
    });

    let cagrNote = 'คำนวณจากอัตราเติบโตเฉลี่ยสะสมต่อปี (CAGR)';
    if (cagrView === 'by_type' && (targetRid === 3 || targetRid === 4)) {
      cagrNote = 'ภาคนี้มีเฉพาะบ้านเดี่ยว ดัชนีรวมเท่ากับบ้านเดี่ยว ไม่มีข้อมูลทาวน์เฮ้าส์ (Q-H1)';
    }

    // ──────────────── Chart 3C: Affordability Gap Area ────────────────
    const gapRows = ptiData.filter(r => r.region_id === targetRid).sort((a, b) => a.year_be - b.year_be);
    const gapXs = gapRows.map(r => String(r.year_be));
    const gapVals = gapRows.map(r => roundVal(r.hpi_index - r.income_index, 2));

    const posGaps = gapVals.map(g => Math.max(0.0, g));
    const negGaps = gapVals.map(g => Math.min(0.0, g));

    const gapCustom = gapRows.map((r, idx) => [r.hpi_index, r.income_index, gapVals[idx]]);

    const gapTraces = [
      {
        type: 'scatter',
        x: gapXs,
        y: posGaps,
        mode: 'lines',
        name: 'ราคาบ้านพุ่งแซง (ซื้อยากขึ้น)',
        line: { color: '#E5484D', width: 2 },
        fill: 'tozeroy',
        fillcolor: 'rgba(229, 72, 77, 0.20)',
        customdata: gapCustom,
        hovertemplate: '<b>ปี %{x}</b><br>ส่วนต่างราคาบ้าน − รายได้: <b>%{customdata[2]:+.1f} จุด</b><br>ดัชนีราคาบ้าน: %{customdata[0]:.1f}<br>ดัชนีรายได้: %{customdata[1]:.1f}<extra></extra>',
      },
      {
        type: 'scatter',
        x: gapXs,
        y: negGaps,
        mode: 'lines',
        name: 'รายได้โตแซง (ซื้อง่ายขึ้น)',
        line: { color: '#0E9F6E', width: 2 },
        fill: 'tozeroy',
        fillcolor: 'rgba(14, 159, 110, 0.20)',
        customdata: gapCustom,
        hovertemplate: '<b>ปี %{x}</b><br>ส่วนต่างราคาบ้าน − รายได้: <b>%{customdata[2]:+.1f} จุด</b><br>ดัชนีราคาบ้าน: %{customdata[0]:.1f}<br>ดัชนีรายได้: %{customdata[1]:.1f}<extra></extra>',
      },
    ];

    const minG = gapVals.length > 0 ? Math.min(Math.min(...gapVals), 0) - 5 : -5;
    const maxG = gapVals.length > 0 ? Math.max(Math.max(...gapVals), 0) + 5 : 5;

    const gapLayout = getBaseLayout(theme);
    Object.assign(gapLayout, {
      margin: { l: 48, r: 24, t: 20, b: 28 },
      xaxis: { ...gapLayout.xaxis, type: 'category' },
      yaxis: {
        ...gapLayout.yaxis,
        title: { text: 'ส่วนต่างดัชนี (ราคาบ้าน − รายได้)' },
        range: [minG, maxG],
        tickformat: '+,.0f',
      },
      height: 340,
      shapes: [
        {
          type: 'line',
          xref: 'paper',
          x0: 0,
          x1: 1,
          y0: 0,
          y1: 0,
          line: { color: t.text_muted, width: 1.5, dash: 'dash' },
        },
      ],
      annotations: [
        {
          xref: 'paper',
          x: 0.01,
          y: 0,
          text: '0 = รายได้กับราคาบ้านเติบโตเท่ากัน (สมดุล)',
          showarrow: false,
          xanchor: 'left',
          yanchor: 'bottom',
          font: { family: FONT_FAMILY, size: 11, color: t.text_muted },
        },
      ],
    });

    // ──────────────── Chart 3D: Growth Balance Scatter ────────────────
    const scatXs = [];
    const scatYs = [];
    const scatTexts = [];
    const scatColors = [];
    const scatSizes = [];
    const scatCustom = [];

    DB.meta.regions.forEach(reg => {
      const rid = reg.region_id;
      const rname = reg.short_th;
      const sInc = DB.income.find(i => i.year_be === y0 && i.region_id === rid && i.area_type_id === 0);
      const eInc = DB.income.find(i => i.year_be === y1 && i.region_id === rid && i.area_type_id === 0);
      const sHpi = DB.hpi_annual.find(a => a.year_be === y0 && a.region_id === rid && a.property_type_id === pt);
      const eHpi = DB.hpi_annual.find(a => a.year_be === y1 && a.region_id === rid && a.property_type_id === pt);

      const xVal = (sInc && eInc && span > 0) ? (cagr_pct(sInc.monthly_income, eInc.monthly_income, span) || 0.0) : 0.0;
      const yVal = (sHpi && eHpi && span > 0) ? (cagr_pct(sHpi.index_mean12, eHpi.index_mean12, span) || 0.0) : 0.0;
      const g = roundVal(yVal - xVal, 2);
      const isSel = (region !== null && region === rid) || (region === null && rid === 0);

      scatXs.push(xVal);
      scatYs.push(yVal);
      scatTexts.push(`  ${rname}`);
      scatColors.push(regionColor(rname, theme));
      scatSizes.push(isSel ? 20 : 14);

      const statusDesc = g > 0 ? 'ราคาบ้านโตเร็วกว่า' : 'รายได้โตเร็วกว่า';
      scatCustom.push([rname, xVal, yVal, g, statusDesc, rid]);
    });

    const allScatVals = [...scatXs, ...scatYs];
    const vMin = allScatVals.length > 0 ? Math.min(...allScatVals) - 1.0 : 0.0;
    const vMax = allScatVals.length > 0 ? Math.max(...allScatVals) + 1.2 : 6.0;

    const scatTraces = [
      {
        type: 'scatter',
        x: [vMin, vMax],
        y: [vMin, vMax],
        mode: 'lines',
        name: 'เส้นสมดุล (X = Y)',
        line: { color: t.text_muted, width: 1.5, dash: 'dash' },
        hoverinfo: 'skip',
      },
      {
        type: 'scatter',
        x: scatXs,
        y: scatYs,
        mode: 'markers+text',
        name: 'ภูมิภาค',
        text: scatTexts,
        textposition: 'top right',
        textfont: { family: FONT_FAMILY, size: 12, color: t.text, weight: 600 },
        marker: {
          size: scatSizes,
          color: scatColors,
          line: { color: t.surface, width: 2.5 },
        },
        customdata: scatCustom,
        hovertemplate: '<b>%{customdata[0]}</b><br>CAGR รายได้: %{customdata[1]:+.2f}%/ปี<br>CAGR ราคาบ้าน: %{customdata[2]:+.2f}%/ปี<br>ส่วนต่าง (บ้าน − รายได้): %{customdata[3]:+.2f} จุด (%{customdata[4]})<extra></extra>',
      },
    ];

    const scatAnnotations = [
      {
        x: (vMin + vMax) / 2 + 0.3,
        y: (vMin + vMax) / 2 - 0.2,
        text: 'เส้นสมดุล (รายได้โต = ราคาบ้านโต)',
        showarrow: false,
        font: { family: FONT_FAMILY, size: 11, color: t.text_muted },
        textangle: 35,
      },
      {
        xref: 'paper',
        yref: 'paper',
        x: 0.85,
        y: 0.15,
        text: 'รายได้โตไวกว่าราคาบ้าน<br>(ทำเลทองคนซื้อ)',
        showarrow: false,
        xanchor: 'center',
        font: { family: FONT_FAMILY, size: 11.5, color: '#0E9F6E', weight: 600 },
      },
      {
        xref: 'paper',
        yref: 'paper',
        x: 0.25,
        y: 0.90,
        text: 'ราคาบ้านพุ่งแซงรายได้<br>(เริ่มซื้อยาก)',
        showarrow: false,
        xanchor: 'center',
        font: { family: FONT_FAMILY, size: 11.5, color: '#FF7A1A', weight: 600 },
      },
      {
        xref: 'paper',
        yref: 'paper',
        x: 0.08,
        y: 0.72,
        text: 'เสี่ยงฟองสบู่<br>(ราคาพุ่งแต่รายได้ไม่โต)',
        showarrow: false,
        xanchor: 'left',
        font: { family: FONT_FAMILY, size: 10.5, color: '#E5484D' },
      },
    ];

    const scatLayout = getBaseLayout(theme);
    Object.assign(scatLayout, {
      margin: { l: 48, r: 36, t: 20, b: 36 },
      xaxis: {
        ...scatLayout.xaxis,
        title: { text: 'CAGR รายได้ครัวเรือน (%/ปี)' },
        range: [vMin, vMax],
        tickformat: '+,.1f',
      },
      yaxis: {
        ...scatLayout.yaxis,
        title: { text: 'CAGR ราคาบ้าน (%/ปี)' },
        range: [vMin, vMax],
        tickformat: '+,.1f',
      },
      height: 400,
      annotations: scatAnnotations,
    });

    return {
      status_line: status_line,
      kpis: kpis,
      charts: {
        hero: {
          figure: { data: heroTraces, layout: heroLayout },
          read_guide: 'เส้นเหนือ 100 = ซื้อยากขึ้น (แรเงาส้ม) · เส้นใต้ 100 = ซื้อง่ายขึ้น (แรเงาฟ้า)',
          note: `ดัชนีปรับฐานให้ปี ${y0} = 100 · อัตราส่วน = ดัชนีราคาบ้าน ÷ ดัชนีรายได้`,
          empty: null,
        },
        cagr: {
          figure: { data: cagrTraces, layout: cagrLayout },
          read_guide: 'แท่งฟ้า = รายได้ · แท่งส้ม = ราคาบ้าน · สลับดู [ภาพรวม | แยกภาค | แยกบ้าน] ได้',
          note: cagrNote,
          empty: null,
        },
        gap_area: {
          figure: { data: gapTraces, layout: gapLayout },
          read_guide: 'พื้นที่แดง = ราคาบ้านแซง (ซื้อยากขึ้น) · พื้นที่เขียว = รายได้โตแซง (ซื้อง่ายขึ้น)',
          note: 'ช่องว่างความเหลื่อมล้ำ = ดัชนีราคาบ้าน − ดัชนีรายได้',
          empty: null,
        },
        scatter: {
          figure: { data: scatTraces, layout: scatLayout },
          read_guide: 'ใต้เส้นประ = รายได้โตไวกว่า · เหนือเส้นประ = ราคาบ้านแซง · ซ้ายบน = เสี่ยงฟองสบู่',
          note: 'คลิกที่จุดเพื่อเลือกดูภาคนั้นๆ · เส้นประทแยงมุม 45 องศาคือระดับที่รายได้และราคาบ้านเติบโตเท่ากัน',
          empty: null,
        },
      },
      notes: [
        'รายได้มีเฉพาะปีรอบสำรวจ (ทุก 2 ปี) ไม่เติมค่าปีที่ขาด · ดัชนีบอกการเปลี่ยนแปลงเทียบต้นช่วง ไม่ใช่ระดับราคาบ้านเป็นบาท',
        'นิยามกทม.+ปริมณฑลของ สสช. กับ ธปท. อาจไม่ตรงกัน',
        'อัตราส่วนของสองดัชนีตัดผลเงินเฟ้อส่วนใหญ่ออกไปแล้ว แต่ตอบเรื่อง \'รายได้จริงโตหรือไม่\' ไม่ได้',
      ],
      as_of: DB.meta.as_of,
    };
  }

  // ──────────────── Chart Summaries Generator (v2 §12) ────────────────
  const SUMMARY_MINUS = '\u2212';
  const SUMMARY_VALID_CHART_IDS = {
    1: new Set(['t1_map', 't1_trend', 't1_gap', 't1_sources']),
    2: new Set(['t2_map', 't2_trend', 't2_yoy']),
    3: new Set(['t3_ratio', 't3_cagr']),
  };
  const SUMMARY_CHART_TITLES = {
    t1_map: 'แผนที่รายได้เฉลี่ยต่อเดือน',
    t1_trend: 'แนวโน้มรายได้เฉลี่ยต่อเดือน',
    t1_gap: 'ช่องว่างเมือง-ชนบท (%)',
    t1_sources: 'สัดส่วนแหล่งที่มาของรายได้',
    t2_map: 'แผนที่ดัชนีราคาบ้าน',
    t2_trend: 'แนวโน้มดัชนีราคาบ้าน',
    t2_yoy: 'อัตราเปลี่ยนแปลงรายปี (YoY %)',
    t3_ratio: '1 · แนวโน้มดัชนีราคาบ้านเทียบกับรายได้ (Price-to-Income Ratio)',
    t3_cagr: '3 · เปรียบเทียบอัตราเติบโต (CAGR)',
  };
  const SUMMARY_PROPERTY_TYPE_NAMES = {
    1: 'รวมทุกประเภท',
    2: 'บ้านเดี่ยว',
    3: 'ทาวน์เฮ้าส์',
  };
  const SUMMARY_AREA_NAMES = {
    0: 'รวมทุกเขต',
    1: 'ในเขตเทศบาล (เมือง)',
    2: 'นอกเขตเทศบาล (ชนบท)',
  };
  const SUMMARY_CAGR_VIEW_NAMES = {
    summary: 'ภาพรวม',
    by_region: 'แยกภาค',
    by_type: 'แยกบ้าน',
  };
  const SUMMARY_THAI_MONTH_ABBR = ['', 'ม.ค.', 'ก.พ.', 'มี.ค.', 'เม.ย.', 'พ.ค.', 'มิ.ย.', 'ก.ค.', 'ส.ค.', 'ก.ย.', 'ต.ค.', 'พ.ย.', 'ธ.ค.'];

  function fmtBaht(v) {
    if (v === null || v === undefined) return '—';
    return Math.round(v).toLocaleString('en-US');
  }

  function fmtCagr(v) {
    if (v === null || v === undefined) return '—';
    if (v < 0) return `${SUMMARY_MINUS}${Math.abs(v).toFixed(2)}%/ปี`;
    return `${v.toFixed(2)}%/ปี`;
  }

  function fmtSignPct(v, d = 2) {
    if (v === null || v === undefined) return '—';
    if (v < 0) return `${SUMMARY_MINUS}${Math.abs(v).toFixed(d)}%`;
    return `+${v.toFixed(d)}%`;
  }

  function fmtDiffPoints(v) {
    if (v === null || v === undefined) return '—';
    if (v < 0) return `${SUMMARY_MINUS}${Math.abs(v).toFixed(2)} จุด`;
    return `+${v.toFixed(2)} จุด`;
  }

  function getScopeName(meta, regionId) {
    if (!regionId || regionId === 0) return 'ทั่วประเทศ';
    const reg = (meta && meta.regions) ? meta.regions.find(r => r.region_id === regionId) : null;
    return reg ? reg.short_th : 'ทั่วประเทศ';
  }

  function _buildT1MapSummary(f, meta) {
    const year = f.year;
    const area = f.area;
    const metric = f.metric;
    const region = f.region;
    const scope = getScopeName(meta, region);

    if (metric === 'income_index' || metric === 'index') {
      const rows = [];
      meta.regions.filter(r => r.region_id > 0).forEach(r => {
        const curRow = DB.income.find(x => x.year_be === year && x.area_type_id === area && x.region_id === r.region_id);
        const baseRow = DB.income.find(x => x.year_be === 2554 && x.area_type_id === area && x.region_id === r.region_id);
        if (curRow && baseRow && baseRow.monthly_income) {
          const val = roundVal(100.0 * curRow.monthly_income / baseRow.monthly_income, 1);
          rows.push({ region_id: r.region_id, short_th: r.short_th, value: val });
        }
      });
      if (!rows.length) return { headline: null, bullets: [], caution: 'ไม่มีข้อมูล', empty: null };
      rows.sort((a, b) => b.value - a.value);
      const top = rows[0];
      const bottom = rows[rows.length - 1];
      const below100 = rows.filter(r => r.value < 100.0);

      const headline = `ปี ${year} ดัชนีรายได้สูงสุดที่${top.short_th} (${top.value.toFixed(1)}) ต่ำสุดที่${bottom.short_th} (${bottom.value.toFixed(1)})`;
      const bullets = [
        '5 ภาคเรียงตามดัชนีรายได้: ' + rows.map(r => `${r.short_th} ${r.value.toFixed(1)}`).join(' · '),
      ];
      if (below100.length > 0) {
        bullets.push('ภาคที่ดัชนีรายได้ต่ำกว่า 100: ' + below100.map(r => `${r.short_th} (${r.value.toFixed(1)})`).join(' · '));
      } else {
        bullets.push('ทุกภาคมีดัชนีรายได้สูงกว่าปีฐาน 2554 (ดัชนี > 100)');
      }
      return { headline: headline, bullets: bullets, caution: 'ตัวเลขเป็นราคาตามปี ไม่ปรับเงินเฟ้อ', empty: null };
    } else if (metric === 'transfer_share' || metric === 'transfer') {
      const rows = [];
      meta.regions.filter(r => r.region_id > 0).forEach(r => {
        const curRow = DB.income.find(x => x.year_be === year && x.area_type_id === area && x.region_id === r.region_id);
        if (curRow && curRow.monthly_income) {
          const val = roundVal(100.0 * curRow.current_transfer / curRow.monthly_income, 1);
          rows.push({ region_id: r.region_id, short_th: r.short_th, value: val });
        }
      });
      if (!rows.length) return { headline: null, bullets: [], caution: 'ไม่มีข้อมูล', empty: null };
      rows.sort((a, b) => b.value - a.value);
      const top = rows[0];
      const bottom = rows[rows.length - 1];

      const natRow = DB.income.find(x => x.year_be === year && x.area_type_id === area && x.region_id === 0);
      const natTransfer = natRow && natRow.monthly_income ? roundVal(100.0 * natRow.current_transfer / natRow.monthly_income, 1) : 0.0;

      const headline = `ปี ${year} สัดส่วนเงินโอน/สวัสดิการสูงสุดที่${top.short_th} ${top.value.toFixed(1)}% ต่ำสุดที่${bottom.short_th} ${bottom.value.toFixed(1)}%`;
      const isanBmrText = (top.short_th === 'อีสาน' && bottom.short_th === 'กทม.+ปริมณฑล')
        ? `อีสานสูงสุด ${top.value.toFixed(1)}% กทม.+ปริมณฑลต่ำสุด ${bottom.value.toFixed(1)}% (ทั้งประเทศ ${natTransfer.toFixed(1)}%)`
        : `${top.short_th}สูงสุด ${top.value.toFixed(1)}% ${bottom.short_th}ต่ำสุด ${bottom.value.toFixed(1)}% (ทั้งประเทศ ${natTransfer.toFixed(1)}%)`;
      const bullets = [
        isanBmrText,
        '5 ภาคเรียงตามสัดส่วนเงินโอน: ' + rows.map(r => `${r.short_th} ${r.value.toFixed(1)}%`).join(' · '),
      ];
      return { headline: headline, bullets: bullets, caution: 'ตัวเลขเป็นราคาตามปี ไม่ปรับเงินเฟ้อ', empty: null };
    } else {
      // Default: metric === 'income'
      const rows = [];
      meta.regions.filter(r => r.region_id > 0).forEach(r => {
        const curRow = DB.income.find(x => x.year_be === year && x.area_type_id === area && x.region_id === r.region_id);
        if (curRow && curRow.monthly_income) {
          rows.push({ region_id: r.region_id, short_th: r.short_th, value: curRow.monthly_income });
        }
      });
      if (!rows.length) return { headline: null, bullets: [], caution: 'ไม่มีข้อมูล', empty: null };
      rows.sort((a, b) => b.value - a.value);
      const top = rows[0];
      const bottom = rows[rows.length - 1];
      const ratio = bottom.value ? roundVal(top.value / bottom.value, 2) : 0.0;

      const natRow = DB.income.find(x => x.year_be === year && x.area_type_id === area && x.region_id === 0);
      const natV = natRow ? natRow.monthly_income : 0;

      let headline = '';
      let bullets = [];
      if (region !== null && region > 0) {
        const rank = rows.findIndex(r => r.region_id === region) + 1;
        const cur = rows.find(r => r.region_id === region);
        headline = `ปี ${year} ${cur.short_th} มีรายได้ ${fmtBaht(cur.value)} บาท/เดือน เป็นอันดับที่ ${rank} จาก 5 ภาค (เทียบทั้งประเทศ ${fmtBaht(natV)} บาท/เดือน)`;
        const diff = cur.value - natV;
        const diffText = diff >= 0 ? `สูงกว่าค่าเฉลี่ยทั้งประเทศอยู่ ${fmtBaht(diff)} บาท` : `ต่ำกว่าค่าเฉลี่ยทั้งประเทศอยู่ ${fmtBaht(Math.abs(diff))} บาท`;
        bullets = [
          `${cur.short_th} มีรายได้เป็นอันดับ ${rank} จาก 5 ภาค (${fmtBaht(cur.value)} บาท/เดือน) ${diffText}`,
          `ภาคที่มีรายได้สูงสุดคือ ${top.short_th} (${fmtBaht(top.value)} บาท) ต่ำสุดคือ ${bottom.short_th} (${fmtBaht(bottom.value)} บาท)`,
          '5 ภาคเรียงจากมากไปน้อย: ' + rows.map(r => `${r.short_th} ${fmtBaht(r.value)}`).join(' · ') + ` บาท (ทั้งประเทศ ${fmtBaht(natV)} บาท)`,
        ];
      } else {
        headline = `ปี ${year} ${top.short_th}มีรายได้สูงสุด ${fmtBaht(top.value)} บาท/เดือน ส่วน${bottom.short_th}ต่ำสุด ${fmtBaht(bottom.value)} บาท (ต่างกัน ${ratio.toFixed(2)} เท่า)`;
        bullets = [
          'เรียง 5 ภาคจากมากไปน้อยพร้อมค่า: ' + rows.map((r, i) => i === 0 ? fmtBaht(r.value) : `${r.short_th} ${fmtBaht(r.value)}`).join(' · '),
          `รายได้เฉลี่ยทั้งประเทศอยู่ที่ ${fmtBaht(natV)} บาท/เดือน`,
        ];
      }
      return { headline: headline, bullets: bullets, caution: 'ตัวเลขเป็นราคาตามปี ไม่ปรับเงินเฟ้อ', empty: null };
    }
  }

  function _buildT1TrendSummary(f, meta) {
    const y0 = f.y0;
    const y1 = f.y1;
    const area = f.area;
    const region = f.region;
    const scope = getScopeName(meta, region);

    if (y0 === y1) {
      return {
        headline: `ปี ${y0} เป็นปีฐาน (ดัชนี = 100) จึงยังไม่มีอัตราเติบโต`,
        bullets: ['เปรียบเทียบอัตราการเติบโตได้เมื่อเลือกช่วงปีเริ่มต้นและสิ้นสุดต่างกัน'],
        caution: 'รายได้มีเฉพาะปีรอบสำรวจ (ทุก 2 ปี)',
        empty: null,
      };
    }

    const nat0 = DB.income.find(x => x.year_be === y0 && x.area_type_id === area && x.region_id === 0);
    const nat1 = DB.income.find(x => x.year_be === y1 && x.area_type_id === area && x.region_id === 0);
    const v0Nat = nat0 ? nat0.monthly_income : 0;
    const v1Nat = nat1 ? nat1.monthly_income : 0;
    const pctNat = pct_change(v0Nat, v1Nat) || 0.0;
    const cagrNat = cagr_pct(v0Nat, v1Nat, y1 - y0) || 0.0;

    const regionCagrs = [];
    meta.regions.filter(r => !r.is_national && r.region_id > 0).forEach(r => {
      const row0 = DB.income.find(x => x.year_be === y0 && x.area_type_id === area && x.region_id === r.region_id);
      const row1 = DB.income.find(x => x.year_be === y1 && x.area_type_id === area && x.region_id === r.region_id);
      if (row0 && row1 && row0.monthly_income && row1.monthly_income) {
        const c = cagr_pct(row0.monthly_income, row1.monthly_income, y1 - y0) || 0.0;
        const p = pct_change(row0.monthly_income, row1.monthly_income) || 0.0;
        regionCagrs.push({
          region_id: r.region_id,
          short_th: r.short_th,
          v0: row0.monthly_income,
          v1: row1.monthly_income,
          cagr: c,
          pct: p,
        });
      }
    });

    regionCagrs.sort((a, b) => b.cagr - a.cagr);
    const fastest = regionCagrs[0];
    const slowest = regionCagrs[regionCagrs.length - 1];

    let headline = '';
    let bullets = [];

    if (region !== null && region > 0) {
      const cur = regionCagrs.find(r => r.region_id === region);
      if (cur) {
        const rank = regionCagrs.findIndex(r => r.region_id === region) + 1;
        const direction = cur.pct >= 0 ? 'เพิ่ม' : 'ลดลง';
        headline = `${y0}→${y1} รายได้${cur.short_th}${direction} ${Math.abs(cur.pct).toFixed(1)}% (CAGR ${fmtCagr(cur.cagr)})`;
        const signPct = cur.pct >= 0 ? `+${cur.pct.toFixed(1)}%` : `${SUMMARY_MINUS}${Math.abs(cur.pct).toFixed(1)}%`;
        bullets = [
          `${cur.short_th} เป็นอันดับ ${rank} จาก 5 ภาค ในด้านอัตราเติบโตเฉลี่ยสะสม (CAGR ${fmtCagr(cur.cagr)} เทียบทั้งประเทศ ${fmtCagr(cagrNat)})`,
          `${cur.short_th} ${fmtBaht(cur.v0)} → ${fmtBaht(cur.v1)} บาท (${signPct}, CAGR ${fmtCagr(cur.cagr)}) เทียบทั้งประเทศ ${fmtCagr(cagrNat)}`,
        ];
      }
    } else {
      const direction = pctNat >= 0 ? 'เพิ่ม' : 'ลดลง';
      headline = `${y0}→${y1} รายได้${scope}${direction} ${Math.abs(pctNat).toFixed(1)}% (CAGR ${fmtCagr(cagrNat)})`;
      if (fastest) bullets.push(`โตเร็วสุด${fastest.short_th} ${fmtCagr(fastest.cagr)}`);
      if (slowest) {
        const desc = slowest.cagr < 0 ? ' (รายได้ลดลง)' : '';
        bullets.push(`ต่ำสุด${slowest.short_th} ${fmtCagr(slowest.cagr)}${desc}`);
      }
      const otherCagrs = regionCagrs.slice(1, -1).map(r => `${r.short_th} ${fmtCagr(r.cagr)}`);
      if (otherCagrs.length > 0) {
        bullets.push('ภาคอื่น ๆ: ' + otherCagrs.join(' · '));
      }
    }

    return { headline: headline, bullets: bullets, caution: 'รายได้มีเฉพาะปีรอบสำรวจ (ทุก 2 ปี)', empty: null };
  }

  function _buildT1GapSummary(f, meta) {
    const year = f.year;
    const region = f.region;

    const yearRows = [];
    meta.regions.filter(r => !r.is_national && r.region_id > 0).forEach(r => {
      const urban = DB.income.find(x => x.year_be === year && x.area_type_id === 1 && x.region_id === r.region_id);
      const rural = DB.income.find(x => x.year_be === year && x.area_type_id === 2 && x.region_id === r.region_id);
      if (urban && rural && rural.monthly_income) {
        const gap = roundVal(100.0 * (urban.monthly_income - rural.monthly_income) / rural.monthly_income, 1);
        yearRows.push({ region_id: r.region_id, short_th: r.short_th, gap_pct: gap });
      }
    });
    if (!yearRows.length) return { headline: null, bullets: [], caution: 'ไม่มีข้อมูล', empty: null };
    yearRows.sort((a, b) => b.gap_pct - a.gap_pct);
    const top = yearRows[0];
    const bottom = yearRows[yearRows.length - 1];

    const natUrban = DB.income.find(x => x.year_be === year && x.area_type_id === 1 && x.region_id === 0);
    const natRural = DB.income.find(x => x.year_be === year && x.area_type_id === 2 && x.region_id === 0);
    const natGap = (natUrban && natRural && natRural.monthly_income)
      ? roundVal(100.0 * (natUrban.monthly_income - natRural.monthly_income) / natRural.monthly_income, 1)
      : null;

    const bmrUrban54 = DB.income.find(x => x.year_be === 2554 && x.area_type_id === 1 && x.region_id === 1);
    const bmrRural54 = DB.income.find(x => x.year_be === 2554 && x.area_type_id === 2 && x.region_id === 1);
    const bmr54 = (bmrUrban54 && bmrRural54 && bmrRural54.monthly_income)
      ? roundVal(100.0 * (bmrUrban54.monthly_income - bmrRural54.monthly_income) / bmrRural54.monthly_income, 1)
      : null;

    const bmrUrbanCur = DB.income.find(x => x.year_be === year && x.area_type_id === 1 && x.region_id === 1);
    const bmrRuralCur = DB.income.find(x => x.year_be === year && x.area_type_id === 2 && x.region_id === 1);
    const bmrCur = (bmrUrbanCur && bmrRuralCur && bmrRuralCur.monthly_income)
      ? roundVal(100.0 * (bmrUrbanCur.monthly_income - bmrRuralCur.monthly_income) / bmrRuralCur.monthly_income, 1)
      : null;

    const headline = `ปี ${year} ช่องว่างเมือง-ชนบทสูงสุดที่${top.short_th} ${top.gap_pct.toFixed(1)}% ต่ำสุดที่${bottom.short_th} ${bottom.gap_pct.toFixed(1)}%`;
    const bullets = [];
    if (bmr54 !== null && bmrCur !== null) {
      bullets.push(`กทม.+ปริมณฑลลดจาก ${bmr54.toFixed(1)}% (2554) เหลือ ${bmrCur.toFixed(1)}%`);
    }
    const otherGaps = yearRows.filter(r => r.short_th !== 'กทม.+ปริมณฑล').map(r => `${r.short_th} ${r.gap_pct.toFixed(1)}%`);
    const natText = natGap !== null ? ` (ทั้งประเทศ ${natGap.toFixed(1)}%)` : '';
    if (otherGaps.length > 0) {
      bullets.push(otherGaps.join(' · ') + natText);
    }

    if (region !== null && region > 0) {
      const cur = yearRows.find(r => r.region_id === region);
      if (cur) {
        const rank = yearRows.findIndex(r => r.region_id === region) + 1;
        bullets.unshift(`${cur.short_th} มีช่องว่างเมือง-ชนบทเป็นอันดับ ${rank} จาก 5 ภาค (${cur.gap_pct.toFixed(1)}%)`);
      }
    }

    return { headline: headline, bullets: bullets, caution: 'นิยามกทม.+ปริมณฑลของ สสช. ใช้ 4 จังหวัด', empty: null };
  }

  function _buildT1SourcesSummary(f, meta) {
    const year = f.year;
    const area = f.area;
    const region = f.region;
    const scope = getScopeName(meta, region);

    const regTransfer = [];
    meta.regions.filter(r => !r.is_national && r.region_id > 0).forEach(r => {
      const row = DB.income.find(x => x.year_be === year && x.area_type_id === area && x.region_id === r.region_id);
      if (row && row.monthly_income) {
        const tr = roundVal(100.0 * row.current_transfer / row.monthly_income, 1);
        const wk = roundVal(100.0 * row.from_work / row.monthly_income, 1);
        regTransfer.push({ region: r.short_th, region_id: r.region_id, transfer: tr, work: wk });
      }
    });
    regTransfer.sort((a, b) => b.transfer - a.transfer);

    if (region !== null && region > 0) {
      const row = DB.income.find(x => x.year_be === year && x.area_type_id === area && x.region_id === region);
      const tot = row ? row.monthly_income : 1;
      const w = row ? roundVal(100.0 * row.from_work / tot, 1) : 0;
      const t = row ? roundVal(100.0 * row.current_transfer / tot, 1) : 0;
      const nm = row ? roundVal(100.0 * row.nonmoney_income / tot, 1) : 0;
      const o = roundVal(100.0 - (w + t + nm), 1);

      const headline = `ปี ${year} ${scope} รายได้มาจากการทำงาน ${w.toFixed(1)}% เงินโอน/สวัสดิการ ${t.toFixed(1)}% ไม่เป็นตัวเงิน ${nm.toFixed(1)}% อื่น ๆ ${o.toFixed(1)}%`;
      const rankTr = regTransfer.findIndex(x => x.region_id === region) + 1;
      const curRk = regTransfer.find(x => x.region_id === region);
      const bullets = [
        `${scope} มีสัดส่วนเงินโอน/สวัสดิการสูงเป็นอันดับ ${rankTr} จาก 5 ภาค (${t.toFixed(1)}% เทียบทั้งประเทศ 13.1%)`,
      ];
      const minWork = Math.min(...regTransfer.map(x => x.work));
      if (curRk && curRk.work === minWork) {
        bullets.push(`รายได้จากการทำงานอยู่ที่ ${w.toFixed(1)}% ต่ำที่สุดใน 5 ภาค`);
      } else {
        bullets.push(`สัดส่วนรายได้จากการทำงานอยู่ที่ ${w.toFixed(1)}% (ทั้งประเทศ 70.5%)`);
      }
      return { headline: headline, bullets: bullets, caution: 'อื่น ๆ = ทรัพย์สิน + รายได้ไม่ประจำ', empty: null };
    } else {
      const natRow = DB.income.find(x => x.year_be === year && x.area_type_id === area && x.region_id === 0);
      const tot = natRow ? natRow.monthly_income : 1;
      const w = natRow ? roundVal(100.0 * natRow.from_work / tot, 1) : 70.5;
      const t = natRow ? roundVal(100.0 * natRow.current_transfer / tot, 1) : 13.1;
      const nm = natRow ? roundVal(100.0 * natRow.nonmoney_income / tot, 1) : 14.5;
      const o = roundVal(100.0 - (w + t + nm), 1);

      const headline = `ปี ${year} ทั่วประเทศ รายได้มาจากการทำงาน ${w.toFixed(1)}% เงินโอน/สวัสดิการ ${t.toFixed(1)}% ไม่เป็นตัวเงิน ${nm.toFixed(1)}% อื่น ๆ ${o.toFixed(1)}%`;
      const topTr = regTransfer[0];
      const botTr = regTransfer[regTransfer.length - 1];
      const topWk = [...regTransfer].sort((a, b) => b.work - a.work)[0];
      const bullets = [
        `${topTr.region}พึ่งเงินโอนมากสุด ${topTr.transfer.toFixed(1)}% ${botTr.region}ต่ำสุด ${botTr.transfer.toFixed(1)}%`,
        `${topWk.region}มีสัดส่วนรายได้จากการทำงานสูงสุดที่ ${topWk.work.toFixed(1)}%`,
      ];
      return { headline: headline, bullets: bullets, caution: 'อื่น ๆ = ทรัพย์สิน + รายได้ไม่ประจำ', empty: null };
    }
  }

  function _buildT2MapSummary(f, meta) {
    const year = f.year;
    const pt = f.pt;
    const region = f.region;
    const metric = f.metric;
    const ptName = SUMMARY_PROPERTY_TYPE_NAMES[pt] || 'รวมทุกประเภท';

    if (pt === 3 && (region === 3 || region === 4)) {
      return { headline: null, bullets: [], caution: null, empty: 'ไม่มีข้อมูลทาวน์เฮ้าส์ของภาคนี้ (ธปท. ไม่มีชุดข้อมูลนี้)' };
    }

    if (year === 2554) {
      return {
        headline: 'ปี 2554 เป็นปีฐาน (ดัชนี = 100) จึงยังไม่มีอัตราเติบโต',
        bullets: [`ดัชนีราคาบ้าน${ptName}ทุกภาคเริ่มต้นที่ 100.0 ในปี 2554`],
        caution: 'ดัชนีบอกการเปลี่ยนแปลง ไม่ใช่ระดับราคาบ้านเป็นบาท จึงไม่ใช้จัดอันดับระดับราคา',
        empty: null,
      };
    }

    const natHpi = DB.hpi_annual.find(r => r.year_be === year && r.region_id === 0 && r.property_type_id === pt);
    const nat54 = DB.hpi_annual.find(r => r.year_be === 2554 && r.region_id === 0 && r.property_type_id === pt);
    const idx = natHpi ? natHpi.index_mean12 : 100.0;
    const v54 = nat54 ? nat54.index_mean12 : 100.0;
    const pct = idx - v54;
    const cagr = cagr_pct(v54, idx, year - 2554) || 0.0;

    const headline = `ปี ${year} ดัชนีราคาบ้าน${ptName}ทั้งประเทศ ${idx.toFixed(1)} (สูงกว่าปี 2554 ${pct.toFixed(1)}%) โตเฉลี่ย ${fmtCagr(cagr)}`;

    const cagrRows = [];
    const yoyRows = [];
    meta.regions.filter(r => !r.is_national && r.region_id > 0).forEach(r => {
      const cur = DB.hpi_annual.find(a => a.year_be === year && a.region_id === r.region_id && a.property_type_id === pt);
      const prev = DB.hpi_annual.find(a => a.year_be === year - 1 && a.region_id === r.region_id && a.property_type_id === pt);
      const b54 = DB.hpi_annual.find(a => a.year_be === 2554 && a.region_id === r.region_id && a.property_type_id === pt);
      if (cur && b54 && b54.index_mean12) {
        const cVal = cagr_pct(b54.index_mean12, cur.index_mean12, year - 2554) || 0.0;
        cagrRows.push({ region_id: r.region_id, short_th: r.short_th, value: cVal });
      }
      if (cur && prev && prev.index_mean12) {
        const yVal = roundVal(100.0 * (cur.index_mean12 / prev.index_mean12 - 1.0), 2);
        yoyRows.push({ region_id: r.region_id, short_th: r.short_th, value: yVal });
      }
    });

    cagrRows.sort((a, b) => b.value - a.value);
    yoyRows.sort((a, b) => b.value - a.value);

    const bullets = [];
    if (metric === 'yoy') {
      const topYoy = yoyRows[0];
      const botYoy = yoyRows[yoyRows.length - 1];
      bullets.push(`อัตราเพิ่มจากปีก่อน (YoY): ${topYoy.short_th}สูงสุด ${topYoy.value.toFixed(2)}% ${botYoy.short_th}ต่ำสุด ${botYoy.value.toFixed(2)}%`);
      bullets.push('เรียงตาม YoY: ' + yoyRows.map(r => `${r.short_th} ${r.value.toFixed(2)}%`).join(' · '));
    } else {
      bullets.push('อัตราเติบโตสะสมต่อปี (CAGR): ' + cagrRows.map(r => `${r.short_th} ${r.value.toFixed(2)}`).join(' · '));
    }

    if (region !== null && region > 0) {
      const curC = cagrRows.find(r => r.region_id === region);
      if (curC) {
        const rank = cagrRows.findIndex(r => r.region_id === region) + 1;
        bullets.unshift(`${curC.short_th} มีอัตราเติบโตสะสมเป็นอันดับ ${rank} จาก 5 ภาค (${curC.value.toFixed(2)}%/ปี เทียบทั้งประเทศ ${fmtCagr(cagr)})`);
      }
    }

    return { headline: headline, bullets: bullets, caution: 'ดัชนีบอกการเปลี่ยนแปลง ไม่ใช่ระดับราคาบ้านเป็นบาท จึงไม่ใช้จัดอันดับระดับราคา', empty: null };
  }

  function _buildT2TrendSummary(f, meta) {
    const pt = f.pt;
    const region = f.region;
    const grain = f.grain;
    const ptName = SUMMARY_PROPERTY_TYPE_NAMES[pt] || 'รวมทุกประเภท';
    const scope = getScopeName(meta, region);

    if (pt === 3 && (region === 3 || region === 4)) {
      return { headline: null, bullets: [], caution: null, empty: 'ไม่มีข้อมูลทาวน์เฮ้าส์ของภาคนี้ (ธปท. ไม่มีชุดข้อมูลนี้)' };
    }

    const y0 = 2554;
    const y1 = 2568;
    const rid = region !== null ? region : 0;

    const r0 = DB.hpi_annual.find(a => a.year_be === y0 && a.region_id === rid && a.property_type_id === pt);
    const r1 = DB.hpi_annual.find(a => a.year_be === y1 && a.region_id === rid && a.property_type_id === pt);
    const v0 = r0 ? r0.index_mean12 : 100.0;
    const v1 = r1 ? r1.index_mean12 : 100.0;
    const cagr = cagr_pct(v0, v1, y1 - y0) || 0.0;

    const headline = `${y0}→${y1} ดัชนี${ptName}${scope} 100.0 → ${v1.toFixed(1)} โตเฉลี่ย ${fmtCagr(cagr)}`;
    const bullets = [];
    let caution = '';

    if (grain === 'monthly') {
      const mRows = DB.hpi_monthly.filter(m => m.region_id === rid && m.property_type_id === pt);
      mRows.sort((a, b) => b.month_id - a.month_id);
      const latestM = mRows[0];
      if (latestM) {
        const mName = SUMMARY_THAI_MONTH_ABBR[latestM.month_no] || '';
        bullets.push(`เดือนล่าสุด ${mName} ${latestM.year_be} ดัชนี ${latestM.index_value.toFixed(1)}`);
      }
      caution = 'เส้นรายเดือนเป็นเฉลี่ยเคลื่อนที่ 3 เดือน · เพิ่มฐานข้อมูลสถาบันการเงินเฉพาะกิจ ม.ค. 2566 อาจมีรอยต่อ';
    } else {
      if (pt === 2 && (region === 3 || region === 4)) {
        bullets.push('ดัชนีรวมทุกประเภทเท่ากับบ้านเดี่ยว');
      } else {
        bullets.push(`ดัชนีเพิ่มขึ้นจาก 100.0 สู่ ${v1.toFixed(1)} (เพิ่ม ${(v1 - 100.0).toFixed(1)}%)`);
      }
      caution = 'ดัชนีบอกการเปลี่ยนแปลงเทียบปีฐาน 2554 ไม่ใช่ระดับราคาบ้านเป็นบาท';
    }

    return { headline: headline, bullets: bullets, caution: caution, empty: null };
  }

  function _buildT2YoySummary(f, meta) {
    const year = f.year;
    const pt = f.pt;
    const region = f.region;
    const ptName = SUMMARY_PROPERTY_TYPE_NAMES[pt] || 'รวมทุกประเภท';

    if (pt === 3 && (region === 3 || region === 4)) {
      return { headline: null, bullets: [], caution: null, empty: 'ไม่มีข้อมูลทาวน์เฮ้าส์ของภาคนี้ (ธปท. ไม่มีชุดข้อมูลนี้)' };
    }

    if (year === 2554) {
      return {
        headline: 'ปี 2554 เป็นปีฐาน (ดัชนี = 100) จึงยังไม่มีอัตราเติบโต',
        bullets: ['อัตราการเปลี่ยนแปลงรายปี (YoY) เริ่มต้นคำนวณตั้งแต่ปี 2555 เป็นต้นไป'],
        caution: 'ดัชนีบอกการเปลี่ยนแปลง ไม่ใช่ระดับราคาบ้านเป็นบาท',
        empty: null,
      };
    }

    const yoyRows = [];
    meta.regions.filter(r => !r.is_national && r.region_id > 0).forEach(r => {
      const cur = DB.hpi_annual.find(a => a.year_be === year && a.region_id === r.region_id && a.property_type_id === pt);
      const prev = DB.hpi_annual.find(a => a.year_be === year - 1 && a.region_id === r.region_id && a.property_type_id === pt);
      if (cur && prev && prev.index_mean12) {
        const yVal = roundVal(100.0 * (cur.index_mean12 / prev.index_mean12 - 1.0), 2);
        yoyRows.push({ region_id: r.region_id, short_th: r.short_th, value: yVal });
      }
    });
    if (!yoyRows.length) return { headline: null, bullets: [], caution: 'ไม่มีข้อมูล', empty: null };
    yoyRows.sort((a, b) => b.value - a.value);
    const top = yoyRows[0];
    const bottom = yoyRows[yoyRows.length - 1];

    const natCur = DB.hpi_annual.find(a => a.year_be === year && a.region_id === 0 && a.property_type_id === pt);
    const natPrev = DB.hpi_annual.find(a => a.year_be === year - 1 && a.region_id === 0 && a.property_type_id === pt);
    const natVal = (natCur && natPrev && natPrev.index_mean12)
      ? roundVal(100.0 * (natCur.index_mean12 / natPrev.index_mean12 - 1.0), 2)
      : 0.0;

    const headline = `ปี ${year} ราคาเพิ่มจากปีก่อน ${fmtSignPct(natVal)} (ทั้งประเทศ) สูงสุด${top.short_th} ${fmtSignPct(top.value)} ต่ำสุด${bottom.short_th} ${fmtSignPct(bottom.value)}`;
    const bullets = [
      `เรียงตาม YoY ปี ${year}: ` + yoyRows.map(r => `${r.short_th} ${fmtSignPct(r.value)}`).join(' · '),
      `ช่วง 2555–2568 ช่องที่ติดลบมี 3 ช่อง: เหนือ ปี 2562 (${SUMMARY_MINUS}2.23%) ใต้ ปี 2562 (${SUMMARY_MINUS}0.39%) ใต้ ปี 2564 (${SUMMARY_MINUS}1.41%)`,
    ];

    return { headline: headline, bullets: bullets, caution: 'ดัชนีบอกการเปลี่ยนแปลง ไม่ใช่ระดับราคาบ้านเป็นบาท', empty: null };
  }

  function _buildT3RatioSummary(f, meta) {
    const y0 = f.y0;
    const y1 = f.y1;
    const pt = f.pt;
    const region = f.region;
    const scope = getScopeName(meta, region);

    if (y0 === y1) {
      return {
        headline: `ปี ${y0} เป็นปีฐาน (ดัชนี = 100) จึงยังไม่มีอัตราเติบโต`,
        bullets: ['อัตราส่วนคำนวณจากการเปลี่ยนแปลงของดัชนีทั้งสองเทียบปีเริ่มต้น'],
        caution: 'ดัชนีบอกการเปลี่ยนแปลงเทียบต้นช่วง ไม่ใช่ราคาบ้านเป็นบาท',
        empty: null,
      };
    }

    const rowsY1 = [];
    meta.regions.forEach(reg => {
      const rid = reg.region_id;
      const incBaseRow = DB.income.find(i => i.year_be === y0 && i.region_id === rid && i.area_type_id === 0);
      const hpiBaseRow = DB.hpi_annual.find(a => a.year_be === y0 && a.region_id === rid && a.property_type_id === pt);
      const incRow = DB.income.find(i => i.year_be === y1 && i.region_id === rid && i.area_type_id === 0);
      const hpiRow = DB.hpi_annual.find(a => a.year_be === y1 && a.region_id === rid && a.property_type_id === pt);

      if (incBaseRow && hpiBaseRow && incRow && hpiRow && incBaseRow.monthly_income && hpiBaseRow.index_mean12) {
        const newInc = roundVal(100.0 * incRow.monthly_income / incBaseRow.monthly_income, 1);
        const newHpi = roundVal(100.0 * hpiRow.index_mean12 / hpiBaseRow.index_mean12, 1);
        const newPti = newInc ? roundVal(100.0 * newHpi / newInc, 1) : 100.0;
        rowsY1.push({
          region_id: rid,
          short_th: reg.short_th,
          is_national: reg.is_national,
          income_index: newInc,
          hpi_index: newHpi,
          price_to_income_index: newPti,
        });
      }
    });

    const rid = region !== null ? region : 0;
    const targetRow = rowsY1.find(r => r.region_id === rid) || rowsY1.find(r => r.region_id === 0);
    const natRow = rowsY1.find(r => r.region_id === 0);
    if (!targetRow) return { headline: null, bullets: [], caution: 'ไม่มีข้อมูล', empty: null };

    const pti = targetRow.price_to_income_index;
    const hpi = targetRow.hpi_index;
    const inc = targetRow.income_index;
    const pct = Math.round(Math.abs(pti - 100.0));

    let headline = '';
    if (pti >= 100.0) {
      headline = `ปี ${y1} ราคาบ้านโตเร็วกว่ารายได้ ${pct}% เทียบปี ${y0} (${scope}) จึงซื้อยากขึ้น`;
    } else {
      headline = `ปี ${y1} ราคาบ้านโตช้ากว่ารายได้ ${pct}% เทียบปี ${y0} (${scope}) จึงซื้อง่ายขึ้น`;
    }

    const bullets = [
      `ดัชนีราคาบ้าน ${hpi.toFixed(1)} ÷ ดัชนีรายได้ ${inc.toFixed(1)} = ${pti.toFixed(1)}`,
    ];

    const regionalY1 = rowsY1.filter(r => !r.is_national && r.price_to_income_index !== null);
    if (regionalY1.length > 0) {
      regionalY1.sort((a, b) => b.price_to_income_index - a.price_to_income_index);
      const hardest = regionalY1[0];
      const easiest = regionalY1[regionalY1.length - 1];
      if (region !== null && region > 0) {
        const rank = regionalY1.findIndex(r => r.region_id === region) + 1;
        const natPti = natRow ? natRow.price_to_income_index.toFixed(1) : '—';
        bullets.push(`${scope} ซื้อยากขึ้นเป็นอันดับ ${rank} จาก 5 ภาค (ดัชนี ${pti.toFixed(1)} เทียบทั้งประเทศ ${natPti})`);
      } else {
        bullets.push(`ยากขึ้นมากสุดที่${hardest.short_th} (${hardest.price_to_income_index.toFixed(1)}) น้อยสุดที่${easiest.short_th} (${easiest.price_to_income_index.toFixed(1)})`);
      }
    }

    const caution = 'ดัชนีบอกการเปลี่ยนแปลงเทียบต้นช่วง ไม่ใช่ราคาบ้านเป็นบาท · นิยามกทม.+ปริมณฑลของ สสช. กับ ธปท. อาจไม่ตรงกัน';
    return { headline: headline, bullets: bullets, caution: caution, empty: null };
  }

  function _buildT3CagrSummary(f, meta) {
    const y0 = f.y0;
    const y1 = f.y1;
    const pt = f.pt;
    const region = f.region;
    const cagrView = f.cagr_view;
    const scope = getScopeName(meta, region);

    if (pt === 3 && (region === 3 || region === 4)) {
      return { headline: null, bullets: [], caution: null, empty: 'ไม่มีข้อมูลทาวน์เฮ้าส์ของภาคนี้ (ธปท. ไม่มีชุดข้อมูลนี้)' };
    }

    if (y0 === y1) {
      return {
        headline: `ปี ${y0} เป็นปีฐาน (ดัชนี = 100) จึงยังไม่มีอัตราเติบโต`,
        bullets: ['กรุณาเลือกช่วงปีเริ่มต้นและสิ้นสุดต่างกันเพื่อคำนวณอัตราเติบโตเฉลี่ยสะสม (CAGR)'],
        caution: `คำนวณจากอัตราเติบโตเฉลี่ยสะสมต่อปี (CAGR) ระหว่างปี ${y0} และ ${y1}`,
        empty: null,
      };
    }

    const years = y1 - y0;
    const rid = region !== null ? region : 0;

    const inc0 = DB.income.find(i => i.year_be === y0 && i.region_id === rid && i.area_type_id === 0);
    const inc1 = DB.income.find(i => i.year_be === y1 && i.region_id === rid && i.area_type_id === 0);
    const hpi0 = DB.hpi_annual.find(a => a.year_be === y0 && a.region_id === rid && a.property_type_id === pt);
    const hpi1 = DB.hpi_annual.find(a => a.year_be === y1 && a.region_id === rid && a.property_type_id === pt);

    const incC = (inc0 && inc1 && inc0.monthly_income) ? (cagr_pct(inc0.monthly_income, inc1.monthly_income, years) || 0.0) : 0.0;
    const hpiC = (hpi0 && hpi1 && hpi0.index_mean12) ? (cagr_pct(hpi0.index_mean12, hpi1.index_mean12, years) || 0.0) : 0.0;
    const gap = roundVal(hpiC - incC, 2);

    let headline = '';
    const bullets = [];

    if (cagrView === 'by_type') {
      if (region === 3 || region === 4) {
        headline = `${scope} ดัชนีรวมทุกประเภทเท่ากับบ้านเดี่ยว โต ${hpiC.toFixed(2)}%/ปี เทียบรายได้ ${incC.toFixed(2)}%/ปี`;
        bullets.push('ภาคนี้มีเฉพาะบ้านเดี่ยว ดัชนีรวมเท่ากับบ้านเดี่ยว ไม่มีข้อมูลทาวน์เฮ้าส์');
      } else {
        let thC = 0.0;
        let sdC = 0.0;
        let allC = hpiC;

        const th0 = DB.hpi_annual.find(a => a.year_be === y0 && a.region_id === rid && a.property_type_id === 3);
        const th1 = DB.hpi_annual.find(a => a.year_be === y1 && a.region_id === rid && a.property_type_id === 3);
        if (th0 && th1 && th0.index_mean12) thC = cagr_pct(th0.index_mean12, th1.index_mean12, years) || 0.0;

        const sd0 = DB.hpi_annual.find(a => a.year_be === y0 && a.region_id === rid && a.property_type_id === 2);
        const sd1 = DB.hpi_annual.find(a => a.year_be === y1 && a.region_id === rid && a.property_type_id === 2);
        if (sd0 && sd1 && sd0.index_mean12) sdC = cagr_pct(sd0.index_mean12, sd1.index_mean12, years) || 0.0;

        headline = `${scope} ทาวน์เฮ้าส์โต ${thC.toFixed(2)}%/ปี บ้านเดี่ยว ${sdC.toFixed(2)}%/ปี รวมทุกประเภท ${allC.toFixed(2)}%/ปี เทียบรายได้ ${incC.toFixed(2)}%/ปี`;
        bullets.push(`ทาวน์เฮ้าส์เติบโตเฉลี่ยสะสม ${thC.toFixed(2)}%/ปี`);
        bullets.push(`บ้านเดี่ยวเติบโตเฉลี่ยสะสม ${sdC.toFixed(2)}%/ปี`);
        bullets.push(`รายได้เฉลี่ยเติบโต ${fmtCagr(incC)}`);
      }
    } else if (cagrView === 'summary') {
      headline = `ช่วง ${y0}–${y1} ${scope} ราคาบ้านโตเฉลี่ย ${fmtCagr(hpiC)} เทียบรายได้ ${fmtCagr(incC)}`;
      bullets.push(`ส่วนต่างอัตราเติบโต (ราคาบ้าน − รายได้) อยู่ที่ ${fmtDiffPoints(gap)}`);
    } else {
      // Default: by_region
      headline = `ราคาบ้านโต ${fmtCagr(hpiC)} เทียบรายได้ ${fmtCagr(incC)} (ช่องว่าง ${fmtDiffPoints(gap)})`;

      const regGaps = [];
      meta.regions.filter(r => !r.is_national && r.region_id > 0).forEach(r => {
        const i0 = DB.income.find(x => x.year_be === y0 && x.region_id === r.region_id && x.area_type_id === 0);
        const i1 = DB.income.find(x => x.year_be === y1 && x.region_id === r.region_id && x.area_type_id === 0);
        const h0 = DB.hpi_annual.find(x => x.year_be === y0 && x.region_id === r.region_id && x.property_type_id === pt);
        const h1 = DB.hpi_annual.find(x => x.year_be === y1 && x.region_id === r.region_id && x.property_type_id === pt);

        if (i0 && i1 && h0 && h1 && i0.monthly_income && h0.index_mean12) {
          const ic = cagr_pct(i0.monthly_income, i1.monthly_income, years) || 0.0;
          const hc = cagr_pct(h0.index_mean12, h1.index_mean12, years) || 0.0;
          regGaps.push({
            region_id: r.region_id,
            short_th: r.short_th,
            inc: ic,
            hpi: hc,
            gap: roundVal(hc - ic, 2),
          });
        }
      });

      regGaps.sort((a, b) => b.gap - a.gap);
      const maxGap = regGaps[0];
      const bmr = regGaps.find(x => x.short_th === 'กทม.+ปริมณฑล');

      if (bmr) {
        const incBmrStr = bmr.inc < 0 ? `ติดลบ ${SUMMARY_MINUS}${Math.abs(bmr.inc).toFixed(2)}%/ปี` : `${bmr.inc.toFixed(2)}%/ปี`;
        bullets.push(`กทม.+ปริมณฑล: รายได้${incBmrStr} ขณะที่ราคาบ้านโต ${bmr.hpi.toFixed(2)}%/ปี`);
      }
      if (maxGap) {
        bullets.push(`ช่องว่างมากสุดที่${maxGap.short_th} (${fmtDiffPoints(maxGap.gap)}) โดยราคาบ้านโต ${maxGap.hpi.toFixed(2)}%/ปี เทียบรายได้ ${maxGap.inc.toFixed(2)}%/ปี`);
      }
      if (region !== null && region > 0) {
        const curG = regGaps.find(x => x.region_id === region);
        if (curG) {
          const rank = regGaps.findIndex(x => x.region_id === region) + 1;
          bullets.unshift(`${curG.short_th} มีช่องว่างการเติบโตเป็นอันดับ ${rank} จาก 5 ภาค (${fmtDiffPoints(curG.gap)})`);
        }
      }
    }

    const caution = `คำนวณจากอัตราเติบโตเฉลี่ยสะสมต่อปี (CAGR) ระหว่างปี ${y0} และ ${y1}`;
    return { headline: headline, bullets: bullets, caution: caution, empty: null };
  }

  function getSummary(tabId, chartId, params = {}) {
    const tab = parseInt(tabId, 10);
    if (!SUMMARY_VALID_CHART_IDS[tab] || !SUMMARY_VALID_CHART_IDS[tab].has(chartId)) {
      throw new Error(`รหัสกราฟ '${chartId}' ไม่ถูกต้องสำหรับแท็บ ${tab}`);
    }

    const meta = DB.meta;
    const year = params.year !== undefined ? parseInt(params.year, 10) : 2568;
    const y0 = params.y0 !== undefined ? parseInt(params.y0, 10) : 2554;
    const y1 = params.y1 !== undefined ? parseInt(params.y1, 10) : 2568;
    const region = (params.region !== undefined && params.region !== null && params.region !== '') ? parseInt(params.region, 10) : null;
    const area = params.area !== undefined ? parseInt(params.area, 10) : 0;
    const pt = params.pt !== undefined ? parseInt(params.pt, 10) : 1;
    const metric = params.metric || (tab === 2 ? 'hpi' : 'income');
    const grain = params.grain || 'yearly';
    const cagrView = params.cagr_view || 'summary';

    const f = { year, y0, y1, region, area, pt, metric, grain, cagr_view: cagrView };
    const title = SUMMARY_CHART_TITLES[chartId] || '';
    const scope = getScopeName(meta, region);

    const filtersList = [];
    if (tab === 1) {
      if (chartId === 't1_map' || chartId === 't1_gap' || chartId === 't1_sources') {
        filtersList.push({ label: 'ปี', value: `ปี ${year}` });
      } else if (chartId === 't1_trend') {
        filtersList.push({ label: 'ช่วงปี', value: `${y0}–${y1}` });
      }
      filtersList.push({ label: 'พื้นที่', value: scope });
      if (chartId !== 't1_gap') {
        filtersList.push({ label: 'เขต', value: SUMMARY_AREA_NAMES[area] || 'รวมทุกเขต' });
      }
    } else if (tab === 2) {
      if (chartId === 't2_map' || chartId === 't2_yoy') {
        filtersList.push({ label: 'ปี', value: `ปี ${year}` });
      } else if (chartId === 't2_trend') {
        filtersList.push({ label: 'ความถี่', value: grain === 'monthly' ? 'รายเดือน' : 'รายปี' });
        filtersList.push({ label: 'ช่วงปี', value: `${y0}–${y1}` });
      }
      filtersList.push({ label: 'ประเภทบ้าน', value: SUMMARY_PROPERTY_TYPE_NAMES[pt] || 'รวมทุกประเภท' });
      filtersList.push({ label: 'พื้นที่', value: scope });
    } else if (tab === 3) {
      filtersList.push({ label: 'ช่วงปี', value: `${y0}–${y1}` });
      filtersList.push({ label: 'ประเภทบ้าน', value: SUMMARY_PROPERTY_TYPE_NAMES[pt] || 'รวมทุกประเภท' });
      filtersList.push({ label: 'พื้นที่', value: scope });
      if (chartId === 't3_cagr') {
        filtersList.push({ label: 'มุมมอง', value: SUMMARY_CAGR_VIEW_NAMES[cagrView] || 'แยกภาค' });
      }
    }

    let res = null;
    if (chartId === 't1_map') res = _buildT1MapSummary(f, meta);
    else if (chartId === 't1_trend') res = _buildT1TrendSummary(f, meta);
    else if (chartId === 't1_gap') res = _buildT1GapSummary(f, meta);
    else if (chartId === 't1_sources') res = _buildT1SourcesSummary(f, meta);
    else if (chartId === 't2_map') res = _buildT2MapSummary(f, meta);
    else if (chartId === 't2_trend') res = _buildT2TrendSummary(f, meta);
    else if (chartId === 't2_yoy') res = _buildT2YoySummary(f, meta);
    else if (chartId === 't3_ratio') res = _buildT3RatioSummary(f, meta);
    else if (chartId === 't3_cagr') res = _buildT3CagrSummary(f, meta);

    return {
      chart_id: chartId,
      title: title,
      filters: filtersList,
      headline: res ? res.headline : null,
      bullets: res ? res.bullets : [],
      caution: res ? res.caution : null,
      empty: res ? res.empty : null,
    };
  }

  function getTab(tabId, params) {
    if (tabId === 1) return handleTab1(params);
    if (tabId === 2) return handleTab2(params);
    if (tabId === 3) return handleTab3(params);
    throw new Error('Tab ' + tabId + ' not found');
  }

  return {
    init: init,
    isReady: isReady,
    getMeta: getMeta,
    getTab: getTab,
    getSummary: getSummary,
    cagr_pct: cagr_pct,
    pct_change: pct_change,
  };
}));
