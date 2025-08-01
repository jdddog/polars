from __future__ import annotations

from datetime import date, datetime, time, timedelta
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Callable

import pytest

import polars as pl
from polars._utils.constants import MS_PER_SECOND, NS_PER_SECOND, US_PER_SECOND
from polars.exceptions import ComputeError, InvalidOperationError
from polars.testing import assert_frame_equal
from polars.testing.asserts.series import assert_series_equal
from tests.unit.conftest import INTEGER_DTYPES, NUMERIC_DTYPES

if TYPE_CHECKING:
    from polars._typing import PolarsDataType, PythonDataType


@pytest.mark.parametrize("dtype", [pl.Date(), pl.Date, date])
def test_string_date(dtype: PolarsDataType | PythonDataType) -> None:
    df = pl.DataFrame({"x1": ["2021-01-01"]}).with_columns(
        **{"x1-date": pl.col("x1").cast(dtype)}
    )
    expected = pl.DataFrame({"x1-date": [date(2021, 1, 1)]})
    out = df.select(pl.col("x1-date"))
    assert_frame_equal(expected, out)


def test_invalid_string_date() -> None:
    df = pl.DataFrame({"x1": ["2021-01-aa"]})

    with pytest.raises(InvalidOperationError):
        df.with_columns(**{"x1-date": pl.col("x1").cast(pl.Date)})


def test_string_datetime() -> None:
    df = pl.DataFrame(
        {"x1": ["2021-12-19T00:39:57", "2022-12-19T16:39:57"]}
    ).with_columns(
        **{
            "x1-datetime-ns": pl.col("x1").cast(pl.Datetime(time_unit="ns")),
            "x1-datetime-ms": pl.col("x1").cast(pl.Datetime(time_unit="ms")),
            "x1-datetime-us": pl.col("x1").cast(pl.Datetime(time_unit="us")),
        }
    )
    first_row = datetime(year=2021, month=12, day=19, hour=00, minute=39, second=57)
    second_row = datetime(year=2022, month=12, day=19, hour=16, minute=39, second=57)
    expected = pl.DataFrame(
        {
            "x1-datetime-ns": [first_row, second_row],
            "x1-datetime-ms": [first_row, second_row],
            "x1-datetime-us": [first_row, second_row],
        }
    ).select(
        pl.col("x1-datetime-ns").dt.cast_time_unit("ns"),
        pl.col("x1-datetime-ms").dt.cast_time_unit("ms"),
        pl.col("x1-datetime-us").dt.cast_time_unit("us"),
    )

    out = df.select(
        pl.col("x1-datetime-ns"), pl.col("x1-datetime-ms"), pl.col("x1-datetime-us")
    )
    assert_frame_equal(expected, out)


def test_invalid_string_datetime() -> None:
    df = pl.DataFrame({"x1": ["2021-12-19 00:39:57", "2022-12-19 16:39:57"]})
    with pytest.raises(InvalidOperationError):
        df.with_columns(
            **{"x1-datetime-ns": pl.col("x1").cast(pl.Datetime(time_unit="ns"))}
        )


def test_string_datetime_timezone() -> None:
    ccs_tz = "America/Caracas"
    stg_tz = "America/Santiago"
    utc_tz = "UTC"
    df = pl.DataFrame(
        {"x1": ["1996-12-19T16:39:57 +00:00", "2022-12-19T00:39:57 +00:00"]}
    ).with_columns(
        **{
            "x1-datetime-ns": pl.col("x1").cast(
                pl.Datetime(time_unit="ns", time_zone=ccs_tz)
            ),
            "x1-datetime-ms": pl.col("x1").cast(
                pl.Datetime(time_unit="ms", time_zone=stg_tz)
            ),
            "x1-datetime-us": pl.col("x1").cast(
                pl.Datetime(time_unit="us", time_zone=utc_tz)
            ),
        }
    )

    expected = pl.DataFrame(
        {
            "x1-datetime-ns": [
                datetime(year=1996, month=12, day=19, hour=12, minute=39, second=57),
                datetime(year=2022, month=12, day=18, hour=20, minute=39, second=57),
            ],
            "x1-datetime-ms": [
                datetime(year=1996, month=12, day=19, hour=13, minute=39, second=57),
                datetime(year=2022, month=12, day=18, hour=21, minute=39, second=57),
            ],
            "x1-datetime-us": [
                datetime(year=1996, month=12, day=19, hour=16, minute=39, second=57),
                datetime(year=2022, month=12, day=19, hour=00, minute=39, second=57),
            ],
        }
    ).select(
        pl.col("x1-datetime-ns").dt.cast_time_unit("ns").dt.replace_time_zone(ccs_tz),
        pl.col("x1-datetime-ms").dt.cast_time_unit("ms").dt.replace_time_zone(stg_tz),
        pl.col("x1-datetime-us").dt.cast_time_unit("us").dt.replace_time_zone(utc_tz),
    )

    out = df.select(
        pl.col("x1-datetime-ns"), pl.col("x1-datetime-ms"), pl.col("x1-datetime-us")
    )

    assert_frame_equal(expected, out)


