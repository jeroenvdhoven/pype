from typing import Type

import pandas as pd
from pydantic import create_model
from pyspark.sql import DataFrame as SparkDataFrame
from pyspark.sql import SparkSession

from pype.base.pipeline.type_checker import DataModel, TypeChecker


class SparkData(DataModel):
    def __post_init__(self) -> None:
        """Sets a spark session by calling getOrCreate."""
        self.spark_session = SparkSession.builder.getOrCreate()

    def convert(self) -> SparkDataFrame:
        """Converts this object to a spark DataFrame.

        Returns:
            SparkDataFrame: The spark DataFrame contained by this object.
        """
        converted_data = pd.DataFrame(self.__dict__)

        return self.spark_session.createDataFrame(converted_data)

    @classmethod
    def to_model(cls, data: SparkDataFrame) -> "SparkData":
        """Converts a spark DataFrame to a SparkData model, which can be serialised.

        Args:
            data (SparkDataFrame): A spark DataFrame to serialise.

        Returns:
            SparkData: A serialisable version of the DataFrame.
        """
        pandas_data = data.toPandas()

        return cls(**pandas_data.to_dict(orient="list"))


class SparkTypeChecker(TypeChecker[SparkDataFrame]):
    def fit(self, data: SparkDataFrame) -> "SparkTypeChecker":
        """Fit this SparkTypeChecker to the given data.

        Args:
            data (SparkDataFrame): The data to fit.

        Returns:
            SparkTypeChecker: self
        """
        self.raw_types = self._convert_dtypes(dict(data.dtypes))
        return self

    def _convert_dtypes(self, dct: dict[str, str]) -> dict[str, tuple[str, type]]:
        return {name: self._convert_dtype(string_type) for name, string_type in dct.items()}

    def _convert_dtype(self, string_type: str) -> tuple[str, type]:
        conv_type: Type | None = None
        if string_type == "str":
            conv_type = str
        elif string_type == "int":
            conv_type = int
        elif string_type in ["float", "double"]:
            conv_type = float
        elif string_type == "bool":
            conv_type = bool
        else:
            raise ValueError(f"{string_type} not supported")

        return (string_type, conv_type)

    def transform(self, data: SparkDataFrame) -> SparkDataFrame:
        """Checks if the given data fits the specifications this TypeChecker was fitted for.

        Args:
            data (SparkDataFrame): The data to check.

        Returns:
            SparkDataFrame: data, if the data fits the specifications. Otherwise, an assertion error is thrown.
        """
        assert isinstance(data, SparkDataFrame), "Please provide a spark DataFrame!"
        colnames = list(self.raw_types.keys())
        for col in colnames:
            assert col in data.columns, f"`{col}` is missing from the dataset"
        dtype_dict = dict(data.dtypes)

        data = data.select(colnames)

        for name, (spark_type, _) in self.raw_types.items():
            actual_dtype = dtype_dict[name]
            assert (
                actual_dtype == spark_type
            ), f"Dtypes did not match up for col {name}: Expected {spark_type}, got {actual_dtype}"
        return data

    def get_pydantic_type(self) -> type[SparkData]:
        """Creates a Pydantic model for this data to handle serialisation/deserialisation.

        Returns:
            type[SparkData]: A SparkData model that fits the data this wat fitted on.
        """
        data_type = {
            name: (list[dtype] | dict[str | int, dtype], ...)  # type: ignore
            for name, (_, dtype) in self.raw_types.items()
        }

        model = create_model("SparkData", **data_type, __base__=SparkData)

        return model
