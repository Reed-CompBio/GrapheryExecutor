import os

import setuptools


def read_file(filename):
    base_path = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(base_path, filename)) as file:
        return file.read()


with open("executor/settings/variables.py") as fid:
    for line in fid:
        if line.startswith("SERVER_VERSION"):
            version = line.strip().split()[-1][1:-1]
        if line.startswith("PROG_NAME"):
            prog_name = line.strip().split()[-1][1:-1]


setuptools.setup(
    name=prog_name,
    version=version,
    packages=setuptools.find_packages(exclude=["executor.tests*"]),
    author="Larry Zeng",
    author_email="zengl@reed.edu",
    description="The executor module for graphery",
    install_requires=[
        "networkg @ git+https://github.com/Reed-CompBio/networkx.git@networkg-2.7.1r2#egg=networkg"
    ],
    entry_points={
        "console_scripts": [f"{prog_name}=executor:main"],
    },
    long_description=read_file("README.md"),
    long_description_content_type="text/markdown",
    url="https://github.com/Reed-CompBio/GrapheryExecutor",
    project_urls={
        "Bug Tracker": "https://github.com/Reed-CompBio/GrapheryExecutor/issues",
        "Documentation": "https://docs.graphery.reedcompbio.org",
        "Source Code": "https://github.com/Reed-CompBio/GrapheryExecutor",
    },
    classifiers=[
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
)
