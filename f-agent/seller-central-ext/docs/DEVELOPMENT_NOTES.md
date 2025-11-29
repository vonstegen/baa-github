# Development Notes & Lessons Learned

## The Journey

This extension went through **20+ iterations** (v3.0 to v6.1) to get working correctly. Here's what we learned along the way.

---

## Challenge 1: Shadow DOM Discovery

### Initial Approach (Failed)
```javascript
// We tried this first
document.body.innerText.includes('Copy listing')  // Returns FALSE!
```

### What We Found
Amazon Seller Central uses **KAT (Katal)** - Amazon's internal web component framework. All UI elements are inside Shadow DOM.

### Debugging Commands That Helped
```javascript
// Find all elements with Shadow DOM
document.querySelectorAll('*').forEach(el => {
  if (el.shadowRoot) console.log('Shadow DOM found:', el.tagName, el.className);
});

// Result: LOTS of KAT-* components
// KAT-BUTTON, KAT-DROPDOWN, KAT-PANEL, KAT-BOX, etc.
```

### Solution
```javascript
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

---

## Challenge 2: Dropdown Shows All Options

### Initial Approach (Failed)
```javascript
// Check if "Used" is selected
const hasUsed = findInShadowDOM('Used');  // Always TRUE!
```

### What We Found
The dropdown Shadow DOM contains ALL options, not just the selected one:
```
Full text: Select a condition and sell    Condition    New    Used    Collectible
```

### Debugging Commands That Helped
```javascript
document.querySelectorAll('kat-dropdown').forEach(dropdown => {
  dropdown.shadowRoot.querySelectorAll('*').forEach(el => {
    if (el.textContent.includes('Used')) {
      console.log(el.tagName, el.className, 'Visible:', el.offsetParent !== null);
    }
  });
});

// Result:
// DIV select-header Text: Condition Visible: true     ← The HEADER shows selected value
// KAT-OPTION Text: Used Visible: false               ← Options are HIDDEN
```

### Solution
```javascript
function getSelectedCondition() {
  let selected = null;
  
  document.querySelectorAll('kat-dropdown').forEach(dropdown => {
    if (dropdown.shadowRoot) {
      // Get the HEADER element, not the full text
      const header = dropdown.shadowRoot.querySelector('.select-header');
      const text = header?.textContent.trim();
      
      // Header shows "Used    Condition" when Used is selected
      if (text?.startsWith('Used')) selected = 'Used';
      // etc.
    }
  });
  
  return selected;
}
```

---

## Challenge 3: False Positive from Instruction Text

### Initial Approach (Failed)
```javascript
// Check for "Sell this product" button
const hasSellButton = findInShadowDOM('Sell this product');  // TRUE even when restricted!
```

### What We Found
The page contains instruction text like:
> "If the ability to list this product changes, you will be able to sell by clicking **'Sell this product'** or 'Apply to Sell'."

This text appears even on RESTRICTED products!

### Solution
Only check actual BUTTON elements, not all page text:
```javascript
// Get button labels ONLY
const buttonLabels = [];
document.querySelectorAll('kat-button').forEach(btn => {
  if (btn.shadowRoot) {
    const text = btn.shadowRoot.textContent.trim().toLowerCase();
    if (text.length < 30) {  // Buttons have short text
      buttonLabels.push(text);
    }
  }
});

// Check for EXACT button text
const hasSellButton = buttonLabels.some(l => l === 'sell this product');
```

---

## Challenge 4: Buttons Are Grayed During Loading

### Initial Approach (Failed)
Extension triggers immediately when condition is selected, but buttons are still loading (grayed out).

### What We Found
After selecting a condition, Amazon makes an API call. The buttons appear immediately but are **disabled/grayed** until the response comes back.

### Debugging Commands That Helped
```javascript
document.querySelectorAll('kat-button').forEach(btn => {
  console.log(
    btn.shadowRoot?.textContent.trim(),
    'disabled:', btn.hasAttribute('disabled'),
    'loading:', btn.getAttribute('loading')
  );
});
```

### Solution
```javascript
function areButtonsReady() {
  let hasActiveButton = false;
  
  document.querySelectorAll('kat-button').forEach(btn => {
    if (btn.shadowRoot) {
      const text = btn.shadowRoot.textContent.trim().toLowerCase();
      
      if (text === 'sell this product' || text === 'apply to sell') {
        // Check multiple disabled indicators
        const isDisabled = btn.hasAttribute('disabled') || 
                           btn.getAttribute('loading') === 'true';
        
        const innerBtn = btn.shadowRoot.querySelector('button');
        const innerDisabled = innerBtn?.disabled;
        
        if (!isDisabled && !innerDisabled) {
          hasActiveButton = true;
        }
      }
    }
  });
  
  return hasActiveButton;
}
```

---

## Challenge 5: Two Different Panel States

### What We Found
There are TWO different panel layouts:

**State 1: Has Dropdown**
- Shows "Select a condition and sell" dropdown
- User must select New/Used/Collectible
- Can result in GOOD or NEED_APPROVAL

**State 2: No Dropdown**
- Shows only "Copy listing" button
- No condition selection possible
- Always RESTRICTED

### Solution
```javascript
function hasProductPanel() {
  const hasDropdown = findInShadowDOM('Select a condition and sell');
  const hasCopyListing = findInShadowDOM('Copy listing');
  
  if (hasCopyListing && hasDropdown) {
    // State 1: Wait for condition selection
    const condition = getSelectedCondition();
    return condition && areButtonsReady();
  } else if (hasCopyListing && !hasDropdown) {
    // State 2: Trigger immediately (RESTRICTED)
    return true;
  }
  
  return false;
}
```

---

## Debugging Toolkit

### Essential Console Commands

```javascript
// 1. See all KAT buttons and their text
document.querySelectorAll('kat-button').forEach(btn => {
  if (btn.shadowRoot) console.log(btn.shadowRoot.textContent.trim());
});

// 2. Check dropdown selected value
document.querySelectorAll('kat-dropdown').forEach(d => {
  const header = d.shadowRoot?.querySelector('.select-header');
  console.log('Selected:', header?.textContent.trim());
});

// 3. Search for ANY text in shadow DOM
const search = 'Sell this product';
document.querySelectorAll('*').forEach(el => {
  if (el.shadowRoot?.textContent.includes(search)) {
    console.log('Found in:', el.tagName);
  }
});

// 4. Check if page has dropdown
const hasDropdown = !!Array.from(document.querySelectorAll('*')).find(
  el => el.shadowRoot?.textContent.includes('Select a condition and sell')
);
console.log('Has dropdown:', hasDropdown);
```

---

## Key Takeaways

1. **Always check for Shadow DOM first** when dealing with modern web apps
2. **Don't trust `innerText`** - it won't see Shadow DOM content
3. **Element visibility matters** - dropdowns contain hidden options
4. **Wait for loading states** - buttons may appear before they're active
5. **Test multiple product types** - different products have different UI states
6. **Add comprehensive logging** - `[BAA-SC]` prefix for easy filtering

---

## Version History Summary

| Version | Main Fix |
|---------|----------|
| v3.0 | Initial Shadow DOM support |
| v4.0 | Added `all_frames: true` |
| v4.6 | Exact button text matching |
| v5.3 | Full shadow root search |
| v5.6 | Two-state logic |
| v5.8 | Header element for dropdown |
| v5.9 | `startsWith()` for header text |
| v6.1 | Button loading detection |
