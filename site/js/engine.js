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
        hovertemplate: `${reg.short_th}: ${hoverFmt}<extra></extra>`,
      });

      if (rows.length > 0) {
        trendTraces.push({
          type: 'scatter',
          x: [xs[xs.length - 1]],
          y: [ys[ys.length - 1]],
          mode: 'text',
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
          hovertemplate: `${reg.short_th}: %{y:.1f}<extra></extra>`,
        });

        trendTraces.push({
          type: 'scatter',
          x: [xs[xs.length - 1]],
          y: [ys[ys.length - 1]],
          mode: 'text',
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
    cagr_pct: cagr_pct,
    pct_change: pct_change,
  };
}));
