use polars::prelude::*;
use polars_utils::python_function::PythonObject;
use pyo3::prelude::*;
use pyo3::pymethods;

use crate::error::PyPolarsErr;
use crate::expr::PyExpr;

#[pymethods]
impl PyExpr {
    fn arr_len(&self) -> Self {
        self.inner.clone().arr().len().into()
    }

    fn arr_max(&self) -> Self {
        self.inner.clone().arr().max().into()
    }

    fn arr_min(&self) -> Self {
        self.inner.clone().arr().min().into()
    }

    fn arr_sum(&self) -> Self {
        self.inner.clone().arr().sum().into()
    }

    fn arr_std(&self, ddof: u8) -> Self {
        self.inner.clone().arr().std(ddof).into()
    }

    fn arr_var(&self, ddof: u8) -> Self {
        self.inner.clone().arr().var(ddof).into()
    }

    fn arr_median(&self) -> Self {
        self.inner.clone().arr().median().into()
    }

    fn arr_unique(&self, maintain_order: bool) -> Self {
        if maintain_order {
            self.inner.clone().arr().unique_stable().into()
        } else {
            self.inner.clone().arr().unique().into()
        }
    }

    fn arr_n_unique(&self) -> Self {
        self.inner.clone().arr().n_unique().into()
    }

    fn arr_to_list(&self) -> Self {
        self.inner.clone().arr().to_list().into()
    }

    fn arr_all(&self) -> Self {
        self.inner.clone().arr().all().into()
    }

    fn arr_any(&self) -> Self {
        self.inner.clone().arr().any().into()
    }

    fn arr_sort(&self, descending: bool, nulls_last: bool) -> Self {
        self.inner
            .clone()
            .arr()
            .sort(SortOptions {
                descending,
                nulls_last,
                ..Default::default()
            })
            .into()
    }

    fn arr_reverse(&self) -> Self {
        self.inner.clone().arr().reverse().into()
    }

    fn arr_arg_min(&self) -> Self {
        self.inner.clone().arr().arg_min().into()
    }

    fn arr_arg_max(&self) -> Self {
        self.inner.clone().arr().arg_max().into()
    }

    fn arr_get(&self, index: PyExpr, null_on_oob: bool) -> Self {
        self.inner
            .clone()
            .arr()
            .get(index.inner, null_on_oob)
            .into()
    }

    fn arr_join(&self, separator: PyExpr, ignore_nulls: bool) -> Self {
        self.inner
            .clone()
            .arr()
            .join(separator.inner, ignore_nulls)
            .into()
    }

    #[cfg(feature = "is_in")]
    fn arr_contains(&self, other: PyExpr, nulls_equal: bool) -> Self {
        self.inner
            .clone()
            .arr()
            .contains(other.inner, nulls_equal)
            .into()
    }

    #[cfg(feature = "array_count")]
    fn arr_count_matches(&self, expr: PyExpr) -> Self {
        self.inner.clone().arr().count_matches(expr.inner).into()
    }

    #[pyo3(signature = (name_gen))]
    fn arr_to_struct(&self, name_gen: Option<PyObject>) -> Self {
        let name_gen = name_gen.map(|o| PlanCallback::new_python(PythonObject(o)));
        self.inner.clone().arr().to_struct(name_gen).into()
    }

    fn arr_slice(&self, offset: PyExpr, length: Option<PyExpr>, as_array: bool) -> PyResult<Self> {
        let length = match length {
            Some(i) => i.inner,
            None => lit(i64::MAX),
        };
        Ok(self
            .inner
            .clone()
            .arr()
            .slice(offset.inner, length, as_array)
            .map_err(PyPolarsErr::from)?
            .into())
    }

    fn arr_tail(&self, n: PyExpr, as_array: bool) -> PyResult<Self> {
        Ok(self
            .inner
            .clone()
            .arr()
            .tail(n.inner, as_array)
            .map_err(PyPolarsErr::from)?
            .into())
    }

    fn arr_shift(&self, n: PyExpr) -> Self {
        self.inner.clone().arr().shift(n.inner).into()
    }

    fn arr_explode(&self) -> Self {
        self.inner.clone().arr().explode().into()
    }
}
