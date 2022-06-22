import inspect
import typing
import warnings
from argparse import ArgumentParser
from logging import Logger
from pathlib import Path
from typing import Any, Callable, Iterable, List, Type

from pype.base.data.dataset_source import DataSetSource
from pype.base.evaluate import Evaluator
from pype.base.logging import ExperimentLogger, Serialiser
from pype.base.model import Model
from pype.base.pipeline import Pipe, Pipeline
from pype.base.utils.parsing import get_args_for_prefix


class Experiment:
    MODEL_FILE: str = "model"
    MODEL_CLASS_FILE: str = "model_class"
    PIPELINE_FILE: str = "pipeline"

    def __init__(
        self,
        data_sources: dict[str, DataSetSource],
        model: Model,
        pipeline: Pipeline,
        evaluator: Evaluator,
        logger: ExperimentLogger,
        serialiser: Serialiser,
        output_folder: Path | str,
        additional_files_to_store: list[str] | None = None,
        parameters: dict[str, Any] | None = None,
    ):
        """The core of the pype library: run a standardised ML experiment with the given parameters.

        It is highly recommended to use one of the class methods to initialise this object:
            - from_dictionary: If you've already got your parameters in the right form:
                - `model__<arg>` for model parameters
                - `pipeline__<pipe_name>__<arg> for pipeline parameters.

        Args:
            data_sources (dict[str, DataSetSource]): The DataSets to use, in DataSource form.
                Should contain at least a 'train' DataSet. These will be initialised in the beginning of the run.
            model (Model): The Model to fit.
            pipeline (Pipeline): The Pipeline to use to transform data before feeding it to the Model.
            evaluator (Evaluator): The evaluator to test how good your Model performs.
            logger (ExperimentLogger): The experiment logger to make sure you record how well your experiment worked,
                and log any artifacts such as the trained model.
            serialiser (Serialiser): The serialiser to serialise any Python objects (expect the Model).
            output_folder: (Path | str): The output folder to log artifacts to.
            additional_files_to_store (list[str] | None, optional): Extra files to store, such as python files.
                Defaults to no extra files (None).
            parameters (dict[str, Any] | None, optional): Any parameters to log as part of this experiment.
                Defaults to None.
        """
        assert "train" in data_sources, "Must provide a 'train' entry in the data_sources dictionary."
        if additional_files_to_store is None:
            additional_files_to_store = []
        if parameters is None:
            parameters = {}
            warnings.warn(
                """
                It is highly recommended to provide the parameters used to initialise your
                run here for logging purposes. Consider using the `from_command_line` or
                `from_dictionary` initialisation methods
                """
            )
        if isinstance(output_folder, str):
            output_folder = Path(output_folder)

        self.data_sources = data_sources
        self.model = model
        self.pipeline = pipeline
        self.evaluator = evaluator

        self.logger = Logger(__name__)
        self.experiment_logger = logger
        self.parameters = parameters
        self.serialiser = serialiser
        self.output_folder = output_folder
        self.additional_files_to_store = additional_files_to_store

    def run(self) -> dict[str, dict[str, str | float | int | bool]]:
        """Execute the experiment.

        Returns:
            dict[str, dict[str, str | float | int | bool]]: The performance metrics of this run.
        """
        with self.experiment_logger:
            self.logger.info("Load data")
            datasets = {name: data_source_set.read() for name, data_source_set in self.data_sources.items()}

            self.logger.info("Fit pipeline")
            self.pipeline.fit(datasets["train"])

            self.logger.info("Transform data")
            transformed = {name: self.pipeline.transform(data) for name, data in datasets.items()}

            self.logger.info("Fit model")
            self.model.fit(transformed["train"])

            self.logger.info("Evaluate model")
            metrics = {name: self.evaluator.evaluate(self.model, data) for name, data in datasets.items()}

            self.logger.info("Log results: metrics, parameters, pipeline, model")
            for dataset_name, metric_set in metrics.items():
                self.experiment_logger.log_metrics(dataset_name, metric_set)

            of = self.output_folder
            self.experiment_logger.log_model(
                self.model, of / self.MODEL_FILE, of / self.MODEL_CLASS_FILE, self.serialiser
            )
            self.experiment_logger.log_artifact(of / self.PIPELINE_FILE, self.serialiser, object=self.pipeline)
            self.experiment_logger.log_parameters(self.parameters)

            for extra_file in self.additional_files_to_store:
                self.experiment_logger.log_file(extra_file)

            self.logger.info("Done")
        return metrics

    @classmethod
    def from_dictionary(
        cls,
        data_sources: dict[str, DataSetSource],
        model_class: Type[Model],
        pipeline: Pipeline,
        evaluator: Evaluator,
        logger: ExperimentLogger,
        serialiser: Serialiser,
        output_folder: Path | str,
        parameters: dict[str, Any],
        additional_files_to_store: list[str] | None = None,
    ) -> "Experiment":
        """Creates an Experiment from a dictionary with parameters.

        Args:
            data_sources (dict[str, DataSetSource]): The DataSets to use, in DataSource form.
                Should contain at least a 'train' DataSet. These will be initialised in the beginning of the run.
            model_class (Type[Model]): The class of the Model to fit.
            pipeline (Pipeline): The Pipeline to use to transform data before feeding it to the Model.
            evaluator (Evaluator): The evaluator to test how good your Model performs.
            logger (ExperimentLogger): The experiment logger to make sure you record how well your experiment worked,
                and log any artifacts such as the trained model.
            serialiser (Serialiser): The serialiser to serialise any Python objects (expect the Model).
            output_folder: (Path | str): The output folder to log artifacts to.
            parameters (dict[str, Any] | None, optional): Any parameters to log as part of this experiment.
                Defaults to None.
            additional_files_to_store (list[str] | None, optional): Extra files to store, such as python files.
                Defaults to no extra files (None).

        Returns:
            Experiment: An Experiment created with the given parameters.
        """
        model_args = get_args_for_prefix("model__", parameters)
        model = model_class(**model_args)

        pipeline_args = get_args_for_prefix("pipeline__", parameters)
        pipeline.reinitialise(pipeline_args)

        return Experiment(
            data_sources,
            model,
            pipeline,
            evaluator,
            logger,
            serialiser,
            output_folder,
            additional_files_to_store,
            parameters,
        )

    @classmethod
    def from_command_line(
        cls,
        data_sources: dict[str, DataSetSource],
        model_class: Type[Model],
        pipeline: Pipeline,
        evaluator: Evaluator,
        logger: ExperimentLogger,
        serialiser: Serialiser,
        output_folder: Path | str,
        additional_files_to_store: list[str] | None = None,
    ) -> "Experiment":
        """Automatically initialises an Experiment from command line arguments.

        # TODO: how to best store these extra files to the output folder as well?

        Args:
            data_sources (dict[str, DataSetSource]): The DataSets to use, in DataSource form.
                Should contain at least a 'train' DataSet. These will be initialised in the beginning of the run.
            model_class (Type[Model]): The class of the Model to fit.
            pipeline (Pipeline): The Pipeline to use to transform data before feeding it to the Model.
            evaluator (Evaluator): The evaluator to test how good your Model performs.
            logger (ExperimentLogger): The experiment logger to make sure you record how well your experiment worked,
                and log any artifacts such as the trained model.
            serialiser (Serialiser): The serialiser to serialise any Python objects (expect the Model).
            output_folder: (Path | str): The output folder to log artifacts to.
            additional_files_to_store (list[str] | None, optional): Extra files to store, such as python files.
                Defaults to no extra files (None).

        Returns:
            Experiment: An Experiment created with the given parameters from the command line.
        """
        arg_parser = cls._get_cmd_args(model_class, pipeline)
        parsed_args = arg_parser.parse_args()

        return cls.from_dictionary(
            data_sources,
            model_class,
            pipeline,
            evaluator,
            logger,
            serialiser,
            output_folder,
            parsed_args.__dict__,
            additional_files_to_store,
        )

    @classmethod
    def _get_cmd_args(cls, model_class: Type[Model], pipeline: Pipeline) -> ArgumentParser:
        parser = ArgumentParser()

        cls._add_args_to_parser_for_class(parser, model_class, "model", [Model])
        cls._add_args_to_parser_for_pipeline(parser, pipeline)
        return parser

    @classmethod
    def _add_args_to_parser_for_pipeline(cls, parser: ArgumentParser, pipeline: Pipeline) -> None:
        for pipe in pipeline:
            if isinstance(pipe, Pipe):
                cls._add_args_to_parser_for_class(parser, pipe.operator_class, f"pipeline__{pipe.name}", [])
            else:
                cls._add_args_to_parser_for_pipeline(parser, pipe)

    @classmethod
    def _add_args_to_parser_for_class(
        cls, parser: ArgumentParser, class_: Type, prefix: str, excluded_superclasses: List[Type]
    ) -> None:
        init_func = class_.__init__
        cls._add_args_to_parser_for_function(parser, init_func, prefix)

        signature = inspect.signature(init_func)
        for _, param in signature.parameters.items():
            if param.kind == param.VAR_KEYWORD:
                for superclass in class_.__bases__:
                    if superclass not in excluded_superclasses:
                        cls._add_args_to_parser_for_class(parser, superclass, prefix, excluded_superclasses)

    @classmethod
    def _add_args_to_parser_for_function(cls, parser: ArgumentParser, function: Callable, prefix: str) -> None:
        args = inspect.signature(function)
        for name, parameter in args.parameters.items():
            class_ = parameter.annotation
            arg_name = f"--{prefix}__{name}"
            required = parameter.default == inspect._empty
            if name in ["self", "cls"]:
                continue
            if class_ in [str, float, int, bool]:
                parser.add_argument(arg_name, type=class_, required=required)
            elif typing.get_origin(class_) in [list, tuple, Iterable]:
                subtype = typing.get_args(class_)[0]
                parser.add_argument(arg_name, type=subtype, nargs="+", required=required)
            else:
                warnings.warn(
                    f"Currently the class {str(class_)} is not supported for automatic command line importing."
                )