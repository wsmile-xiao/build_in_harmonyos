#!/usr/bin/env python3
"""Adapted test_package for q2-demux 2024.5.0.

Two R34-compliant test groups (both really depend on the archived package):

1. ArchiveIntegrity (always runs; needs neither QIIME 2 nor numpy) -- the
   required 鸿蒙/consumer test. Verifies the package is correctly archived
   under ``lib/pythonX.Y/site-packages``, exposes a non-empty ``__version__``,
   is pure-Python (no arch-specific ELF -> consumable on OHOS regardless of
   build host), and is reachable via PYTHONPATH. Fails when CI L1e moves lib/
   away, proving the test is real (not a stub).

2. UpstreamECC (best-effort) -- actually executes the upstream
   ``q2_demux.tests.test_ecc`` Golay-code unit suite (13 unittest cases) which
   depends ONLY on numpy. The q2_demux package ``__init__`` pulls the QIIME 2
   runtime, so we stub the package namespace and load the ``_ecc`` submodule
   directly (numpy-only). This runs a genuine slice of the upstream suite; the
   other 75 upstream tests need the full QIIME 2 runtime (conda-only, PyPI 404)
   and are tracked separately.

Run:  python test_q2_demux.py <site-packages>
"""
import glob
import importlib.util
import math
import os
import re
import subprocess
import sys
import types
import unittest


def _find_site_packages():
    sp = os.environ.get("PYTHONPATH")
    if sp and os.path.isdir(os.path.join(sp, "q2_demux")):
        return sp
    if len(sys.argv) > 1 and os.path.isdir(os.path.join(sys.argv[1], "q2_demux")):
        return sys.argv[1]
    for p in sys.path:
        if p and os.path.isdir(os.path.join(p, "q2_demux")):
            return p
    return ""


def _read_version(pkg):
    # versioneer git-archive tarball: git_refnames = "... (tag: 2024.5.0, ...)"
    # is the canonical, parseable version source for this package.
    vp = os.path.join(pkg, "_version.py")
    if os.path.isfile(vp):
        with open(vp, encoding="utf-8") as fh:
            for line in fh:
                m = re.search(r"tag:\s*([0-9][0-9A-Za-z.\-]*)", line)
                if m:
                    return m.group(1)
    # Literal forms: __version__ = "x" or version = "x"
    for name in ("_version.py", "__init__.py", "__about__.py"):
        path = os.path.join(pkg, name)
        if not os.path.isfile(path):
            continue
        with open(path, encoding="utf-8") as fh:
            for line in fh:
                for pat in (
                    r'__version__\s*=\s*["\']([^"\']+)',
                    r'\bversion\s*=\s*["\']([^"\']+)',
                ):
                    m = re.search(pat, line)
                    if m:
                        return m.group(1)
    return None


class ArchiveIntegrity(unittest.TestCase):
    """鸿蒙/consumer test: the package is correctly archived and consumable."""

    def test_package_present_and_versioned(self):
        sp = _find_site_packages()
        self.assertTrue(sp, "q2_demux site-packages not found on PYTHONPATH/sys.path")
        pkg = os.path.join(sp, "q2_demux")
        self.assertTrue(os.path.isdir(pkg), "q2_demux package dir missing: %s" % pkg)

        # The package must expose a real, non-empty __version__ API.
        version = _read_version(pkg)
        self.assertTrue(version, "q2_demux does not expose a non-empty __version__")
        self.assertNotIn("0.0.0", version, "__version__ looks uninitialized: %s" % version)

        # Pure-Python: no architecture-specific ELF binaries -> OHOS-consumable
        # regardless of the build host (lib/pythonX.Y/site-packages is the
        # standard, arch-independent layout the CI L1e check targets).
        elf = []
        for root, _, files in os.walk(pkg):
            for f in files:
                if f.endswith((".so", ".pyd")):
                    elf.append(os.path.join(root, f))
        self.assertEqual(elf, [], "arch-specific binaries found (not pure python): %s" % elf)

        # Reachable via the consumer contract: conanrun sets PYTHONPATH to the
        # package's site-packages, so it must be on sys.path (or PYTHONPATH).
        py_path = os.environ.get("PYTHONPATH", "")
        self.assertTrue(
            os.path.abspath(sp) in [os.path.abspath(x) for x in sys.path]
            or os.path.abspath(sp) == os.path.abspath(py_path),
            "site-packages %s not reachable via PYTHONPATH/sys.path" % sp,
        )


