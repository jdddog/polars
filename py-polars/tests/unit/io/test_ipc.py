from __future__ import annotations

import io
from decimal import Decimal
from typing import TYPE_CHECKING, Any, no_type_check

import pandas as pd
import pytest

import polars as pl
from polars.interchange.protocol import CompatLevel
from polars.testing import assert_frame_equal, assert_series_equal

if TYPE_CHECKING:
    from pathlib import Path

    from polars._typing import IpcCompression
    from tests.unit.conftest import MemoryUsage

COMPRESSIONS = ["uncompressed", "lz4", "zstd"]


def read_ipc(is_stream: bool, *args: Any, **kwargs: Any) -> pl.DataFrame:
    if is_stream:
        return pl.read_ipc_stream(*args, **kwargs)
    else:
        return pl.read_ipc(*args, **kwargs)


def write_ipc(df: pl.DataFrame, is_stream: bool, *args: Any, **kwargs: Any) -> Any:
    if is_stream:
        return df.write_ipc_stream(*args, **kwargs)
    else:
        return df.write_ipc(*args, **kwargs)


@pytest.mark.parametrize("compression", COMPRESSIONS)
@pytest.mark.parametrize("stream", [True, False])
def test_from_to_buffer(
    df: pl.DataFrame, compression: IpcCompression, stream: bool
) -> None:
    # use an ad-hoc buffer (file=None)
    buf1 = write_ipc(df, stream, None, compression=compression)
    buf1.seek(0)
    read_df = read_ipc(stream, buf1, use_pyarrow=False)
    assert_frame_equal(df, read_df, categorical_as_str=True)

    # explicitly supply an existing buffer
    buf2 = io.BytesIO()
    buf2.seek(0)
    write_ipc(df, stream, buf2, compression=compression)
    buf2.seek(0)
    read_df = read_ipc(stream, buf2, use_pyarrow=False)
    assert_frame_equal(df, read_df, categorical_as_str=True)


@pytest.mark.parametrize("compression", COMPRESSIONS)
@pytest.mark.parametrize("path_as_string", [True, False])
@pytest.mark.parametrize("stream", [True, False])
@pytest.mark.write_disk
def test_from_to_file(
    df: pl.DataFrame,
    compression: IpcCompression,
    path_as_string: bool,
    tmp_path: Path,
    stream: bool,
) -> None:
    tmp_path.mkdir(exist_ok=True)
    file_path = tmp_path / "small.ipc"
    if path_as_string:
        file_path = str(file_path)  # type: ignore[assignment]
    write_ipc(df, stream, file_path, compression=compression)
    df_read = read_ipc(stream, file_path, use_pyarrow=False)

    assert_frame_equal(df, df_read, categorical_as_str=True)


@pytest.mark.parametrize("stream", [True, False])
@pytest.mark.write_disk
def test_select_columns_from_file(
    df: pl.DataFrame, tmp_path: Path, stream: bool
) -> None:
    tmp_path.mkdir(exist_ok=True)
    file_path = tmp_path / "small.ipc"
    write_ipc(df, stream, file_path)
    df_read = read_ipc(stream, file_path, columns=["bools"])

    assert df_read.columns == ["bools"]


@pytest.mark.parametrize("stream", [True, False])
def test_select_columns_from_buffer(stream: bool) -> None:
    df = pl.DataFrame(
        {
            "a": [1],
            "b": [2],
            "c": [3],
        },
        schema={"a": pl.Int64(), "b": pl.Int128(), "c": pl.UInt8()},
    )

    f = io.BytesIO()
    write_ipc(df, stream, f)
    f.seek(0)

    actual = read_ipc(stream, f, columns=["b", "c", "a"], use_pyarrow=False)

    expected = pl.DataFrame(
        {
            "b": [2],
            "c": [3],
            "a": [1],
        },
        schema={"b": pl.Int128(), "c": pl.UInt8(), "a": pl.Int64()},
    )
    assert_frame_equal(expected, actual)


