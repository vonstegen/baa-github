# L-Agent: Listing Agent

**Status:** ⬜ Planned

## Purpose

The L-Agent handles creating and managing Amazon FBA listings.

## Planned Features

- Automatic listing creation via SP-API
- Condition grading assistance
- Description generation
- Pricing strategy (initial price)
- Shipment creation
- Label generation

## Integration

Receives purchased books from B-Agent:
```python
# From B-Agent
purchased_books = b_agent.get_completed_orders()

# L-Agent processes
for book in purchased_books:
    condition = l_agent.assess_condition(book)
    listing = l_agent.create_listing(book, condition)
    shipment = l_agent.add_to_shipment(listing)
```

## SP-API Integration

- Listings API for creating/updating listings
- Feeds API for bulk operations
- Fulfillment Inbound API for shipments

## Development

Coming after B-Agent is complete.
