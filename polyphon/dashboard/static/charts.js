const COLORS = ['#a78bfa', '#34d399', '#f59e0b', '#f87171', '#38bdf8'];
const CHART_DEFAULTS = {
  plugins: { legend: { display: false } },
  scales: {
    x: { ticks: { color: '#64748b' }, grid: { color: '#1e2130' } },
    y: { ticks: { color: '#64748b' }, grid: { color: '#2d3148' }, beginAtZero: true },
  },
};

let charts = {};

function $(id) { return document.getElementById(id); }

function fmt(n, decimals = 0) {
  if (n === null || n === undefined) return '—';
  return Number(n).toLocaleString('en', { maximumFractionDigits: decimals, minimumFractionDigits: decimals });
}

function makeOrUpdate(id, config) {
  if (charts[id]) charts[id].destroy();
  charts[id] = new Chart($(id), config);
}

async function load() {
  const summary = await fetch('/api/summary').then(r => r.json()).catch(() => null);

  if (!summary || !summary.total_requests) {
    $('no-data').style.display = 'block';
    $('content').style.display = 'none';
    return;
  }

  $('no-data').style.display = 'none';
  $('content').style.display = 'block';
  $('last-updated').textContent = `Last updated ${new Date().toLocaleTimeString()}`;

  // ── ⏱️ Performance ─────────────────────────────────────────────────────────
  $('avg-latency').textContent = fmt(summary.avg_latency_ms);

  // First chunk latency — fetch raw metrics for this
  const rows = await fetch('/api/metrics').then(r => r.json()).catch(() => []);
  const sorted = [...rows].sort((a, b) => a.ts - b.ts);
  $('first-latency').textContent = sorted.length ? fmt(sorted[0].duration_ms) : '—';

  const totalGenMs = rows.reduce((s, r) => s + r.duration_ms, 0);
  const totalChars = summary.total_chars;
  const charsPerSec = totalChars / (totalGenMs / 1000);
  $('chars-per-sec').textContent = fmt(charsPerSec);

  const totalAudioS = (summary.total_audio_minutes || 0) * 60;
  const realtimeFactor = totalAudioS / (totalGenMs / 1000);
  const rtEl = $('realtime-factor');
  rtEl.textContent = fmt(realtimeFactor, 1) + '×';
  rtEl.className = 'stat ' + (realtimeFactor >= 5 ? 'good' : realtimeFactor >= 2 ? 'warn' : 'bad');

  // ── 💰 Cost ────────────────────────────────────────────────────────────────
  $('total-cost').textContent = '$' + fmt(summary.total_cost_usd, 4);
  $('total-chars').textContent = fmt(totalChars);
  const costPerK = totalChars > 0 ? (summary.total_cost_usd / totalChars * 1000) : 0;
  $('cost-per-k').textContent = '$' + fmt(costPerK, 4);
  $('cost-per-page').textContent = '$' + fmt(costPerK * 1.8, 4);

  // ── 🔊 Audio Quality ───────────────────────────────────────────────────────
  $('total-audio').textContent = fmt(summary.total_audio_minutes, 2);
  $('total-size').textContent = fmt(summary.total_size_kb, 1);
  const bytesPerChar = summary.total_size_kb * 1024 / (totalChars || 1);
  $('bytes-per-char').textContent = fmt(bytesPerChar, 2);

  // ── 🔁 Reliability ─────────────────────────────────────────────────────────
  const srEl = $('success-rate');
  const sr = summary.success_rate;
  srEl.textContent = fmt(sr, 1) + '%';
  srEl.className = 'stat ' + (sr >= 99 ? 'good' : sr >= 95 ? 'warn' : 'bad');
  const successes = rows.filter(r => r.success).length;
  const failures = rows.length - successes;
  $('success-counts').textContent = `${successes} ok · ${failures} failed`;
  $('total-requests').textContent = fmt(summary.total_requests);

  // ── 📊 Provider Comparison charts ──────────────────────────────────────────
  const providers = summary.by_provider || [];
  const labels = providers.map(p => p.provider);

  makeOrUpdate('latency-chart', {
    type: 'bar',
    data: {
      labels,
      datasets: [{ label: 'Avg latency (ms)', data: providers.map(p => Math.round(p.avg_latency_ms)), backgroundColor: COLORS, borderRadius: 6 }],
    },
    options: { ...CHART_DEFAULTS, plugins: { legend: { display: false } } },
  });

  makeOrUpdate('cost-chart', {
    type: 'bar',
    data: {
      labels,
      datasets: [{ label: 'Cost (USD)', data: providers.map(p => p.cost?.toFixed(5) ?? 0), backgroundColor: COLORS, borderRadius: 6 }],
    },
    options: { ...CHART_DEFAULTS, plugins: { legend: { display: false } } },
  });

  makeOrUpdate('requests-chart', {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{ data: providers.map(p => p.requests), backgroundColor: COLORS }],
    },
    options: { plugins: { legend: { position: 'bottom', labels: { color: '#94a3b8' } } } },
  });

  makeOrUpdate('throughput-chart', {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Chars/sec',
        data: providers.map(p => p.avg_latency_ms > 0 ? Math.round((p.chars / p.requests) / (p.avg_latency_ms / 1000)) : 0),
        backgroundColor: COLORS,
        borderRadius: 6,
      }],
    },
    options: { ...CHART_DEFAULTS, plugins: { legend: { display: false } } },
  });

  // ── Provider table ─────────────────────────────────────────────────────────
  $('provider-table').innerHTML = providers.map(p => `
    <tr>
      <td><strong>${p.provider}</strong></td>
      <td>${fmt(p.requests)}</td>
      <td>${fmt(p.chars)}</td>
      <td>${fmt(p.avg_latency_ms)} ms</td>
      <td>${fmt(p.audio_s / 60, 2)} min</td>
      <td>$${fmt(p.cost, 5)}</td>
      <td>${fmt(p.bytes_per_char, 2)}</td>
    </tr>
  `).join('');

  // ── Jobs table ─────────────────────────────────────────────────────────────
  const jobs = summary.by_job || [];
  $('jobs-table').innerHTML = jobs.map(j => `
    <tr>
      <td><strong>${j.job || '(unnamed)'}</strong></td>
      <td>${fmt(j.chunks)}</td>
      <td>${fmt(j.chars)}</td>
      <td>${fmt(j.audio_s / 60, 2)} min</td>
      <td>$${fmt(j.cost, 5)}</td>
    </tr>
  `).join('');
}

load();
setInterval(load, 10000);
