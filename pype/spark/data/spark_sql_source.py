from pyspark.sql import DataFrame as SparkDataFrame
from pyspark.sql import SparkSession

from pype.base.data.data_source import DataSource


class SparkSqlSource(DataSource[SparkDataFrame]):
    def __init__(
        self,
        spark_session: SparkSession,
        query: str,
    ) -> None:
        """Use Spark SQL as an input data source.

        Args:
            spark_session (SparkSession): The current SparkSession.
            query (str): The query to run to get the data.
        """
        super().__init__()
        self.query = query
        self.spark_session = spark_session

    def read(self) -> SparkDataFrame:
        """Execute the query stored in this object.

        Returns:
            SparkDataFrame: The DataFrame generated by the query.
        """
        return self.spark_session.sql(self.query)
