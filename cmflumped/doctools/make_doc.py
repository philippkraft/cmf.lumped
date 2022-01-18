#!/usr/bin/env python3
from spotpy import describe
from pathlib import Path
from textwrap import dedent
import cmf
import shutil
import re
import sys
from sphinx.cmd.build import make_main as sphinx_make
from logging import getLogger
logger = getLogger(__name__)


def name(setup):
    return setup.name


def Name(setup):
    return setup.name.capitalize()


def get_doc_class(setup, classname):
    return getattr(sys.modules[setup.__module__], classname, None)


class Implementation:

    def __init__(self, setup):
        self.setup = setup

    def parameter_text(self):
        cls = get_doc_class(self.setup, 'Parameters')
        return (
                dedent(cls.__doc__) + '\n' +
                '\n'.join(
                    f':{p.name}: [{p.minbound:0.4g}..{p.maxbound:0.4g}] {p.description}'
                    for p in self.setup.parameters
                )
        )

    def model_text(self):
        cls = type(self.setup)
        return cls.describe(self.setup)

    def project_text(self):
        return cmf.describe(self.setup.project)

    def __repr__(self):
        return f'Implementation({self.setup})'

    def __str__(self):
        return '\n'.join((self.parameter_text(), self.model_text(), self.project_text()))


class Documentation:

    def copy_conf_py(self):
        """
        Copies the conf.py file needed to compile the documentation from the sources,
        if it is not present in the target directory
        """
        if not (self.homedir / 'conf.py').exists():
            srcdir = Path(__file__).parent
            conf_py = srcdir / 'conf.py'
            shutil.copy(conf_py, self.homedir)

    def __init__(self, setup, homedir: Path = None):
        self.setup = setup
        self.homedir = homedir or Path(f'{name(self.setup)}-docs')
        self.homedir.mkdir(parents=True, exist_ok=True)

    def copy_figures(self, text):
        figures = re.findall(r'\.\. figure:: (.*)', text)
        for fig in figures:
            if (img := self.homedir.parent / fig).exists():
                shutil.copy(img, self.homedir)

    def write_doc_text(self, classname: str):

        if cls := get_doc_class(self.setup, classname):
            doc = cls.describe(self.setup)
            self.write_text(classname.lower(), doc)
            self.copy_figures(doc)
        else:
            logger.warning(f'No class <{classname}> found in {self.setup.name}')

    def write_text(self, filename: str, text: str, module_prefix=True):
        if module_prefix:
            path = self.homedir / f'{self.setup.name}.{filename}.rst'
        else:
            path = self.homedir / f'{filename}.rst'

        with path.open('w', encoding='utf-8') as f:
            f.write(str(text))

    def index_text(self):
        """
        Uses either an existing index.rst, or copies ../index.rst to the current source directory and extends it
        with a link to the current model. If neither exists, a base index.rst is created.
        """
        if (self.homedir / 'index.rst').exists():
            return (self.homedir / 'index.rst').read_text(encoding='utf-8')
        elif (self.homedir.parent / 'index.rst').exists():
            return (self.homedir.parent / 'index.rst').read_text(encoding='utf-8') + \
                   f'\n   {Name(self.setup)} <{name(self.setup)}.main>'
        else:
            return dedent(f'''
                Modelling results
                ==============================

                .. toctree::
                   :maxdepth: 2

                   {Name(self.setup)} <{name(self.setup)}.main>

                ''')

    def main_text(self):
        toctree = '.. toctree::\n   ' + '\n   '.join(
            f'{name(self.setup)}.{chapter}'
            for chapter in ('concept', 'implementation', 'result', 'discussion', 'bibliography')
        )
        mod = sys.modules.get(self.setup.name, None)
        mod_doc = getattr(mod, '__doc__', '') or ''
        return mod_doc + '\n' + toctree

    def make_rst(self):
        self.write_doc_text('Concept')
        self.write_text('implementation', str(Implementation(self.setup)))
        self.write_doc_text('Result')
        self.write_doc_text('Discussion')
        self.write_doc_text('Bibliography')
        self.write_text('main', self.main_text())
        self.write_text('index', self.index_text(), module_prefix=False)
        self.copy_conf_py()
        return self

    def compile_html(self):
        """
        Erstellt aus den rst-Dateien die html-Dokumentation
        """
        builddir = self.homedir / '_build'
        args = ['-M', 'html', str(self.homedir), str(builddir)]
        sphinx_make(args)
        return builddir



