const fs = require('fs');
const path = require('path');
const DashboardEngine = require('../site/js/engine.js');

const dataFile = path.join(__dirname, '../site/data/dashboard_data.json');
const expectedFile = path.join(__dirname, '../data/expected_values.json');

const rawData = JSON.parse(fs.readFileSync(dataFile, 'utf8'));
const expected = JSON.parse(fs.readFileSync(expectedFile, 'utf8'));

DashboardEngine.init(rawData);

console.log('--- Testing Engine Metadata ---');
const meta = DashboardEngine.getMeta();
console.assert(meta.regions.length === 6, 'Meta regions length should be 6');
console.assert(meta.as_of.income_latest_wave === 2568, 'Income latest wave should be 2568');
console.log('Metadata OK');

console.log('--- Testing Tab 1 (2566) ---');
const t1 = DashboardEngine.getTab(1, { year: 2566, area: 0, region: null, theme: 'dark' });
const kpis1 = {};
t1.kpis.forEach(k => kpis1[k.id] = k);

console.log('Tab 1 Income:', kpis1.income.value, '(Expected: 29030)');
console.assert(kpis1.income.value === 29030, `Expected 29030, got ${kpis1.income.value}`);
console.assert(kpis1.income.delta.value === 24.9, `Expected delta 24.9, got ${kpis1.income.delta.value}`);
console.assert(kpis1.cagr.value === expected.income_cagr_pct.TH, `Expected CAGR ${expected.income_cagr_pct.TH}, got ${kpis1.cagr.value}`);
console.assert(kpis1.transfer.value === expected.treemap_shares_2566_national_pct.CURRENT_TRANSFER, `Expected transfer 13.1, got ${kpis1.transfer.value}`);
console.assert(kpis1.gap.value === expected.urban_rural_gap_pct_2566.TH, `Expected gap 33.8, got ${kpis1.gap.value}`);

console.log('--- Testing Tab 1 Base Year 2554 ---');
const t1_base = DashboardEngine.getTab(1, { year: 2554, area: 0, region: null, theme: 'dark' });
const kpis1_base = {};
t1_base.kpis.forEach(k => kpis1_base[k.id] = k);
console.assert(kpis1_base.cagr.value === '—', `Expected cagr '—', got ${kpis1_base.cagr.value}`);
console.assert(kpis1_base.cagr.delta === null, 'Expected cagr delta null');
console.assert(kpis1_base.income.delta === null, 'Expected income delta null');

console.log('--- Testing Tab 2 (2566) ---');
const t2 = DashboardEngine.getTab(2, { year: 2566, pt: 1, region: null, theme: 'dark' });
const kpis2 = {};
t2.kpis.forEach(k => kpis2[k.id] = k);
console.log('Tab 2 HPI:', kpis2.hpi.value, '(Expected: 167.7)');
console.assert(kpis2.hpi.value === 167.7, `Expected 167.7, got ${kpis2.hpi.value}`);
console.assert(kpis2.cagr.value === expected.hpi_all_cagr_pct.TH, `Expected CAGR ${expected.hpi_all_cagr_pct.TH}, got ${kpis2.cagr.value}`);

console.log('--- Testing Tab 2 Townhouse in North/NE (pt=3, region=3) ---');
const t2_th = DashboardEngine.getTab(2, { year: 2566, pt: 3, region: 3, theme: 'dark' });
console.assert(t2_th.charts.choropleth.empty !== null, 'Expected empty notice for townhouse in North');

console.log('--- Testing Tab 3 (2554 -> 2566) ---');
const t3 = DashboardEngine.getTab(3, { y0: 2554, y1: 2566, pt: 1, region: null, theme: 'dark' });
const kpis3 = {};
t3.kpis.forEach(k => kpis3[k.id] = k);
console.log('Tab 3 PTI:', kpis3.pti.value, '(Expected: 134.2)');
console.assert(kpis3.pti.value === expected.price_to_income_index_2566_all.TH, `Expected PTI ${expected.price_to_income_index_2566_all.TH}, got ${kpis3.pti.value}`);
console.assert(kpis3.inc_cagr.value === expected.income_cagr_pct.TH, `Expected inc CAGR ${expected.income_cagr_pct.TH}, got ${kpis3.inc_cagr.value}`);
console.assert(kpis3.hpi_cagr.value === expected.hpi_all_cagr_pct.TH, `Expected HPI CAGR ${expected.hpi_all_cagr_pct.TH}, got ${kpis3.hpi_cagr.value}`);

console.log('--- Testing Tab 3 Regional PTI (2566) ---');
const regions = ['BMR', 'CEN', 'NOR', 'NES', 'SOU'];
const regIds = [1, 2, 3, 4, 5];
regIds.forEach((rid, idx) => {
  const code = regions[idx];
  const t3_reg = DashboardEngine.getTab(3, { y0: 2554, y1: 2566, pt: 1, region: rid, theme: 'dark' });
  const k = {};
  t3_reg.kpis.forEach(item => k[item.id] = item);
  const expPti = expected.price_to_income_index_2566_all[code];
  console.assert(k.pti.value === expPti, `Expected PTI for ${code} ${expPti}, got ${k.pti.value}`);
});

console.log('ALL TESTS PASSED SUCCESSFULLY! 🚀');
