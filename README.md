# Retail Inventory Availability Mesh

High-throughput catalog availability, atomic cart reservations, and stock reconciliation engine in Python for on-demand grocery and retail delivery platforms.

## Core Capabilities
- Atomic inventory reservation with lease timeouts and automatic rollback.
- Multi-store SKU stock reconciliation across external merchant feeds.
- Thread-safe optimistic concurrency control preventing overselling.
- High-concurrency cart checkout validation.

## Test Suite
```bash
pytest -v
```
