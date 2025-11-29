/**
 * BAA Seller Central Checker - Content Script v3.0
 * =================================================
 * 
 * Works on:
 * - Product search pages (slide-out panel)
 * - Easylist pages (/abis/listing/easylist)
 * - Add a product pages
 * 
 * DETECTION PRIORITY:
 * 1. GOOD: "Sell this product" button visible and clickable
 * 2. NOT_AVAILABLE: "Not Available" badge/text (hardest restriction)
 * 3. RESTRICTED: "not accepting applications", "cannot list"
 * 4. NEED_APPROVAL: "Apply to sell", "Approval required"
 * 5. UNKNOWN: Can't determine
 */

(function() {
  const DEBUG = true;
  const PREFIX = '[BAA-SC]';
  
  function log(...args) {
    if (DEBUG) console.log(PREFIX, ...args);
  }

  // =========================================================================
  // EXTRACT ASIN
  // =========================================================================
  function getASIN() {
    const url = window.location.href;
    
    // Priority 1: URL parameters (most reliable)
    const urlPatterns = [
      /[?&]asin=([A-Z0-9]{10})/i,
      /[?&]identifiers=([A-Z0-9]{10})/i,
      /[?&]q=([A-Z0-9]{10})/i,
      /\/dp\/([A-Z0-9]{10})/i,
    ];
    
    for (const pattern of urlPatterns) {
      const m = url.match(pattern);
      if (m) {
        log('ASIN from URL:', m[1]);
        return m[1];
      }
    }
    
    // Priority 2: Page content
    const pageText = document.body.innerText;
    
    // Look for "ASIN: XXXXXXXXXX" or "ASIN XXXXXXXXXX"
    let m = pageText.match(/\bASIN[:\s]+([A-Z0-9]{10})\b/i);
    if (m) {
      log('ASIN from page text:', m[1]);
      return m[1];
    }
    
    // Look for ISBN-10 pattern (books often use ISBN as ASIN)
    m = pageText.match(/\bISBN[:\s]+(\d{10})\b/i);
    if (m) {
      log('ASIN from ISBN:', m[1]);
      return m[1];
    }
    
    // Look for B0... pattern (standard ASIN format)
    m = pageText.match(/\b(B[A-Z0-9]{9})\b/);
    if (m) {
      log('ASIN B-pattern:', m[1]);
      return m[1];
    }
    
    // Look for 10-digit ISBN starting with 0 or 1
    m = pageText.match(/\b([01]\d{9})\b/);
    if (m) {
      log('ASIN from ISBN pattern:', m[1]);
      return m[1];
    }
    
    log('❌ No ASIN found');
    return null;
  }

  // =========================================================================
  // EXTRACT BSR
  // =========================================================================
  function getBSR() {
    const text = document.body.innerText;
    
    // "Amazon Sales Rank: 12,345" or "Sales Rank: 12345"
    const patterns = [
      /Amazon\s*Sales\s*Rank[:\s]+#?([0-9,]+)/i,
      /Sales\s*Rank[:\s]+#?([0-9,]+)/i,
      /BSR[:\s]+#?([0-9,]+)/i,
    ];
    
    for (const pattern of patterns) {
      const m = text.match(pattern);
      if (m) {
        const bsr = parseInt(m[1].replace(/,/g, ''));
        log('BSR found:', bsr);
        return bsr;
      }
    }
    
    return null;
  }

  // =========================================================================
  // EXTRACT TITLE
  // =========================================================================
  function getTitle() {
    // Look for product title in typical locations
    const candidates = [];
    
    // Try common selectors
    const selectors = [
      'h1',
      '[class*="product-title"]',
      '[class*="productTitle"]',
      '[class*="item-name"]',
      '[class*="itemName"]',
    ];
    
    for (const sel of selectors) {
      document.querySelectorAll(sel).forEach(el => {
        const text = el.innerText.trim();
        if (text.length > 15 && text.length < 300) {
          candidates.push(text);
        }
      });
    }
    
    // Filter out Seller Central UI text
    const filtered = candidates.filter(t => 
      !t.includes('Seller Central') &&
      !t.includes('List Your Products') &&
      !t.includes('Add Products') &&
      !t.includes('Product information')
    );
    
    if (filtered.length > 0) {
      return filtered[0];
    }
    
    return null;
  }

  // =========================================================================
  // CHECK ELIGIBILITY - Core Logic (v5.6)
  // =========================================================================
  function checkEligibility() {
    log('========================================');
    log('CHECKING ELIGIBILITY v5.6');
    log('========================================');
    
    // Search ALL shadow roots for specific text
    function findInShadowDOM(searchText) {
      let found = false;
      document.querySelectorAll('*').forEach(el => {
        if (el.shadowRoot && el.shadowRoot.textContent.includes(searchText)) {
          found = true;
        }
      });
      return found;
    }
    
    // Check for "Select a condition and sell" dropdown
    const hasConditionDropdown = findInShadowDOM('Select a condition and sell');
    log('Has condition dropdown:', hasConditionDropdown);
    
    if (!hasConditionDropdown) {
      // STATE 2: No dropdown → Always RESTRICTED
      log('State 2: No dropdown');
      log('🚫 RESULT: RESTRICTED');
      return { status: 'RESTRICTED', message: 'This product is restricted from listing', indicator: 'no_dropdown' };
    }
    
    // STATE 1: Has dropdown → Check buttons for GOOD or NEED_APPROVAL
    log('State 1: Has dropdown - checking buttons...');
    
    // Get button labels from KAT-BUTTON Shadow DOMs
    const buttonLabels = [];
    document.querySelectorAll('kat-button, KAT-BUTTON').forEach(btn => {
      if (btn.shadowRoot) {
        const text = btn.shadowRoot.textContent.trim().toLowerCase();
        if (text && text.length < 30) {
          buttonLabels.push(text);
        }
      }
    });
    
    log('Button labels:', buttonLabels);
    
    // Check buttons
    const hasSellThisProduct = buttonLabels.some(l => l === 'sell this product');
    const hasApplyToSell = buttonLabels.some(l => l === 'apply to sell');
    
    log('hasSellThisProduct:', hasSellThisProduct);
    log('hasApplyToSell:', hasApplyToSell);
    
    // GOOD: "Sell this product" button exists
    if (hasSellThisProduct) {
      log('✅ RESULT: GOOD');
      return { status: 'GOOD', message: 'You can sell this product!', indicator: 'sell_button' };
    }
    
    // NEED_APPROVAL: "Apply to sell" button exists
    if (hasApplyToSell) {
      log('⚠️ RESULT: NEED_APPROVAL');
      return { status: 'NEED_APPROVAL', message: 'You need approval to list this product', indicator: 'apply_button' };
    }
    
    // UNKNOWN: Has dropdown but couldn't determine status
    log('❓ RESULT: UNKNOWN');
    return { status: 'UNKNOWN', message: 'Could not determine eligibility', indicator: 'unknown' };
  }

  // =========================================================================
  // SHOW NOTIFICATION
  // =========================================================================
  function showNotification(data) {
    // Remove existing notification
    const existing = document.getElementById('baa-sc-notification');
    if (existing) existing.remove();
    
    const colors = {
      'GOOD': '#10b981',        // Green
      'NEED_APPROVAL': '#f59e0b', // Orange
      'RESTRICTED': '#ef4444',   // Red
      'NOT_AVAILABLE': '#7c3aed', // Purple
      'UNKNOWN': '#6b7280'       // Gray
    };
    
    const icons = {
      'GOOD': '✓',
      'NEED_APPROVAL': '⚠',
      'RESTRICTED': '✗',
      'NOT_AVAILABLE': '⊘',
      'UNKNOWN': '?'
    };
    
    const statusLabels = {
      'GOOD': 'CAN SELL',
      'NEED_APPROVAL': 'NEED APPROVAL',
      'RESTRICTED': 'RESTRICTED',
      'NOT_AVAILABLE': 'NOT AVAILABLE',
      'UNKNOWN': 'UNKNOWN'
    };
    
    const color = colors[data.status] || colors.UNKNOWN;
    const icon = icons[data.status] || '?';
    const label = statusLabels[data.status] || data.status;
    
    const div = document.createElement('div');
    div.id = 'baa-sc-notification';
    div.innerHTML = `
      <style>
        @keyframes baaSlideIn {
          from { transform: translateX(400px); opacity: 0; }
          to { transform: translateX(0); opacity: 1; }
        }
        #baa-sc-notification {
          position: fixed !important;
          top: 80px !important;
          right: 20px !important;
          background: ${color} !important;
          color: white !important;
          padding: 16px 20px !important;
          border-radius: 12px !important;
          box-shadow: 0 8px 32px rgba(0,0,0,0.3) !important;
          z-index: 2147483647 !important;
          font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Arial, sans-serif !important;
          font-size: 14px !important;
          min-width: 280px !important;
          max-width: 350px !important;
          animation: baaSlideIn 0.4s ease !important;
          border: 2px solid rgba(255,255,255,0.2) !important;
        }
        #baa-sc-notification * { 
          color: white !important; 
          font-family: inherit !important;
        }
        #baa-sc-notification .baa-header {
          display: flex !important;
          align-items: center !important;
          gap: 12px !important;
          margin-bottom: 12px !important;
          padding-bottom: 10px !important;
          border-bottom: 1px solid rgba(255,255,255,0.2) !important;
        }
        #baa-sc-notification .baa-icon {
          font-size: 36px !important;
          line-height: 1 !important;
        }
        #baa-sc-notification .baa-status {
          font-size: 18px !important;
          font-weight: 700 !important;
          letter-spacing: 0.5px !important;
        }
        #baa-sc-notification .baa-close {
          position: absolute !important;
          top: 8px !important;
          right: 12px !important;
          cursor: pointer !important;
          font-size: 20px !important;
          opacity: 0.7 !important;
          transition: opacity 0.2s !important;
        }
        #baa-sc-notification .baa-close:hover {
          opacity: 1 !important;
        }
        #baa-sc-notification .baa-details {
          font-size: 13px !important;
          opacity: 0.9 !important;
        }
        #baa-sc-notification .baa-row {
          margin-bottom: 4px !important;
        }
        #baa-sc-notification .baa-message {
          margin-top: 10px !important;
          padding-top: 8px !important;
          border-top: 1px solid rgba(255,255,255,0.2) !important;
          font-size: 12px !important;
          opacity: 0.85 !important;
        }
      </style>
      <span class="baa-close">×</span>
      <div class="baa-header">
        <span class="baa-icon">${icon}</span>
        <span class="baa-status">${label}</span>
      </div>
      <div class="baa-details">
        <div class="baa-row"><strong>ASIN:</strong> ${data.asin}</div>
        ${data.bsr ? `<div class="baa-row"><strong>BSR:</strong> #${data.bsr.toLocaleString()}</div>` : ''}
        ${data.title ? `<div class="baa-row"><strong>Title:</strong> ${data.title.substring(0, 60)}${data.title.length > 60 ? '...' : ''}</div>` : ''}
      </div>
      <div class="baa-message">${data.message}</div>
    `;
    
    document.body.appendChild(div);
    
    // Close button
    div.querySelector('.baa-close').onclick = () => div.remove();
    
    // Auto-remove after 15 seconds
    setTimeout(() => {
      if (div.parentNode) {
        div.style.opacity = '0';
        div.style.transform = 'translateX(400px)';
        div.style.transition = 'all 0.3s ease';
        setTimeout(() => div.remove(), 300);
      }
    }, 15000);
  }

  // =========================================================================
  // MAIN RUN FUNCTION
  // =========================================================================
  function run() {
    log('Running eligibility check...');
    log('URL:', window.location.href);
    
    const asin = getASIN();
    if (!asin) {
      log('No ASIN found, skipping check');
      return null;
    }
    
    const bsr = getBSR();
    const title = getTitle();
    const result = checkEligibility();
    
    const data = {
      asin: asin,
      bsr: bsr,
      title: title,
      status: result.status,
      message: result.message,
      indicator: result.indicator,
      url: window.location.href,
      checkedAt: new Date().toISOString()
    };
    
    log('========================================');
    log('FINAL RESULT:', data.status);
    log('Data:', JSON.stringify(data, null, 2));
    log('========================================');
    
    // Show notification
    showNotification(data);
    
    // Store result
    try {
      browser.storage.local.set({ lastCheck: data });
      browser.runtime.sendMessage({ type: 'STORE_CHECK', data: data }).catch(() => {});
    } catch (e) {
      log('Storage error:', e);
    }
    
    return data;
  }

  // =========================================================================
  // INITIALIZATION
  // =========================================================================
  function init() {
    const isInIframe = window.self !== window.top;
    
    log('========================================');
    log('BAA Seller Central Checker v4.0');
    log('In iframe:', isInIframe);
    log('========================================');
    log('Page URL:', window.location.href);
    
    // Track state to prevent duplicate checks
    let lastCheckedASIN = null;
    
    // Check if this is an easylist page (always check these immediately)
    const url = window.location.href;
    const isEasylistPage = url.includes('easylist') || url.includes('/abis/listing');
    
    if (isEasylistPage) {
      log('Easylist page detected - running single check');
      setTimeout(run, 2000);
      return;
    }
    
    log('Starting polling for slide-out panel...');
    
    /**
     * Search ALL shadow roots for specific text
     */
    function findInShadowDOM(searchText) {
      let found = false;
      document.querySelectorAll('*').forEach(el => {
        if (el.shadowRoot && el.shadowRoot.textContent.includes(searchText)) {
          found = true;
        }
      });
      return found;
    }
    
    /**
     * Get the selected condition from dropdown (New, Used, Collectible, or null)
     * Checks the visible select-header element, not all options
     */
    function getSelectedCondition() {
      let selected = null;
      
      document.querySelectorAll('kat-dropdown, KAT-DROPDOWN').forEach(dropdown => {
        if (dropdown.shadowRoot) {
          // Look for the visible header that shows the selected value
          const header = dropdown.shadowRoot.querySelector('.select-header, .header-row, [class*="header"]');
          
          if (header) {
            const text = header.textContent.trim();
            log('Dropdown header text:', text);
            
            // Check if it STARTS WITH a real condition (not "Condition" placeholder)
            // The header may contain extra text, so use startsWith
            if (text.startsWith('New')) {
              selected = 'New';
            } else if (text.startsWith('Used')) {
              selected = 'Used';
            } else if (text.startsWith('Collectible')) {
              selected = 'Collectible';
            }
            // If text starts with "Condition", selected stays null
          }
        }
      });
      
      return selected;
    }
    
    /**
     * Check if slide-out panel is ready to be checked
     * 
     * State 1: "Select a condition and sell" IS present
     *          → Wait for dropdown to show New/Used/Collectible, then check
     * 
     * State 2: "Select a condition and sell" is NOT present
     *          → Trigger immediately → RESTRICTED
     */
    function hasProductPanel() {
      // Must have ASIN in regular page text
      const pageText = document.body.innerText;
      const hasASIN = pageText.includes('ASIN:');
      if (!hasASIN) return false;
      
      // Check for Copy listing button (indicates panel is open)
      const hasCopyListing = findInShadowDOM('Copy listing');
      if (!hasCopyListing) return false;
      
      // Check for condition dropdown
      const hasConditionDropdown = findInShadowDOM('Select a condition and sell');
      
      if (hasConditionDropdown) {
        // STATE 1: Has dropdown → Wait for New/Used/Collectible selection
        const selectedCondition = getSelectedCondition();
        
        if (selectedCondition) {
          // Check if buttons are still loading (grayed out)
          const buttonsReady = areButtonsReady();
          
          if (buttonsReady) {
            log('State 1: Condition =', selectedCondition, '+ buttons READY - triggering');
            return true;
          } else {
            log('State 1: Condition =', selectedCondition, '- waiting for buttons to load...');
            return false;
          }
        } else {
          // Still showing "Condition" placeholder - wait
          return false;
        }
      } else {
        // STATE 2: No dropdown → Trigger immediately (RESTRICTED)
        log('State 2: No dropdown - triggering (RESTRICTED)');
        return true;
      }
    }
    
    /**
     * Check if action buttons are ready (not disabled/loading)
     */
    function areButtonsReady() {
      let hasActiveButton = false;
      
      document.querySelectorAll('kat-button, KAT-BUTTON').forEach(btn => {
        if (btn.shadowRoot) {
          const text = btn.shadowRoot.textContent.trim().toLowerCase();
          
          // Check for our action buttons
          if (text === 'sell this product' || text === 'apply to sell') {
            // Check if button is disabled or loading
            const isDisabled = btn.hasAttribute('disabled') || 
                               btn.getAttribute('disabled') === 'true' ||
                               btn.hasAttribute('loading') ||
                               btn.getAttribute('loading') === 'true';
            
            // Also check inner button element
            const innerBtn = btn.shadowRoot.querySelector('button');
            const innerDisabled = innerBtn && (innerBtn.disabled || innerBtn.hasAttribute('disabled'));
            
            // Check for visual loading state (grayed class)
            const hasLoadingClass = btn.className.includes('loading') || 
                                    btn.className.includes('disabled') ||
                                    (innerBtn && innerBtn.className.includes('loading'));
            
            if (!isDisabled && !innerDisabled && !hasLoadingClass) {
              hasActiveButton = true;
            }
          }
        }
      });
      
      return hasActiveButton;
    }
    
    /**
     * Poll every 2 seconds
     */
    setInterval(() => {
      if (hasProductPanel()) {
        const currentASIN = getASIN();
        
        if (currentASIN && currentASIN !== lastCheckedASIN) {
          log('Panel ready with ASIN:', currentASIN);
          lastCheckedASIN = currentASIN;
          
          // Small delay then run check
          setTimeout(run, 500);
        }
      } else {
        // Panel closed or condition not selected, reset
        if (lastCheckedASIN) {
          log('Panel closed, ready for next check');
          lastCheckedASIN = null;
        }
      }
    }, 2000);
    
    // Listen for manual check requests from popup
    browser.runtime.onMessage.addListener((msg, sender, respond) => {
      if (msg.type === 'CHECK_NOW') {
        log('Manual check requested');
        lastCheckedASIN = null;
        const data = run();
        respond({ success: !!data, data: data });
      }
      return true;
    });
    
    log('Polling every 2 seconds for panel');
  }

  // Start
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
})();
