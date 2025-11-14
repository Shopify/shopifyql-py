---
title: About ShopifyQL for analytics
description: Learn how to use the ShopifyQL syntax for querying store data.
---


You can use the GraphQL Admin API to query data from a merchant using ShopifyQL. The ShopifyQL API enables you to write analytical queries to find insights in merchants' store data.

You can use the ShopifyQL API to create reporting apps that provide business insights for merchants. The ShopifyQL API also enables you to export data from a store, so you can import the data into data warehouses.

For a complete reference of the ShopifyQL language, refer to the [ShopifyQL reference](https://help.shopify.com/manual/reports-and-analytics/shopify-reports/report-types/shopifyql-editor/shopifyql-syntax).

## Access scopes

To use ShopifyQL, you need to [request access to protected customer data](/docs/apps/launch/protected-customer-data#request-access-to-protected-customer-data) in the Partner Dashboard. Your app also needs to meet certain [requirements](/docs/apps/launch/protected-customer-data#requirements) to ensure customer privacy and security. You will need to request access for protected customer data including name, email, address, and phone fields.

You also need to [request access to authenticated access scopes](/docs/api/usage/access-scopes#authenticated-access-scopes) for the `read_reports` access scope.

## How it works

ShopifyQL, or Shopify Query Language, is Shopify's query language built for commerce. Query languages are used to request and retrieve data from databases. Your store's data is stored in database tables, structured in defined columns and rows. Refer to the documentation on [how to use ShopifyQL](https://help.shopify.com/manual/reports-and-analytics/shopify-reports/report-types/shopifyql-editor).

The GraphQL Admin API enables you to interact with store data using ShopifyQL. You can compose queries that sort and filter store data, so you can create interfaces or visuals that merchants can use to find patterns in their stores.

## Segment query language

The segment query language is a different implementation of ShopifyQL that uses a subset of ShopifyQL. The segment query language only uses the `WHERE` clause from ShopifyQL to filter customers by their attributes.

You can use the segment query language to create a collection of customers that are filtered out by specific criteria. Filtered customers in a collection are called "segment members", and the collections of filtered customers are called "segments". Merchants can create segments in the Shopify admin.

For a complete reference of the segment query language, refer to the [segment query language reference](/docs/api/shopifyql/segment-query-language-reference).

## Example

The following example shows how to use [`shopifyqlQuery`](/docs/api/admin-graphql/latest/queries/shopifyqlQuery) in the GraphQL Admin API to retrieve the total sales for the previous 3 months.

<StackedCodeBlock title="POST https://{shop}.myshopify.com/api/{api_version}/graphql.json">
<CodeBlocks type="basic" title="GraphQL query">
    <CodeBlock>
      ```graphql
      {
        # The example below sends a ShopifyQL query to the Admin GraphQL API.
        shopifyqlQuery(query: "FROM sales SHOW total_sales GROUP BY month SINCE -3m ORDER BY month") {
          tableData {
            columns {
              name
              dataType
              displayName
            }
            rows
          }
          # parseErrors specifies that you want errors returned, if there were any
          parseErrors
        }
      }
      ```
    </CodeBlock>
  </CodeBlocks>
  <CodeBlocks type="basic" title="JSON response">
    <CodeBlock>
      ```json
      {
        "shopifyqlQuery": {
          "tableData": {
            "columns": [
              {
                "name": "month",
                "dataType": "MONTH_TIMESTAMP",
                "displayName": "Month"
              },
              {
                "name": "total_sales",
                "dataType": "MONEY",
                "displayName": "Total sales"
              }
            ],
            "rows": [
              {
                "month": "2025-01-01",
                "total_sales": "123.456"
              },
               {
                "month": "2025-01-03",
                "total_sales": "55.44"
              },
               {
                "month": "2025-01-04",
                "total_sales": "99.87"
              }
            ]
          },
          "parseErrors": []
        }
      }
      ```
    </CodeBlock>
  </CodeBlocks>
</StackedCodeBlock>

## Python SDK

For Python developers, Shopify offers a dedicated Python SDK that simplifies working with ShopifyQL queries. The `shopifyql` package handles the GraphQL API interactions for you and provides a clean, Pythonic interface for running queries and working with results.

### Key features

- **Minimal setup**: Get started with just a shop name and access token
- **Flexible result formats**: Choose from dependency-free records (default), pandas DataFrames, or polars DataFrames
- **Connection reuse**: Built-in session management for efficient multiple queries
- **Rate limiting**: Automatic rate limit handling to avoid 429 errors
- **OAuth helper**: Optional development utility to obtain access tokens via browser
- **Type-safe results**: Structured data ready for analysis

### Installation

Install the base package with no heavy dependencies:

```bash
pip install shopifyql
```

Or include support for pandas and polars:

```bash
pip install "shopifyql[all]"
```

### Quick start example

The same query from the GraphQL example above becomes much simpler with the Python SDK:

```python
from shopifyql import ShopifyQLClient

client = ShopifyQLClient(shop="your-shop", access_token="shpat_...")

records = client.query("FROM sales SHOW total_sales GROUP BY month SINCE -3m ORDER BY month")
print(records)
# [{"month": "2025-01-01", "total_sales": "123.456"}, ...]
```

### Working with pandas

For data analysis workflows, you can get results directly as pandas DataFrames:

```python
from shopifyql import ShopifyQLClient

client = ShopifyQLClient(shop="your-shop", access_token="shpat_...")
df = client.query_pandas("FROM sales SHOW total_sales GROUP BY month SINCE -3m ORDER BY month")
print(df.head())
```

### Using the Jupyter notebook template

The fastest way to get started is with our CLI template that sets up a complete development environment:

```bash
shopify app init --template=https://github.com/Shopify/shopify-app-notebooks-template
```

This template provides:
- Pre-configured Python 3.11+ environment with Jupyter notebooks
- Automatic app configuration and authentication
- All necessary dependencies installed
- Ready-to-use development environment powered by Shopify CLI

For more details, examples, and advanced usage, visit the [shopifyql Python package repository](https://github.com/Shopify/shopifyql-py).

## Next steps

- Access the language reference for [ShopifyQL](https://help.shopify.com/manual/reports-and-analytics/shopify-reports/report-types/shopifyql-editor/shopifyql-syntax).
- Access the language reference for Shopify's [segment query language](/docs/api/shopifyql/segment-query-language-reference).
- Try the [Python SDK for ShopifyQL](https://github.com/Shopify/shopifyql-py) for a simplified development experience.


