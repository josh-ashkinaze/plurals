import os
import sys

sys.path.insert(0, os.path.abspath('..'))

# -- Project information -----------------------------------------------------
project = 'Plurals'
author = 'Joshua Ashkinaze'

# -- General configuration ---------------------------------------------------
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.viewcode',
]

templates_path = ['_templates']
exclude_patterns = []

# -- Options for HTML output -------------------------------------------------
html_theme = 'sphinx_book_theme'
html_static_path = ['_static']
html_theme_options = {
    "show_navbar_depth": 10,  # Controls depth of expanded items (default is 1)
    "collapse_navbar": False,  # Keep navbar expandable (this is the default)
}

# html_sidebars = {
#    '**': ['sidebar.html', 'sourcelink.html', 'searchbox.html']
# }




