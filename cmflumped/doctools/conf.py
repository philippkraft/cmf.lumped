project = '{project}'
copyright = '{copyright}'
author = '{author}'

# The short X.Y version
version = '{version}'
# The full version, including alpha/beta/rc tags
release = '{full_version}'

import sys
from pathlib import Path
p= Path(__file__).absolute().parent.parent.parent
print(p)
sys.path.append(str(p))

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.mathjax',
    'sphinx.ext.viewcode',
    'sphinx.ext.todo',
]

templates_path = ['.']

source_suffix = '.rst'

master_doc = 'index'

language = 'de'

exclude_patterns = []

pygments_style = 'sphinx'


html_theme = 'alabaster'


numfig=True
todo_include_todos=True

# -- Extension configuration -------------------------------------------------
