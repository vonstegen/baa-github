# S-Agent: Shipping & Status Agent

Part of the [Book Arbitrage Agent (BAA)](../README.md) system.

## 🎯 Purpose

The S-Agent tracks the complete lifecycle of every book from purchase to sale, providing visibility into:
- Order status from source marketplaces
- Inbound shipping to your location
- Processing and condition grading
- FBA shipment status
- Amazon inventory status
- Sale completion and profit tracking

## 📊 Book Lifecycle Stages

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         BOOK LIFECYCLE                                       │
│                                                                              │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐  │
│  │ ORDERED │───▶│ SHIPPED │───▶│RECEIVED │───▶│PROCESSED│───▶│  FBA    │  │
│  │         │    │ TO YOU  │    │         │    │         │    │ INBOUND │  │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘    └─────────┘  │
│       │              │              │              │              │         │
│       ▼              ▼              ▼              ▼              ▼         │
│   B-Agent        Tracking       Scan In        Grade &        Ship to      │
│   places         number         barcode        list           Amazon       │
│   order          updates                                                    │
│                                                                              │
│  ┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐                  │
│  │   FBA   │───▶│  LIVE   │───▶│  SOLD   │───▶│COMPLETE │                  │
│  │CHECK-IN │    │         │    │         │    │         │                  │
│  └─────────┘    └─────────┘    └─────────┘    └─────────┘                  │
│       │              │              │              │                        │
│       ▼              ▼              ▼              ▼                        │
│   Amazon          Active        Order          Profit                      │
│   receives        listing       shipped        calculated                  │
│   inventory       on Amazon     to buyer                                   │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 📦 Status Definitions

| Status | Description | Triggered By |
|--------|-------------|--------------|
| `ORDERED` | Order placed with source marketplace | B-Agent |
| `SHIPPED_TO_YOU` | Source has shipped the book | Tracking update |
| `IN_TRANSIT_TO_YOU` | Book is in transit to your location | Tracking update |
| `DELIVERED_TO_YOU` | Book delivered to your location | Tracking update |
| `RECEIVED` | Book scanned into inventory | Manual scan |
| `PROCESSING` | Book being graded/prepared | Manual update |
| `PROCESSED` | Book graded, listing created | L-Agent |
| `FBA_SHIPMENT_CREATED` | Added to FBA shipment | L-Agent |
| `FBA_SHIPPED` | Shipment sent to Amazon | Tracking update |
| `FBA_IN_TRANSIT` | Shipment in transit to Amazon | Tracking update |
| `FBA_DELIVERED` | Shipment delivered to Amazon FC | Tracking update |
| `FBA_RECEIVING` | Amazon is processing shipment | SP-API |
| `FBA_AVAILABLE` | Live and available for sale | SP-API |
| `RESERVED` | Customer order pending | SP-API |
| `SOLD` | Item sold and shipped to customer | SP-API |
| `COMPLETE` | Sale complete, profit calculated | S-Agent |
| `RETURNED` | Customer returned item | SP-API |
| `STRANDED` | Listing issue, needs attention | SP-API |
| `LOST` | Item lost in transit/warehouse | Manual/SP-API |

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                            S-AGENT                                           │
│                                                                              │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      STATUS TRACKER                                   │  │
│  │                                                                        │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │  │
│  │  │   Source    │  │   FBA       │  │   Amazon    │  │   Manual    │  │  │
│  │  │  Tracking   │  │  Tracking   │  │   SP-API    │  │   Input     │  │  │
│  │  │  (eBay,etc) │  │  (UPS,etc)  │  │             │  │   (Scans)   │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘  │  │
│  │         │                │                │                │          │  │
│  │         └────────────────┴────────────────┴────────────────┘          │  │
│  │                                   │                                    │  │
│  │                                   ▼                                    │  │
│  │                         ┌─────────────────┐                           │  │
│  │                         │  Status Engine  │                           │  │
│  │                         │                 │                           │  │
│  │                         │ • State machine │                           │  │
│  │                         │ • Transitions   │                           │  │
│  │                         │ • Validations   │                           │  │
│  │                         └─────────────────┘                           │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                   │                                        │
│                                   ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      DATA STORAGE                                     │  │
│  │                                                                        │  │
│  │  • Book records with full history                                     │  │
│  │  • Status change timestamps                                           │  │
│  │  • Financial tracking (cost, fees, revenue, profit)                  │  │
│  │  • Performance metrics                                                │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
│                                   │                                        │
│                                   ▼                                        │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │                      OUTPUTS                                          │  │
│  │                                                                        │  │
│  │  • Dashboard / Status board                                           │  │
│  │  • Alerts (delays, issues, stranded inventory)                       │  │
│  │  • Reports (P&L, velocity, aging)                                    │  │
│  │  • Integration with other agents                                      │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────────────┘
```

## 📁 File Structure

```
s-agent/
├── README.md                 # This file
├── src/
│   ├── main.py              # S-Agent orchestrator
│   ├── models/
│   │   ├── book.py          # Book data model
│   │   ├── status.py        # Status enum and transitions
│   │   └── events.py        # Status change events
│   ├── trackers/
│   │   ├── source_tracker.py    # eBay, AbeBooks tracking
│   │   ├── shipping_tracker.py  # UPS, USPS, FedEx
│   │   └── amazon_tracker.py    # SP-API inventory status
│   ├── storage/
│   │   ├── database.py      # SQLite/PostgreSQL
│   │   └── models.py        # ORM models
│   ├── reports/
│   │   ├── dashboard.py     # Status dashboard
│   │   ├── pnl.py          # Profit & Loss
│   │   └── alerts.py       # Alert system
│   └── api/
│       └── endpoints.py     # REST API for integrations
├── config/
│   └── settings.yaml        # Configuration
├── data/
│   └── inventory.db         # Local database
└── docs/
    └── API.md              # API documentation