@pytest.mark.parametrize(("dtype"), [pl.Int8, pl.Int16, pl.Int32, pl.Int64])
def test_leading_plus_zero_int(dtype: pl.DataType) -> None:
    s_int = pl.Series(
        [
            "-000000000000002",
            "-1",
            "-0",
            "0",
            "+0",
            "1",
            "+1",
            "0000000000000000000002",
            "+000000000000000000003",
        ]
    )
    assert_series_equal(
        s_int.cast(dtype), pl.Series([-2, -1, 0, 0, 0, 1, 1, 2, 3], dtype=dtype)
    )


@pytest.mark.parametrize(("dtype"), [pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64])
def test_leading_plus_zero_uint(dtype: pl.DataType) -> None:
    s_int = pl.Series(
        ["0", "+0", "1", "+1", "0000000000000000000002", "+000000000000000000003"]
    )
    assert_series_equal(s_int.cast(dtype), pl.Series([0, 0, 1, 1, 2, 3], dtype=dtype))


@pytest.mark.parametrize(("dtype"), [pl.Float32, pl.Float64])
def test_leading_plus_zero_float(dtype: pl.DataType) -> None:
    s_float = pl.Series(
        [
            "-000000000000002.0",
            "-1.0",
            "-.5",
            "-0.0",
            "0.",
            "+0",
            "+.5",
            "1",
            "+1",
            "0000000000000000000002",
            "+000000000000000000003",
        ]
    )
    assert_series_equal(
        s_float.cast(dtype),
        pl.Series(
            [-2.0, -1.0, -0.5, 0.0, 0.0, 0.0, 0.5, 1.0, 1.0, 2.0, 3.0], dtype=dtype
        ),
    )


def _cast_series(
    val: int | datetime | date | time | timedelta,
    dtype_in: PolarsDataType,
    dtype_out: PolarsDataType,
    strict: bool,
) -> int | datetime | date | time | timedelta | None:
    return pl.Series("a", [val], dtype=dtype_in).cast(dtype_out, strict=strict).item()  # type: ignore[no-any-return]


def _cast_expr(
    val: int | datetime | date | time | timedelta,
    dtype_in: PolarsDataType,
    dtype_out: PolarsDataType,
    strict: bool,
) -> int | datetime | date | time | timedelta | None:
    return (  # type: ignore[no-any-return]
        pl.Series("a", [val], dtype=dtype_in)
        .to_frame()
        .select(pl.col("a").cast(dtype_out, strict=strict))
        .item()
    )


def _cast_lit(
    val: int | datetime | date | time | timedelta,
    dtype_in: PolarsDataType,
    dtype_out: PolarsDataType,
    strict: bool,
) -> int | datetime | date | time | timedelta | None:
    return pl.select(pl.lit(val, dtype=dtype_in).cast(dtype_out, strict=strict)).item()  # type: ignore[no-any-return]


@pytest.mark.parametrize(
    ("value", "from_dtype", "to_dtype", "should_succeed", "expected_value"),
    [
        (-1, pl.Int8, pl.UInt8, False, None),
        (-1, pl.Int16, pl.UInt16, False, None),
        (-1, pl.Int32, pl.UInt32, False, None),
        (-1, pl.Int64, pl.UInt64, False, None),
        (2**7, pl.UInt8, pl.Int8, False, None),
        (2**15, pl.UInt16, pl.Int16, False, None),
        (2**31, pl.UInt32, pl.Int32, False, None),
        (2**63, pl.UInt64, pl.Int64, False, None),
        (2**7 - 1, pl.UInt8, pl.Int8, True, 2**7 - 1),
        (2**15 - 1, pl.UInt16, pl.Int16, True, 2**15 - 1),
        (2**31 - 1, pl.UInt32, pl.Int32, True, 2**31 - 1),
        (2**63 - 1, pl.UInt64, pl.Int64, True, 2**63 - 1),
    ],
)
def test_strict_cast_int(
    value: int,
    from_dtype: PolarsDataType,
    to_dtype: PolarsDataType,
    should_succeed: bool,
    expected_value: Any,
) -> None:
    args = [value, from_dtype, to_dtype, True]
    if should_succeed:
        assert _cast_series(*args) == expected_value  # type: ignore[arg-type]
        assert _cast_expr(*args) == expected_value  # type: ignore[arg-type]
        assert _cast_lit(*args) == expected_value  # type: ignore[arg-type]
    else:
        with pytest.raises(InvalidOperationError):
            _cast_series(*args)  # type: ignore[arg-type]
        with pytest.raises(InvalidOperationError):
            _cast_expr(*args)  # type: ignore[arg-type]
        with pytest.raises(InvalidOperationError):
            _cast_lit(*args)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("value", "from_dtype", "to_dtype", "expected_value"),
    [
        (-1, pl.Int8, pl.UInt8, None),
        (-1, pl.Int16, pl.UInt16, None),
        (-1, pl.Int32, pl.UInt32, None),
        (-1, pl.Int64, pl.UInt64, None),
        (2**7, pl.UInt8, pl.Int8, None),
        (2**15, pl.UInt16, pl.Int16, None),
        (2**31, pl.UInt32, pl.Int32, None),
        (2**63, pl.UInt64, pl.Int64, None),
        (2**7 - 1, pl.UInt8, pl.Int8, 2**7 - 1),
        (2**15 - 1, pl.UInt16, pl.Int16, 2**15 - 1),
        (2**31 - 1, pl.UInt32, pl.Int32, 2**31 - 1),
        (2**63 - 1, pl.UInt64, pl.Int64, 2**63 - 1),
    ],
)
def test_cast_int(
    value: int,
    from_dtype: PolarsDataType,
    to_dtype: PolarsDataType,
    expected_value: Any,
) -> None:
    args = [value, from_dtype, to_dtype, False]
    assert _cast_series(*args) == expected_value  # type: ignore[arg-type]
    assert _cast_expr(*args) == expected_value  # type: ignore[arg-type]
    assert _cast_lit(*args) == expected_value  # type: ignore[arg-type]


