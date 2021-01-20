#!/usr/bin/env python3
from spotpy import describe
from pathlib import Path
from textwrap import dedent
import cmf
import shutil
import importlib
import sys
from sphinx.cmd.build import make_main as sphinx_make


def name(setup):
    return setup.__module__


def Name(setup):
    return setup.__module__.capitalize()


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

def index(setup, doc_dir: Path):
    if (doc_dir / 'index.rst').exists():
        return (doc_dir / 'index.rst').read_text(encoding='utf-8')
    elif (doc_dir.parent / 'index.rst').exists():
        return (doc_dir.parent / 'index.rst').read_text(encoding='utf-8') + \
               f'\n   {Name(setup)} <{name(setup)}.main>'
    else:
        return f'''
Modelling results
==============================

.. toctree::
   :maxdepth: 2
   
   {Name(setup)} <{name(setup)}.main>

'''

def main_text(setup):
    toctree = '.. toctree::\n   ' + '\n   '.join(
        f'{name(setup)}.{chapter}'
        for chapter in ('concept', 'implementation', 'result')
    )
    mod = sys.modules.get(setup.__module__, None)
    mod_doc = getattr(mod, '__doc__', '') or ''
    return mod_doc + '\n' + toctree


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

.. autoclass:: {str(setup)}
    :members:

Das CMF-Projekt
...................

{cmf_text}

    ''')


def create_output_directory(setup):
    """Creates and prepares the directory for output"""
    home = Path(f'{name(setup)}-docs').absolute()
    home.mkdir(parents=True, exist_ok=True)

    src = Path(__file__).parent
    conf_py = src / 'conf.py'

    shutil.copy(conf_py, home)
    return home

def create_rst(setup)->Path:
    # rst = describe.rst(setup)
    home = create_output_directory(setup)

    concept_path = (home / f'{name(setup)}.concept.rst')
    if not concept_path.exists():
        concept_path.write_text(concept(setup), encoding='utf-8')
    index_path = home / 'index.rst'
    index_path.write_text(index(setup, home), encoding='utf-8')
    mt = main_text(setup)
    it = impl_text(setup)
    (home / f'{name(setup)}.main.rst').write_text(mt, encoding='utf-8')
    (home / f'{name(setup)}.implementation.rst').write_text(it, encoding='utf-8')
    return home

def do_sphinx(setup, home: Path):
    """
    Erstellt aus den rst-Dateien die html-Dokumentation
    """
    builddir = home / '_build'
    args = ['-M', 'html', str(home), str(builddir)]
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