```

## 🔧 Data Model

### Book Record

```python
@dataclass
class Book:
    # Identification
    id: str                      # Internal ID
    asin: str                    # Amazon ASIN
    isbn: str                    # ISBN (if available)
    title: str
    
    # Source purchase
    source_marketplace: str      # eBay, AbeBooks, etc.
    source_order_id: str
    source_price: float
    source_shipping: float
    source_tracking: str
    
    # Current status
    status: BookStatus
    status_updated_at: datetime
    
    # Location tracking
    current_location: str        # Source, InTransit, YourLocation, FBA, etc.
    
    # FBA details
    fba_shipment_id: str
    fba_tracking: str
    fnsku: str
    
    # Listing details
    condition: str
    listing_price: float
    
    # Sale details (when sold)
    sale_date: datetime
    sale_price: float
    amazon_fees: float
    
    # Calculated
    total_cost: float            # source_price + source_shipping + fba_fees
    profit: float                # sale_price - total_cost - amazon_fees
    roi: float                   # profit / total_cost * 100
    days_to_sell: int            # Days from FBA_AVAILABLE to SOLD
    
    # History
    status_history: List[StatusEvent]
```

### Status Event

```python
@dataclass
class StatusEvent:
    status: BookStatus
    timestamp: datetime
    source: str                  # What triggered this update
    notes: str                   # Optional notes
    metadata: dict               # Additional data (tracking info, etc.)
```

## 🚀 Usage

### Initialize S-Agent

```python
from s_agent import SAgent

agent = SAgent()
```

### Add a new book (from B-Agent)

```python
book = agent.add_book(
    asin="1234567890",
    title="Example Book",
    source_marketplace="eBay",
    source_order_id="EB-123456",
    source_price=10.99,
    source_shipping=3.99
)
# Status: ORDERED
```

### Update tracking

```python
agent.update_tracking(
    book_id=book.id,
    tracking_number="1Z999AA10123456784",
    carrier="UPS"
)
# Status auto-updates based on tracking
```

### Mark as received

```python
agent.mark_received(book.id, notes="Good condition as expected")
# Status: RECEIVED
```

### Update after processing (from L-Agent)

```python
agent.mark_processed(
    book_id=book.id,
    condition="Very Good",
    listing_price=24.99,
    fnsku="X001ABC123"
)
# Status: PROCESSED
```

### Add to FBA shipment

```python
agent.add_to_shipment(
    book_id=book.id,
    shipment_id="FBA15ABC123",
    tracking="1Z999AA10123456785"
)
# Status: FBA_SHIPMENT_CREATED
```

### Query books by status

```python
# Books waiting to be received
pending = agent.get_books_by_status(BookStatus.SHIPPED_TO_YOU)

# Books in FBA receiving
receiving = agent.get_books_by_status(BookStatus.FBA_RECEIVING)

