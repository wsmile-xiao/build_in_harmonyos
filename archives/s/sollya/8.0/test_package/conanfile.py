#!/usr/bin/env python3
"""test_package for sollya 8.0.

Consumer-level verification (R34 / device-facts §2.19): run the **installed**
command-line tool on the target platform and assert the *fingerprint the
artefact reports about itself*.

The assertions live in the standalone test source ``check_version.sh``:

* CI gate **L0c** (``ci/conan/build_and_test.sh``, ``no_test_sources``)
  requires at least one real test source file (``.c/.cpp/.cc/.cxx/.sh/.py``)
  directly under ``test_package/``.  The first version kept every assertion in
  this Python file, so ``test_package/`` contained only ``conanfile.py`` +
  ``MANIFEST.yml`` and ``finish`` step 5 (W3 local CI simulation) failed with
  ``L0c: No test source files in test_package/`` (finish EXIT_CODE=2 resumable).
* The script is **actually invoked** below through ``self.run(...)``, so it is
  not a dead file parked to satisfy the gate — ``L0d`` also still holds because
  ``test()`` exists and contains a ``self.run()`` call.

``check_version.sh`` writes the raw ``sollya --version`` output (84 lines /
3085 bytes measured on device in verification round 5) into the test build
folder and greps the four self-reported fingerprints:

  1. ``This is sollya 8.0``                              (PACKAGE_STRING)
  2. ``based on GMP 6.3.0, MPFR 4.2.2 and MPFI 1.5.4.``  (three linked deps)
  3. ``It uses FPLLL as:``                               (--with-fplll effect)
  4. ``CeCILL-C``                                        (license cross-check)

The library-consumer dimension (linking ``-lsollya`` with ``<sollya.h>``) is
already covered by upstream tests-lib's 348 programs inside build() via
``make check``, so no hand-rolled link line is duplicated here (hand-aggregating
6 dependency -I/-L/-l is exactly the kind of untested format string that costs
an extra verify round).
"""

import os
import shutil

from conan import ConanFile
from conan.tools.layout import basic_layout


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # Nothing to compile: the artefact under test is the installed CLI
        # (bin/sollya), linked against libsollya + gmp/mpfr/mpfi/fplll/
        # libxml2/zlib.  Running it exercises header install, library
        # install, loader wiring and transitive deps at once.
        pass

    def test(self):
        # Standalone test source (CI L0c) — really executed here (L0d).
        # check_version.sh runs `sollya --version` under env="conanrun" (which
        # supplies the three runtime shared libs libfplll.so.9 / libxml2.so.16
        # / libmpfi.so.0), saves the raw output to $1 and asserts the 4
        # self-reported fingerprints; a non-zero exit fails conan's test stage.
        #
        # Inline SDK llvm/lib prefix, same rationale as the main recipe's
        # build() (PR #12419 CI build #59839): conanrunenv *prepends* the
        # conan libxml2 package dir ahead of the profile-injected llvm/lib,
        # and musl hard-fails on an unloadable same-named libxml2.so.16
        # without falling back — the installed bin/sollya DT_NEEDEDs
        # libxml2.so.16, so without this prefix the consumer would die on the
        # same worker with "Error loading shared library libxml2.so.16".
        # test_package is its own package, so the (compact) derivation is
        # duplicated here rather than imported from the main conanfile.
        script = os.path.join(self.source_folder, "check_version.sh")
        out_txt = os.path.join(self.build_folder, "sollya-version.txt")
        cmd = "sh {} {}".format(script, out_txt)
        libdir = self._sdk_xml2_libdir()
        if libdir:
            cmd = ('LD_LIBRARY_PATH="%s${LD_LIBRARY_PATH:+:$LD_LIBRARY_PATH}" %s'
                   % (libdir, cmd))
        self.run(cmd, env="conanrun")

    def _sdk_xml2_libdir(self):
        """<sdk>/llvm/lib when it really contains libxml2.so.16, else None
        (realpath the compiler first — it is a symlink into the SDK)."""
        exe = self.conf.get("tools.build:compiler_executables")
        candidates = [exe["c"]] if isinstance(exe, dict) and exe.get("c") else []
        for name in ("clang", "clang-15"):
            path = shutil.which(name)
            if path:
                candidates.append(path)
                break
        for c in candidates:
            real = os.path.realpath(c)
            libdir = os.path.normpath(
                os.path.join(os.path.dirname(real), "..", "lib"))
            if os.path.isfile(os.path.join(libdir, "libxml2.so.16")):
                return libdir
        return None