@pytest.mark.parametrize("stream", [True, False])
def test_select_columns_projection(stream: bool) -> None:
    df = pl.DataFrame({"a": [1, 2, 3], "b": [True, False, True], "c": ["a", "b", "c"]})
    expected = pl.DataFrame({"b": [True, False, True], "c": ["a", "b", "c"]})

    f = io.BytesIO()
    write_ipc(df, stream, f)
    f.seek(0)

    read_df = read_ipc(stream, f, columns=[1, 2], use_pyarrow=False)
    assert_frame_equal(expected, read_df)


@pytest.mark.parametrize("compression", COMPRESSIONS)
@pytest.mark.parametrize("stream", [True, False])
def test_compressed_simple(compression: IpcCompression, stream: bool) -> None:
    df = pl.DataFrame({"a": [1, 2, 3], "b": [True, False, True], "c": ["a", "b", "c"]})

    f = io.BytesIO()
    write_ipc(df, stream, f, compression=compression)
    f.seek(0)

    df_read = read_ipc(stream, f, use_pyarrow=False)
    assert_frame_equal(df_read, df)


@pytest.mark.parametrize("compression", COMPRESSIONS)
def test_ipc_schema(compression: IpcCompression) -> None:
    schema = {
        "i64": pl.Int64(),
        "i128": pl.Int128(),
        "u8": pl.UInt8(),
        "f32": pl.Float32(),
        "f64": pl.Float64(),
        "str": pl.String(),
        "bool": pl.Boolean(),
    }
    df = pl.DataFrame(
        {
            "i64": [1, 2],
            "i128": [1, 2],
            "u8": [1, 2],
            "f32": [1, 2],
            "f64": [1, 2],
            "str": ["a", None],
            "bool": [True, False],
        },
        schema=schema,
    )

    f = io.BytesIO()
    df.write_ipc(f, compression=compression)
    f.seek(0)

    assert pl.read_ipc_schema(f) == schema


@pytest.mark.write_disk
@pytest.mark.parametrize("compression", COMPRESSIONS)
@pytest.mark.parametrize("path_as_string", [True, False])
def test_ipc_schema_from_file(
    df_no_lists: pl.DataFrame,
    compression: IpcCompression,
    path_as_string: bool,
    tmp_path: Path,
) -> None:
    tmp_path.mkdir(exist_ok=True)

    file_path = tmp_path / "small.ipc"
    if path_as_string:
        file_path = str(file_path)  # type: ignore[assignment]
    df_no_lists.write_ipc(file_path, compression=compression)
    schema = pl.read_ipc_schema(file_path)

    expected = {
        "bools": pl.Boolean(),
        "bools_nulls": pl.Boolean(),
        "int": pl.Int64(),
        "int_nulls": pl.Int64(),
        "floats": pl.Float64(),
        "floats_nulls": pl.Float64(),
        "strings": pl.String(),
        "strings_nulls": pl.String(),
        "date": pl.Date(),
        "datetime": pl.Datetime(),
        "time": pl.Time(),
        "cat": pl.Categorical(),
        "enum": pl.Enum(["foo", "ham", "bar"]),
    }
    assert schema == expected


@pytest.mark.parametrize("stream", [True, False])
def test_ipc_column_order(stream: bool) -> None:
    df = pl.DataFrame(
        {
            "cola": ["x", "y", "z"],
            "colb": [1, 2, 3],
            "colc": [4.5, 5.6, 6.7],
        }
    )
    f = io.BytesIO()
    write_ipc(df, stream, f)
    f.seek(0)

    columns = ["colc", "colb", "cola"]
    # read file into polars; the specified column order is no longer respected
    assert read_ipc(stream, f, columns=columns).columns == columns


@pytest.mark.write_disk
def test_glob_ipc(df: pl.DataFrame, tmp_path: Path) -> None:
    file_path = tmp_path / "small.ipc"
    df.write_ipc(file_path)

    file_path_glob = tmp_path / "small*.ipc"

    result_scan = pl.scan_ipc(file_path_glob).collect()
    result_read = pl.read_ipc(file_path_glob, use_pyarrow=False)

    for result in [result_scan, result_read]:
        assert_frame_equal(result, df, categorical_as_str=True)


