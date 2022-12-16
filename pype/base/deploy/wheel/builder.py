import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from shutil import copytree
from tempfile import TemporaryDirectory

from pype.base.constants import Constants
from pype.base.utils.workspace import switch_directory

from .extensions import WheelExtension

BaseExtension = WheelExtension(
    "base",
    functionality=[(Path(__file__).parent / "helpers" / "load_model.py", ["load_model"])],
    libraries=["pype.base"],
)


@dataclass
class WheelBuilder:
    """Class to help turn an output folder from an Experiment into a wheel file.

    This should allow you to save models into shippable packages
    quite easily.
    # TODO: add proper tests

    The functionality can be extended quite easily using the `extensions` argument.
    See `WheelExtension` for how to make your own. The base functionality is also
    included as an extension, feel free to check out how that was done as well.

    Args:
        model_folder (Path): Path to the output folder generated by an Experiment
        model_name (str): The name of the model. Will be used as package name. Should follow
            proper package naming conventions.
        version (str): Model/package version.
        output_wheel_file (Path | str | None, optional): The output directory. Defaults to "wheel_output"
            in the current directory.
        libraries (list[str] | None, optional): A list of (versioned) libraries that are used as
            dependencies. By default we use the requirements.txt file from the experiment run.
        extensions (list[WheelExtension] | None, optional): A list of extension to add to this
            wheel file. Extensions add extra functionality besides the base "import pipeline" functionality.
            This can include hosting a FastAPI app for instance.
    """

    model_folder: Path
    model_name: str
    version: str
    output_wheel_file: Path | str | None = None
    libraries: list[str] | None = None
    extensions: list[WheelExtension] | None = None

    def __post_init__(self) -> None:
        """Performs checks and default initialisations."""
        if self.output_wheel_file is None:
            self.output_wheel_file = Path("").parent.absolute() / "wheel_output"
        if self.extensions is None:
            self.extensions = []
        if BaseExtension not in self.extensions:
            self.extensions.append(BaseExtension)
        self._validate_extensions()

    def _validate_extensions(self) -> None:
        names = set()
        function_names = set()

        assert isinstance(self.extensions, list)
        for extension in self.extensions:
            assert extension.name not in names, f"{extension.name} is a duplicated extension name, this is not allowed."
            names.add(extension.name)

            for _, imports in extension.functionality:
                for imp in imports:
                    assert (
                        imp not in function_names
                    ), f"{imp} is a duplicated function name from {extension.name}, this is not allowed."
                    function_names.add(imp)

    def build(self) -> None:
        """Builds the actual package."""
        local_dir = Path(__file__).parent / "helpers"
        template_file = local_dir / "setup_template.py"

        if self.libraries is None:
            with open(self.model_folder / Constants.REQUIREMENTS_FILE, "r") as f:
                requirements_raw = f.readlines()
                libraries = list(map(lambda x: x.replace("\n", ""), filter(lambda x: "==" in x, requirements_raw)))
        else:
            libraries = self.libraries
        assert len(libraries) > 0, "Using pype, it is assumend there is at least 1 dependency"

        with TemporaryDirectory() as tmp_directory:
            tmp_directory_path = Path(tmp_directory)
            tmp_package_dir = tmp_directory_path / self.model_name
            tmp_model_dir = tmp_package_dir / "outputs"
            tmp_setup_file = tmp_directory_path / "setup.py"
            tmp_init_file = tmp_package_dir / "__init__.py"

            tmp_package_dir.mkdir()
            with open(tmp_init_file, "w") as f:
                f.write("")

            assert isinstance(self.extensions, list)
            for extension in self.extensions:
                print(extension, extension.name)
                extension.extend(self.model_name, libraries, tmp_package_dir)

            requirements = '", "'.join(libraries)

            with open(template_file, "r") as f:
                setup_file_raw = f.read()
                setup_file_formatted = (
                    setup_file_raw.replace("{install_requires}", requirements)
                    .replace("{package_name}", self.model_name)
                    .replace("{version}", self.version)
                )

            copytree(self.model_folder, tmp_model_dir)
            with open(tmp_setup_file, "w") as f:
                f.write(setup_file_formatted)

            output_wheel_file = str(self.output_wheel_file)
            with switch_directory(tmp_directory):
                subprocess.check_output(
                    [sys.executable, "setup.py", "bdist_wheel", "--dist-dir", output_wheel_file]
                ).decode()