def _cast_series_t(
    val: int | datetime | date | time | timedelta,
    dtype_in: PolarsDataType,
    dtype_out: PolarsDataType,
    strict: bool,
) -> pl.Series:
    return pl.Series("a", [val], dtype=dtype_in).cast(dtype_out, strict=strict)


def _cast_expr_t(
    val: int | datetime | date | time | timedelta,
    dtype_in: PolarsDataType,
    dtype_out: PolarsDataType,
    strict: bool,
) -> pl.Series:
    return (
        pl.Series("a", [val], dtype=dtype_in)
        .to_frame()
        .select(pl.col("a").cast(dtype_out, strict=strict))
        .to_series()
    )


def _cast_lit_t(
    val: int | datetime | date | time | timedelta,
    dtype_in: PolarsDataType,
    dtype_out: PolarsDataType,
    strict: bool,
) -> pl.Series:
    return pl.select(
        pl.lit(val, dtype=dtype_in).cast(dtype_out, strict=strict)
    ).to_series()


@pytest.mark.parametrize(
    (
        "value",
        "from_dtype",
        "to_dtype",
        "should_succeed",
        "expected_value",
    ),
    [
        # date to datetime
        (date(1970, 1, 1), pl.Date, pl.Datetime("ms"), True, datetime(1970, 1, 1)),
        (date(1970, 1, 1), pl.Date, pl.Datetime("us"), True, datetime(1970, 1, 1)),
        (date(1970, 1, 1), pl.Date, pl.Datetime("ns"), True, datetime(1970, 1, 1)),
        # datetime to date
        (datetime(1970, 1, 1), pl.Datetime("ms"), pl.Date, True, date(1970, 1, 1)),
        (datetime(1970, 1, 1), pl.Datetime("us"), pl.Date, True, date(1970, 1, 1)),
        (datetime(1970, 1, 1), pl.Datetime("ns"), pl.Date, True, date(1970, 1, 1)),
        # datetime to time
        (datetime(2000, 1, 1, 1, 0, 0), pl.Datetime("ms"), pl.Time, True, time(hour=1)),
        (datetime(2000, 1, 1, 1, 0, 0), pl.Datetime("us"), pl.Time, True, time(hour=1)),
        (datetime(2000, 1, 1, 1, 0, 0), pl.Datetime("ns"), pl.Time, True, time(hour=1)),
        # duration to int
        (timedelta(seconds=1), pl.Duration("ms"), pl.Int32, True, MS_PER_SECOND),
        (timedelta(seconds=1), pl.Duration("us"), pl.Int64, True, US_PER_SECOND),
        (timedelta(seconds=1), pl.Duration("ns"), pl.Int64, True, NS_PER_SECOND),
        # time to duration
        (time(hour=1), pl.Time, pl.Duration("ms"), True, timedelta(hours=1)),
        (time(hour=1), pl.Time, pl.Duration("us"), True, timedelta(hours=1)),
        (time(hour=1), pl.Time, pl.Duration("ns"), True, timedelta(hours=1)),
        # int to date
        (100, pl.UInt8, pl.Date, True, date(1970, 4, 11)),
        (100, pl.UInt16, pl.Date, True, date(1970, 4, 11)),
        (100, pl.UInt32, pl.Date, True, date(1970, 4, 11)),
        (100, pl.UInt64, pl.Date, True, date(1970, 4, 11)),
        (100, pl.Int8, pl.Date, True, date(1970, 4, 11)),
        (100, pl.Int16, pl.Date, True, date(1970, 4, 11)),
        (100, pl.Int32, pl.Date, True, date(1970, 4, 11)),
        (100, pl.Int64, pl.Date, True, date(1970, 4, 11)),
        # failures
        (2**63 - 1, pl.Int64, pl.Date, False, None),
        (-(2**62), pl.Int64, pl.Date, False, None),
        (date(1970, 5, 10), pl.Date, pl.Int8, False, None),
        (date(2149, 6, 7), pl.Date, pl.Int16, False, None),
        (datetime(9999, 12, 31), pl.Datetime, pl.Int8, False, None),
        (datetime(9999, 12, 31), pl.Datetime, pl.Int16, False, None),
    ],
)
def test_strict_cast_temporal(
    value: int,
    from_dtype: PolarsDataType,
    to_dtype: PolarsDataType,
    should_succeed: bool,
    expected_value: Any,
) -> None:
    args = [value, from_dtype, to_dtype, True]
    if should_succeed:
        out = _cast_series_t(*args)  # type: ignore[arg-type]
        assert out.item() == expected_value
        assert out.dtype == to_dtype
        out = _cast_expr_t(*args)  # type: ignore[arg-type]
        assert out.item() == expected_value
        assert out.dtype == to_dtype
        out = _cast_lit_t(*args)  # type: ignore[arg-type]
        assert out.item() == expected_value
        assert out.dtype == to_dtype
    else:
        with pytest.raises(InvalidOperationError):
            _cast_series_t(*args)  # type: ignore[arg-type]
        with pytest.raises(InvalidOperationError):
            _cast_expr_t(*args)  # type: ignore[arg-type]
        with pytest.raises(InvalidOperationError):
            _cast_lit_t(*args)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    (
        "value",
        "from_dtype",
        "to_dtype",
        "expected_value",
    ),
    [
        # date to datetime
        (date(1970, 1, 1), pl.Date, pl.Datetime("ms"), datetime(1970, 1, 1)),
        (date(1970, 1, 1), pl.Date, pl.Datetime("us"), datetime(1970, 1, 1)),
        (date(1970, 1, 1), pl.Date, pl.Datetime("ns"), datetime(1970, 1, 1)),
        # datetime to date
        (datetime(1970, 1, 1), pl.Datetime("ms"), pl.Date, date(1970, 1, 1)),
        (datetime(1970, 1, 1), pl.Datetime("us"), pl.Date, date(1970, 1, 1)),
        (datetime(1970, 1, 1), pl.Datetime("ns"), pl.Date, date(1970, 1, 1)),
        # datetime to time
        (datetime(2000, 1, 1, 1, 0, 0), pl.Datetime("ms"), pl.Time, time(hour=1)),
        (datetime(2000, 1, 1, 1, 0, 0), pl.Datetime("us"), pl.Time, time(hour=1)),
        (datetime(2000, 1, 1, 1, 0, 0), pl.Datetime("ns"), pl.Time, time(hour=1)),
        # duration to int
        (timedelta(seconds=1), pl.Duration("ms"), pl.Int32, MS_PER_SECOND),
        (timedelta(seconds=1), pl.Duration("us"), pl.Int64, US_PER_SECOND),
        (timedelta(seconds=1), pl.Duration("ns"), pl.Int64, NS_PER_SECOND),
        # time to duration
        (time(hour=1), pl.Time, pl.Duration("ms"), timedelta(hours=1)),
        (time(hour=1), pl.Time, pl.Duration("us"), timedelta(hours=1)),
        (time(hour=1), pl.Time, pl.Duration("ns"), timedelta(hours=1)),
        # int to date
        (100, pl.UInt8, pl.Date, date(1970, 4, 11)),
        (100, pl.UInt16, pl.Date, date(1970, 4, 11)),
        (100, pl.UInt32, pl.Date, date(1970, 4, 11)),
        (100, pl.UInt64, pl.Date, date(1970, 4, 11)),
        (100, pl.Int8, pl.Date, date(1970, 4, 11)),
        (100, pl.Int16, pl.Date, date(1970, 4, 11)),
        (100, pl.Int32, pl.Date, date(1970, 4, 11)),
        (100, pl.Int64, pl.Date, date(1970, 4, 11)),
        # failures
        (2**63 - 1, pl.Int64, pl.Date, None),
        (-(2**62), pl.Int64, pl.Date, None),
        (date(1970, 5, 10), pl.Date, pl.Int8, None),
        (date(2149, 6, 7), pl.Date, pl.Int16, None),
        (datetime(9999, 12, 31), pl.Datetime, pl.Int8, None),
        (datetime(9999, 12, 31), pl.Datetime, pl.Int16, None),
    ],
)
def test_cast_temporal(
    value: int,
    from_dtype: PolarsDataType,
    to_dtype: PolarsDataType,
    expected_value: Any,
) -> None:
    args = [value, from_dtype, to_dtype, False]
    out = _cast_series_t(*args)  # type: ignore[arg-type]
    if expected_value is None:
        assert out.item() is None
    else:
        assert out.item() == expected_value
        assert out.dtype == to_dtype

    out = _cast_expr_t(*args)  # type: ignore[arg-type]
    if expected_value is None:
        assert out.item() is None
    else:
        assert out.item() == expected_value
        assert out.dtype == to_dtype

    out = _cast_lit_t(*args)  # type: ignore[arg-type]
    if expected_value is None:
        assert out.item() is None
    else:
        assert out.item() == expected_value
        assert out.dtype == to_dtype


