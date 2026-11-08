"""Every page file must at least be valid Python.

A typo in a page only shows up when someone opens that page, so this catches
it early, without starting the app.
"""
import py_compile
from pathlib import Path

import pytest

PAGE_FILES = sorted(Path("views").glob("*.py")) + [Path("app.py")]


@pytest.mark.parametrize("path", PAGE_FILES, ids=lambda path: path.name)
def test_page_file_is_valid_python(path):
    py_compile.compile(str(path), doraise=True)
