from unittest.mock import MagicMock

from pype.spark.data import SparkDataFrameSource


class Test_SparkDataFrameSource:
    def test(self):
        df = MagicMock()

        source = SparkDataFrameSource(df)
        result = source.read()

        assert result == df
