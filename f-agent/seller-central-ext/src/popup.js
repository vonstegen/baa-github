document.addEventListener('DOMContentLoaded', async () => {
  await loadLastCheck();
  await loadStats();
});

async function loadLastCheck() {
  const result = await browser.storage.local.get('lastCheck');
  if (!result.lastCheck) return;
  
  const data = result.lastCheck;
  
  document.getElementById('noData').style.display = 'none';
  document.getElementById('lastCheckCard').style.display = 'block';
  
  document.getElementById('asin').textContent = data.asin;
  
  const statusEl = document.getElementById('status');
  statusEl.textContent = data.status;
  statusEl.className = 'status';
  
  const checkEl = document.getElementById('lastCheck');
  checkEl.className = 'last-check';
  
  if (data.status === 'GOOD') {
    statusEl.classList.add('good');
    checkEl.classList.add('good');
  } else if (data.status === 'NEED_APPROVAL') {
    statusEl.classList.add('approval');
    checkEl.classList.add('approval');
  } else if (data.status === 'RESTRICTED' || data.status === 'NOT_AVAILABLE') {
    statusEl.classList.add('bad');
    checkEl.classList.add('bad');
  } else {
    statusEl.classList.add('unknown');
    checkEl.classList.add('unknown');
  }
  
  document.getElementById('time').textContent = timeAgo(new Date(data.checkedAt));
}

async function loadStats() {
  const result = await browser.storage.local.get('stats');
  const stats = result.stats;
  
  if (stats && stats.total > 0) {
    document.getElementById('statsCard').style.display = 'block';
    document.getElementById('sGood').textContent = stats.good || 0;
    document.getElementById('sApproval').textContent = stats.needApproval || 0;
    document.getElementById('sRestricted').textContent = stats.restricted || 0;
    document.getElementById('sTotal').textContent = stats.total || 0;
  }
}

document.getElementById('checkBtn').addEventListener('click', async () => {
  const btn = document.getElementById('checkBtn');
  btn.disabled = true;
  btn.textContent = '⏳ Checking...';
  
  try {
    const tabs = await browser.tabs.query({ active: true, currentWindow: true });
    if (tabs[0]?.url?.includes('sellercentral.amazon.com')) {
      await browser.tabs.sendMessage(tabs[0].id, { type: 'CHECK_NOW' });
      setTimeout(async () => {
        await loadLastCheck();
        await loadStats();
        btn.textContent = '✓ Done';
        setTimeout(() => { btn.textContent = '🔍 Check Current Page'; btn.disabled = false; }, 1500);
      }, 2000);
    } else {
      alert('Please open a Seller Central page first');
      btn.textContent = '🔍 Check Current Page';
      btn.disabled = false;
    }
  } catch (e) {
    console.error(e);
    btn.textContent = '✗ Error';
    setTimeout(() => { btn.textContent = '🔍 Check Current Page'; btn.disabled = false; }, 2000);
  }
});

document.getElementById('exportBtn').addEventListener('click', async () => {
  const btn = document.getElementById('exportBtn');
  btn.disabled = true;
  btn.textContent = '⏳ Exporting...';
  
  try {
    const response = await browser.runtime.sendMessage({ type: 'EXPORT_CSV' });
    if (response?.csv) {
      const blob = new Blob([response.csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `baa-checks-${new Date().toISOString().split('T')[0]}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      btn.textContent = '✓ Done';
    } else {
      btn.textContent = 'No Data';
    }
  } catch (e) {
    btn.textContent = '✗ Error';
  }
  
  setTimeout(() => { btn.textContent = '📥 Export CSV'; btn.disabled = false; }, 2000);
});

// JSON Export for F-Agent integration
document.getElementById('exportJsonBtn').addEventListener('click', async () => {
  const btn = document.getElementById('exportJsonBtn');
  btn.disabled = true;
  btn.textContent = '⏳ Exporting...';
  
  try {
    const response = await browser.runtime.sendMessage({ type: 'EXPORT_JSON' });
    if (response?.json) {
      const blob = new Blob([response.json], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `baa-eligibility-${new Date().toISOString().split('T')[0]}.json`;
      a.click();
      URL.revokeObjectURL(url);
      
      // Show export info
      const count = JSON.parse(response.json).results.length;
      document.getElementById('exportInfo').style.display = 'block';
      document.getElementById('exportMessage').innerHTML = `
        ✅ Exported <strong>${count}</strong> results<br>
        <span style="font-size: 11px;">Save to: <code>f-agent/data/extension_export.json</code></span>
      `;
      
      btn.textContent = '✓ Done';
    } else {
      btn.textContent = 'No Data';
    }
  } catch (e) {
    console.error(e);
    btn.textContent = '✗ Error';
  }
  
  setTimeout(() => { btn.textContent = '📤 Export JSON (F-Agent)'; btn.disabled = false; }, 3000);
});

function timeAgo(date) {
  const s = Math.floor((new Date() - date) / 1000);
  if (s < 60) return 'just now';
  const m = Math.floor(s / 60);
  if (m < 60) return m + 'm ago';
  const h = Math.floor(m / 60);
  if (h < 24) return h + 'h ago';
  return Math.floor(h / 24) + 'd ago';
}