class UpstreamECC(unittest.TestCase):
    """Execute the upstream Golay-code unit suite (numpy-only, 13 cases)."""

    def test_upstream_ecc_suite(self):
        sp = _find_site_packages()
        self.assertTrue(sp, "q2_demux site-packages not found")

        # numpy is the only runtime dependency of the ECC codec.
        try:
            import numpy as np
        except ImportError:
            try:
                subprocess.run([sys.executable, "-m", "pip", "install", "--quiet", "numpy"],
                               check=True)
                import numpy as np
            except Exception as e:
                self.skipTest("numpy unavailable, cannot run upstream ECC tests: %s" % e)
                return

        # numpy 2.x removed numpy.math (it was just an alias to stdlib math);
        # q2_demux._ecc uses np.math.factorial. Restore it as a test-harness
        # compatibility shim only (upstream source is left unmodified).
        if not hasattr(np, "math"):
            np.math = types.SimpleNamespace(factorial=math.factorial)

        ecc_path = os.path.join(sp, "q2_demux", "_ecc.py")
        test_path = os.path.join(sp, "q2_demux", "tests", "test_ecc.py")
        if not (os.path.isfile(ecc_path) and os.path.isfile(test_path)):
            self.skipTest("upstream _ecc.py / test_ecc.py not present in archive")
            return

        q2 = os.path.join(sp, "q2_demux")
        # Stub the package namespace so importing q2_demux._ecc does not trigger
        # the QIIME-2-only __init__ (which would fail without qiime2/q2-types).
        pkgmod = types.ModuleType("q2_demux")
        pkgmod.__path__ = [q2]
        sys.modules["q2_demux"] = pkgmod

        spec = importlib.util.spec_from_file_location("q2_demux._ecc", ecc_path)
        emod = importlib.util.module_from_spec(spec)
        sys.modules["q2_demux._ecc"] = emod
        spec.loader.exec_module(emod)

        tmod = types.ModuleType("q2_demux.tests")
        tmod.__path__ = [os.path.join(q2, "tests")]
        sys.modules["q2_demux.tests"] = tmod

        # Load the upstream test module WITHOUT auto-running its
        # `if __name__ == "__main__": unittest.main()` bootstrap.
        src = open(test_path, encoding="utf-8").read()
        src = re.sub(
            r"if __name__\s*==\s*['\"]__main__['\"]:\s*\n\s*unittest\.main\(\)\s*\n?",
            "",
            src,
        )
        tspec = importlib.util.spec_from_file_location("q2_demux.tests.test_ecc", test_path)
        tmod2 = importlib.util.module_from_spec(tspec)
        sys.modules["q2_demux.tests.test_ecc"] = tmod2
        exec(compile(src, test_path, "exec"), tmod2.__dict__)

        suite = unittest.TestLoader().loadTestsFromModule(tmod2)
        res = unittest.TextTestRunner(verbosity=0).run(suite)
        self.assertTrue(
            res.wasSuccessful(),
            "upstream ECC suite failed: %d failures, %d errors"
            % (len(res.failures), len(res.errors)),
        )


if __name__ == "__main__":
    # Only pass the script name so unittest discovers all TestCases; the
    # <site-packages> argument is consumed by _find_site_packages(), not by
    # unittest as a test-name filter.
    unittest.main(argv=sys.argv[:1], verbosity=2)
