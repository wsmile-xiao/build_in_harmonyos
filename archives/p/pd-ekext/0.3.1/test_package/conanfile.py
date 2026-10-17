#!/usr/bin/env python3
"""test_package for pd-ekext 0.3.1 -- functional consumer test.

pd-ekext installs 43 Pure Data externals as dlopen()-able shared objects and
nothing else: there is no library to link against and no command line program
to execute.  The test therefore does what Pd itself does when a patch
instantiates one of these objects:

  1. compiles ``pd_ekext_test.c`` for the *same* target as the package, against
     the Pd API headers that pd-ekext re-exports through ``cpp_info``
     (puredata/0.54.1 is an application and publishes no include dirs itself);
  2. links it with ``-rdynamic`` so it exports the Pure Data runtime shim the
     externals import -- this is exactly how a ``pd`` executable satisfies them;
  3. runs it against the packaged ``lib/pd-externals/ekext`` directory.

For every one of the 43 externals the program dlopen()s it with
``RTLD_NOW | RTLD_LOCAL`` (proving every Pd symbol it imports is satisfiable
from the loading image, and only from Pd), calls its ``setup()`` and checks
that a Pd class with the expected name, a non-zero instance size and at least
one method got registered.  It then instantiates four externals through the
creation function Pd would call and asserts the exact values their real
methods emit on their outlets.

The program exits non-zero if any check fails, so ``conan create`` fails the
package.
"""
import json
import os
import shutil
import tempfile

from conan import ConanFile
from conan.errors import ConanException


class PdEkextTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    @staticmethod
    def _workdir():
        """Writable scratch directory outside the archive tree.

        E002: /tmp may be read-only, so prefer TMPDIR and then ~/tmp, matching
        the mktemp convention used by the other test_package probes.
        """
        for root in (os.environ.get("TMPDIR"),
                     os.path.join(os.path.expanduser("~"), "tmp")):
            if root:
                try:
                    os.makedirs(root, exist_ok=True)
                    return tempfile.mkdtemp(prefix="pd-ekext-test-", dir=root)
                except OSError:
                    continue
        return tempfile.mkdtemp(prefix="pd-ekext-test-")

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        ext_dir = os.path.join(dep.package_folder, "lib", "pd-externals", "ekext")
        if not os.path.isdir(ext_dir):
            raise ConanException("packaged externals dir not found: %s" % ext_dir)

        include_dirs = [d for d in (dep.cpp_info.includedirs or [])
                        if os.path.isfile(os.path.join(d, "m_pd.h"))]
        if not include_dirs:
            raise ConanException(
                "pd-ekext did not export the Pd API headers "
                "(includedirs=%s)" % list(dep.cpp_info.includedirs or []))

        # R33: compiler comes from the Conan profile conf, never from ${CC}.
        executables = self.conf.get("tools.build:compiler_executables",
                                    default={}, check_type=dict)
        cc = executables.get("c") or "clang"

        workdir = self._workdir()
        binary = os.path.join(workdir, "pd_ekext_test")
        try:
            includes = " ".join('-I"%s"' % d for d in include_dirs)
            self.run(
                '%s -std=gnu11 -O1 -Wall -Wextra -rdynamic %s "%s" -o "%s" -ldl -lm'
                % (cc, includes,
                   os.path.join(self.source_folder, "pd_ekext_test.c"), binary))
            rc = self.run('"%s" "%s"' % (binary, ext_dir), env="conanrun",
                          ignore_errors=True)
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": (rc == 0),
            "command": ("pd_ekext_test (dlopen+setup all 43 externals; drive "
                        "positive/cup/doubledelta/list_sum)"),
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "skipped",
            "reason": ("pd-ekext ships no automated test suite: upstream has no "
                       "make check target, only Pd help patches and two demo "
                       "patches (maskxor-test.pd, test_scalefilter.pd, "
                       "isoWrap~-test.pd) that need a running Pd"),
            "discovered": 0, "executed": 0, "passed": 0, "failed": 0, "skipped": 0,
        }))
        if rc != 0:
            raise ConanException("pd-ekext test failed (rc=%s)" % rc)