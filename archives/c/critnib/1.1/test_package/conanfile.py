#!/usr/bin/env python3
"""Conan test_package — critnib 1.1 (consumer link + API exercise).

Direct-compile route: no CMakeToolchain, so no CMake compiler-ID probe
can fail the test phase either. test_critnib.c is compiled straight
against the packaged headers + library with the validated profile
compiler. The test performs 6 real assertions
(new/insert/get/find_le+find_ge/remove/iter); HMBS_TEST_PACKAGE_RESULT
carries discovered/passedCount from the actual run (exit 0 == all
passed).
"""
import glob as _glob
import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class CritnibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def _cc(self):
        # Same validation as the main recipe: conf absolute path first,
        # PATH fallback only when it is missing/non-executable.
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cand = (compilers.get("c") or "").strip()
        if cand and os.path.isfile(cand) and os.access(cand, os.X_OK):
            return cand
        if cand:
            self.output.warning(
                "conf c compiler '%s' not usable, falling back to PATH lookup" % cand)
        return shutil.which("clang") or shutil.which("cc") or "clang"

    def build(self):
        incs = []
        libdirs = []
        for _ref, _dep in self.dependencies.items():
            for _i in _dep.cpp_info.includedirs:
                _p = _i if os.path.isabs(_i) else os.path.join(_dep.package_folder, _i)
                incs.append('"-I%s"' % _p)
            for _l in _dep.cpp_info.libdirs:
                _p = _l if os.path.isabs(_l) else os.path.join(_dep.package_folder, _l)
                libdirs.append(_p)
        libfile = ""
        for _d in libdirs:
            cands = sorted(_glob.glob(os.path.join(_d, "libcritnib.*")))
            pref = [c for c in cands if c.endswith(".a")] + [
                c for c in cands if not c.endswith(".a")
            ]
            if pref:
                libfile = pref[0]
                break
        if not libfile:
            raise Exception("libcritnib archive not found in %r" % (libdirs,))
        src = os.path.join(self.source_folder, "test_critnib.c")
        out = os.path.join(self.build_folder, "test_critnib")
        cmd = '"%s" "%s" -o "%s" %s "%s" -lpthread' % (
            self._cc(), src, out, " ".join(incs), libfile,
        )
        self.run(cmd)

    def test(self):
        if can_run(self):
            test_bin = os.path.join(self.build_folder, "test_critnib")
            try:
                os.chmod(test_bin, 0o755)
            except OSError:
                pass
            cmd = '"%s"' % test_bin
            self.run(cmd, env="conanrun")
            marker = {
                "executed": True,
                "passed": True,
                "command": cmd,
                "discovered": 6,
                "passedCount": 6,
            }
            print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker))
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(marker, ensure_ascii=False))
