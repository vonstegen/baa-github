# Technical Documentation: BAA Seller Central Extension

## Overview

This document covers the technical implementation details, lessons learned, and architectural decisions made during development.

## The Shadow DOM Challenge

### Problem

Amazon Seller Central uses **KAT (Katal)** - Amazon's internal web component framework. All UI elements are rendered inside Shadow DOM, making them invisible to standard DOM queries:

```javascript
// This returns false even when "Copy listing" is visible on screen!
document.body.innerText.includes('Copy listing')  // false
```

### Solution

We discovered that Shadow DOM elements are "open" and accessible via `el.shadowRoot`:

```javascript
// Search ALL shadow roots
function findInShadowDOM(searchText) {
  let found = false;
  document.querySelectorAll('*').forEach(el => {
    if (el.shadowRoot && el.shadowRoot.textContent.includes(searchText)) {
      found = true;
    }
  });
  return found;
}
```

### Key KAT Components

| Component | Purpose | Shadow DOM Content |
|-----------|---------|-------------------|
| `KAT-BUTTON` | Action buttons | Button label text |
| `KAT-DROPDOWN` | Condition selector | All options + selected value |
| `KAT-PANEL` | Slide-out container | Product information |

## Dropdown Detection Challenge

### Problem

The condition dropdown shadow DOM contains ALL options, not just the selected one:

```
Full text: Select a condition and sell    Condition    New    Used    Collectible
```

Simply checking for "Used" in the text would always return true!

### Solution

We found the **header element** shows only the selected value:

```javascript
function getSelectedCondition() {
  let selected = null;
  
  document.querySelectorAll('kat-dropdown, KAT-DROPDOWN').forEach(dropdown => {
    if (dropdown.shadowRoot) {
      const header = dropdown.shadowRoot.querySelector(
        '.select-header, .header-row, [class*="header"]'
      );
      
      if (header) {
        const text = header.textContent.trim();
        // Header shows "Used    Condition" when Used is selected
        if (text.startsWith('New')) selected = 'New';
        else if (text.startsWith('Used')) selected = 'Used';
        else if (text.startsWith('Collectible')) selected = 'Collectible';
      }
    }
  });
  
  return selected;
}
```

## Button Loading State

### Problem

After selecting a condition, buttons appear but are initially **grayed/disabled** while loading. Checking immediately gives wrong results.

### Solution

Wait for buttons to become active:

```javascript
function areButtonsReady() {
  let hasActiveButton = false;
  
  document.querySelectorAll('kat-button, KAT-BUTTON').forEach(btn => {
    if (btn.shadowRoot) {
      const text = btn.shadowRoot.textContent.trim().toLowerCase();
      
      if (text === 'sell this product' || text === 'apply to sell') {
        const isDisabled = btn.hasAttribute('disabled') || 
                           btn.getAttribute('loading') === 'true';
        
        const innerBtn = btn.shadowRoot.querySelector('button');
        const innerDisabled = innerBtn && innerBtn.disabled;
        
        if (!isDisabled && !innerDisabled) {
          hasActiveButton = true;
        }
      }
    }
  });
  
  return hasActiveButton;
}
```

## State Machine

```
┌─────────────────────────────────────────────────────────────┐
│                      INITIAL STATE                          │
│                    (Page Loaded)                            │
└─────────────────────────────────────────────────────────────┘
                            │
                            ▼
┌─────────────────────────────────────────────────────────────┐
│                   POLLING (every 2s)                        │
│                                                             │
│  Check: hasASIN && hasCopyListing                          │
└─────────────────────────────────────────────────────────────┘
                            │
              ┌─────────────┴─────────────┐
              │                           │
              ▼                           ▼
┌──────────────────────┐    ┌──────────────────────────────┐
│     STATE 1          │    │         STATE 2              │
│  Has Dropdown        │    │      No Dropdown             │
│                      │    │                              │
│  Wait for:           │    │  Trigger immediately         │
│  - Condition select  │    │  → RESTRICTED                │
│  - Button ready      │    │                              │
└──────────────────────┘    └──────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────────────────────────────┐
│                    CHECK ELIGIBILITY                         │
│                                                              │
│  Find button in Shadow DOM:                                  │
│  - "Sell this product" → GOOD                               │
│  - "Apply to sell" → NEED_APPROVAL                          │
│  - Neither found → UNKNOWN                                   │
└──────────────────────────────────────────────────────────────┘
              │
              ▼
┌──────────────────────────────────────────────────────────────┐
│                   SHOW NOTIFICATION                          │
│                                                              │
│  Display colored popup with:                                 │
│  - Status (GOOD/NEED_APPROVAL/RESTRICTED)                   │
│  - ASIN                                                      │
│  - BSR                                                       │
│  - Title                                                     │
└──────────────────────────────────────────────────────────────┘
```

