#!/usr/bin/env python3
from spotpy import describe
from pathlib import Path
from textwrap import dedent
import cmf
import shutil
import importlib
import sys
from sphinx.cmd.build import make_main as sphinx_make
from logging import getLogger
logger = getLogger(__name__)

def name(setup):
    return setup.__module__


def Name(setup):
    return setup.__module__.capitalize()


def write_doc_text(setup: object, classname: str, homedir: Path):

    cls = getattr(sys.modules[setup.__module__], classname, None)
    if cls:
        doc = dedent(cls.__doc__.format(name=name(setup), Name=Name(setup))).strip() + '\n'
        cname = f'{setup.__module__}.{classname.lower()}'
        path = homedir / f'{cname}.rst'
        path.write_text(doc, encoding='utf-8')
        imgpath = homedir.parent / (cname + '.png')
        if imgpath.exists():
            shutil.copy(imgpath, homedir)
    else:
        logger.warning(f'No class <{classname}> found in {setup.__module__}')


def write_result_text(setup: object, homedir: Path, classname='Result'):
    cls = getattr(sys.modules[setup.__module__], classname, None)
    if cls:

        with cls(setup) as r:
            doc = str(r)
            cname = f'{setup.__module__}.{classname.lower()}'
            path = homedir / f'{cname}.rst'
            path.write_text(doc, encoding='utf-8')
            r.outputdir = str(homedir)
            r.dotty_plot()
            r.timeseries_plot()
    else:
        logger.warning(f'No class <{classname}> found in {setup.__module__}')



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

.. autoclass:: {setup.__module__}.{setup.__class__.__name__}
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

    # (home / f'{name(setup)}.concept.rst').write_text(concept(setup), encoding='utf-8')
    write_doc_text(setup, 'Concept', home)
    write_result_text(setup, home)
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
