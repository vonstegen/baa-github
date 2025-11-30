/**
 * BAA Seller Central - Background Script
 */

// Store check data
browser.runtime.onMessage.addListener((msg, sender, respond) => {
  if (msg.type === 'STORE_CHECK') {
    storeCheck(msg.data).then(() => respond({ success: true }));
    return true;
  }
  
  if (msg.type === 'GET_STATS') {
    getStats().then(stats => respond(stats));
    return true;
  }
  
  if (msg.type === 'EXPORT_CSV') {
    exportCSV().then(csv => respond({ csv }));
    return true;
  }
  
  if (msg.type === 'EXPORT_JSON') {
    exportJSON().then(json => respond({ json }));
    return true;
  }
  
  if (msg.type === 'CLEAR_DATA') {
    browser.storage.local.clear().then(() => respond({ success: true }));
    return true;
  }
});

async function storeCheck(data) {
  const result = await browser.storage.local.get('checks');
  const checks = result.checks || {};
  
  checks[data.asin] = {
    ...data,
    storedAt: new Date().toISOString()
  };
  
  await browser.storage.local.set({ checks });
  await updateStats();
}

async function updateStats() {
  const result = await browser.storage.local.get('checks');
  const checks = Object.values(result.checks || {});
  
  const stats = {
    total: checks.length,
    good: checks.filter(c => c.status === 'GOOD').length,
    needApproval: checks.filter(c => c.status === 'NEED_APPROVAL').length,
    restricted: checks.filter(c => c.status === 'RESTRICTED' || c.status === 'NOT_AVAILABLE').length,
    unknown: checks.filter(c => c.status === 'UNKNOWN').length
  };
  
  await browser.storage.local.set({ stats });
  return stats;
}

async function getStats() {
  const result = await browser.storage.local.get('stats');
  return result.stats || { total: 0, good: 0, needApproval: 0, restricted: 0, unknown: 0 };
}

async function exportCSV() {
  const result = await browser.storage.local.get('checks');
  const checks = Object.values(result.checks || {});
  
  if (checks.length === 0) return '';
  
  let csv = 'ASIN,Status,BSR,Message,URL,Checked At\n';
  
  for (const c of checks) {
    csv += `"${c.asin}","${c.status}","${c.bsr || ''}","${c.message}","${c.url}","${c.checkedAt}"\n`;
  }
  
  return csv;
}

/**
 * Export JSON for F-Agent integration
 * 
 * Format expected by F-Agent's ExtensionBridge:
 * {
 *   "exportedAt": "ISO timestamp",
 *   "version": "6.2",
 *   "results": [
 *     {
 *       "asin": "1234567890",
 *       "status": "GOOD | NEED_APPROVAL | RESTRICTED",
 *       "condition": "Used",
 *       "bsr": 150000,
 *       "title": "Book Title",
 *       "message": "Status message",
 *       "checkedAt": "ISO timestamp"
 *     }
 *   ]
 * }
 */
async function exportJSON() {
  const result = await browser.storage.local.get('checks');
  const checks = Object.values(result.checks || {});
  
  if (checks.length === 0) return '';
  
  const exportData = {
    exportedAt: new Date().toISOString(),
    version: "6.2",
    source: "baa-seller-central-extension",
    results: checks.map(c => ({
      asin: c.asin,
      status: c.status,
      condition: c.condition || 'Used',
      bsr: c.bsr || null,
      title: c.title || '',
      message: c.message || '',
      url: c.url || '',
      checkedAt: c.checkedAt
    }))
  };
  
  return JSON.stringify(exportData, null, 2);
}

console.log('[BAA-SC] Background script loaded');
