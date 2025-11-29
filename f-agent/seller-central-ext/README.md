# BAA Seller Central Extension

A Firefox browser extension that automatically checks book selling eligibility on Amazon Seller Central. Part of the **Book Arbitrage Agent (BAA)** project.

## 🎯 Purpose

When sourcing books for Amazon FBA arbitrage, you need to quickly determine if you can sell a specific book. This extension automatically detects your eligibility status when viewing products in Amazon Seller Central's product search.

## ✨ Features

- **Auto-detection**: Automatically triggers when you select a condition (New/Used/Collectible) from the dropdown
- **Visual notifications**: Color-coded popup showing eligibility status
- **Three status types**:
  - ✅ **GOOD** (Green) - You can sell this product
  - ⚠️ **NEED APPROVAL** (Orange) - You need to apply for approval
  - 🚫 **RESTRICTED** (Red) - Product is restricted from listing
- **Product info display**: Shows ASIN, BSR, and title in the notification
- **Shadow DOM support**: Works with Amazon's KAT (Katal) web components

## 📸 Screenshots

### GOOD Status
![GOOD Status](docs/screenshots/good-status.png)
*"Sell this product" button available - you can list this item*

### NEED APPROVAL Status
![NEED APPROVAL Status](docs/screenshots/need-approval-status.png)
*"Apply to sell" button shown - brand approval required*

### RESTRICTED Status
![RESTRICTED Status](docs/screenshots/restricted-status.png)
*Only "Copy listing" button - product cannot be listed*

## 🔧 Installation

### Firefox (Temporary - For Development)

1. Download or clone this repository
2. Open Firefox and navigate to `about:debugging`
3. Click "This Firefox" in the left sidebar
4. Click "Load Temporary Add-on..."
5. Navigate to the extension folder and select `manifest.json`
6. The extension is now loaded!

### Firefox (Permanent - Unsigned)

1. Navigate to `about:config`
2. Set `xpinstall.signatures.required` to `false`
3. Go to `about:addons`
4. Click the gear icon → "Install Add-on From File..."
5. Select the `.zip` file

## 📖 How to Use

