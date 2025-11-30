"""
Import Extension Data and Analyze

This script:
1. Imports eligibility data from the browser extension's JSON export
2. Runs the decision engine on all imported books
3. Shows results and recommendations

Usage:
    python import_and_analyze.py [path_to_json]
    
    If no path provided, looks for:
    - data/extension_export.json
    - Downloads/baa-eligibility-*.json (most recent)
"""

import sys
import os
from pathlib import Path
from datetime import datetime
import glob

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from eligibility.extension_bridge import ExtensionBridge, EligibilityStatus
from decision.engine import DecisionEngine, ProductData, Decision


def find_export_file() -> str:
    """Find the most recent export file"""
    
    # Check default location first
    default_path = Path("data/extension_export.json")
    if default_path.exists():
        return str(default_path)
    
    # Check Downloads folder (Windows)
    downloads = Path.home() / "Downloads"
    if downloads.exists():
        files = list(downloads.glob("baa-eligibility-*.json"))
        if files:
            # Get most recent
            files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
            return str(files[0])
    
    return None


def main():
    print("=" * 70)
    print("F-AGENT: Import Extension Data & Analyze")
    print("=" * 70)
    print()
    
    # Find export file
    if len(sys.argv) > 1:
        export_path = sys.argv[1]
    else:
        export_path = find_export_file()
    
    if not export_path:
        print("❌ No export file found!")
        print()
        print("To export from the extension:")
        print("  1. Click the BAA Seller Central extension icon")
        print("  2. Click '📤 Export JSON (F-Agent)'")
        print("  3. Save the file to: f-agent/data/extension_export.json")
        print()
        print("Or specify a path:")
        print("  python import_and_analyze.py path/to/export.json")
        return
    
    print(f"📂 Import file: {export_path}")
    print()
    
    # Import data
    bridge = ExtensionBridge(export_path=export_path)
    results = bridge.import_from_extension(export_path)
    
    if not results:
        print("❌ No results found in export file")
        return
    
    print()
    print("-" * 70)
    print("ELIGIBILITY SUMMARY")
    print("-" * 70)
    
    # Show eligibility summary
    by_status = {}
    for r in results:
        status = r.status.value
        by_status[status] = by_status.get(status, 0) + 1
    
    for status, count in sorted(by_status.items()):
        icon = {"GOOD": "✅", "NEED_APPROVAL": "⚠️", "RESTRICTED": "🚫"}.get(status, "❓")
        print(f"  {icon} {status}: {count}")
    
    print()
    print("-" * 70)
    print("DECISION ANALYSIS")
    print("-" * 70)
    print()
    
    # Run decision engine
    engine = DecisionEngine()
    
    decisions = {"BUY": [], "SKIP": [], "WATCH": []}
    
    for eligibility in results:
        # Build product data (without Keepa data for now)
        product = ProductData(
            asin=eligibility.asin,
            eligibility_status=eligibility.status.value,
            bsr=eligibility.bsr,
            title=eligibility.title
        )
        
        decision = engine.analyze(product)
        decisions[decision.decision.value].append({
            "asin": eligibility.asin,
            "title": eligibility.title or "Unknown",
            "eligibility": eligibility.status.value,
            "reason": decision.reason
        })
        
        # Print each result
        icon = {"BUY": "✅", "SKIP": "❌", "WATCH": "👀"}[decision.decision.value]
        print(f"{icon} {eligibility.asin}")
        print(f"   Title: {eligibility.title or 'Unknown'}")
        print(f"   Eligibility: {eligibility.status.value}")
        print(f"   Decision: {decision.decision.value}")
        print(f"   Reason: {decision.reason}")
        print()
    
    # Summary
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"✅ BUY:   {len(decisions['BUY'])}")
    print(f"❌ SKIP:  {len(decisions['SKIP'])}")
    print(f"👀 WATCH: {len(decisions['WATCH'])}")
    print()
    
    total = len(results)
    buy_rate = len(decisions['BUY']) / total * 100 if total > 0 else 0
    print(f"Buy Rate: {buy_rate:.1f}%")
    
    # Show buyable ASINs
    if decisions['BUY']:
        print()
        print("-" * 70)
        print("📋 BUYABLE ASINs (copy for B-Agent):")
        print("-" * 70)
        for item in decisions['BUY']:
            print(f"  {item['asin']}  # {item['title'][:40]}")
    
    # Note about Keepa
    print()
    print("-" * 70)
    print("💡 NOTE: Analysis based on eligibility only.")
    print("   For full analysis (BSR, price, sales), configure KEEPA_API_KEY")
    print("   and run: python main.py <asin1> <asin2> ...")


if __name__ == "__main__":
    main()
