# Installation Guide

## Prerequisites

- Firefox browser (version 109 or higher)
- Amazon Seller Central account
- Access to Seller Central's Add Products feature

## Installation Methods

### Method 1: Temporary Installation (Recommended for Testing)

This method is ideal for testing and development. The extension will be removed when Firefox restarts.

1. **Download the Extension**
   ```bash
   git clone https://github.com/yourusername/baa-seller-central.git
   cd baa-seller-central
   ```

2. **Open Firefox Developer Tools**
   - Type `about:debugging` in the address bar
   - Press Enter

3. **Load the Extension**
   - Click "This Firefox" in the left sidebar
   - Click "Load Temporary Add-on..."
   - Navigate to the `src` folder
   - Select `manifest.json`

4. **Verify Installation**
   - You should see "BAA Seller Central Checker" in the extensions list
   - The extension icon should appear in the toolbar

### Method 2: Permanent Installation (Unsigned)

⚠️ **Warning**: This requires disabling signature verification, which reduces security.

1. **Disable Signature Requirement**
   - Type `about:config` in the address bar
   - Accept the risk warning
   - Search for `xpinstall.signatures.required`
   - Double-click to set it to `false`

2. **Package the Extension**
   ```bash
   cd baa-seller-central/src
   zip -r ../baa-seller-central.zip *
   ```

3. **Install the Extension**
   - Type `about:addons` in the address bar
   - Click the gear icon (⚙️)
   - Select "Install Add-on From File..."
   - Choose `baa-seller-central.zip`

### Method 3: Firefox Developer Edition

For long-term unsigned extension use:

1. Download [Firefox Developer Edition](https://www.mozilla.org/firefox/developer/)
2. Follow Method 1 or Method 2 above

## Post-Installation Setup

### Verify the Extension is Working

1. Go to [Amazon Seller Central](https://sellercentral.amazon.com)
2. Open the browser console (F12 → Console)
3. Look for: `[BAA-SC] BAA Seller Central Checker v6.1`
4. Navigate to Catalog → Add Products
5. Search for any ASIN

### Test with Sample ASINs

| ASIN | Expected Result |
|------|-----------------|
| 1835080030 | ✅ GOOD |
| 1593278268 | ⚠️ NEED_APPROVAL |
| 1837022011 | 🚫 RESTRICTED |

## Updating the Extension

### Temporary Installation
1. Make changes to the code
2. Go to `about:debugging`
3. Click "Reload" next to the extension

### Permanent Installation
1. Make changes to the code
2. Re-create the zip file
3. Go to `about:addons`
4. Remove the old extension
5. Install the new zip file

## Troubleshooting Installation

### Extension Not Loading

**Symptoms**: Nothing appears in `about:debugging`

**Solutions**:
- Ensure `manifest.json` is valid JSON (no trailing commas)
- Check for JavaScript syntax errors in `content.js`
- Verify all files referenced in manifest exist

### Extension Not Running on Page

**Symptoms**: No `[BAA-SC]` logs in console

**Solutions**:
- Verify you're on `sellercentral.amazon.com`
- Check that content scripts are enabled
- Try reloading the extension
- Clear browser cache

### Permission Errors

**Symptoms**: Console shows permission denied errors

**Solutions**:
- Verify manifest permissions include the Seller Central URL
- Check that `all_frames` is set to `true`
- Ensure storage permission is granted

## Uninstallation

### Temporary Installation
- Simply close Firefox, or
- Go to `about:debugging` and click "Remove"

### Permanent Installation
1. Go to `about:addons`
2. Find "BAA Seller Central Checker"
3. Click the three dots (...)
4. Select "Remove"

## Browser Console Access

The extension logs important information to the browser console:

1. Press `F12` to open Developer Tools
2. Click the "Console" tab
3. Type `[BAA-SC]` in the filter to see only extension logs

## File Locations

After installation, extension files are stored at:

**Temporary**: In Firefox's temporary extension directory (varies by OS)

**Permanent**: 
- Windows: `%APPDATA%\Mozilla\Firefox\Profiles\<profile>\extensions\`
- macOS: `~/Library/Application Support/Firefox/Profiles/<profile>/extensions/`
- Linux: `~/.mozilla/firefox/<profile>/extensions/`
