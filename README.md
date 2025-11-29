# Book Arbitrage Agent (BAA)

A multi-agent AI system for automating Amazon FBA book arbitrage operations.

## 🎯 Overview

BAA automates the entire book arbitrage workflow using specialized AI agents:

| Agent | Purpose | Status |
|-------|---------|--------|
| **F-Agent** | Finding profitable books | 🟡 In Progress |
| **B-Agent** | Buying from marketplaces | ⬜ Planned |
| **L-Agent** | Listing on Amazon | ⬜ Planned |
| **S-Agent** | Shipping & Status tracking | 🟡 In Progress |
| **R-Agent** | Repricing inventory | ⬜ Planned |

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BAA ORCHESTRATOR                                     │
│                    (Central Coordination Layer)                              │
└─────────────────────────────────────────────────────────────────────────────┘
         │                    │                    │                    │
         ▼                    ▼                    ▼                    ▼
┌─────────────┐      ┌─────────────┐      ┌─────────────┐      ┌─────────────┐
│  F-AGENT    │      │  B-AGENT    │      │  L-AGENT    │      │  R-AGENT    │
│  (Finding)  │─────▶│  (Buying)   │─────▶│  (Listing)  │─────▶│ (Repricing) │
└─────────────┘      └─────────────┘      └─────────────┘      └─────────────┘
                            │                    │
                            ▼                    ▼
                     ┌─────────────────────────────────┐
                     │           S-AGENT               │
                     │    (Shipping & Status)          │
                     │                                 │
                     │  Tracks entire book lifecycle:  │
                     │  Order → Ship → Receive →       │
                     │  Process → FBA → Sell           │
                     └─────────────────────────────────┘
```

## 📦 Repository Structure

```
baa/
├── README.md                 # This file
├── f-agent/                  # Finding Agent
│   ├── seller-central-ext/   # ✅ Browser extension for eligibility
│   ├── src/                  # Agent source code
│   ├── config/               # Thresholds and settings
│   └── docs/                 # Documentation
├── b-agent/                  # Buying Agent (planned)
├── l-agent/                  # Listing Agent (planned)
├── s-agent/                  # Shipping & Status Agent
│   ├── src/                  # Status tracking code
│   │   ├── models/           # Book and Status models
│   │   ├── trackers/         # Shipping trackers
│   │   └── reports/          # Dashboard and reports
│   ├── config/               # Settings
│   └── docs/                 # Documentation
├── r-agent/                  # Repricing Agent (planned)
└── docs/                     # System-wide documentation
```

## 🚀 Quick Start

### F-Agent Setup

1. **Install the Seller Central Extension** (Firefox)
   ```bash
   cd f-agent/seller-central-ext
   # Load as temporary extension in about:debugging
   ```

2. **Set up Python environment**
   ```bash
   cd f-agent
   pip install -r requirements.txt
   ```

3. **Configure API keys**
   ```bash
   export KEEPA_API_KEY=your_keepa_api_key
   ```

4. **Run analysis**
   ```bash
   cd f-agent/src
   python main.py 1234567890 0987654321
   ```

## 📊 F-Agent Components

### Seller Central Extension (v6.1)
Browser extension that automatically checks selling eligibility on Amazon Seller Central.

**Features:**
- Auto-detection when selecting product conditions
- Shadow DOM support for Amazon's KAT components
- Visual notifications (GOOD ✅ / NEED APPROVAL ⚠️ / RESTRICTED 🚫)

**Development Stats:**
- 20+ iterations over 3-4 hours
- Full Shadow DOM reverse engineering
- Smart button loading detection

[Full Extension Documentation →](f-agent/seller-central-ext/README.md)

### Decision Engine
Makes BUY/SKIP/WATCH decisions based on:
- Eligibility status (from extension)
- BSR and sales velocity (from Keepa)
- ROI calculations (2025 FBA fees)
- Competition analysis
- Publisher watchlist

### Keepa Integration
Fetches historical data:
- BSR history (90 days)
- Price trends
- Sales velocity estimation
- Competition tracking

## 📈 Decision Criteria

| Criteria | Threshold | Required |
|----------|-----------|----------|
| Eligibility | GOOD | ✅ Yes |
| BSR | < 2,000,000 | ✅ Yes |
| Monthly Sales | > 1 | Preferred |
| ROI | > 30% | ✅ Yes |
| FBA Sellers | < 10 | Preferred |
| Price Trend | Stable/Rising | Preferred |

## 🛠️ Technology Stack

- **Python 3.10+** - Core agent logic
- **Firefox Extension** - Browser automation
- **Keepa API** - Historical data
- **SQLite** - Local caching
- **YAML** - Configuration

## 📅 Development Timeline

### Completed ✅
- Seller Central Extension (v6.1)
- Extension Bridge (Python integration)
- Decision Engine with 2025 FBA fees
- Keepa API client (stub)

### In Progress 🟡
- Full Keepa integration
- Batch processing
- CLI interface

### Planned ⬜
- B-Agent (marketplace buying)
- L-Agent (Amazon listing)
- R-Agent (repricing)
- Web dashboard
- AI-powered optimization

## 📖 Documentation

- [F-Agent Architecture](f-agent/docs/ARCHITECTURE.md)
- [Extension Technical Docs](f-agent/seller-central-ext/docs/TECHNICAL.md)
- [Project History](f-agent/seller-central-ext/docs/PROJECT_HISTORY.md)
- [Installation Guide](f-agent/seller-central-ext/docs/INSTALLATION.md)
- [S-Agent Status Tracking](s-agent/README.md)

## 🧪 Test ASINs

| ASIN | Expected | Description |
|------|----------|-------------|
| 1835080030 | ✅ GOOD | Cryptography Algorithms |
| 1593278268 | ⚠️ NEED_APPROVAL | Serious Cryptography |
| 1837022011 | 🚫 RESTRICTED | Generative AI with LangChain |
| 0735211299 | Test | Atomic Habits |
| 1401971369 | Test | The Let Them Theory |

## 📄 License

MIT License - See [LICENSE](LICENSE) for details.

## 🤝 Contributing

Contributions welcome! Please read the documentation before submitting PRs.

## ⚠️ Disclaimer

This tool is for educational purposes. Always comply with:
- Amazon's Terms of Service
- Marketplace policies
- Applicable laws and regulations

Use at your own risk.