1. Go to [Amazon Seller Central](https://sellercentral.amazon.com)
2. Navigate to **Catalog** → **Add Products**
3. Search for a book by ASIN, ISBN, or title
4. Click on a product to open the slide-out panel
5. **For State 1 products**: Select a condition (New/Used/Collectible) from the dropdown
6. **For State 2 products**: Extension triggers immediately
7. Wait for the notification to appear (top-right corner)

## 🔄 How It Works

### Two Panel States

The extension detects two different states in the Seller Central product panel:

#### State 1: Has Condition Dropdown
```
┌─────────────────────────────────────┐
│ Product information                 │
│ ASIN: 1234567890                   │
│ Select a condition and sell        │
│ [Dropdown: New/Used/Collectible ▼] │
│ [Copy listing] [Sell/Apply button] │
└─────────────────────────────────────┘
```
- Extension **waits** for you to select a condition
- Checks the actual button that appears
- Returns **GOOD** or **NEED_APPROVAL**

#### State 2: No Condition Dropdown (Restricted)
```
┌─────────────────────────────────────┐
│ Product information                 │
│ ASIN: 1234567890                   │
│ [Copy listing]                      │
│ "This product has listing          │
│  limitations..."                    │
└─────────────────────────────────────┘
```
- Extension triggers **immediately**
- Always returns **RESTRICTED**

### Detection Logic

```
1. Panel opens → Check for "Select a condition and sell"
   │
   ├─ YES (State 1):
   │   └─ Wait for condition selection (New/Used/Collectible)
   │       └─ Wait for button to be active (not grayed)
   │           └─ Check button text:
   │               • "Sell this product" → GOOD ✅
   │               • "Apply to sell" → NEED_APPROVAL ⚠️
   │
   └─ NO (State 2):
       └─ Trigger immediately → RESTRICTED 🚫
```

### Technical Details

Amazon Seller Central uses **KAT (Katal)** web components with **Shadow DOM**. Regular DOM queries can't access content inside Shadow DOM, so the extension:

1. Searches all shadow roots for text content
2. Specifically queries `kat-button` elements for button labels
3. Checks `kat-dropdown` shadow roots for selected condition
4. Waits for buttons to become active (not disabled/loading)

## 📁 File Structure

```
baa-seller-central/
├── manifest.json      # Extension configuration
├── content.js         # Main detection logic (runs on SC pages)
├── background.js      # Storage management
├── popup.html         # Extension popup UI
├── popup.js           # Popup functionality
└── icons/
    ├── icon-48.png    # Extension icon (48x48)
    └── icon-96.png    # Extension icon (96x96)
```

## 🛠️ Development

### Key Functions

| Function | Purpose |
|----------|---------|
| `findInShadowDOM(text)` | Search all shadow roots for specific text |
| `getSelectedCondition()` | Get dropdown value (New/Used/Collectible) |
| `areButtonsReady()` | Check if buttons are active (not loading) |
| `hasProductPanel()` | Determine if panel is ready for check |
| `checkEligibility()` | Main logic - returns status |
| `showNotification(data)` | Display colored popup |

### Polling Mechanism

The extension polls every 2 seconds checking:
1. Is ASIN visible? (panel open)
2. Is "Copy listing" present? (panel loaded)
3. Is condition selected? (for State 1)
4. Are buttons ready? (not grayed/loading)

### Console Logging

All logs are prefixed with `[BAA-SC]` for easy filtering:

```javascript
// Filter in browser console:
[BAA-SC]
```

Example output:
```
[BAA-SC] BAA Seller Central Checker v6.1
[BAA-SC] State 1: Condition = Used + buttons READY - triggering
[BAA-SC] Panel ready with ASIN: 1593278268
[BAA-SC] CHECKING ELIGIBILITY v5.6
[BAA-SC] Has condition dropdown: true
[BAA-SC] Button labels: ['search', '', 'copy listing', 'apply to sell']
[BAA-SC] ⚠️ RESULT: NEED_APPROVAL
```

## 🐛 Troubleshooting

### Extension not triggering?

1. **Check console** for `[BAA-SC]` logs
2. **Verify panel is open** with product info visible
3. **Select a condition** from dropdown (State 1)
4. **Wait 2-3 seconds** for polling cycle

### Wrong status showing?

1. **Wait for button to turn blue** (not grayed)
2. **Check button text** matches expected
3. **Reload extension** via `about:debugging`

### Console commands for debugging

```javascript
// Check if dropdown text is visible
document.querySelectorAll('kat-dropdown').forEach(d => {
  if(d.shadowRoot) console.log(d.shadowRoot.textContent);
});

// Check button labels
document.querySelectorAll('kat-button').forEach(b => {
  if(b.shadowRoot) console.log(b.shadowRoot.textContent.trim());
});

// Check if text is in shadow DOM
document.querySelectorAll('*').forEach(el => {
  if(el.shadowRoot && el.shadowRoot.textContent.includes('Sell this product')) {
    console.log('Found in:', el.tagName);
  }
});
```

## 📊 Test ASINs

| ASIN | Expected Result | Notes |
|------|-----------------|-------|
| 1835080030 | ✅ GOOD | Cryptography Algorithms |
| 1593278268 | ⚠️ NEED_APPROVAL | Serious Cryptography |
| 1837022011 | 🚫 RESTRICTED | Generative AI with LangChain |
| 0735211299 | Test | Atomic Habits |
| 1401971369 | Test | The Let Them Theory |

## 🔮 Future Enhancements

- [ ] Chrome extension support
- [ ] Batch ASIN checking
- [ ] CSV export of results
- [ ] Integration with BAA orchestrator
- [ ] Price/profit calculation
- [ ] Historical tracking

## 📜 Version History

| Version | Changes |
|---------|---------|
| v6.1 | Smart button loading detection - waits for active state |
| v5.9 | Fixed dropdown detection using `startsWith` |
| v5.6 | Simplified State 1/State 2 logic |
| v5.3 | Full shadow DOM search for all KAT components |
| v4.0 | Added `all_frames: true` for iframe support |
| v3.0 | Initial Shadow DOM support |

## ⏱️ Development Stats

This extension was developed through **20+ iterations** over approximately **3-4 hours** of intensive debugging.

| Metric | Value |
|--------|-------|
| Total Versions | 20+ (v3.0 → v6.1) |
| Development Time | ~3-4 hours |
| Lines of Code | ~600 |
| Shadow DOM Elements Discovered | 20+ KAT components |
| Documentation Files | 6 |

### Why So Many Iterations?

Amazon Seller Central uses **Shadow DOM** extensively, making every standard DOM technique fail. Each iteration uncovered a new challenge:

1. **v3.x** - Discovered MutationObserver unreliable, switched to polling
2. **v4.x** - Discovered Shadow DOM, learned to query shadow roots
3. **v5.x** - Discovered dropdown contains ALL options, found header element
4. **v6.x** - Discovered buttons are grayed during loading

See [docs/PROJECT_HISTORY.md](docs/PROJECT_HISTORY.md) for the complete development timeline.

## 🤝 Contributing

This is part of the BAA (Book Arbitrage Agent) project. Contributions welcome!

## 📄 License

MIT License - See LICENSE file for details.

## 🔗 Related

- [BAA Project Overview](../README.md)
- [SP-API Restrictions Script](../baa-restrictions-api/)
- [Decision Logic Framework](../docs/decision-logic.md)
