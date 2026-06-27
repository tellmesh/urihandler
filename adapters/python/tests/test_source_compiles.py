# Guards a recurring extraction bug: the agent's bundled-fallback shape
#   try: from urirun_connector_X import *
#   except ImportError: from __future__ import annotations  # <- SyntaxError, must be first stmt
# traps `from __future__` (or the docstring) inside the except block. That one SyntaxError cascades
# into many confusing pytest COLLECTION errors. Compiling is import-free, so this catches EVERY broken
# source file — including ones no other test imports — as a single clear failure naming each file.
# Run standalone (`pytest tests/test_source_compiles.py`) to diagnose a collection-interrupted suite.
import os
import pathlib
import py_compile
import subprocess
import sys
import unittest

_ROOT = pathlib.Path(__file__).resolve().parent.parent  # adapters/python
_PKGS = ["urirun", "urirun_runtime", "urirun_node", "urirun_flow",
         "urirun_contracts", "urirun_twin", "urirun_scanner"]


class SourceCompilesTests(unittest.TestCase):
    def test_all_package_sources_compile(self):
        bad = []
        for pkg in _PKGS:
            root = _ROOT / pkg
            if not root.exists():
                continue
            for f in root.rglob("*.py"):
                if "build/lib" in str(f):
                    continue
                try:
                    py_compile.compile(str(f), doraise=True)
                except py_compile.PyCompileError as exc:
                    bad.append(f"{f.relative_to(_ROOT)}: {str(exc).splitlines()[-1]}")
        self.assertEqual(bad, [], "package source has syntax errors:\n  " + "\n  ".join(bad))


class ExtractedPackagesImportableTests(unittest.TestCase):
    def test_extracted_packages_import_in_a_clean_subprocess(self):
        """The extracted top-level packages must import in a CLEAN subprocess — i.e. the editable
        install's finder is registered for them, not only for `urirun`. In-process tests pass via
        conftest's sys.path prepend, which MASKS a stale editable finder; but a subprocess flow/worker
        (`python -m …`) has no such path, so a stale finder makes a real flow fail at runtime with
        `ModuleNotFoundError: No module named 'urirun_node'`. This guards that class directly.
        If it fails: re-run `pip install -e adapters/python` (the finder went stale after a new
        top-level package was extracted)."""
        pkgs = ["urirun_node", "urirun_flow", "urirun_contracts", "urirun_twin",
                "urirun_runtime", "urirun_scanner", "urirun_connectors_toolkit"]
        env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}  # no path crutch — test the finder
        proc = subprocess.run([sys.executable, "-c", "import " + ", ".join(pkgs)],
                              capture_output=True, text=True, timeout=60, cwd="/", env=env)
        self.assertEqual(proc.returncode, 0,
                         "extracted packages not importable in a clean subprocess — stale editable "
                         "finder after an extraction. Fix: `pip install -e adapters/python`.\n"
                         + proc.stderr.strip())


if __name__ == "__main__":
    unittest.main()
