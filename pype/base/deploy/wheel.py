import subprocess
import sys
from pathlib import Path
from shutil import copyfile, copytree
from tempfile import TemporaryDirectory

from pype.base.constants import Constants
from pype.base.utils.workspace import switch_directory


def make_wheel(
    model_folder: Path,
    model_name: str,
    version: str,
    output_wheel_file: Path | str | None = None,
    libraries: list[str] | None = None,
) -> None:
    """Turns an output folder from an Experiment into a wheel file.

    This should allow you to save models into shippable packages
    quite easily.
    # TODO: add proper tests

    Args:
        model_folder (Path): Path to the output folder generated by an Experiment
        model_name (str): The name of the model. Will be used as package name. Should follow
            proper package naming conventions.
        version (str): Model/package version.
        output_wheel_file (Path | str | None, optional): The output directory. Defaults to "wheel_output"
            in the current directory.
        libraries (list[str] | None, optional): A list of (versioned) libraries that are used as
            dependencies. By default we use the requirements.txt file from the experiment run.
    """
    if output_wheel_file is None:
        output_wheel_file = Path("").parent.absolute() / "wheel_output"

    local_dir = Path(__file__).parent / "wheel_helpers"
    template_file = local_dir / "setup_template.py"
    main_file = local_dir / "wheel_main.py"

    if libraries is None:
        with open(model_folder / Constants.REQUIREMENTS_FILE, "r") as f:
            requirements_raw = f.readlines()
            assert len(requirements_raw) > 0, "Using pype, it is assumend there is at least 1 dependency"
            requirements = '", "'.join(filter(lambda x: "==" in x, requirements_raw)).replace("\n", "")
    else:
        assert len(libraries) > 0, "Using pype, it is assumend there is at least 1 dependency"
        requirements = '", "'.join(libraries)

    with open(template_file, "r") as f:
        setup_file_raw = f.read()
        setup_file_formatted = (
            setup_file_raw.replace("{install_requires}", requirements)
            .replace("{package_name}", model_name)
            .replace("{version}", version)
        )

    with TemporaryDirectory() as tmp_directory:
        tmp_directory_path = Path(tmp_directory)
        tmp_model_dir = tmp_directory_path / model_name / "outputs"
        tmp_setup_file = tmp_directory_path / "setup.py"
        tmp_main_file = tmp_directory_path / model_name / "main.py"

        copytree(model_folder, tmp_model_dir)
        copyfile(main_file, tmp_main_file)

        with open(tmp_setup_file, "w") as f:
            f.write(setup_file_formatted)
        with open(tmp_directory_path / "__init__.py", "w") as f:
            f.write("")
        with open(tmp_directory_path / model_name / "__init__.py", "w") as f:
            f.write("from .main import load_model, load_app")

        output_wheel_file = str(output_wheel_file)
        with switch_directory(tmp_directory):
            subprocess.check_output(
                [sys.executable, "setup.py", "bdist_wheel", "--dist-dir", output_wheel_file]
            ).decode()
