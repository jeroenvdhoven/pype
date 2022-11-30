from setuptools import find_namespace_packages, setup

deps = [
    "pype-base",
    # We will provide absolute no guarantees that our integration will work with
    # EVERY version of pyspark. This has been developed under pyspark==3.3.0.
    "pyspark",
]
test_deps = ["pandas"]

setup(
    name="pype-spark",
    install_requires=deps,
    extras_require={"dev": deps + test_deps, "test": deps + test_deps},
    packages=find_namespace_packages(include=["pype.*"]),
)