def test_from_float16() -> None:
    # Create a feather file with a 16-bit floating point column
    pandas_df = pd.DataFrame({"column": [1.0]}, dtype="float16")
    f = io.BytesIO()
    pandas_df.to_feather(f)
    f.seek(0)
    assert pl.read_ipc(f, use_pyarrow=False).dtypes == [pl.Float32]


@pytest.mark.write_disk
def test_binview_ipc_mmap(tmp_path: Path) -> None:
    df = pl.DataFrame({"foo": ["aa" * 10, "bb", None, "small", "big" * 20]})
    file_path = tmp_path / "dump.ipc"
    df.write_ipc(file_path, compat_level=CompatLevel.newest())
    read = pl.read_ipc(file_path, memory_map=True)
    assert_frame_equal(df, read)


def test_list_nested_enum() -> None:
    dtype = pl.List(pl.Enum(["a", "b", "c"]))
    df = pl.DataFrame(pl.Series("list_cat", [["a", "b", "c", None]], dtype=dtype))
    buffer = io.BytesIO()
    df.write_ipc(buffer, compat_level=CompatLevel.newest())
    buffer.seek(0)
    df = pl.read_ipc(buffer)
    assert df.get_column("list_cat").dtype == dtype


def test_struct_nested_enum() -> None:
    dtype = pl.Struct({"enum": pl.Enum(["a", "b", "c"])})
    df = pl.DataFrame(
        pl.Series(
            "struct_cat", [{"enum": "a"}, {"enum": "b"}, {"enum": None}], dtype=dtype
        )
    )
    buffer = io.BytesIO()
    df.write_ipc(buffer, compat_level=CompatLevel.newest())
    buffer.seek(0)
    df = pl.read_ipc(buffer)
    assert df.get_column("struct_cat").dtype == dtype


@pytest.mark.slow
def test_ipc_view_gc_14448() -> None:
    f = io.BytesIO()
    # This size was required to trigger the bug
    df = pl.DataFrame(
        pl.Series(["small"] * 10 + ["looooooong string......."] * 750).slice(20, 20)
    )
    df.write_ipc(f, compat_level=CompatLevel.newest())
    f.seek(0)
    assert_frame_equal(pl.read_ipc(f), df)


@pytest.mark.slow
@pytest.mark.write_disk
@pytest.mark.parametrize("stream", [True, False])
def test_read_ipc_only_loads_selected_columns(
    memory_usage_without_pyarrow: MemoryUsage,
    tmp_path: Path,
    stream: bool,
) -> None:
    """Only requested columns are loaded by ``read_ipc()``/``read_ipc_stream()``."""
    tmp_path.mkdir(exist_ok=True)

    # Each column will be about 16MB of RAM. There's a fixed overhead tied to
    # block size so smaller file sizes can be misleading in terms of memory
    # usage.
    series = pl.arange(0, 2_000_000, dtype=pl.Int64, eager=True)

    file_path = tmp_path / "multicolumn.ipc"
    df = pl.DataFrame(
        {
            "a": series,
            "b": series,
        }
    )
    write_ipc(df, stream, file_path)
    del df, series

    memory_usage_without_pyarrow.reset_tracking()

    # Only load one column:
    kwargs = {}
    if not stream:
        kwargs["memory_map"] = False
    df = read_ipc(stream, str(file_path), columns=["b"], rechunk=False, **kwargs)
    del df
    # Only one column's worth of memory should be used; 2 columns would be
    # 32_000_000 at least, but there's some overhead.
    # assert 16_000_000 < memory_usage_without_pyarrow.get_peak() < 23_000_000


