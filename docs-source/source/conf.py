# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join("..", "..")))
import pabutools

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "pabutools"
copyright = "2023, Simon Rey, Grzegorz Pierczyński, Markus Utke and Piotr Skowron"
author = "Simon Rey, Grzegorz Pierczyński, Markus Utke and Piotr Skowron"

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.autodoc",
    "sphinx.ext.imgmath",
    "enum_tools.autoenum",
]

nitpicky = True
nitpick_ignore_regex = [
    (r"^py:.*$", r"^(?!pabutools\.).*")
]

add_module_names = False
autodoc_member_order = "groupwise"
autodoc_typehints_format = "short"
python_use_unqualified_type_names = True

napoleon_google_docstring = False

templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]

source_suffix = ".rst"
master_doc = "index"

version = pabutools.__version__
release = pabutools.__version__
language = "en"

pygments_style = "sphinx"

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "sphinx_book_theme"
# html_static_path = ["_static"]
html_extra_path = [
    "outcome_vis_ex/outcome_vis_ex_greedy.html",
    "outcome_vis_ex/outcome_vis_ex_mes_rounds.html",
    "outcome_vis_ex/outcome_vis_ex_mes_summary.html",
]

html_title = "Pabutools"
html_theme_options = {
    "repository_url": "https://github.com/COMSOC-Community/pabutools",
    "use_repository_button": True,
}
html_context = {"default_mode": "light"}
