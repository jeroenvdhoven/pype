from typing import Iterable, List

from pype.base.data.data import Data


class DataSet(dict[str, Data]):
    """A DataSet consisting of multiple name-Data pairs.

    The Data can be multiple types of objects:
    - pandas DataFrames (or of other languages)
    - spark DataFrames
    - strings, integers, etc.
    """

    def get_all(self, keys: List[str]) -> List[Data]:
        """Returns all data associated with the given keys, in order.

        Args:
            keys (List[str]): The keys of all data to return.

        Returns:
            List[Data]: All data associated with the given keys.
        """
        return [self[key] for key in keys]

    def set_all(self, keys: List[str], data: Iterable[Data]) -> None:
        """Set all data to the given keys, in order.

        This assumes the keys and data set are of the same length.

        Args:
            keys (List[str]): The keys of the given data.
            data (Iterable[Data]): The data to store.
        """
        for key, d in zip(keys, data):
            self[key] = d

    def copy(self) -> "DataSet[Data]":
        """Create a shallow copy of this DataSet.

        This calls the superclass copy() function, but with more fitting type hints.

        Returns:
            DataSet[Data]: A shallow copy of this DataSet.
        """
        return super().copy()  # type: ignore