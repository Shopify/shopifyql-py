from concurrent.futures import ThreadPoolExecutor
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from shopifyql.client import ShopifyQLClient


@pytest.fixture
def client():
    return ShopifyQLClient(shop="test-shop", access_token="shpat_123")


def test_url_and_default_version(client):
    assert (
        client.url == "https://test-shop.myshopify.com/admin/api/2025-10/graphql.json"
    )


def test_custom_version_in_url():
    c = ShopifyQLClient(shop="s1", access_token="tok", version="2024-07")
    assert c.url == "https://s1.myshopify.com/admin/api/2024-07/graphql.json"


def test_context_manager_creates_and_closes_session():
    c = ShopifyQLClient(shop="s", access_token="t")
    # Outside context, no session is created
    assert c._get_session() is None

    with patch("shopifyql.client.requests.Session") as session_cls:
        session = session_cls.return_value
        with c as ctx:
            assert ctx is c
            s = c._get_session()
            assert s is session
        # On exit, session.close is called
        session.close.assert_called_once()


@patch("shopifyql.client.requests.post")
def test_graphql_inline_uses_requests_post(req_post: MagicMock, client):
    resp = req_post.return_value
    resp.json.return_value = {"data": {"ok": True}}
    resp.raise_for_status.return_value = None

    q = "query { shop { name } }"

    result = client.graphql_query(q, variables={"a": 1})

    req_post.assert_called_once()
    args, kwargs = req_post.call_args
    assert args[0] == client.url
    assert kwargs["headers"]["X-Shopify-Access-Token"] == "shpat_123"
    assert kwargs["headers"]["Content-Type"] == "application/json"
    assert kwargs["json"]["query"] == q
    assert kwargs["json"]["variables"] == {"a": 1}
    assert result == {"data": {"ok": True}}


@patch("shopifyql.client.requests.Session")
def test_graphql_in_context_uses_session_post(session_cls: MagicMock, client):
    session = session_cls.return_value
    response = session.post.return_value
    response.json.return_value = {"data": {"ok": True}}
    response.raise_for_status.return_value = None

    with client as c:
        c.graphql_query("q")

    args, kwargs = session.post.call_args
    assert args[0] == client.url


@patch("shopifyql.client.time.sleep")
@patch("shopifyql.client.requests.Session")
def test_non_200_http_error_is_raised_in_context(
    session_cls: MagicMock, sleep: MagicMock, client
):
    import requests

    session = session_cls.return_value
    resp = MagicMock()
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=SimpleNamespace(status_code=500)
    )
    session.post.return_value = resp

    with client as c:
        with pytest.raises(requests.exceptions.HTTPError):
            c.graphql_query("q")


def test_threaded_usage_creates_session_per_thread():
    c = ShopifyQLClient(shop="s", access_token="t")

    created_sessions = []

    def make_session():
        s = MagicMock()
        r = MagicMock()
        r.raise_for_status.return_value = None
        r.json.return_value = {"data": {"ok": True}}
        s.post.return_value = r
        created_sessions.append(s)
        return s

    with patch(
        "shopifyql.client.requests.Session", side_effect=make_session
    ) as session_cls:
        with c:

            def work(_):
                return c.graphql_query("q")

            with ThreadPoolExecutor(max_workers=3) as ex:
                list(ex.map(work, range(3)))

        # One session for main thread (context enter) + at least one worker
        assert session_cls.call_count >= 2
        # At least one worker session performed a request; the main thread's session may remain unused
        assert any(s.post.called for s in created_sessions)


@patch("shopifyql.client.requests.Session")
def test_query_wrapper_success_parses_table_data(session_cls: MagicMock):
    session = session_cls.return_value
    resp = session.post.return_value
    resp.raise_for_status.return_value = None

    table = {
        "columns": [
            {
                "name": "total_sales",
                "dataType": "INTEGER",
                "displayName": "Total Sales",
            },
        ],
        "rows": [[1], [2]],
    }
    payload = {"data": {"shopifyqlQuery": {"tableData": table}}}
    resp.json.return_value = payload

    c = ShopifyQLClient(shop="s", access_token="t")
    with c:
        out = c.query("from sales show total_sales", result_class=_DummyResult)

    assert out == {"columns": ["total_sales"], "rows": [[1], [2]]}


