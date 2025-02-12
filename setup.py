import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

requirements = """
wheel
pandas>=1.2.5
matplotlib>=3.4.2
scipy>=1.7.0
click>=7.1.2
tables>=3.6.1
openpyxl>=3.0.0
cmf>=2.0.0
spotpy
sphinx>=4.0.0
networkx>=2.4
pyyaml
setuptools""".split('\n')


def get_version(rel_path):
    import os
    def read(rel_path):
        here = os.path.abspath(os.path.dirname(__file__))
        with open(os.path.join(here, rel_path)) as f:
            return f.read()
    for line in read(rel_path).splitlines():
        if line.startswith('__version__'):
            delim = '"' if '"' in line else "'"
            return line.split(delim)[1]
    else:
        raise RuntimeError("Unable to find version string.")


setuptools.setup(
    name="cmflumped",
    version=get_version('cmflumped/__init__.py'),
    author="Philipp Kraft",
    author_email="philipp.kraft@envr.jlug.de",
    description="A toolbox to build, debug, run and calibrate lumped cmf models",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/philippkraft/cmf.lumped",
    packages=setuptools.find_packages(),
    classifiers=[
        "Development Status :: 3 - Alpha",
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