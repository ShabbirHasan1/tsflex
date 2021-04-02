"""FeatureCollection class for collection and calculation of features."""

__author__ = "Jonas Van Der Donckt, Emiel Deprost, Jeroen Van Der Donckt"

import pandas as pd

from typing import List, Union, Dict, Tuple

from .strided_rolling import StridedRolling
from .feature import FeatureDescription, MultipleFeatureDescriptions


class FeatureCollection:
    """Collection of features to be calculated."""

    def __init__(
        self,
        feature_desc_list: Union[
            List[FeatureDescription], List[MultipleFeatureDescriptions]
        ] = None,
    ):
        """Create a FeatureCollection.

        Parameters
        ----------
        features_list : Union[List[Feature], List[MultipleFeatures]], optional
            Initial list of Features to add to collection, by default None

        """
        # The feature collection is a dict where the key is a tuple(str, int, int), the
        # tuple values correspond to (signal_key, window, stride)
        self._feature_desc_dict: Dict[
            Tuple[str, int, int], List[FeatureDescription]
        ] = {}
        # A list of all the features, holds the same references as the dict above but
        # is simply stored in another way
        self._feature_desc_list: List[FeatureDescription] = []
        if feature_desc_list:
            self.add(feature_desc_list)

    @staticmethod
    def _get_collection_key(feature: FeatureDescription):
        return feature.key, feature.window, feature.stride

    def _add_feature(self, feature: FeatureDescription):
        self._feature_desc_list.append(feature)

        key = self._get_collection_key(feature)
        if key in self._feature_desc_dict.keys():
            self._feature_desc_dict[key].append(feature)
        else:
            self._feature_desc_dict[key] = [feature]

    def add(
        self,
        features_list: Union[
            List[FeatureDescription], List[MultipleFeatureDescriptions]
        ],
    ):
        """Add a list of FetaureDescription to the FeatureCollection.

        Parameters
        ----------
        features_list : Union[List[Feature], List[MultipleFeatures]]
            List of features to add.

        """
        for feature in features_list:
            if isinstance(feature, MultipleFeatureDescriptions):
                self.add(feature.feature_descriptions)
            elif isinstance(feature, FeatureDescription):
                self._add_feature(feature)

    def calculate(
        self, signals: Union[List[pd.Series], pd.DataFrame], merge_dfs=False
    ) -> Union[List[pd.DataFrame], pd.DataFrame]:
        """Calculate features on the passed signals.

        Parameters
        ----------
        signals : Union[List[pd.Series], pd.DataFrame]
            Dataframe or Series list with all the required signals for the feature
            calculation.
        merge_dfs : bool, optional
            Whether the results should be merged to a DataFrame with an outer merge,
            by default False

        Returns
        -------
        Union[List[pd.DataFrame], pd.DataFrame]
            A DataFrame or List of DataFrames with the features in it.

        Raises
        ------
        KeyError
            Raised when a needed key is not found in `signals`.

        """
        series_dict = dict()

        if isinstance(signals, pd.DataFrame):
            series_list = [signals[s] for s in signals.columns]
        else:
            series_list = signals

        for s in series_list:
            assert isinstance(s, pd.Series), "Error non pd.Series object passed"
            series_dict[s.name] = s.copy()

        # TODO add MultiProcessing
        #   Won't be that easy as we save the output ...
        # For all operations on the same stridedRolling object
        calculated_feature_list: List[pd.DataFrame] = []
        for signal_key, win, stride in self._feature_desc_dict.keys():
            try:
                stroll = StridedRolling(series_dict[signal_key], win, stride)
            except KeyError:
                raise KeyError(f"Key {signal_key} not found in series dict.")

            for feature in self._feature_desc_dict[(signal_key, win, stride)]:
                print(f"Feature calculation: {feature}")
                df = stroll.apply_func(feature.function)
                calculated_feature_list.append(df)

        if merge_dfs:
            df_merged = pd.DataFrame()
            for calculated_feature in calculated_feature_list:
                df_merged = pd.merge(
                    left=df_merged,
                    right=calculated_feature,
                    how="outer",
                    left_index=True,
                    right_index=True,
                )
            return df_merged
        else:
            return calculated_feature_list

    def __repr__(self):
        """Representation string of FeatureCollection."""
        repr_string = f"{self.__class__.__name__}(\n"
        for feature in self._feature_desc_list:
            repr_string += f"\t{repr(feature)} \n"
        return repr_string + ")"