@patch("shopifyql.client.time.sleep")
@patch("shopifyql.client.requests.post")
def test_non_429_http_error_is_raised(req_post: MagicMock, sleep: MagicMock, client):
    import requests

    resp = MagicMock()
    resp.raise_for_status.side_effect = requests.exceptions.HTTPError(
        response=SimpleNamespace(status_code=500)
    )
    req_post.return_value = resp

    with pytest.raises(requests.exceptions.HTTPError):
        client.graphql_query("q")


class _DummyResult:
    @classmethod
    def from_table_data(cls, table_data):
        # return a simple projection for assertion
        return {
            "columns": [c.get("name") for c in table_data.get("columns", [])],
            "rows": table_data.get("rows", []),
        }


@patch("shopifyql.client.requests.Session")
def test_query_wrapper_raises_on_empty_table_data(session_cls: MagicMock):
    session = session_cls.return_value
    resp = session.post.return_value
    resp.raise_for_status.return_value = None
    resp.json.return_value = {"data": {"shopifyqlQuery": {"tableData": {}}}}

    c = ShopifyQLClient(shop="s", access_token="t")
    with c:
        with pytest.raises(ValueError):
            c.query("from sales show total_sales")


@patch("shopifyql.client.requests.Session")
def test_query_default_returns_records(session_cls: MagicMock):
    session = session_cls.return_value
    resp = session.post.return_value
    resp.raise_for_status.return_value = None

    table = {
        "columns": [
            {"name": "col1", "dataType": "INTEGER", "displayName": "Col 1"},
        ],
        "rows": [[1], [2]],
    }
    payload = {"data": {"shopifyqlQuery": {"tableData": table}}}
    resp.json.return_value = payload

    c = ShopifyQLClient(shop="s", access_token="t")
    with c:
        out = c.query("from sales show total_sales")

    assert isinstance(out, list)
    assert out == [{"col1": 1}, {"col1": 2}]


@patch("shopifyql.client.requests.Session")
def test_query_pandas_returns_dataframe_with_dtypes(session_cls: MagicMock):
    pytest.importorskip("pandas")
    import pandas as pd  # type: ignore

    session = session_cls.return_value
    resp = session.post.return_value
    resp.raise_for_status.return_value = None

    table = {
        "columns": [
            {"name": "col_int", "dataType": "INTEGER", "displayName": "Col Int"},
            {"name": "col_str", "dataType": "STRING", "displayName": "Col Str"},
        ],
        "rows": [[1, "a"], [2, "b"]],
    }
    payload = {"data": {"shopifyqlQuery": {"tableData": table}}}
    resp.json.return_value = payload

    c = ShopifyQLClient(shop="s", access_token="t")
    with c:
        df = c.query_pandas("from sales show total_sales")

    assert isinstance(df, pd.DataFrame)
    assert list(df.columns) == ["col_int", "col_str"]
    assert str(df.dtypes["col_int"]) == "Int64"
    assert str(df.dtypes["col_str"]) == "string"


@patch("shopifyql.client.requests.Session")
def test_query_polars_returns_dataframe_with_schema(session_cls: MagicMock):
    pl = pytest.importorskip("polars")

    session = session_cls.return_value
    resp = session.post.return_value
    resp.raise_for_status.return_value = None

    table = {
        "columns": [
            {"name": "col_int", "dataType": "INTEGER", "displayName": "Col Int"},
            {"name": "col_str", "dataType": "STRING", "displayName": "Col Str"},
        ],
        "rows": [[1, "a"], [2, "b"]],
    }
    payload = {"data": {"shopifyqlQuery": {"tableData": table}}}
    resp.json.return_value = payload

    c = ShopifyQLClient(shop="s", access_token="t")
    with c:
        df = c.query_polars("from sales show total_sales")

    assert isinstance(df, pl.DataFrame)
    # Schema should reflect types mapping
    assert df.schema.get("col_int") == pl.Int64
    assert df.schema.get("col_str") == pl.String
