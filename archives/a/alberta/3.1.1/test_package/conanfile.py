#!/usr/bin/env python3
"""Conan test_package for alberta 3.1.1 -- exercises the real public API.

Builds test.c (generate_filename / MEM_ALLOC+MEM_FREE / parameter
round-trip, 3 checks against libalberta_utilities) with the compiler and
dependency flags from the Conan graph, runs it, and emits the
HMBS_TEST_PACKAGE_RESULT marker with the real case counts.
"""
import json
import os
import shutil

from conan import ConanFile
from conan.tools.build import cross_building


class AlbertaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Collect -I/-L/-l from alberta plus its transitive deps (tirpc).
        # Headers install to include/alberta/; add that subdir as well.
        incs = []
        libdirs = []
        libs = []
        for _ref, _d in self.dependencies.items():
            pf = getattr(_d, "package_folder", None) or ""
            for p in _d.cpp_info.includedirs:
                full = p if (os.path.isabs(p) or not pf) else os.path.join(pf, p)
                incs.append(full)
                sub = os.path.join(full, "alberta")
                if os.path.isdir(sub):
                    incs.append(sub)
            for p in _d.cpp_info.libdirs:
                libdirs.append(p if (os.path.isabs(p) or not pf) else os.path.join(pf, p))
            libs.extend(_d.cpp_info.libs)
        inc = " ".join(dict.fromkeys("-I" + i for i in incs))
        libdir_flags = " ".join(dict.fromkeys("-L" + l for l in libdirs if l))
        lib_flags = " ".join("-l" + l for l in libs if l)
        cc = os.environ.get("CC") or "clang"
        # lib_flags already carries the 16 alberta libs in link order
        # plus -ltirpc from the transitive dependency; -lm last for the
        # math helpers (sqrt in dnrm2).
        self.run(
            "{} test.c -o test_alberta {} {} {} -lm".format(
                cc, inc, libdir_flags, lib_flags),
            env="conanbuild",
        )

    def test(self):
        if cross_building(self):
            self.output.info("cross-building: build only, skip run")
            return
        # OHOS: /system/bin/sh (mksh) cannot execute ELF binaries
        # directly, so wrap execution with a verified shell. Never trust a
        # poisoned CONFIG_SHELL blindly: the preflight profile exports
        # /data/service/hnp/bin/bash which is inaccessible on some workers
        # (m4 configure[139] Error 127 signature); accept an absolute path
        # only after existence + exec-bit verification, else /bin/sh.
        shell = None
        for cand in (os.environ.get("CONFIG_SHELL"),
                     os.environ.get("SHELL"),
                     "/bin/sh", "/system/bin/sh"):
            if not cand:
                continue
            if os.path.isabs(cand):
                if os.path.isfile(cand) and os.access(cand, os.X_OK):
                    shell = cand
                    break
            elif shutil.which(cand):
                shell = shutil.which(cand)
                break
        if shell is None:
            shell = shutil.which("sh") or shutil.which("bash") or "/bin/sh"
        command = "{} -c ./test_alberta".format(shell)
        # 3 explicit checks in test.c (see MANIFEST.yml).
        result = {"executed": True, "passed": False, "command": command,
                  "discovered": 3, "passedCount": 0}
        try:
            self.run(command, env="conanrun")
        except Exception:
            self.output.info("HMBS_TEST_PACKAGE_RESULT="
                             + json.dumps(result, ensure_ascii=False))
            raise
        result["passed"] = True
        result["passedCount"] = 3
        self.output.info("HMBS_TEST_PACKAGE_RESULT="
                         + json.dumps(result, ensure_ascii=False))
