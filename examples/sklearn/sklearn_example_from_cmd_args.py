"""Call this using some form of command line.

e.g. python -m examples.sklearn.sklearn_example_from_cmd_args --model__fit_intercept=False
"""

from pathlib import Path
from typing import Iterable

import numpy as np
import pandas as pd
from sklearn.datasets import load_iris
from sklearn.metrics import accuracy_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

from pype.base.data import DataSetSource
from pype.base.deploy.inference import Inferencer
from pype.base.evaluate.evaluator import Evaluator
from pype.base.experiment.experiment import Experiment
from pype.base.logger.local_logger import LocalLogger
from pype.base.pipeline.pipe import Pipe
from pype.base.pipeline.pipeline import Pipeline
from pype.base.pipeline.type_checker import TypeCheckerPipe
from pype.base.serialiser.joblib_serialiser import JoblibSerialiser
from pype.sklearn.data.data_frame_source import DataFrameSource
from pype.sklearn.model.logistic_regression_model import LogisticRegressionModel
from pype.sklearn.pipeline.numpy_type_checker import NumpyTypeChecker
from pype.sklearn.pipeline.pandas_type_checker import PandasTypeChecker


#  Try a run with sklearn and argument reading
def _make_data() -> Iterable[np.ndarray]:
    iris = load_iris(as_frame=True)
    x = pd.DataFrame(iris["data"])
    y = pd.DataFrame(iris["target"])

    kept_rows = y["target"] < 2
    x = x.loc[kept_rows, :]
    y = y.loc[kept_rows, :]

    return train_test_split(x, y, test_size=0.2)


train_x, test_x, train_y, test_y = _make_data()

ds = {
    "train": DataSetSource(
        x=DataFrameSource(train_x),
        y=DataFrameSource(train_y),
    ),
    "test": DataSetSource(
        x=DataFrameSource(test_x),
        y=DataFrameSource(test_y),
    ),
}

evaluator = Evaluator(
    {
        "accuracy": accuracy_score,
    }
)

tcc = [
    (np.ndarray, NumpyTypeChecker),
    (pd.DataFrame, PandasTypeChecker),
]

input_ds_type_checker = TypeCheckerPipe(
    "type_checker-in",
    input_names=["x"],
    type_checker_classes=tcc,
)

output_ds_type_checker = TypeCheckerPipe(
    "type_checker-out",
    input_names=["y"],
    type_checker_classes=tcc,
)

pipeline = Pipeline([Pipe("scale", StandardScaler, inputs=["x"], outputs=["x"])])
of = Path("outputs")

experiment = Experiment.from_command_line(
    data_sources=ds,
    model_class=LogisticRegressionModel,
    model_inputs=["x"],
    model_outputs=["y"],
    pipeline=pipeline,
    evaluator=evaluator,
    logger=LocalLogger(),
    input_type_checker=input_ds_type_checker,
    output_type_checker=output_ds_type_checker,
    serialiser=JoblibSerialiser(),
    output_folder=of,
)

metrics = experiment.run()
print("Metrics:", metrics)

# Try loading results again
folder = Path("outputs")
inferencer = Inferencer.from_folder(folder)

train_x, test_x, train_y, test_y = _make_data()
test_data = DataSetSource(
    x=DataFrameSource(test_x),
    y=DataFrameSource(test_y),
)
result = inferencer.predict(test_data)
print(result)
