# -*- coding: utf-8 -*-
"""Contains a (rather) fast implementation of a strided rolling window."""

__author__ = "Vic Degraeve, Jonas Van Der Donckt, Jeroen Van Der Donckt, Emiel Deprost"

from typing import Union, Dict

import numpy as np
import pandas as pd

from .function_wrapper import NumpyFuncWrapper


class StridedRolling:
    """Custom sliding window with stride for pandas DataFrames."""

    # Only keep pd.Series and not Union
    def __init__(self, df: Union[pd.Series, pd.DataFrame], window: int, stride: int):
        """Create StridedRolling object.

        Parameters
        ----------
        df : Union[pd.Series, pd.DataFrame]
            :class:`pd.Series` or :class:`pd.DataFrame` to slide over, the index must
            be a (time-zone-aware) :class:`pd.DatetimeIndex`.
        window : int
            Sliding window length in samples.
        stride : int
            Step/stride length in samples.

        """
        # construct the (expanded) sliding window-stride array
        # Old code: self.time_indexes = df.index[:-window + 1][::stride]
        # Index indicates the start of the windows
        df = df.to_frame() if isinstance(df, pd.Series) else df
        self.window = window
        self.stride = stride
        self.time_indexes = df.index[window - 1:][
                            ::stride
                            ]  # Index indicates the end of the windows
        # TODO: Make this here lazy by only doing on first call of apply func
        self._strided_vals = {}
        for col in df.columns:
            self._strided_vals[col] = sliding_window(
                df[col], window=window, stride=stride
            )

    @property
    def strided_vals(self) -> Dict[str, np.ndarray]:
        """Get the expanded series of each column.

        Returns:
        -------
        Dict[str, np.ndarray]
            A `dict` with the column-name as key, and the corresponding expanded
            series as value.
        """
        return self._strided_vals

    # Make this the __call__ method
    def apply_func(
            self, np_func: NumpyFuncWrapper, return_df=True
    ) -> pd.DataFrame:
        """Apply a function to the expanded time-series.

        Parameters
        ----------
        np_func : NumpyFuncWrapper
            The Callable (wrapped) function which will be applied.
        return_df : bool, optional
            If true, a DataFrame will be returned, otherwise a dict will be returned,
            by default True

        Returns
        -------
        pd.DataFrame
            The merged output of the function applied to every column in a
            new DataFrame or a dict. The DataFrame's column-names have the format:
                `<signal_col_name>_<feature_name>__w=<window>_s=<stride>`.

        """
        feat_out = {}
        feat_names = np_func.output_names
        for col in self.strided_vals.keys():
            out = np.apply_along_axis(np_func, axis=-1, arr=self.strided_vals[col])
            if out.ndim == 1 or (out.ndim == 2 and out.shape[1] == 1):
                assert len(feat_names) == 1
                feat_out[
                    f"{col}_{feat_names[0]}__w={self.window}_s={self.stride}"
                ] = out.flatten()
            if out.ndim == 2 and out.shape[1] > 1:
                assert len(feat_names) == out.shape[1]
                for col_idx in range(out.shape[1]):
                    feat_out[
                        f"{col}_{feat_names[col_idx]}__w={self.window}_s={self.stride}"
                    ] = out[:, col_idx]
        return pd.DataFrame(index=self.time_indexes, data=feat_out)


def sliding_window(series: pd.Series, window: int, stride=1, axis=-1) -> np.ndarray:
    """Calculate a strided sliding window over a series.

    Parameters
    ----------
    series : pd.Series
        :class:`pd.Series` to slide over.
    window : int
        Sliding window length in samples.
    stride : int, optional
        Step/stride length in samples, by default 1.
    axis : int, optional
        The axis to slide over, by default -1.

    Returns
    -------
    np.ndarray
        The expanded series, a 2D array of shape:
        (len(`series`)//`stride`, `window`).

    Raises
    ------
    ValueError
        If the axis is greater than or equal to the number of data dimensions.
    ValueError
        If the stride is negative.
    ValueError
        If the window is greater than the size of the selected axis

    """
    # TODO: het werkt op DataFrame als je axis = 0 -> wrapper code errond
    data = series.values
    if axis >= data.ndim:
        raise ValueError("Axis value out of range")
    if stride < 1:
        raise ValueError("Step size may not be zero or negative")
    if window > data.shape[axis]:
        raise ValueError("Sliding window size may not exceed size of selected axis")

    shape = list(data.shape)
    shape[axis] = np.floor(data.shape[axis] / stride - window / stride + 1).astype(int)
    shape.append(window)

    strides = list(data.strides)
    strides[axis] *= stride
    strides.append(data.strides[axis])

    strided = np.lib.stride_tricks.as_strided(data, shape=shape, strides=strides)
    return strided
