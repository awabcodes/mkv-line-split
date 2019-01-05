import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="mkv-line-split",
    version="1.0.1",
    author="Awab Abdoun",
    author_email="awabcodes@gmail.com",
    LICENSE="MIT",
    description="Script to split audio lines from .mkv files according to the subtitle",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/awabcodes/mkv-line-splitter",
    packages=setuptools.find_packages(),
    install_requires=[
        'tqdm',
        'pysubs2',
        ],
    entry_points={
        "console_scripts": ['linesplit = linesplit.linesplit:main']
        },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
)