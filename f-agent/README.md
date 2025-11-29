# F-Agent: Finding Agent

Part of the [Book Arbitrage Agent (BAA)](../README.md) system.

## 🎯 Purpose

The F-Agent discovers profitable book arbitrage opportunities by analyzing:
- **Eligibility** - Can you sell it on Amazon?
- **Demand** - How fast does it sell?
- **Profitability** - Will you make money?

## 📦 Components

```
f-agent/
├── seller-central-ext/      # ✅ Browser extension (v6.1)
├── src/
│   ├── main.py              # Main orchestrator
│   ├── eligibility/         # Extension bridge
│   ├── decision/            # BUY/SKIP/WATCH logic
│   └── keepa/               # Historical data
├── config/
│   ├── thresholds.yaml      # Decision criteria
│   └── publisher_watchlist.yaml
├── data/                    # Cache & results
└── docs/
    └── ARCHITECTURE.md      # Detailed design
```

## 🚀 Quick Start

### 1. Install Browser Extension

```bash
cd seller-central-ext/src
# Load in Firefox via about:debugging → Load Temporary Add-on
```

### 2. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure (Optional)

```bash
# For Keepa integration
export KEEPA_API_KEY=your_api_key

# Edit decision thresholds
nano config/thresholds.yaml
```

### 4. Run Analysis

```bash
cd src
python main.py 1234567890 0987654321
```

Or from a file:
```bash
python main.py -f asins.txt
```

## 📊 Output Example

```
✅ 1234567890: BUY
   Eligibility: GOOD
   Reason: All criteria passed - recommend purchase
   ROI: 45.2%
   Max Buy: $12.50

❌ 0987654321: SKIP
   Eligibility: RESTRICTED
   Reason: Skip: Product is restricted

Summary: 1 BUY / 1 SKIP / 0 WATCH
Buy Rate: 50.0%
```

## 🔧 Configuration

### Decision Thresholds (`config/thresholds.yaml`)

| Setting | Default | Description |
|---------|---------|-------------|
| `bsr.max_rank` | 2,000,000 | Maximum BSR to consider |
| `roi.minimum_percent` | 30 | Minimum ROI required |
| `competition.max_fba_sellers` | 10 | Max FBA competition |
| `sales.min_monthly_sales` | 1 | Minimum monthly sales |

### Publisher Watchlist

Edit `config/publisher_watchlist.yaml` to add publishers to avoid.

## 🔗 Integration

### With Browser Extension

```python
from eligibility.extension_bridge import ExtensionBridge

bridge = ExtensionBridge()
result = bridge.check_eligibility("1234567890")
print(result.status)  # GOOD, NEED_APPROVAL, or RESTRICTED
```

### With Keepa API

```python
from keepa.api_client import KeepaClient

client = KeepaClient()  # Requires KEEPA_API_KEY env var
product = client.get_product("1234567890")
print(product.current_bsr, product.estimated_monthly_sales)
```

### Full Analysis

```python
from main import FAgent

agent = FAgent()
result = agent.analyze_book("1234567890", source_price=10.99)

if result.decision.value == "BUY":
    print(f"Buy at max ${result.max_buy_price}")
```

## 📈 Decision Flow

```
Input: ASIN + Source Price
         │
         ▼
┌─────────────────────┐
│ Check Eligibility   │ → RESTRICTED? → SKIP
│ (SC Extension)      │
└─────────────────────┘
         │ GOOD/NEED_APPROVAL
         ▼
┌─────────────────────┐
│ Fetch Keepa Data    │ → BSR > 2M? → SKIP
│ (BSR, Price, Sales) │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ Calculate ROI       │ → ROI < 30%? → SKIP
│ (2025 FBA Fees)     │
└─────────────────────┘
         │
         ▼
┌─────────────────────┐
│ Check Competition   │ → Too many? → WATCH
│ Check Price Trend   │ → Declining? → WATCH
└─────────────────────┘
         │
         ▼
       BUY ✅
```

## 📖 Documentation

- [Architecture](docs/ARCHITECTURE.md) - Detailed system design
- [Extension Docs](seller-central-ext/README.md) - Browser extension
- [Technical Details](seller-central-ext/docs/TECHNICAL.md) - Shadow DOM handling
- [Project History](seller-central-ext/docs/PROJECT_HISTORY.md) - Development timeline

## 🧪 Testing

```bash
# Test with known ASINs
python src/main.py 1835080030 1593278268 1837022011

# Expected:
# 1835080030 → GOOD (or based on your account)
# 1593278268 → NEED_APPROVAL
# 1837022011 → RESTRICTED
```

## ⏭️ Output to B-Agent

After F-Agent approves books, send the buy list to **B-Agent** for purchasing:

```python
buy_list = agent.get_buy_list()
# → Pass to B-Agent for marketplace purchasing
```