# All active (not sold/complete)
active = agent.get_active_books()
```

### Get dashboard data

```python
dashboard = agent.get_dashboard()
# {
#     'total_books': 150,
#     'by_status': {
#         'ORDERED': 5,
#         'SHIPPED_TO_YOU': 12,
#         'RECEIVED': 8,
#         ...
#     },
#     'total_invested': 1500.00,
#     'total_sold': 45,
#     'total_revenue': 1200.00,
#     'total_profit': 450.00,
#     'average_roi': 42.5,
#     'average_days_to_sell': 18
# }
```

### Generate P&L report

```python
pnl = agent.generate_pnl_report(
    start_date="2025-01-01",
    end_date="2025-11-30"
)
```

## 📊 Reports & Alerts

### Dashboard Metrics

- Books by status (pipeline view)
- Total invested vs. returned
- Profit & Loss summary
- Average days to sell
- ROI by source marketplace
- Inventory aging

### Alerts

| Alert | Trigger | Action |
|-------|---------|--------|
| `DELIVERY_DELAYED` | No tracking update in 7 days | Contact seller |
| `STRANDED_INVENTORY` | Amazon listing issue | Fix listing |
| `AGING_INVENTORY` | No sale in 60 days | Consider repricing |
| `LOW_MARGIN` | Actual ROI < expected | Review sourcing |
| `LOST_SHIPMENT` | FBA shipment not received | File claim |

## 🔗 Integration with Other Agents

### From B-Agent (Buying)
```python
# B-Agent creates book record after purchase
s_agent.add_book(
    asin=purchase.asin,
    source_marketplace=purchase.marketplace,
    source_order_id=purchase.order_id,
    source_price=purchase.price,
    source_shipping=purchase.shipping
)
```

### From L-Agent (Listing)
```python
# L-Agent updates after processing
s_agent.mark_processed(
    book_id=book_id,
    condition=graded_condition,
    listing_price=calculated_price,
    fnsku=amazon_fnsku
)

# L-Agent updates after shipment creation
s_agent.add_to_shipment(
    book_id=book_id,
    shipment_id=fba_shipment_id,
    tracking=tracking_number
)
```

### From R-Agent (Repricing)
```python
# R-Agent can query active inventory
active_books = s_agent.get_books_by_status(BookStatus.FBA_AVAILABLE)

# R-Agent updates listing price
s_agent.update_listing_price(book_id, new_price)
```

### To All Agents (Events)
```python
# S-Agent emits events that other agents can subscribe to
@s_agent.on_status_change
def handle_status_change(book, old_status, new_status):
    if new_status == BookStatus.SOLD:
        # Notify for analytics
        analytics.record_sale(book)
```

## 🛠️ Configuration

```yaml
# config/settings.yaml

database:
  type: sqlite  # or postgresql
  path: data/inventory.db

tracking:
  # API keys for tracking services
  ups_api_key: ${UPS_API_KEY}
  usps_api_key: ${USPS_API_KEY}
  
  # Check interval (minutes)
  check_interval: 60

amazon:
  # SP-API credentials for inventory status
  refresh_token: ${SP_API_REFRESH_TOKEN}
  
  # Check interval (minutes)
  inventory_check_interval: 30

alerts:
  # Enable/disable alerts
  enabled: true
  
  # Notification method
  method: email  # or slack, webhook
  
  # Thresholds
  delivery_delay_days: 7
  aging_inventory_days: 60
  
dashboard:
  # Auto-refresh interval (seconds)
  refresh_interval: 300
```

## 📈 Metrics Tracked

### Per Book
- Days in each status
- Total time to sale
- Actual vs. expected profit
- ROI percentage

### Aggregate
- Total books processed
- Total investment
- Total revenue
- Total profit
- Average ROI
- Average days to sell
- Success rate (sold vs. returned/lost)
- Profit by source marketplace
- Profit by book category

## 🔮 Future Enhancements

- [ ] Web dashboard UI
- [ ] Mobile app for scanning/receiving
- [ ] Barcode scanner integration
- [ ] Automated tracking updates
- [ ] Machine learning for sale prediction
- [ ] Integration with accounting software
- [ ] Multi-user support
- [ ] Batch operations

## 📖 Documentation

- [API Reference](docs/API.md)
- [Database Schema](docs/SCHEMA.md)
- [Integration Guide](docs/INTEGRATION.md)
