from setuptools import setup, find_packages

setup(
    name="canoe-lake",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "duckdb>=0.9.0",
        "pandas>=2.0.0",
        "python-dotenv>=1.0.0",
        "requests>=2.31.0",
        "pyarrow>=14.0.0",
    ],
    entry_points={
        "console_scripts": [
            "canoe-lake=canoe_lake.cli:main",
        ],
    },
)