@pytest.mark.parametrize(
    (
        "value",
        "from_dtype",
        "to_dtype",
        "expected_value",
    ),
    [
        (str(2**7 - 1), pl.String, pl.Int8, 2**7 - 1),
        (str(2**15 - 1), pl.String, pl.Int16, 2**15 - 1),
        (str(2**31 - 1), pl.String, pl.Int32, 2**31 - 1),
        (str(2**63 - 1), pl.String, pl.Int64, 2**63 - 1),
        ("1.0", pl.String, pl.Float32, 1.0),
        ("1.0", pl.String, pl.Float64, 1.0),
        # overflow
        (str(2**7), pl.String, pl.Int8, None),
        (str(2**15), pl.String, pl.Int16, None),
        (str(2**31), pl.String, pl.Int32, None),
        (str(2**63), pl.String, pl.Int64, None),
    ],
)
def test_cast_string(
    value: int,
    from_dtype: PolarsDataType,
    to_dtype: PolarsDataType,
    expected_value: Any,
) -> None:
    args = [value, from_dtype, to_dtype, False]
    out = _cast_series_t(*args)  # type: ignore[arg-type]
    if expected_value is None:
        assert out.item() is None
    else:
        assert out.item() == expected_value
        assert out.dtype == to_dtype

    out = _cast_expr_t(*args)  # type: ignore[arg-type]
    if expected_value is None:
        assert out.item() is None
    else:
        assert out.item() == expected_value
        assert out.dtype == to_dtype

    out = _cast_lit_t(*args)  # type: ignore[arg-type]
    if expected_value is None:
        assert out.item() is None
    else:
        assert out.item() == expected_value
        assert out.dtype == to_dtype


