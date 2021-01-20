import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

with open("requirements.txt") as fh:
    requirements = fh.readlines()


setuptools.setup(
    name="cmflumped",
    version="2021.1.20",
    author="Philipp Kraft",
    author_email="philipp.kraft@envr.jlug.de",
    description="A toolbox to build, debug, run and calibrate lumped cmf models",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/philippkraft/cmf.lumped",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha"
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=requirements,
    entry_points = {
        'console_scripts': [
            'cmf.lumped=cmflumped.__main__:main'
        ]
    }
)