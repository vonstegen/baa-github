# Changelog

All notable changes to the BAA Seller Central Extension are documented in this file.

## [6.2] - 2025-11-29

### Added
- **JSON Export for F-Agent** - New "Export JSON (F-Agent)" button in popup
- Export format specifically designed for F-Agent's ExtensionBridge
- Export info display showing count and save location
- Green styling for JSON export button

### Changed
- Background script now handles EXPORT_JSON message type
- JSON export includes version, timestamp, and source metadata

### Export Format
```json
{
  "exportedAt": "2025-11-29T20:00:00Z",
  "version": "6.2",
  "source": "baa-seller-central-extension",
  "results": [
    {
      "asin": "1234567890",
      "status": "GOOD",
      "condition": "Used",
      "bsr": 150000,
      "title": "Book Title",
      "checkedAt": "2025-11-29T19:00:00Z"
    }
  ]
}
```

## [6.1] - 2025-11-29

### Added
- Smart button loading detection - waits for buttons to become active (blue) before checking
- `areButtonsReady()` function to detect disabled/loading state
- Better logging for button states

### Fixed
- Extension no longer triggers when buttons are grayed out during loading
- Correct status detection after condition selection

## [5.9] - 2025-11-29

### Fixed
- Dropdown header text detection using `startsWith()` instead of exact match
- Header shows "Used    Condition" when selected, now properly detected

## [5.8] - 2025-11-29

### Added
- Header element detection for dropdown value
- More accurate condition selection detection

### Fixed
- No longer falsely detects "Used" from dropdown options list

## [5.7] - 2025-11-29

### Added
- `getSelectedCondition()` function to check actual dropdown value
- Condition validation (New/Used/Collectible only)

### Fixed
- Extension waits for actual condition selection before triggering

## [5.6] - 2025-11-29

### Changed
- Simplified logic: State 1 can only return GOOD or NEED_APPROVAL
- State 2 always returns RESTRICTED

### Removed
- Unnecessary complexity in status determination

## [5.4] - 2025-11-29

### Added
- Full Shadow DOM search in `hasProductPanel()`
- `findInShadowDOM()` helper function for polling

### Fixed
- Auto-trigger now works with Shadow DOM content

## [5.3] - 2025-11-29

### Added
- Comprehensive Shadow DOM search for all KAT components
- Search all `*` elements for shadow roots

### Fixed
- "Select a condition and sell" detection in KAT-DROPDOWN

## [5.1] - 2025-11-29

### Changed
- State 1: "Copy listing" + "Select a condition and sell" both present
- State 2: "Copy listing" present but NO dropdown

### Fixed
- Correct state detection based on dropdown presence

## [5.0] - 2025-11-29

### Added
- Two-state detection logic
- State 1: Wait for condition selection
- State 2: Immediate trigger for restricted products

## [4.9] - 2025-11-29

### Changed
- checkEligibility now checks for dropdown first
- No dropdown = automatic RESTRICTED

## [4.8] - 2025-11-29

### Added
- Detection for panels without condition dropdown
- Immediate RESTRICTED status for copy-only panels

## [4.6] - 2025-11-29

### Fixed
- Button detection now uses exact match (`===`) not `includes()`
- Prevents false positives from instruction text containing button names

## [4.5] - 2025-11-29

### Added
- Detailed debug logging for button detection
- Individual button shadowRoot inspection

## [4.4] - 2025-11-29

### Added
- Condition selection detection via multiple methods
- "Sell this product" or "Apply to sell" button presence as selection indicator

## [4.3] - 2025-11-29

### Added
- Dropdown value checking via Shadow DOM
- Validation that actual condition is selected (not placeholder)

## [4.2] - 2025-11-29

### Changed
- Trigger only after condition is selected from dropdown
- Wait for condition-specific messages to appear

## [4.1] - 2025-11-29

### Added
- Shadow DOM support for KAT-BUTTON elements
- Recursive text extraction from shadow roots

### Fixed
- Button text detection now works with Amazon's web components

## [4.0] - 2025-11-29

### Added
- `all_frames: true` in manifest for iframe support
- Frame detection logging

### Changed
- Content script now runs in all frames

## [3.9] - 2025-11-29

### Changed
- Switched from MutationObserver to polling approach
- Check every 2 seconds for panel state

## [3.8] - 2025-11-29

### Added
- Smart panel detection with multiple criteria
- Polling for panel readiness

## [3.7] - 2025-11-29

### Changed
- Increased wait time from 1s to 2s for slide-out panel

## [3.6] - 2025-11-29

### Added
- Restriction text detection ("not accepting applications", "listing limitations")
- Priority-based status determination

## [3.0] - 2025-11-29

### Added
- Initial working version
- Basic button text detection
- Visual notification system
- Popup UI for manual checks

## Development Notes

### Key Discoveries

1. **Shadow DOM** - Amazon uses KAT components with Shadow DOM, requiring special handling
2. **Dropdown Structure** - Dropdown shadow contains all options, header shows selected value
3. **Button Loading** - Buttons appear grayed during API calls, must wait for active state
4. **Two Panel States** - Some products have no condition dropdown (always restricted)

### Testing ASINs

Verified working with:
- 1835080030 (GOOD)
- 1593278268 (NEED_APPROVAL)
- 1837022011 (RESTRICTED)
- 0735211299 (Atomic Habits)
- 1401971369 (The Let Them Theory)