@pytest.mark.parametrize(
    (
        "value",
        "from_dtype",
        "to_dtype",
        "should_succeed",
        "expected_value",
    ),
    [
        (str(2**7 - 1), pl.String, pl.Int8, True, 2**7 - 1),
        (str(2**15 - 1), pl.String, pl.Int16, True, 2**15 - 1),
        (str(2**31 - 1), pl.String, pl.Int32, True, 2**31 - 1),
        (str(2**63 - 1), pl.String, pl.Int64, True, 2**63 - 1),
        ("1.0", pl.String, pl.Float32, True, 1.0),
        ("1.0", pl.String, pl.Float64, True, 1.0),
        # overflow
        (str(2**7), pl.String, pl.Int8, False, None),
        (str(2**15), pl.String, pl.Int16, False, None),
        (str(2**31), pl.String, pl.Int32, False, None),
        (str(2**63), pl.String, pl.Int64, False, None),
    ],
)
def test_strict_cast_string(
    value: int,
    from_dtype: PolarsDataType,
    to_dtype: PolarsDataType,
    should_succeed: bool,
    expected_value: Any,
) -> None:
    args = [value, from_dtype, to_dtype, True]
    if should_succeed:
        out = _cast_series_t(*args)  # type: ignore[arg-type]
        assert out.item() == expected_value
        assert out.dtype == to_dtype
        out = _cast_expr_t(*args)  # type: ignore[arg-type]
        assert out.item() == expected_value
        assert out.dtype == to_dtype
        out = _cast_lit_t(*args)  # type: ignore[arg-type]
        assert out.item() == expected_value
        assert out.dtype == to_dtype
    else:
        with pytest.raises(InvalidOperationError):
            _cast_series_t(*args)  # type: ignore[arg-type]
        with pytest.raises(InvalidOperationError):
            _cast_expr_t(*args)  # type: ignore[arg-type]
        with pytest.raises(InvalidOperationError):
            _cast_lit_t(*args)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "dtype_in",
    [(pl.Categorical), (pl.Enum(["1"]))],
)
@pytest.mark.parametrize(
    "dtype_out",
    [
        pl.String,
        pl.Categorical,
        pl.Enum(["1", "2"]),
    ],
)
def test_cast_categorical_name_retention(
    dtype_in: PolarsDataType, dtype_out: PolarsDataType
) -> None:
    assert pl.Series("a", ["1"], dtype=dtype_in).cast(dtype_out).name == "a"


