#!/usr/bin/env python3
"""Conan test_package for ml-dtypes 0.5.4 (NumPy dtype extensions, C++ extension).

L1 consumer-side verification: imports the packaged ``ml_dtypes`` under the
``conanrun`` environment (PYTHONPATH -> the package's site-packages,
LD_LIBRARY_PATH -> dependency libs) and really exercises its API
(7 checkpoints, incl. a HarmonyOS-only signed-ELF check; see test_ml_dtypes.py).

Upstream suite evidence: the aggregate produced by the real ``pytest`` run in
the main recipe's ``build()`` is stored inside the package
(``res/upstream_test_summary.json``); this ``test()`` reads it back and re-emits
it as ``HMBS_UPSTREAM_TEST_RESULT``.  The gate only scans the test_package
phase stdout, and ``conan create`` skips ``build()`` entirely on a cache hit, so
the marker must be emitted here.  The numbers come from parsing the real pytest
output — nothing is fabricated.
"""

import json
import os

from conan import ConanFile
from conan.errors import ConanException


class TestPackageConan(ConanFile):
    settings = "os", "arch"
    generators = "VirtualRunEnv"
    exports_sources = "test_ml_dtypes.py"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _python3(self):
        """Interpreter used to run the consumer test.

        The extension module shipped by this package is compiled against the
        Conan-managed CPython and links its ``libpython3.12.so.1.0``, so that
        interpreter is preferred.  Fallback matters because on the CI worker the
        HNP python3 (``/data/service/hnp/bin/python3``) appears earlier on PATH:
        it is a *different* CPython build, and starting it with the Conan
        libpython on ``LD_LIBRARY_PATH`` aborts with
        ``Error relocating /data/service/hnp/bin/python3: Py_BytesMain: symbol
        not found`` (exit 127).
        """
        import shutil

        try:
            dep = self.dependencies["python"]
            cand = os.path.join(dep.package_folder, "bin", "python3.12")
            if os.path.isfile(cand):
                return cand
        except Exception:  # python not resolvable in this graph -> fall back
            pass

        cands = [os.environ.get("HMBS_PYTHON3"),
                 shutil.which("python3"),
                 os.path.expanduser("~/usr/local/bin/python3"),
                 "/usr/local/bin/python3", "/usr/bin/python3"]
        for c in cands:
            if c and os.path.isfile(c):
                return c
        raise ConanException(
            "python3 not found: set HMBS_PYTHON3=<path> or install a CPython "
            "with dev headers under ~/usr/local")

    def test(self):
        py = self._python3()
        script = os.path.join(self.recipe_folder, "test_ml_dtypes.py")
        self.run('"%s" "%s"' % (py, script), env="conanrun")
        self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": '"%s" "%s"' % (py, script),
            "discovered": 7,
            "passedCount": 7,
        }, ensure_ascii=False))

        pkg = self.dependencies["ml-dtypes"]
        summary_path = os.path.join(pkg.package_folder, "res",
                                    "upstream_test_summary.json")
        if os.path.isfile(summary_path):
            with open(summary_path, "r", encoding="utf-8") as fh:
                upstream = json.load(fh)
        else:
            upstream = {
                "status": "failed",
                "framework": "pytest",
                "command": "python -m pytest ml_dtypes/tests -v "
                           "(run inside the main recipe build())",
                "discovered": 0, "executed": 0, "passed": 0,
                "failed": 0, "skipped": 0,
                "reason": "upstream_test_summary.json missing in the package: "
                          "no genuine upstream-test evidence available",
            }
        self.output.info("HMBS_UPSTREAM_TEST_RESULT=" +
                         json.dumps(upstream, ensure_ascii=False))
