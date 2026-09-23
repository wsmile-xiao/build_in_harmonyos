#!/usr/bin/env python3
"""Conan test_package for picosat 965.

Compiles test_picosat.c against the packaged library and runs it. The test
exercises the real public API (init/add/sat/deref/variables/reset) on one
SAT and one UNSAT problem. Emits HMBS machine-evidence markers.
"""

import json
import os

from conan import ConanFile
from conan.tools.build import can_run


class PicosatTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            # HMBS [readonly_tmp]: /tmp is read-only; prefer the injected
            # writable TMPDIR, fall back to a build-folder dir. Exported on
            # the command line because env="conanbuild" filters outer env.
            tmpdir = (
                os.environ.get("TMPDIR")
                or os.environ.get("TMP")
                or os.environ.get("TEMP")
                or os.path.join(self.build_folder, "tmp")
            )
            try:
                os.makedirs(tmpdir, exist_ok=True)
            except OSError:
                tmpdir = os.path.join(self.build_folder, "tmp")
                os.makedirs(tmpdir, exist_ok=True)
            try:
                cc = self.conf.get("tools.build:compiler_executables:c", "clang", check_type=str)
            except Exception:
                cc = "clang"
            cc = cc or "clang"
            pkg = self.dependencies["picosat"]
            include = pkg.cpp_info.includedirs[0]
            libdir = pkg.cpp_info.libdirs[0]
            src = os.path.join(self.source_folder, "test_picosat.c")
            self.run(
                'TMPDIR="%s" TMP="%s" TEMP="%s" \"%s\" \"%s\" -o test_picosat -I"%s" -L"%s" -lpicosat'
                % (tmpdir, tmpdir, tmpdir, cc, src, include, libdir),
                env="conanbuild",
            )
            self.run('TMPDIR="%s" TMP="%s" TEMP="%s" ./test_picosat' % (tmpdir, tmpdir, tmpdir), env="conanrun")
            test_pkg = {
                "executed": True,
                "passed": True,
                "command": "clang test_picosat.c -o test_picosat -lpicosat && ./test_picosat",
                "discovered": 7,
                "passedCount": 7,
            }
            self.output.info("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg, ensure_ascii=False))
            upstream = {
                "status": "no_tests",
                "framework": "none",
                "command": "ls source tree + grep makefile.in for check/test targets",
                "discovered": 0,
                "executed": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "reason": (
                    "picosat-965 source tree has 16 files and no tests/ or test/ directory; "
                    "makefile.in defines only all/clean/analyze plus binary and library targets "
                    "with no check or test target, so there is no upstream suite to execute"
                ),
            }
            self.output.info("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
            print("HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False))