@pytest.mark.write_disk
def test_ipc_decimal_15920(
    tmp_path: Path,
) -> None:
    tmp_path.mkdir(exist_ok=True)

    base_df = pl.Series(
        "x",
        [
            *[
                Decimal(x)
                for x in [
                    "10.1", "11.2", "12.3", "13.4", "14.5", "15.6", "16.7", "17.8", "18.9", "19.0",
                    "20.1", "21.2", "22.3", "23.4", "24.5", "25.6", "26.7", "27.8", "28.9", "29.0",
                    "30.1", "31.2", "32.3", "33.4", "34.5", "35.6", "36.7", "37.8", "38.9", "39.0"
                ]
            ],
            *(50 * [None])
        ],
        dtype=pl.Decimal(18, 2),
    ).to_frame()  # fmt: skip

    for df in [base_df, base_df.drop_nulls()]:
        path = f"{tmp_path}/data"
        df.write_ipc(path)
        assert_frame_equal(pl.read_ipc(path), df)


def test_ipc_variadic_buffers_categorical_binview_18636() -> None:
    df = pl.DataFrame(
        {
            "Test": pl.Series(["Value012"], dtype=pl.Categorical),
            "Test2": pl.Series(["Value Two 20032"], dtype=pl.String),
        }
    )

    b = io.BytesIO()
    df.write_ipc(b)
    b.seek(0)
    assert_frame_equal(pl.read_ipc(b), df)


@pytest.mark.parametrize("size", [0, 1, 2, 13])
def test_ipc_chunked_roundtrip(size: int) -> None:
    a = pl.Series("a", [{"x": 1}] * size, pl.Struct({"x": pl.Int8})).to_frame()

    c = pl.concat([a] * 2, how="vertical")

    f = io.BytesIO()
    c.write_ipc(f)

    f.seek(0)
    assert_frame_equal(c, pl.read_ipc(f))


@pytest.mark.parametrize("size", [0, 1, 2, 13])
def test_zfs_ipc_roundtrip(size: int) -> None:
    a = pl.Series("a", [{}] * size, pl.Struct([])).to_frame()

    f = io.BytesIO()
    a.write_ipc(f)

    f.seek(0)
    assert_frame_equal(a, pl.read_ipc(f))


@pytest.mark.parametrize("size", [0, 1, 2, 13])
def test_zfs_ipc_chunked_roundtrip(size: int) -> None:
    a = pl.Series("a", [{}] * size, pl.Struct([])).to_frame()

    c = pl.concat([a] * 2, how="vertical")

    f = io.BytesIO()
    c.write_ipc(f)

    f.seek(0)
    assert_frame_equal(c, pl.read_ipc(f))


@pytest.mark.parametrize("size", [0, 1, 2, 13])
@pytest.mark.parametrize("value", [{}, {"x": 1}])
@pytest.mark.write_disk
def test_memmap_ipc_chunked_structs(
    size: int, value: dict[str, int], tmp_path: Path
) -> None:
    a = pl.Series("a", [value] * size, pl.Struct).to_frame()

    c = pl.concat([a] * 2, how="vertical")

    f = tmp_path / "f.ipc"
    c.write_ipc(f)
    assert_frame_equal(c, pl.read_ipc(f))


def test_categorical_lexical_sort_2732() -> None:
    df = pl.DataFrame(
        {
            "a": ["foo", "bar", "baz"],
            "b": [1, 3, 2],
        },
        schema_overrides={"a": pl.Categorical("lexical")},
    )
    f = io.BytesIO()
    df.write_ipc(f)
    f.seek(0)
    assert_frame_equal(df, pl.read_ipc(f))


def test_enum_scan_21564() -> None:
    s = pl.Series("a", ["A"], pl.Enum(["A"]))

    # DataFrame with a an enum field
    f = io.BytesIO()
    s.to_frame().write_ipc(f)

    f.seek(0)
    assert_series_equal(
        pl.scan_ipc(f).collect().to_series(),
        s,
    )


@no_type_check
def test_roundtrip_empty_str_list_21163() -> None:
    schema = {
        "s": pl.Utf8,
        "list": pl.List(pl.Utf8),
    }
    row1 = pl.DataFrame({"s": ["A"], "list": [[]]}, schema=schema)
    row2 = pl.DataFrame({"s": ["B"], "list": [[]]}, schema=schema)
    df = pl.concat([row1, row2])
    bytes = df.serialize()
    deserialized = pl.DataFrame.deserialize(io.BytesIO(bytes))
    assert_frame_equal(df, deserialized)
