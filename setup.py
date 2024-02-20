import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

setuptools.setup(
    name="wuggy",
    version="1.1.2",
    author="Emmanuel Keuleers",
    author_email="E.A.Keuleers@tilburguniversity.edu",
    description="Wuggy: A multilingual pseudoword generator",
    long_description="Wuggy: A multilingual pseudoword generator implemented as a Python library",
    long_description_content_type="text/markdown",
    url="https://github.com/WuggyCode/wuggy",
    packages=setuptools.find_packages(),
    install_requires=requirements,
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
)
