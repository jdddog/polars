#![allow(unsafe_op_in_unsafe_fn)]

use polars_error::polars_ensure;

use super::*;

pub struct MeanWindow<'a, T> {
    sum: SumWindow<'a, T, f64>,
}

impl<'a, T> RollingAggWindowNoNulls<'a, T> for MeanWindow<'a, T>
where
    T: NativeType
        + IsFloat
        + std::iter::Sum
        + AddAssign
        + SubAssign
        + Div<Output = T>
        + NumCast
        + Add<Output = T>
        + Sub<Output = T>
        + PartialOrd,
{
    fn new(
        slice: &'a [T],
        start: usize,
        end: usize,
        params: Option<RollingFnParams>,
        window_size: Option<usize>,
    ) -> Self {
        Self {
            sum: SumWindow::<T, f64>::new(slice, start, end, params, window_size),
        }
    }

    unsafe fn update(&mut self, start: usize, end: usize) -> Option<T> {
        let sum = self.sum.update(start, end).unwrap_unchecked();
        Some(sum / NumCast::from(end - start).unwrap())
    }
}

pub fn rolling_mean<T>(
    values: &[T],
    window_size: usize,
    min_periods: usize,
    center: bool,
    weights: Option<&[f64]>,
    _params: Option<RollingFnParams>,
) -> PolarsResult<ArrayRef>
where
    T: NativeType + Float + std::iter::Sum<T> + SubAssign + AddAssign + IsFloat,
{
    let offset_fn = match center {
        true => det_offsets_center,
        false => det_offsets,
    };
    match weights {
        None => rolling_apply_agg_window::<MeanWindow<_>, _, _>(
            values,
            window_size,
            min_periods,
            offset_fn,
            None,
        ),
        Some(weights) => {
            // A weighted mean is a weighted sum with normalized weights
            let mut wts = no_nulls::coerce_weights(weights);
            let wsum = wts.iter().fold(T::zero(), |acc, x| acc + *x);
            polars_ensure!(
                wsum != T::zero(),
                ComputeError: "Weighted mean is undefined if weights sum to 0"
            );
            wts.iter_mut().for_each(|w| *w = *w / wsum);
            no_nulls::rolling_apply_weights(
                values,
                window_size,
                min_periods,
                offset_fn,
                no_nulls::compute_sum_weights,
                &wts,
            )
        },
    }
}