def test_cast_date_to_time() -> None:
    s = pl.Series([date(1970, 1, 1), date(2000, 12, 31)])
    msg = "casting from Date to Time not supported"
    with pytest.raises(InvalidOperationError, match=msg):
        s.cast(pl.Time)


def test_cast_time_to_date() -> None:
    s = pl.Series([time(0, 0), time(20, 00)])
    msg = "casting from Time to Date not supported"
    with pytest.raises(InvalidOperationError, match=msg):
        s.cast(pl.Date)


def test_cast_decimal_to_boolean() -> None:
    s = pl.Series("s", [Decimal("0.0"), Decimal("1.5"), Decimal("-1.5")])
    assert_series_equal(s.cast(pl.Boolean), pl.Series("s", [False, True, True]))

    df = s.to_frame()
    assert_frame_equal(
        df.select(pl.col("s").cast(pl.Boolean)),
        pl.DataFrame({"s": [False, True, True]}),
    )


def test_cast_array_to_different_width() -> None:
    s = pl.Series([[1, 2], [3, 4]], dtype=pl.Array(pl.Int8, 2))
    with pytest.raises(
        InvalidOperationError, match="cannot cast Array to a different width"
    ):
        s.cast(pl.Array(pl.Int16, 3))


def test_cast_decimal_to_decimal_high_precision() -> None:
    precision = 22
    values = [Decimal("9" * precision)]
    s = pl.Series(values, dtype=pl.Decimal(None, 0))

    target_dtype = pl.Decimal(precision, 0)
    result = s.cast(target_dtype)

    assert result.dtype == target_dtype
    assert result.to_list() == values


@pytest.mark.parametrize("value", [float("inf"), float("nan")])
def test_invalid_cast_float_to_decimal(value: float) -> None:
    s = pl.Series([value], dtype=pl.Float64)
    with pytest.raises(
        InvalidOperationError,
        match=r"conversion from `f64` to `decimal\[\*,0\]` failed",
    ):
        s.cast(pl.Decimal)


def test_err_on_time_datetime_cast() -> None:
    s = pl.Series([time(10, 0, 0), time(11, 30, 59)])
    with pytest.raises(
        InvalidOperationError,
        match="casting from Time to Datetime\\(Microseconds, None\\) not supported; consider using `dt.combine`",
    ):
        s.cast(pl.Datetime)


def test_err_on_invalid_time_zone_cast() -> None:
    s = pl.Series([datetime(2021, 1, 1)])
    with pytest.raises(ComputeError, match=r"unable to parse time zone: 'qwerty'"):
        s.cast(pl.Datetime("us", "qwerty"))


def test_invalid_inner_type_cast_list() -> None:
    s = pl.Series([[-1, 1]])
    with pytest.raises(
        InvalidOperationError,
        match=r"cannot cast List inner type: 'Int64' to Categorical",
    ):
        s.cast(pl.List(pl.Categorical))


@pytest.mark.parametrize(
    ("values", "result"),
    [
        ([[]], [b""]),
        ([[1, 2], [3, 4]], [b"\x01\x02", b"\x03\x04"]),
        ([[1, 2], None, [3, 4]], [b"\x01\x02", None, b"\x03\x04"]),
        (
            [None, [111, 110, 101], [12, None], [116, 119, 111], list(range(256))],
            [
                None,
                b"one",
                # A list with a null in it gets turned into a null:
                None,
                b"two",
                bytes(i for i in range(256)),
            ],
        ),
    ],
)
def test_list_uint8_to_bytes(
    values: list[list[int | None] | None], result: list[bytes | None]
) -> None:
    s = pl.Series(
        values,
        dtype=pl.List(pl.UInt8()),
    )
    assert s.cast(pl.Binary(), strict=False).to_list() == result


def test_list_uint8_to_bytes_strict() -> None:
    series = pl.Series(
        [[1, 2], [3, 4]],
        dtype=pl.List(pl.UInt8()),
    )
    assert series.cast(pl.Binary(), strict=True).to_list() == [b"\x01\x02", b"\x03\x04"]

    series = pl.Series(
        "mycol",
        [[1, 2], [3, None]],
        dtype=pl.List(pl.UInt8()),
    )
    with pytest.raises(
        InvalidOperationError,
        match="conversion from `list\\[u8\\]` to `binary` failed in column 'mycol' for 1 out of 2 values: \\[\\[3, null\\]\\]",
    ):
        series.cast(pl.Binary(), strict=True)


def test_all_null_cast_5826() -> None:
    df = pl.DataFrame(data=[pl.Series("a", [None], dtype=pl.String)])
    out = df.with_columns(pl.col("a").cast(pl.Boolean))
    assert out.dtypes == [pl.Boolean]
    assert out.item() is None


