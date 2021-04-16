# -*- coding: utf-8 -*-
"""Utilities for the processing pipelines
"""

__author__ = 'Jonas Van Der Donckt'

import traceback
from datetime import timedelta
from typing import Dict, List, Any

import pandas as pd
from pathos.multiprocessing import ProcessPool
from tqdm.auto import tqdm

from .series_processor import SeriesProcessorPipeline


def process_chunks_multithreaded(
        df_dict_list: List[Dict[str, pd.DataFrame]],
        processing_pipeline: SeriesProcessorPipeline,
        njobs: int,
        **processing_kwargs
) -> List[Any]:
    """Process  `df_dict_list` in a multithreaded manner, order is preserved.

    Note
    ----
    This method is not concerned with joining the chunks as this operation is highly
    dependent on the preprocessing steps. This is the user's responsibility.

    Parameters
    ----------
    df_dict_list: List[Dict[str, pd.DataFrame]]
        A list of df_dict chunks. most likely the output of `chunk_df_dict`.
    processing_pipeline: SeriesProcessorPipeline
        The pipeline that will be called on each item in `df_dict_list`.
    njobs: int
        The number of jobs that will be spawned.
    **processing_kwargs
        Keyword args that will be passed on to the processing pipeline.

    Returns
    -------
    List[Any]
        A list of the `processing_pipeline`'s outputs. The order is preserved.
    """

    def _executor(chunk):
        try:
            return processing_pipeline(chunk, **processing_kwargs)
        except:
            traceback.print_exc()
            return pd.DataFrame()

    processed_out = []
    with ProcessPool(nodes=min(njobs, len(df_dict_list))) as pool:
        results = pool.imap(_executor, df_dict_list)
        for f in tqdm(results, total=len(df_dict_list)):
            processed_out.append(f)
    return processed_out


