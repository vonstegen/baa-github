# B-Agent: Buying Agent

**Status:** ⬜ Planned

## Purpose

The B-Agent handles purchasing approved books from various marketplaces at the best prices.

## Planned Features

- Multi-marketplace price comparison (eBay, AbeBooks, ThriftBooks, etc.)
- Automatic order placement
- Shipping cost calculation
- Budget management
- Order tracking

## Integration

Receives buy list from F-Agent:
```python
# From F-Agent
buy_list = f_agent.get_buy_list()

# B-Agent processes
for book in buy_list:
    best_source = b_agent.find_best_price(book.asin, book.max_buy_price)
    if best_source:
        b_agent.place_order(best_source)
```

## Marketplaces to Support

- [ ] eBay
- [ ] AbeBooks
- [ ] ThriftBooks
- [ ] Better World Books
- [ ] Amazon (used)
- [ ] Local library sales

## Development

Coming soon after F-Agent is complete.
