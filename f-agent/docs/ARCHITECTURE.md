# F-Agent: Finding Agent Architecture

## Overview

The F-Agent is responsible for **discovering profitable book arbitrage opportunities**. It combines multiple data sources to determine:

1. **Can I sell it?** → Seller Central Extension
2. **Should I sell it?** → Keepa data analysis
3. **Will it be profitable?** → ROI calculations

## F-Agent Components

```
┌─────────────────────────────────────────────────────────────────────────┐
│                            F-AGENT                                       │
│                      (Finding Agent)                                     │
│                                                                          │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    DATA SOURCES                                   │  │
│  │                                                                    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │  │
│  │  │   Keepa     │  │  Seller     │  │   Source Markets        │  │  │
│  │  │   API       │  │  Central    │  │   (eBay, AbeBooks,      │  │  │
│  │  │             │  │  Extension  │  │    ThriftBooks, etc.)   │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │  │
│  │        │                │                      │                 │  │
│  │        ▼                ▼                      ▼                 │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │  │
│  │  │ Historical  │  │ Eligibility │  │  Current Listings       │  │  │
│  │  │ Price/BSR   │  │ Status      │  │  & Prices               │  │  │
│  │  │ Analysis    │  │ Check       │  │                         │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────────┘  │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                │                                        │
│                                ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    DECISION ENGINE                                │  │
│  │                                                                    │  │
│  │   Input: ASIN + Condition + Source Price                         │  │
│  │                                                                    │  │
│  │   Checks:                                                         │  │
│  │   □ Eligibility (GOOD/NEED_APPROVAL/RESTRICTED)                  │  │
│  │   □ BSR threshold (< 2,000,000)                                  │  │
│  │   □ Sales velocity (Keepa drops)                                 │  │
│  │   □ Price stability (90-day trend)                               │  │
│  │   □ Competition (# of FBA sellers)                               │  │
│  │   □ ROI calculation (> 30% minimum)                              │  │
│  │   □ Publisher watchlist (avoid problematic publishers)           │  │
│  │                                                                    │  │
│  │   Output: BUY / SKIP / WATCH                                      │  │
│  └──────────────────────────────────────────────────────────────────┘  │
│                                │                                        │
│                                ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────┐  │
│  │                    OUTPUT                                         │  │
│  │                                                                    │  │
│  │   • Approved book list → B-Agent                                 │  │
│  │   • Watch list → Monitor for price changes                       │  │
│  │   • Rejection log → Learning/adjustment                          │  │
│  └──────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────┘
```

## Component Details

### 1. Seller Central Extension (Eligibility Checking)

**Purpose:** Determine if we CAN sell a book on Amazon

**Location:** `baa-seller-central/` (already built!)

**Input:** ASIN
**Output:** 
```json
{
  "asin": "1234567890",
  "status": "GOOD | NEED_APPROVAL | RESTRICTED",
  "condition": "Used",
  "checkedAt": "2025-11-29T19:00:00Z"
}
```

**Integration Options:**

Option A: **Browser Automation**
- Puppeteer/Playwright controls Firefox with extension loaded
- Navigates to product search, triggers extension
- Reads results from extension storage

Option B: **Extension API**
- Add API endpoint to extension
- F-Agent sends ASINs, extension returns results
- More complex but faster for batch processing

Option C: **Shared Database**
- Extension saves results to database
- F-Agent reads from same database
- Simplest integration, slight delay

### 2. Keepa Data Analyzer

**Purpose:** Analyze historical data to predict profitability

**Data Points from Keepa:**
- BSR history (90 days)
- Price history (Amazon, FBA, FBM)
- Sales velocity (BSR drops = sales)
- Buy Box winner history
- Offer counts over time

**Analysis Scripts Needed:**

```
keepa-analyzer/
├── fetch_product_data.py      # Get data from Keepa API
├── calculate_sales_velocity.py # BSR drops = estimated sales
├── analyze_price_trends.py     # Price stability analysis
├── competition_analysis.py     # FBA seller count trends
├── roi_calculator.py           # Full profit calculation
└── decision_engine.py          # Final BUY/SKIP decision
```

### 3. Decision Engine

**Purpose:** Make final BUY/SKIP/WATCH decision

**Decision Criteria (2025 Updated):**

| Criteria | Threshold | Weight |
|----------|-----------|--------|
| Eligibility | GOOD or NEED_APPROVAL* | Required |
| BSR | < 2,000,000 | Required |
| Sales Velocity | > 1 sale/month | High |
| Price Trend | Stable or rising | Medium |
| FBA Competition | < 10 sellers | Medium |
| ROI | > 30% | Required |
| Publisher | Not on watchlist | Required |

