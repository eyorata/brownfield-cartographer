# RECONNAISSANCE.md (Interim)

Date: 2026-03-11

Target codebase (required): `dbt-labs/jaffle_shop` (local clone at `./_targets/jaffle_shop`)

## Goal

Produce a Day-One onboarding brief for an unfamiliar brownfield data codebase by manually answering:

- What does this system do?
- What are the key datasets (sources and outputs)?
- Where are the critical transformations defined?
- What are the main failure modes / blast radius if something changes?
- What would I do in the first hour to validate my mental model?

## Quick Description (What This Repo Is)

`jaffle_shop` is a small dbt demo project that transforms "raw" ecommerce data into analytics-ready tables.

- Inputs: seeded CSVs materialized into warehouse tables via `dbt seed`
- Transformations: dbt models in `models/` (staging + marts)
- Outputs: `customers` and `orders` models, intended to be queried by analysts

Repo notes from `README.md`:

- This repo is preserved (not actively maintained).
- It intentionally uses seeds as a self-contained demo (an anti-pattern in real production).

## Project Configuration (Where dbt Looks)

From `dbt_project.yml`:

- Project name: `jaffle_shop`
- `models/` is the model path
- Materialization defaults:
  - `models/jaffle_shop/staging`: `view`
  - everything else: `table`

## Inventory (The Files That Matter)

Core dbt models (SQL):

- `models/staging/stg_customers.sql`
- `models/staging/stg_orders.sql`
- `models/staging/stg_payments.sql`
- `models/customers.sql`
- `models/orders.sql`

Tests / schema docs (YAML):

- `models/staging/schema.yml` (staging tests)
- `models/schema.yml` (model tests + documentation)

Seed inputs (CSV):

- `seeds/raw_customers.csv`
- `seeds/raw_orders.csv`
- `seeds/raw_payments.csv`

## Data Lineage (Manual)

High-level DAG:

1. Seeds -> raw tables
   - `raw_customers` from `seeds/raw_customers.csv`
   - `raw_orders` from `seeds/raw_orders.csv`
   - `raw_payments` from `seeds/raw_payments.csv`

2. Staging -> cleaned views
   - `stg_customers` reads `raw_customers` (see `models/staging/stg_customers.sql`)
   - `stg_orders` reads `raw_orders` (see `models/staging/stg_orders.sql`)
   - `stg_payments` reads `raw_payments` (see `models/staging/stg_payments.sql`)

3. Marts -> analytics tables
   - `customers` reads `stg_customers`, `stg_orders`, `stg_payments` (see `models/customers.sql`)
   - `orders` reads `stg_orders`, `stg_payments` (see `models/orders.sql`)

Key join keys and facts:

- `customers.customer_id` is the user/customer key.
- `orders.customer_id` links orders to customers.
- `payments.order_id` links payments to orders.
- `customers` computes lifetime value and order counts via aggregates over `orders` and `payments`.
- `orders` computes per-payment-method amounts via Jinja loops over `payment_methods`.

## Data Quality / Contracts (Manual)

Staging tests (`models/staging/schema.yml`):

- Uniqueness and not-null constraints for IDs (e.g. `customer_id`, `order_id`, `payment_id`).
- Accepted values constraints:
  - `stg_orders.status` in `['placed','shipped','completed','return_pending','returned']`
  - `stg_payments.payment_method` in `['credit_card','coupon','bank_transfer','gift_card']`

Model tests (`models/schema.yml`):

- `orders.customer_id` has a relationships test pointing to `customers.customer_id`.
- `orders.amount` and per-payment-method amounts are not-null.

Potential issue spotted:

- `models/schema.yml` documents `total_order_amount` for `customers`, but `models/customers.sql` currently outputs `customer_lifetime_value` (naming mismatch that can confuse downstream users).

## First-Hour Validation Checklist

- Run `dbt seed`, then `dbt run`, then `dbt test` to validate the project end-to-end.
- Spot-check row counts:
  - `raw_*` row counts match CSV sizes.
  - `stg_*` row counts match `raw_*` row counts (modulo cleaning).
  - `orders` row counts match `stg_orders`.
  - `customers` row counts match `stg_customers`.
- Sanity check:
  - `orders.amount` equals sum of payment-method amounts.
  - `customers.customer_lifetime_value` equals sum of `orders.amount` grouped by customer.

## Blast Radius (Manual)

If a seed schema changes:

- `raw_customers` change affects: `stg_customers` -> `customers`
- `raw_orders` change affects: `stg_orders` -> `orders`, `customers`
- `raw_payments` change affects: `stg_payments` -> `orders`, `customers`

The `orders` model is a hub:

- It feeds `customers` aggregates.
- It is also used to join payments to customers.

## Cartographer Run (This Repo)

Command used:

```powershell
.\.venv\Scripts\python.exe .\src\cli.py analyze .\_targets\jaffle_shop
```

Artifacts produced (in the target repo):

- `./_targets/jaffle_shop/.cartography/module_graph.json`
- `./_targets/jaffle_shop/.cartography/lineage_graph.json`

Early accuracy observations:

- Lineage graph captures the expected `raw_* -> stg_* -> customers/orders` dependencies.
- SQL parsing logs errors because models contain Jinja; the current lineage extractor relies on regex fallback for `{{ ref(...) }}` and `{{ source(...) }}`.

Known gaps (planned fixes later):

- `module_graph.json` currently lists files but does not encode dbt model-to-model edges (those edges live in `lineage_graph.json`).
- YAML parsing is limited to schema-style `models:`/`sources:` structures; it does not build a complete contract view (tests, exposures, etc.).

## Plan To Reach Final Submission

- Extend the module/system map to represent dbt model dependencies directly (so "module graph" is meaningful for SQL/YAML-only repos).
- Improve SQL lineage to understand more Jinja patterns (loops, macros) and capture line-level citations for refs.
- Generate `CODEBASE.md` and `onboarding_brief.md` automatically per target repo (required for final).
- Add `query` mode (Navigator) to answer:
  - "What produces dataset X?"
  - "What consumes dataset X?"
  - "What breaks if I change column Y in model Z?"
