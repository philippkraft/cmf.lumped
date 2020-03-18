#!/usr/bin/env python3
from spotpy import describe
from pathlib import Path
from textwrap import dedent
import re
import cmf
import os
import importlib
import sys
from sphinx.cmd.build import make_main as sphinx_make
import webbrowser


def name(setup):
    return str(setup).split('.')[-1]


def Name(setup):
    return str(setup).split('.')[-1].capitalize()


def concept(setup, overwrite=False):
    return dedent(f'''
        Konzept für das Modell von {Name(setup)}
        ------------------------------------------

        :numref:`fig_{name(setup)}_concept` zeigt das Modell Konzept. Die Idee beruht auf den folgenden Ideen:

        .. todo:: 

           {Name(setup)}: Hier folgt eine Beschreibung des Konzepts.


        .. _fig_{name(setup)}_concept:
        .. figure:: {name(setup)}.concept.png

            Die Konzept-Skizze für das {Name(setup)} Modell...
        ''')


def main_text(setup):
    toctree = '.. toctree::\n   ' + '\n   '.join(
        f'{name(setup)}.{chapter}'
        for chapter in ('concept', 'implementation', 'result')
    )

    mod = sys.modules[setup.__module__]
    return mod.__doc__ + '\n' + toctree


def impl_text(setup):
    parameter_text = '\n'.join(
        f':{p.name}: [{p.minbound:0.4g}..{p.maxbound:0.4g}] {p.description}'
        for p in setup.parameters
    )

    cmf_text = cmf.describe(setup.project)

    return dedent(f'''
Implementierung des Konzepts
-------------------------------

Modell-Parameter
.................

{parameter_text}

Die Modell-Klasse
.................

.. autoclass:: {str(setup)}.Modell
    :members:

Das CMF-Projekt
...................

{cmf_text}

    ''')


def create_rst(setup):
    # rst = describe.rst(setup)
    home = Path(f'output/{name(setup)}')
    home.mkdir(parents=True, exist_ok=True)
    concept_path = (home / f'{name(setup)}.concept.rst')
    if not concept_path.exists():
        concept_path.write_text(concept(setup), encoding='utf-8')
    (home / f'{name(setup)}.main.rst').write_text(main_text(setup), encoding='utf-8')
    (home / f'{name(setup)}.implementation.rst').write_text(impl_text(setup), encoding='utf-8')


def do_sphinx(setup):
    """
    Erstellt aus den rst-Dateien die html-Dokumentation
    """
    sourcedir = f'output/{name(setup)}'
    builddir = f'{sourcedir}/_build'
    args = ['-M', 'html', sourcedir, builddir]
    sphinx_make(args)
    return builddir


if __name__ == '__main__':

    sys.path.insert(0, '.')

    module = importlib.import_module('.' + sys.argv[1], 'models')

    # Erzeuge das Modell
    setup = module.Modell()
    # Schreibe die rst-Dateien
    create_rst(setup)
    # Erzeuge die HTML-Dokumentation
    builddir = do_sphinx(setup)
