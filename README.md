# shopifyql

Python SDK for running ShopifyQL queries from Python. It aims to make it fast and easy to get your store data with minimal setup, while staying flexible for power users.

Key points:

- No hard runtime deps by default (only `requests`).
- Choose your result backend: dependency-free records (default), pandas, or polars.
- Optional OAuth helper to obtain an access token during development.

## Quick setup with CLI template

For the easiest way to test this package, you can use our CLI template that sets up everything for you to start working in a Jupyter Notebook with access to your store:

```bash
shopify app init --template=https://github.com/Shopify/shopify-app-notebooks-template
```

This template will:
- Set up a Python 3.13 environment with all dependencies needed to run `shopifyql` inside Jupyter notebooks
- Handle app configuration and authentication automatically
- Provide a ready-to-use development environment powered by Shopify CLI

See the [template repository](https://github.com/Shopify/shopify-app-notebooks-template) for more details.

## Requirements

- Python 3.11+
- A Shopify `shop` (e.g., `your-shop-name`) and an Admin API access token with `read_reports, read_analytics` scopes.

## Installation

Base (no heavy dependencies):

```bash
pip install shopifyql
```

With pandas support:

```bash
pip install "shopifyql[pandas]"
```

With polars support:

```bash
pip install "shopifyql[polars]"
```

With both pandas and polars:

```bash
pip install "shopifyql[all]"
```

Using uv for local development of this repo:

```bash
uv venv
uv sync --group dev
```

## Quick start

The default return type is a list of dict records, so you can use the library without dependencies if needed.

```python
from shopifyql import ShopifyQLClient

client = ShopifyQLClient(shop="your-shop", access_token="shpat_...")

records = client.query("FROM sales SHOW total_sales SINCE 2025-01-01 UNTIL 2025-01-31")
print(records[:2])  # e.g., [{"total_sales": 123.45}, {"total_sales": 67.89}]
```

### Using pandas

```bash
pip install "shopifyql[pandas]"
```

```python
from shopifyql import ShopifyQLClient, ShopifyQLPandasResult

client = ShopifyQLClient(shop="your-shop", access_token="shpat_...")
df = client.query_pandas("FROM sales SHOW orders TIMESERIES DAY SINCE -30d")
print(df.head())
```

### Using polars

```bash
pip install "shopifyql[polars]"
```

```python
from shopifyql import ShopifyQLClient, ShopifyQLPolarsResult

client = ShopifyQLClient(shop="your-shop", access_token="shpat_...")
df = client.query_polars("FROM sales SHOW total_sales group by product_title")
print(df.head())
```

## OAuth helper (optional)

If you don’t have a token handy, you can use a local browser OAuth helper to obtain one during development:

```python
from shopifyql import ShopifyQLClient

client = ShopifyQLClient.from_oauth(
    shop="your-shop",
    key="your_api_key",
    secret="your_api_secret",
    port = 4545
)

df = client.query_pandas("FROM sales SHOW total_sales SINCE -7d")
```

### Steps for oauth

- Scopes required are `read_reports,read_analytics` scopes can be modified in your app version settings: https://dev.shopify.com/dashboard/ -> Your App -> Versions -> Create a version
- A valid redirect_uri is needed for this oauth flow to work, please use `http://localhost:4545/callback`
- You can only receive scopes that are enabled in your app settings, if you need more you will want to submit a new app version.
- If your browser lands on `admin.shopify.com/.../oauth/authorize` and the helper never returns to `http://localhost:4545/callback`, your app’s Redirect URLs probably don’t include the exact `redirect_uri`. Add `http://localhost:4545/callback` (or the port you pass, configurable in from_oauth) to App setup → Redirect URLs, then try again. The `redirect_uri` must match exactly.
- After auth, you can confirm what the scopes are currently available with:

```python
scopes = client.get_current_scopes()
print(scopes)
```

## Context manager and connection reuse

When running multiple queries, use the client as a context manager to reuse a keep-alive `requests.Session` per thread and avoid repeated TLS/HTTP setup costs:

```python
from shopifyql import ShopifyQLClient

SHOP = "your-shop"
ACCESS_TOKEN = "shpat_..."

with ShopifyQLClient(SHOP, ACCESS_TOKEN) as client:
    df1 = client.query_pandas("FROM sales SHOW total_sales GROUP BY product_title SINCE -30d UNTIL now")
    df2 = client.query_pandas("FROM sales SHOW net_sales GROUP BY product_title SINCE -30d UNTIL now")
    print(df1.merge(df2, on="product_title"))
```

## Custom result classes

You can provide your own result transformer by implementing `ShopifyQLResult`:

```python
from typing import Any
from shopifyql import ShopifyQLClient, ShopifyQLResult

class MyResult(ShopifyQLResult):
    @classmethod
    def from_table_data(cls, table_data: dict[str, Any]) -> Any:
        # Transform the ShopifyQL tableData into your preferred structure
        return {c["name"]: [row[i] for i, _ in enumerate(table_data["columns"])] for i, c in enumerate(table_data["columns"])}

client = ShopifyQLClient(shop="your-shop", access_token="shpat_...")
custom = client.query("from sales show total_sales", result_class=MyResult)
```

## Error handling & rate limits

The client will:

- Gate requests with a fixed-window rate limiter to avoid 429s; if the window is exhausted, it sleeps until the next window (with jitter).
- Backoff and retry on transient request errors (and other request exceptions) up to `max_retries`.

You may see:

- `requests.exceptions.HTTPError` for non-2xx HTTP responses (after retries as applicable).
- `requests.exceptions.RequestException` for network errors (after retries).
- `ValueError("No valid table data found in response")` when the ShopifyQL response is malformed.

## Configuration

- API version: defaults to `2025-10`. Override via constructor `version="YYYY-MM"`.
- Timeout: defaults to 10s per request via constructor `connect_timeout`.
- Retries: defaults to `max_retries=3` with exponential backoff and jitter.
- Rate limiting: `FixedWindowConfig(window_seconds=60, max_requests=1000)` by default; override via `rate_limit_config`.
- Connections: when used as a context manager, the client reuses a per-thread `requests.Session` (keep-alive); outside a context it uses ephemeral sessions.
- Connection pool: `pool_maxsize=10` by default.

## Development

Clone and develop with uv or pip:

```bash
uv venv
uv sync --group=dev
pytest -q
```