## Manifest Configuration

### Key Settings

```json
{
  "manifest_version": 2,
  "content_scripts": [
    {
      "matches": ["https://sellercentral.amazon.com/*"],
      "js": ["content.js"],
      "run_at": "document_idle",
      "all_frames": true  // Important for iframe content
    }
  ]
}
```

### Permissions

- `storage` - Save check history
- `activeTab` - Access current tab
- `https://sellercentral.amazon.com/*` - Run on Seller Central

## Debugging Tips

### Console Commands

```javascript
// 1. Check what buttons exist
document.querySelectorAll('kat-button').forEach(btn => {
  if(btn.shadowRoot) console.log(btn.shadowRoot.textContent.trim());
});

// 2. Check dropdown value
document.querySelectorAll('kat-dropdown').forEach(d => {
  if(d.shadowRoot) {
    const header = d.shadowRoot.querySelector('.select-header');
    console.log('Selected:', header?.textContent.trim());
  }
});

// 3. Find specific text in shadow DOM
const searchText = 'Sell this product';
document.querySelectorAll('*').forEach(el => {
  if(el.shadowRoot?.textContent.includes(searchText)) {
    console.log('Found in:', el.tagName, el.className);
  }
});

// 4. Check button disabled state
document.querySelectorAll('kat-button').forEach(btn => {
  console.log(
    btn.shadowRoot?.textContent.trim(),
    'disabled:', btn.hasAttribute('disabled')
  );
});
```

### Common Issues

| Issue | Cause | Solution |
|-------|-------|----------|
| Extension not triggering | Shadow DOM not searched | Use `findInShadowDOM()` |
| Wrong status (GOOD instead of NEED_APPROVAL) | Button text found in page text | Check only button labels |
| Triggers before selection | Dropdown shows all options | Check header element only |
| Wrong status (checking too early) | Buttons still loading | Wait for `areButtonsReady()` |

## Performance Considerations

### Polling Interval

Currently set to **2 seconds**. Trade-offs:
- Shorter: Faster response, higher CPU usage
- Longer: Slower response, lower CPU usage

### Shadow DOM Search

Searching all shadow roots is O(n) where n = number of elements. For Seller Central pages, this is acceptable (~1000 elements, <10ms).

## Browser Compatibility

| Browser | Status | Notes |
|---------|--------|-------|
| Firefox | ✅ Tested | Primary development browser |
| Chrome | ⚠️ Untested | Should work with minor manifest changes |
| Edge | ⚠️ Untested | Chromium-based, similar to Chrome |
| Safari | ❌ Not supported | Different extension API |

### Chrome Migration Notes

1. Change `manifest_version` to 3
2. Replace `browser` with `chrome` API
3. Update background script to service worker
4. Adjust permissions format

## Security Considerations

- Extension only runs on `sellercentral.amazon.com`
- No external API calls
- No data sent to third parties
- All processing done locally

## Future Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    BAA Orchestrator                         │
│                                                             │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │   Finding   │  │   Buying    │  │   Listing   │        │
│  │    Agent    │  │    Agent    │  │    Agent    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
│         │                │                │                │
│         └────────────────┼────────────────┘                │
│                          │                                  │
│                          ▼                                  │
│  ┌─────────────────────────────────────────────────────┐  │
│  │         Seller Central Extension (This)              │  │
│  │                                                       │  │
│  │  • Eligibility checking                              │  │
│  │  • Real-time status detection                        │  │
│  │  • Browser automation support                        │  │
│  └─────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

## Lessons Learned

1. **Shadow DOM is everywhere** - Modern web apps increasingly use Shadow DOM. Always check for it.

2. **Visual state ≠ DOM state** - A button can look disabled but not have a `disabled` attribute.

3. **Text content includes all children** - `textContent` on a dropdown includes all options, not just selected.

4. **Timing matters** - Always wait for dynamic content to fully load before checking.

5. **Amazon's UI is complex** - Multiple layers of abstraction make scraping challenging.

6. **Console debugging is essential** - Always add comprehensive logging during development.