@pytest.mark.parametrize("dtype", INTEGER_DTYPES)
def test_bool_numeric_supertype(dtype: PolarsDataType) -> None:
    df = pl.DataFrame({"v": [1, 2, 3, 4, 5, 6]})
    result = df.select((pl.col("v") < 3).sum().cast(dtype) / pl.len())
    assert result.item() - 0.3333333 <= 0.00001


@pytest.mark.parametrize("dtype", [pl.String(), pl.String, str])
def test_cast_consistency(dtype: PolarsDataType | PythonDataType) -> None:
    assert pl.DataFrame().with_columns(a=pl.lit(0.0)).with_columns(
        b=pl.col("a").cast(dtype), c=pl.lit(0.0).cast(dtype)
    ).to_dict(as_series=False) == {"a": [0.0], "b": ["0.0"], "c": ["0.0"]}


def test_cast_int_to_string_unsets_sorted_flag_19424() -> None:
    s = pl.Series([1, 2]).set_sorted()
    assert s.flags["SORTED_ASC"]
    assert not s.cast(pl.String).flags["SORTED_ASC"]


def test_cast_integer_to_decimal() -> None:
    s = pl.Series([1, 2, 3])
    result = s.cast(pl.Decimal(10, 2))
    expected = pl.Series(
        "", [Decimal("1.00"), Decimal("2.00"), Decimal("3.00")], pl.Decimal(10, 2)
    )
    assert_series_equal(result, expected)


def test_cast_python_dtypes() -> None:
    s = pl.Series([0, 1])
    assert s.cast(int).dtype == pl.Int64
    assert s.cast(float).dtype == pl.Float64
    assert s.cast(bool).dtype == pl.Boolean
    assert s.cast(str).dtype == pl.String


def test_overflowing_cast_literals_21023() -> None:
    for optimizations in [pl.QueryOptFlags(), pl.QueryOptFlags.none()]:
        assert_frame_equal(
            (
                pl.LazyFrame()
                .select(
                    pl.lit(pl.Series([128], dtype=pl.Int64)).cast(
                        pl.Int8, wrap_numerical=True
                    )
                )
                .collect(optimizations=optimizations)
            ),
            pl.Series([-128], dtype=pl.Int8).to_frame(),
        )


@pytest.mark.parametrize("value", [True, False])
@pytest.mark.parametrize(
    "dtype",
    [
        pl.Enum(["a", "b"]),
        pl.Series(["a", "b"], dtype=pl.Categorical).dtype,
    ],
)
def test_invalid_bool_to_cat(value: bool, dtype: PolarsDataType) -> None:
    # Enum
    with pytest.raises(
        InvalidOperationError,
        match="cannot cast Boolean to Categorical",
    ):
        pl.Series([value]).cast(dtype)


@pytest.mark.parametrize(
    ("values", "from_dtype", "to_dtype", "pre_apply"),
    [
        ([["A"]], pl.List(pl.String), pl.List(pl.Int8), None),
        ([["A"]], pl.Array(pl.String, 1), pl.List(pl.Int8), None),
        ([[["A"]]], pl.List(pl.List(pl.String)), pl.List(pl.List(pl.Int8)), None),
        (
            [
                {"x": "1", "y": "2"},
                {"x": "A", "y": "B"},
                {"x": "3", "y": "4"},
                {"x": "X", "y": "Y"},
                {"x": "5", "y": "6"},
            ],
            pl.Struct(
                {
                    "x": pl.String,
                    "y": pl.String,
                }
            ),
            pl.Struct(
                {
                    "x": pl.Int8,
                    "y": pl.Int32,
                }
            ),
            None,
        ),
    ],
)
def test_nested_strict_casts_failing(
    values: list[Any],
    from_dtype: pl.DataType,
    to_dtype: pl.DataType,
    pre_apply: Callable[[pl.Series], pl.Series] | None,
) -> None:
    s = pl.Series(values, dtype=from_dtype)

    if pre_apply is not None:
        s = pre_apply(s)

    with pytest.raises(
        pl.exceptions.InvalidOperationError,
        match=r"conversion from",
    ):
        s.cast(to_dtype)


