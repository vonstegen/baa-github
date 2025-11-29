# R-Agent: Repricing Agent

**Status:** ⬜ Planned

## Purpose

The R-Agent maintains optimal prices for maximum profit and Buy Box wins.

## Planned Features

- Real-time competitor price monitoring
- Dynamic repricing algorithms
- Buy Box optimization strategies
- Long-tail inventory management
- Liquidation rules for stale inventory
- Profit margin protection

## Integration

Monitors active inventory from L-Agent:
```python
# Continuous monitoring
active_inventory = l_agent.get_active_listings()

for listing in active_inventory:
    optimal_price = r_agent.calculate_optimal_price(listing)
    if optimal_price != listing.current_price:
        r_agent.update_price(listing, optimal_price)
```

## Repricing Strategies

- **Competitive** - Match or beat lowest FBA price
- **Buy Box** - Optimize for Buy Box ownership
- **Profit** - Maintain minimum profit margin
- **Velocity** - Adjust based on sales speed
- **Liquidation** - Reduce price on aged inventory

## Development

Coming after L-Agent is complete.
