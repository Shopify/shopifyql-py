import logging
import random
import threading
import time
import weakref
from contextlib import contextmanager
from typing import TYPE_CHECKING, Any

import requests

from .limiter import FixedWindowConfig, FixedWindowRateLimiter
from .results import ShopifyQLRecordsResult, ShopifyQLResult

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    import pandas as pd  # noqa: F401
    import polars as pl  # noqa: F401


class ShopifyQLClient:
    """
    A tiny client for interacting with the Shopify GraphQL API.

    Args:
        shop: Shopify shop name
        access_token: Shopify access token
        version: Shopify API version
    """

    DEFAULT_VERSION: str = "2025-10"
    DEFAULT_PORT = 4545

    @classmethod
    def from_oauth(
        cls,
        shop: str,
        key: str = None,
        secret: str = None,
        version: str = DEFAULT_VERSION,
        port: int = DEFAULT_PORT,
    ) -> "ShopifyQLClient":
        """
        Create a ShopifyQLClient from OAuth authentication.
        Args:
            shop: Shopify shop name
            key: Shopify API key
            secret: Shopify API secret
            version: Shopify API version
            port: Port to use for the local oauth server
        Returns:
            A ShopifyQLClient instance
        """
        from .auth import ShopifyAuthenticator

        auth = ShopifyAuthenticator(shop=shop, key=key, secret=secret, port=port)
        access_token = auth.authenticate()
        return cls(shop, access_token, version)

    def __init__(
        self,
        shop: str,
        access_token: str,
        version: str = DEFAULT_VERSION,
        rate_limit_config: FixedWindowConfig | None = None,
        max_retries: int = 3,
        connect_timeout: int = 10,
        pool_maxsize: int = 10,
    ) -> None:
        self._shop = shop
        self._access_token = access_token
        self._api_version = version or self.DEFAULT_VERSION
        self._local = threading.local()
        self._in_context = False
        self._sessions = weakref.WeakSet()
        rate_limit_config = rate_limit_config or FixedWindowConfig()
        self._rate_limiter = FixedWindowRateLimiter(config=rate_limit_config)
        self._max_retries = max_retries
        self._connect_timeout = connect_timeout
        self._pool_maxsize = pool_maxsize

        # Ensure sessions are closed when the client is garbage collected
        def _finalize_sessions(sessions: weakref.WeakSet):
            for s in list(sessions):
                try:
                    s.close()
                except Exception:
                    pass

        self._finalizer = weakref.finalize(self, _finalize_sessions, self._sessions)

    @contextmanager
    def _get_session(self) -> requests.Session:
        if self._in_context:
            session = getattr(self._local, "session", None)
            if session is None:
                session = requests.Session()
                self._sessions.add(session)
                weakref.finalize(session, session.close)
                self._local.session = session
            yield session
        else:
            with requests.Session() as session:
                yield session

    def __enter__(self) -> "ShopifyQLClient":
        self._in_context = True
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        session = getattr(self._local, "session", None)
        if session is not None:
            try:
                session.close()
            finally:
                self._local.session = None
        self._in_context = False

    @property
    def url(self):
        """GraphQL endpoint URL"""
        return f"https://{self._shop}.myshopify.com/admin/api/{self._api_version}/graphql.json"

    def _validate_errors(self, json_response: dict[str, Any]) -> dict[str, Any]:
        """
        Validate the errors in the JSON response and raise a ValueError if there are any.
        Args:
            json_response: The JSON response from the GraphQL API
        Returns:
            The JSON response
        Raises:
            ValueError: If the response contains errors
        """
        if errors := json_response.get("errors"):
            messages = "\n".join([error.get("message") for error in errors])
            raise ValueError(f"ShopifyQLClient errors: \n{messages}")
        return json_response

    def graphql_query(
        self,
        query: str,
        variables: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Execute a GraphQL query and return parsed JSON. Handles rate limit errors and retries.

        Args:
            query: The GraphQL query to execute
            variables: Variables to pass to the query

        Returns:
            JSON response from the GraphQL API

        Raises:
            requests.exceptions.HTTPError: If the response is not 200 OK
            requests.exceptions.RequestException: If the request fails
            ValueError: If the response is not valid JSON
        """

        headers = {
            "X-Shopify-Access-Token": self._access_token,
            "Content-Type": "application/json",
        }

        payload: dict[str, Any] = {"query": query}
        if variables is not None:
            payload["variables"] = variables

        attempt = 0
        while True:
            try:
                # Gate requests using the fixed-window rate limiter
                wait_seconds = self._rate_limiter.acquire()
                if wait_seconds > 0:
                    # Add jitter to the wait time to avoid thundering herd
                    jitter_ms = random.randint(100, 500)
                    time.sleep(wait_seconds + (jitter_ms / 1000.0))

                # Make the request
                with self._get_session() as session:
                    response = session.post(
                        self.url,
                        headers=headers,
                        json=payload,
                        timeout=self._connect_timeout,
                    )
                    response.raise_for_status()
                    json_response = response.json()
                    return self._validate_errors(json_response)

            except requests.exceptions.RequestException as e:
                logger.error(f"ShopifyQLClient request exception: {e}")
                if attempt < self._max_retries:
                    attempt += 1
                    wait_time = (2**attempt) + random.uniform(0, 1)
                    time.sleep(wait_time)
                    continue
                raise

    def get_current_scopes(self) -> list[str]:
        """
        Get the current scopes granted to the app.
        Returns:
            List of scopes granted to the app
        """

        gql = """
        query AccessScopeList {
            currentAppInstallation {
                accessScopes {
                    handle
                }
            }
        }
        """
        json_response = self.graphql_query(gql)
        return [
            scope.get("handle")
            for scope in json_response.get("data", {})
            .get("currentAppInstallation", {})
            .get("accessScopes", [])
        ]

    def query(
        self,
        shopifyql_query: str,
        result_class: type[ShopifyQLResult] | None = None,
    ) -> Any:
        """
        Execute a ShopifyQL query and return a result object.

        Args:
            shopifyql_query: The ShopifyQL query to execute
            result_class: The class to use to parse the result

        Returns:
            Result object

        Raises:
            ValueError: If the response does not contain valid table data
        """
        gql = """
        query ($q: String!) {
            shopifyqlQuery(query: $q) {
                tableData { columns { name dataType displayName } rows }
                parseErrors
            }
        }
        """
        json_response = self.graphql_query(gql, variables={"q": shopifyql_query})
        if not json_response:
            current_scopes = self.get_current_scopes()
            raise ValueError(
                f"Empty response from ShopifyQL API, make sure you have the correct scopes enabled in your Shopify app settings. Check our docs: https://shopify.dev/docs/api/admin-graphql/latest/queries/shopifyqlQuery \n Current Scopes: {current_scopes}"
            )

        table_data = (
            json_response.get("data", {}).get("shopifyqlQuery", {}).get("tableData", {})
        )
        if not table_data or not table_data.get("columns"):
            logger.warning(f"Current Scopes: {self.get_current_scopes()}")
            raise ValueError(
                "Server returned no valid table data, make sure you have requested the correct scopes. Check our docs: https://shopify.dev/docs/api/admin-graphql/latest/queries/shopifyqlQuery \n Current Scopes: {current_scopes}"
            )

        rc: type[ShopifyQLResult] = result_class or ShopifyQLRecordsResult
        return rc.from_table_data(table_data)

    def query_records(self, shopifyql_query: str) -> list[dict[str, Any]]:
        return self.query(shopifyql_query, result_class=ShopifyQLRecordsResult)

    def query_pandas(self, shopifyql_query: str) -> "pd.DataFrame":
        from .results import ShopifyQLPandasResult

        return self.query(shopifyql_query, result_class=ShopifyQLPandasResult)

    def query_polars(self, shopifyql_query: str) -> "pl.DataFrame":
        from .results import ShopifyQLPolarsResult

        return self.query(shopifyql_query, result_class=ShopifyQLPolarsResult)