def chunk_df_dict(
        df_dict: Dict[str, pd.DataFrame],
        fs_dict: Dict[str, int],
        verbose=False,
        cut_minute_wise: bool = False,
        min_chunk_dur_s=None,
        max_chunk_dur_s=None,
        sub_chunk_margin_s=0,
        copy=True,
) -> List[Dict[str, pd.DataFrame]]:
    """Divide the `df_dict` in chunks.

    Does 2 things:
        1. Detecting gaps in the `df_dict` time series
        2. Divides the df_dict into chunks, according to the parameter configuration.

    Note
    ----
    Assumes that the data modalities within the df_dict_users have identical gaps on
    the same time-positions!

    Note
    ----
    The term `sub-chunk` refers to the chunks who exceed the `max_chunk_duration_s`
    parameter and are therefore further divided into sub-chunks.

    Parameters
    ----------
    df_dict : Dict[str, pd.DataFrame]
        The data-dict, the key represents the sensor modality, and its value the
        corresponding `DataFrame`. Each DataFrame must have a `DateTime-index`.
    fs_dict: Dict[str, int]
        The sample frequency dict. This dict must at least withhold of the keys from the
        `df_dict`.
    verbose : bool, optional
        If set, will print more verbose output, by default True
    cut_minute_wise : bool, optional
        If set, will cut on minute level granularity, by default False
    min_chunk_dur_s : int, optional
        The minimum duration of a chunk in seconds, by default None
    max_chunk_dur_s : int, optional
        The max duration of a chunk, by default None
    sub_chunk_margin_s: int, optional
        The left and right margin of the sub-chunks.
    copy: boolean, optional
        If set True will return a new view (on which you won't get a
        `SettingWithCopyWarning` if you change the content), by default False.

    Returns
    -------
    List[Dict[str, pd.DataFrame]]
        A list of df_dict chunks.

    """
    df_list_dict: List[Dict[str, pd.DataFrame]] = []

    def print_verbose_time(df_s, t_begin, t_end, msg=""):
        fmt = "%Y-%m-%d %H:%M"
        if not verbose:
            return
        print(
            f"slice {t_begin.strftime(fmt)} - {t_end.strftime(fmt)} -"
            f" {df_s[t_begin:t_end].shape}"
        )
        if len(msg):
            print(f"\t└──>  {msg}")

    def slice_time(df_s, t_begin, t_end):
        """Slices the ds_s dict."""
        if copy:
            return df_s[t_begin:t_end].copy()
        else:
            return df_s[t_begin:t_end]

    def insert_chunk(idx, dict_key, chunk):
        t_chunk_start, t_chunk_end = chunk.index[[0, -1]]
        if idx >= len(df_list_dict):
            df_list_dict.append({dict_key: chunk})
            print_verbose_time(
                chunk, t_chunk_start, t_chunk_end, "APPEND sub chunk"
            )
        else:
            # there already exists a key-(sub)chunk template on that place,
            # just add this other sensor modality to it
            # !!!note: no guarantee that this is this other key-(sub)chunk template
            #           covers the same time range!!!
            df_list_dict[idx][dict_key] = chunk
            print_verbose_time(
                chunk, t_chunk_start, t_chunk_end, "INSERT sub chunk"
            )
        return idx + 1

    i = 0
    for sensor_str, df_sensor in df_dict.items():
        if len(df_sensor) < 2:
            if verbose:
                print(f"too small df_sensor - {df_sensor.shape}")
            continue
        assert i == len(df_list_dict)
        assert sensor_str in fs_dict.keys()
        fs_sensor = fs_dict[sensor_str]
        gaps = df_sensor.index.to_series().diff() > timedelta(seconds=1.05 / fs_sensor)
        # set the first and last timestamp to True
        gaps.iloc[[0, -1]] = True
        gaps = df_sensor[gaps].index.tolist()
        if verbose:
            print('-' * 10, ' detected gaps', '-' * 10)
            print(*gaps, sep="\n")

        # reset the iterator
        i = 0
        for (t_begin_c, t_end_c) in zip(gaps, gaps[1:]):
            if cut_minute_wise:
                t_begin_c = (t_begin_c + timedelta(seconds=60)).replace(
                    second=0, microsecond=0
                )

                # As we add time -> we might want to add this sanity check
                if t_begin_c > t_end_c:
                    print_verbose_time(df_sensor, t_begin_c, t_end_c,
                                       "[W] t_end > t_start")
                    continue

            # The t_end is the t_start of the new time range -> hence [:-1]
            # cut on -> [t_start_c(hunk), t_end_c(hunk)[
            df_chunk = df_sensor[t_begin_c:t_end_c][:-1]
            if len(df_chunk) > 2:  # re-adjust the t_end
                t_end_c = df_chunk.index.to_series().iloc[-1]
            else:
                print_verbose_time(df_sensor, t_begin_c, t_end_c, "too small df_chunk")
                continue

            # Check for min duration
            chunk_range_s = len(df_chunk) // fs_sensor
            if isinstance(min_chunk_dur_s, int) and chunk_range_s < min_chunk_dur_s:
                print_verbose_time(
                    df_chunk,
                    t_begin_c,
                    t_end_c,
                    f"Too small chunk min_dur {min_chunk_dur_s} > {df_chunk.shape}",
                )
                continue

            # divide the chunk into sub_chunks (sc's)
            if max_chunk_dur_s is not None and chunk_range_s > max_chunk_dur_s:
                print_verbose_time(df_chunk, t_begin_c, t_end_c,
                                   "Dividing in sub-chunks")
                t_begin_sc = t_begin_c
                while t_begin_sc < t_end_c:
                    # slice, by making use of the margin
                    t_end_sc = t_begin_sc + timedelta(seconds=max_chunk_dur_s)
                    t_end_sc_m = t_end_sc + timedelta(seconds=sub_chunk_margin_s)
                    t_end_sc_m = min(t_end_c, t_end_sc_m)

                    t_begin_sc_m = t_begin_sc - timedelta(seconds=sub_chunk_margin_s)
                    t_begin_sc_m = max(t_begin_c, t_begin_sc_m)

                    # slice & add the sub-chunk to the list
                    i = insert_chunk(
                        idx=i,
                        dict_key=sensor_str,
                        chunk=slice_time(df_sensor, t_begin_sc_m, t_end_sc_m)
                    )

                    # update the condition's variable
                    t_begin_sc = t_end_sc
                continue

            i = insert_chunk(
                idx=i,
                dict_key=sensor_str,
                chunk=slice_time(df_sensor, t_begin_c, t_end_c)
            )
    return df_list_dict