@pytest.mark.parametrize(
    ("values", "from_dtype", "pre_apply", "to"),
    [
        (
            [["A"], ["1"], ["2"]],
            pl.List(pl.String),
            lambda s: s.slice(1, 2),
            pl.Series([[1], [2]]),
        ),
        (
            [["1"], ["A"], ["2"], ["B"], ["3"]],
            pl.List(pl.String),
            lambda s: s.filter(pl.Series([True, False, True, False, True])),
            pl.Series([[1], [2], [3]]),
        ),
        (
            [
                {"x": "1", "y": "2"},
                {"x": "A", "y": "B"},
                {"x": "3", "y": "4"},
                {"x": "X", "y": "Y"},
                {"x": "5", "y": "6"},
            ],
            pl.Struct(
                {
                    "x": pl.String,
                    "y": pl.String,
                }
            ),
            lambda s: s.filter(pl.Series([True, False, True, False, True])),
            pl.Series(
                [
                    {"x": 1, "y": 2},
                    {"x": 3, "y": 4},
                    {"x": 5, "y": 6},
                ]
            ),
        ),
        (
            [
                {"x": "1", "y": "2"},
                {"x": "A", "y": "B"},
                {"x": "3", "y": "4"},
                {"x": "X", "y": "Y"},
                {"x": "5", "y": "6"},
            ],
            pl.Struct(
                {
                    "x": pl.String,
                    "y": pl.String,
                }
            ),
            lambda s: pl.select(
                pl.when(pl.Series([True, False, True, False, True])).then(s)
            ).to_series(),
            pl.Series(
                [
                    {"x": 1, "y": 2},
                    None,
                    {"x": 3, "y": 4},
                    None,
                    {"x": 5, "y": 6},
                ]
            ),
        ),
    ],
)
def test_nested_strict_casts_succeeds(
    values: list[Any],
    from_dtype: pl.DataType,
    pre_apply: Callable[[pl.Series], pl.Series] | None,
    to: pl.Series,
) -> None:
    s = pl.Series(values, dtype=from_dtype)

    if pre_apply is not None:
        s = pre_apply(s)

    assert_series_equal(
        s.cast(to.dtype),
        to,
    )


def test_nested_struct_cast_22744() -> None:
    s = pl.Series(
        "x",
        [{"attrs": {"class": "a"}}],
    )

    expected = pl.select(
        pl.lit(s).struct.with_fields(
            pl.field("attrs").struct.with_fields(
                [pl.field("class"), pl.lit(None, dtype=pl.String()).alias("other")]
            )
        )
    )

    assert_series_equal(
        s.cast(
            pl.Struct({"attrs": pl.Struct({"class": pl.String, "other": pl.String})})
        ),
        expected.to_series(),
    )
    assert_frame_equal(
        pl.DataFrame([s]).cast(
            {
                "x": pl.Struct(
                    {"attrs": pl.Struct({"class": pl.String, "other": pl.String})}
                )
            }
        ),
        expected,
    )


def test_cast_to_self_is_pruned() -> None:
    q = pl.LazyFrame({"x": 1}, schema={"x": pl.Int64}).with_columns(
        y=pl.col("x").cast(pl.Int64)
    )

    plan = q.explain()
    assert 'col("x").alias("y")' in plan

    assert_frame_equal(q.collect(), pl.DataFrame({"x": 1, "y": 1}))


@pytest.mark.parametrize(
    ("s", "to", "should_fail"),
    [
        (
            pl.Series([datetime(2025, 1, 1)]),
            pl.Datetime("ns"),
            False,
        ),
        (
            pl.Series([datetime(9999, 1, 1)]),
            pl.Datetime("ns"),
            True,
        ),
        (
            pl.Series([datetime(2025, 1, 1), datetime(9999, 1, 1)]),
            pl.Datetime("ns"),
            True,
        ),
        (
            pl.Series([[datetime(2025, 1, 1)], [datetime(9999, 1, 1)]]),
            pl.List(pl.Datetime("ns")),
            True,
        ),
        # lower date limit for nanosecond
        (pl.Series([date(1677, 9, 22)]), pl.Datetime("ns"), False),
        (pl.Series([date(1677, 9, 21)]), pl.Datetime("ns"), True),
        # upper date limit for nanosecond
        (pl.Series([date(2262, 4, 11)]), pl.Datetime("ns"), False),
        (pl.Series([date(2262, 4, 12)]), pl.Datetime("ns"), True),
    ],
)
def test_cast_temporals_overflow_16039(
    s: pl.Series, to: pl.DataType, should_fail: bool
) -> None:
    if should_fail:
        with pytest.raises(
            pl.exceptions.InvalidOperationError, match="conversion from"
        ):
            s.cast(to)
    else:
        s.cast(to)


@pytest.mark.parametrize("dtype", NUMERIC_DTYPES)
def test_prune_superfluous_cast(dtype: PolarsDataType) -> None:
    lf = pl.LazyFrame({"a": [1, 2, 3]}, schema={"a": dtype})
    result = lf.select(pl.col("a").cast(dtype))
    assert "strict_cast" not in result.explain()


def test_not_prune_necessary_cast() -> None:
    lf = pl.LazyFrame({"a": [1, 2, 3]}, schema={"a": pl.UInt16})
    result = lf.select(pl.col("a").cast(pl.UInt8))
    assert "strict_cast" in result.explain()