*NEED_APPROVAL only if approval success rate > 70%

**Output Actions:**
- **BUY** → Send to B-Agent with source recommendation
- **SKIP** → Log reason for learning
- **WATCH** → Add to monitoring list

## Data Flow

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Book       │     │  F-Agent    │     │  B-Agent    │
│  Source     │────▶│  (Finding)  │────▶│  (Buying)   │
│  (scan/     │     │             │     │             │
│   list)     │     │             │     │             │
└─────────────┘     └─────────────┘     └─────────────┘
      │                   │
      │                   ▼
      │           ┌─────────────────┐
      │           │ Parallel Checks │
      │           ├─────────────────┤
      │           │ • Keepa API     │
      │           │ • SC Extension  │
      │           │ • Source prices │
      │           └─────────────────┘
      │                   │
      │                   ▼
      │           ┌─────────────────┐
      │           │ Decision Engine │
      │           ├─────────────────┤
      │           │ BUY / SKIP /    │
      │           │ WATCH           │
      │           └─────────────────┘
```

## Integration with Seller Central Extension

### Method 1: Extension Storage Bridge (Recommended for MVP)

```javascript
// In extension: Save results to storage
browser.storage.local.set({
  [`eligibility_${asin}`]: {
    status: 'GOOD',
    checkedAt: new Date().toISOString(),
    condition: 'Used'
  }
});

// F-Agent reads via WebExtensions API or file export
```

### Method 2: WebSocket Communication

```javascript
// Extension listens for commands
const ws = new WebSocket('ws://localhost:8765');
ws.onmessage = (event) => {
  const { action, asin } = JSON.parse(event.data);
  if (action === 'check') {
    // Navigate to ASIN, get result, send back
    ws.send(JSON.stringify({ asin, status: 'GOOD' }));
  }
};
```

### Method 3: REST API in Extension

```javascript
// Extension background script
browser.webRequest.onBeforeRequest.addListener(
  (details) => {
    if (details.url.includes('/baa-api/check/')) {
      const asin = details.url.split('/').pop();
      // Return cached result or trigger check
    }
  },
  { urls: ["*://localhost/baa-api/*"] }
);
```

## F-Agent File Structure

```
f-agent/
├── README.md
├── config/
│   ├── thresholds.yaml        # BSR, ROI, etc. thresholds
│   ├── publisher_watchlist.yaml
│   └── fee_structure.yaml     # Current FBA fees
├── src/
│   ├── main.py                # F-Agent orchestrator
│   ├── eligibility/
│   │   ├── extension_bridge.py    # Talk to SC extension
│   │   └── cache.py               # Cache eligibility results
│   ├── keepa/
│   │   ├── api_client.py          # Keepa API wrapper
│   │   ├── sales_velocity.py      # BSR drop analysis
│   │   ├── price_analyzer.py      # Price trend analysis
│   │   └── competition.py         # Seller count analysis
│   ├── decision/
│   │   ├── engine.py              # Main decision logic
│   │   ├── roi_calculator.py      # Profit calculations
│   │   └── rules.py               # Configurable rules
│   └── output/
│       ├── buy_list.py            # Format for B-Agent
│       ├── watch_list.py          # Monitoring queue
│       └── reporter.py            # Stats and logging
├── tests/
│   └── ...
└── data/
    ├── eligibility_cache.db       # SQLite cache
    └── decision_log.csv           # Learning data
```

## Next Steps

1. **Create Keepa API integration** - Fetch product data
2. **Build decision engine** - Implement rule logic
3. **Create extension bridge** - Connect to SC extension
4. **Set up caching** - Avoid redundant API calls
5. **Build monitoring** - Track decisions and outcomes

## API Requirements

### Keepa API
- Endpoint: `https://api.keepa.com/product`
- Rate limit: 10 requests/minute (free tier)
- Data needed: BSR, prices, offer counts

### Seller Central Extension
- Already built! v6.1
- Needs: Export mechanism for F-Agent

## Configuration Example

```yaml
# config/thresholds.yaml
eligibility:
  allowed_statuses:
    - GOOD
    - NEED_APPROVAL  # Only with high approval rate

bsr:
  max_rank: 2000000
  preferred_max: 500000

sales:
  min_monthly_sales: 1
  preferred_monthly_sales: 3

roi:
  minimum_percent: 30
  preferred_percent: 50

competition:
  max_fba_sellers: 10
  preferred_fba_sellers: 5

price:
  min_selling_price: 10.00
  require_stable_trend: true
```

## Success Metrics

| Metric | Target |
|--------|--------|
| Books analyzed/hour | 100+ |
| Decision accuracy | > 80% profitable |
| False positive rate | < 10% |
| API cost efficiency | < $0.01/book |
