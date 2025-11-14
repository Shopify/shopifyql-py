from abc import ABC, abstractmethod
from collections.abc import Iterable, Mapping
from typing import Any


class ShopifyQLResult(ABC):
    """
    Abstract base class for ShopifyQL result objects.

    Args:
        table_data: The table data from the ShopifyQL API

    Returns:
        The result object. Subclasses must implement this method.
    """

    @classmethod
    @abstractmethod
    def from_table_data(cls, table_data: dict[str, Any]) -> Any: ...


class ShopifyQLRecordsResult(ShopifyQLResult):
    """
    Dependency-free result that returns a list of dictionaries (records).
    Keys are column names and values are row values.
    """

    @classmethod
    def from_table_data(cls, table_data: dict[str, Any]) -> list[dict[str, Any]]:
        columns = table_data.get("columns", [])
        rows = table_data.get("rows", [])
        column_names = [c.get("name") for c in columns]
        return [dict(zip(column_names, row)) for row in rows]


class ShopifyQLPandasResult(ShopifyQLResult):
    """
    Result object for ShopifyQL queries that returns a pandas DataFrame.
    """

    TYPES_MAP: dict[str, object] = {
        "UNSPECIFIED": "string",
        "MONEY": "Float64",
        "PERCENT": "Float64",
        "INTEGER": "Int64",
        "FLOAT": "Float64",
        "DECIMAL": "Float64",
        "STRING": "string",
        "BOOLEAN": "boolean",
        "TIMESTAMP": "datetime64[ns]",
        "SECOND_TIMESTAMP": "datetime64[ns]",
        "MINUTE_TIMESTAMP": "datetime64[ns]",
        "HOUR_TIMESTAMP": "datetime64[ns]",
        "DAY_TIMESTAMP": "datetime64[ns]",
        "WEEK_TIMESTAMP": "datetime64[ns]",
        "MONTH_TIMESTAMP": "datetime64[ns]",
        "QUARTER_TIMESTAMP": "datetime64[ns]",
        "YEAR_TIMESTAMP": "datetime64[ns]",
        "DAY_OF_WEEK": "Int64",
        "HOUR_OF_DAY": "Int64",
        "MONTH_OF_YEAR": "Int64",
        "WEEK_OF_YEAR": "Int64",
        "IDENTITY": "string",
        "ARRAY": "object",
        "MILLISECOND_DURATION": "timedelta64[ns]",
        "SECOND_DURATION": "timedelta64[ns]",
        "MINUTE_DURATION": "timedelta64[ns]",
        "HOUR_DURATION": "timedelta64[ns]",
        "DAY_DURATION": "timedelta64[ns]",
        "CUMULATIVE": "Float64",
    }

    @classmethod
    def _pandas_dtypes_from_columns(
        cls, columns: Iterable[Mapping[str, Any]]
    ) -> dict[str, object]:
        pandas_dtypes: dict[str, object] = {}
        for column in columns:
            column_name = str(column.get("name", ""))
            shopifyql_type = str(column.get("dataType", "")).upper()
            pandas_dtype = cls.TYPES_MAP.get(shopifyql_type, "string")
            if column_name:
                pandas_dtypes[column_name] = pandas_dtype
        return pandas_dtypes

    @classmethod
    def from_table_data(cls, table_data: dict[str, Any]) -> Any:
        try:
            import pandas as pd  # type: ignore
        except ImportError as e:
            raise ImportError(
                "pandas is not installed. Install with 'pip install shopifyql[pandas]' or 'pip install pandas'."
            ) from e

        data_types = cls._pandas_dtypes_from_columns(table_data["columns"])
        column_names = [str(c.get("name", "")) for c in table_data["columns"]]
        df = pd.DataFrame(table_data["rows"], columns=column_names)
        return df.astype(data_types)


class ShopifyQLPolarsResult(ShopifyQLResult):
    """
    Result object for ShopifyQL queries that returns a polars DataFrame.
    """

    @classmethod
    def _polars_dtypes_from_columns(
        cls, columns: Iterable[Mapping[str, Any]]
    ) -> dict[str, object]:
        # Build a Polars-specific mapping to concrete pl.DataType objects
        try:
            import polars as pl  # type: ignore
        except ImportError:
            # Defer error handling to caller
            raise

        dtype_map: dict[str, object] = {
            "UNSPECIFIED": pl.String,
            "MONEY": pl.Float64,
            "PERCENT": pl.Float64,
            "INTEGER": pl.Int64,
            "FLOAT": pl.Float64,
            "DECIMAL": pl.Float64,
            "STRING": pl.String,
            "BOOLEAN": pl.Boolean,
            "TIMESTAMP": pl.Datetime(time_unit="ns"),
            "SECOND_TIMESTAMP": pl.Datetime(time_unit="ns"),
            "MINUTE_TIMESTAMP": pl.Datetime(time_unit="ns"),
            "HOUR_TIMESTAMP": pl.Datetime(time_unit="ns"),
            "DAY_TIMESTAMP": pl.Datetime(time_unit="ns"),
            "WEEK_TIMESTAMP": pl.Datetime(time_unit="ns"),
            "MONTH_TIMESTAMP": pl.Datetime(time_unit="ns"),
            "QUARTER_TIMESTAMP": pl.Datetime(time_unit="ns"),
            "YEAR_TIMESTAMP": pl.Datetime(time_unit="ns"),
            "DAY_OF_WEEK": pl.Int64,
            "HOUR_OF_DAY": pl.Int64,
            "MONTH_OF_YEAR": pl.Int64,
            "WEEK_OF_YEAR": pl.Int64,
            "IDENTITY": pl.String,
            # ARRAY intentionally omitted to allow inference for heterogeneous data
            "MILLISECOND_DURATION": pl.Duration(time_unit="ns"),
            "SECOND_DURATION": pl.Duration(time_unit="ns"),
            "MINUTE_DURATION": pl.Duration(time_unit="ns"),
            "HOUR_DURATION": pl.Duration(time_unit="ns"),
            "DAY_DURATION": pl.Duration(time_unit="ns"),
            "CUMULATIVE": pl.Float64,
        }

        polars_dtypes: dict[str, object] = {}
        for column in columns:
            column_name = str(column.get("name", ""))
            shopifyql_type = str(column.get("dataType", "")).upper()
            polars_dtype = dtype_map.get(shopifyql_type)
            if column_name and polars_dtype is not None:
                polars_dtypes[column_name] = polars_dtype
        return polars_dtypes

    @classmethod
    def from_table_data(cls, table_data: dict[str, Any]) -> Any:
        try:
            import polars as pl  # type: ignore
        except ImportError as e:
            raise ImportError(
                "polars is not installed. Install with 'pip install shopifyql[polars]' or 'pip install polars'."
            ) from e

        column_names = [str(c.get("name", "")) for c in table_data["columns"]]
        data_types = cls._polars_dtypes_from_columns(table_data["columns"])
        df = pl.DataFrame(table_data["rows"], schema=column_names, orient="row")
        return df.cast(data_types)
