This is the documentation of **tsflex**, which is a `time-series first` Python toolkit for 
**processing & feature extraction**, making few assumptions about input data.

This makes _tsflex_ suitable for use-cases such as inference on streaming data, performing operations on irregularly sampled time-series, and dealing with time-gaps.

> ~ _**With great flexibility comes great responsiblity, read our docs!**_ - the tsflex devs

<link rel="preload stylesheet" as="style" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.2/css/all.min.css" integrity="sha512-HK5fgLBL+xu6dm/Ii3z4xhlSUyZgTT9tuc/hSrtw6uzJOvgRr2a9jyxxT1ely+B+xFAmJKVSTbpM/CuL7qxO8w==" crossorigin>

<div class="container" style="text-align: center">
        <h3><strong>Installation</strong></h3><br>
        <a title="tsflex on PyPI" href="https://pypi.org/project/tsflex/" style="margin-right:.8em; background-color: #48c774; border-color: transparent; color: #fff; padding: 0.75rem; border-radius: 4px;"
                   itemprop="downloadUrl" data-ga-event-category="PyPI">
                    <span class="icon"><i class="fa fa-download"></i></span>
                    <span>PyPI</span>
                </a> &nbsp;
                <a title="tsflex on GitHub" href="https://github.com/predict-idlab/tsflex" style="color: #4a4a4a; background-color: #f5f5f5 !important; font-size: 1em; font-weight: 400; line-height: 1.5; border-radius: 4px; padding: 0.75rem; "
                   data-ga-event-category="GitHub">
                    <span class="icon"><i class="fab fa-github"></i></span>
                    <span>GitHub</span>
                </a>
</div>
<br>
<hr style="height: 1px; border: none; border-top: 1px solid darkgrey;">


<div style="text-align: center;">
<h3><b><a href="#header-submodules">Jump to API reference</a></b></h3>
</div>

## Getting started 🚀

*tsflex* serves two main functionalities; time-series _processing_ and _feature extraction_:

* The [processing](/tsflex/processing) module withholds a `SeriesPipeline` in which uni- and multivariate data processing operations can be defined.
* The [feature extraction](/tsflex/features) module defines a `FeatureCollection` which does the bookkeeping of the defined features for the data.

<br>

## Data formats 🗄️

*tsflex* leverages the flexibility and convenience that [Pandas](https://pandas.pydata.org/docs/index.html) delivers. This has the consequence that your input should always be either one or more `pd.Series/pd.DataFrame`. Using type-hinting, the input-data can be defined as:

```python
import pandas as pd; from typing import Union, List
data: Union[pd.Series, pd.DataFrame, List[Union[pd.Series, pd.DataFrame]]]
```

For brevity, we call an item from `data`, i.e., series or dataframe-colum, a time-series (`ts`). 

> _tsflex_ was mainly intended to work on _flat data_ such as a **list of series** or a **wide-dataframe**.

### Wide vs. Long Data
![image](https://raw.githubusercontent.com/predict-idlab/tsflex/main/docs/_static/long_wide.png)

Time series data is often stored in 2 data-types:

1. `Wide` time-series data, also known as flat data, is the most common variant. Each column represents a data-modality and the **index** is the **shared time**.<br>
    **Note**: As shown in the example above, not all data-modalities might have values for the shared (~union) index. This circumstance introduces Not a Number (`NaN`) entries.
2. `Long` time-series data, which consists of 3 columns:
      * A _non-index_ `time`-column, which thus can withhold duplicates
      * A `kind` column, defining the `ts` its name.
      * A `value` column, withholding the value for the corresponding _kind-time_ combination

> **_tsflex_ was built to support `wide-dataframes` & `series-list`data**

!!!tip
    If you use long data, you might want to convert this to other modalities.<br>
    Remark that it is not recommended to transform `long -> wide` as this might introduce `NaN`s, potentially resulting in unwanted processing or feature-extraction behavior.<br></br>
    The snippet below provides the functionality for the `long -> series-list` transformation.

```python
import pandas as pd; from typing import List

def long_dataframe_to_series_list(
    long_df: pd.DataFrame, time_col: str, value_col: str, kind_col: str
) -> List[pd.Series]:
    codes, uniques = pd.factorize(long_df[kind_col])
    series_list = []
    for idx, unique in enumerate(uniques):
        series_list.append(
            pd.Series(
                data=long_df.loc[codes == idx, value_col].values,
                index=long_df.loc[codes == idx, time_col],
                name=unique,
            )
        )
    return series_list
```
### Supported data-types

_tsflex_  is rather versatile regarding the `ts`-data its types (e.g. np.float32, string-data, time-based data).

`TODO: add examples`

**Note**: it is the end-users responsibility to use a function which interplays nicely with the data's format.
