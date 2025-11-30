cd C:\Users\andre\Git_Projects\baa-github\f-agent\src
python test_decision_engine.py
```

This will test the decision engine with 8 different scenarios showing:
- ✅ Books that should be bought
- ❌ Books that should be skipped (and why)
- 👀 Books that should be watched

## Full Integration Flow

For the complete system to work automatically:
```
┌─────────────────────┐
│  1. Extension       │  You browse Seller Central
│     (Manual)        │  Extension checks eligibility
│                     │  Saves to browser storage
└─────────┬───────────┘
          │
          ▼ (Need to build this bridge)
┌─────────────────────┐
│  2. Export Data     │  Extension exports to JSON
│     (TODO)          │  Or: Browser automation reads storage
└─────────┬───────────┘
          │
          ▼
┌─────────────────────┐
│  3. F-Agent         │  Reads eligibility data
│     (Working!)      │  Adds Keepa data
│                     │  Makes BUY/SKIP/WATCH decision
└─────────────────────┘