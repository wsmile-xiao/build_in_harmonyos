#!/usr/bin/env python3
"""Conan test_package for pd-flext 0.6.4.

Builds a real flext-based Pd external against the installed pd-flext package
(framework library + headers) with the matching compile-time ABI selector
``-DFLEXT_SHARED``, then loads it with the OHOS ``pd`` from the puredata
package and drives it headlessly.  The external posts deterministic markers:
``FLEXT_TEST_INIT: 100`` at construction and ``FLEXT_TEST_RESULT: 105`` after
``100 + 5``, and its outlet reaches ``[print]`` as ``FLEXT_TEST: 105``.
"""
import json
import os
import shlex

from conan import ConanFile
from conan.errors import ConanException

CHECKS = 3


class PdFlextTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        self.requires("puredata/0.54.1")

    def _cpp(self):
        exe = self.conf.get("tools.build:compiler_executables",
                            default={}, check_type=dict) or {}
        return exe.get("cpp") or "clang++"

    def _bash(self):
        for candidate in (
            os.environ.get("CONFIG_SHELL"),
            "/storage/Users/currentUser/.harmonybrew/bin/bash",
            "/data/service/hnp/bin/bash",
            "/bin/bash",
        ):
            if candidate and os.path.isfile(candidate):
                return candidate
        return "bash"

    def test(self):
        dep = self.dependencies[self.tested_reference_str]
        pkg = dep.package_folder
        inc_flext = os.path.join(pkg, "include", "flext")
        inc_pd = os.path.join(pkg, "include", "puredata")
        libdir = os.path.join(pkg, "lib")
        pd_bin = os.path.join(self.dependencies["puredata"].package_folder,
                              "bin", "pd")
        for path in (pd_bin, os.path.join(libdir, "libflext-pd.so")):
            if not os.path.isfile(path):
                raise ConanException("required artifact not found: %s" % path)

        here = os.path.dirname(os.path.abspath(__file__))
        outdir = os.path.join(self.build_folder, "ext")
        os.makedirs(outdir, exist_ok=True)
        ext = os.path.join(outdir, "flextest.pd_linux")
        compile_cmd = (
            '%s -shared -fPIC -O2 -std=c++17 -DFLEXT_SYS=2 -DFLEXT_SHARED '
            '-pthread -I%s -I%s -o %s %s -L%s -lflext-pd'
            % (shlex.quote(self._cpp()), shlex.quote(inc_flext),
               shlex.quote(inc_pd), shlex.quote(ext),
               shlex.quote(os.path.join(here, "test_flext.cpp")),
               shlex.quote(libdir)))
        self.run(compile_cmd, env="conanbuild")

        workdir = os.environ.get("TMPDIR") or os.path.join(
            os.path.expanduser("~"), "tmp")
        os.makedirs(workdir, exist_ok=True)
        inner = ('PD_BIN=%s EXT_DIR=%s PATCH=%s FLEXT_LIBDIR=%s TMPDIR=%s sh %s'
                 % (shlex.quote(pd_bin), shlex.quote(outdir),
                    shlex.quote(os.path.join(here, "test_pd_flext.pd")),
                    shlex.quote(libdir), shlex.quote(workdir),
                    shlex.quote(os.path.join(here, "test_pd_flext.sh"))))
        if self.settings.os == "OHOS":
            command = "%s -c %s" % (shlex.quote(self._bash()), shlex.quote(inner))
        else:
            command = inner
        rc = self.run(command, ignore_errors=True, env="conanrun")

        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": (rc == 0),
            "command": "test_pd_flext.sh (pd loads a flext-built external)",
            "consumer_passed": CHECKS if rc == 0 else 0,
            "consumer_total": CHECKS,
        }))
        print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps({
            "status": "skipped",
            "reason": "pd-flext ships no automated test suite (only the "
                      "tutorial externals under tutorial/)",
            "discovered": 0, "executed": 0, "passed": 0, "failed": 0,
            "skipped": 0,
        }))

        if rc != 0:
            raise ConanException("pd-flext test failed (rc=%s)" % rc)
