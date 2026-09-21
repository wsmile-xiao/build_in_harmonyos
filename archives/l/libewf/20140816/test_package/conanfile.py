#!/usr/bin/env python3
"""Consumer tests for the packaged libewf library.

Builds test_libewf.c against the installed libewf (version string,
access flags, handle lifecycle, file-signature negative check) and
runs it. Emits the HMBS_TEST_PACKAGE_RESULT marker with the real
assertion count, then re-emits HMBS_UPSTREAM_TEST_RESULT from the
packaged res/upstream_test_result.json (the exact payload build()
produced) so the marker survives cached builds where conan skips
build(). Missing or invalid res file is a hard error: refusing to
pass silently (libbde/20240502 pattern).
"""

import json
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import replace_in_file


class LibewfTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def _usable_compiler(self, key, fallbacks):
        """PATH-first compiler for stale profile paths (libbde/20240502 precedent).

        The profile may bake CMAKE_C_COMPILER=/data/service/hnp/bin/clang,
        which is inaccessible in some preflight sandboxes; HMBS prepends
        the real tool dirs to PATH, so prefer an absolute conf path only
        when it exists and is executable, else PATH lookup.
        """
        try:
            compilers = self.conf.get(
                "tools.build:compiler_executables", default={}, check_type=dict
            ) or {}
        except Exception:
            compilers = {}
        cand = compilers.get(key) if isinstance(compilers, dict) else None
        if cand and os.path.isabs(str(cand)):
            try:
                if os.path.isfile(str(cand)) and os.access(str(cand), os.X_OK):
                    return str(cand)
            except Exception:
                pass
        for name in fallbacks:
            try:
                found = shutil.which(name)
            except Exception:
                found = None
            if found:
                try:
                    if os.path.isfile(found) and os.access(found, os.X_OK):
                        return found
                except Exception:
                    continue
        if cand and str(cand):
            return str(cand)
        return fallbacks[0]

    def build(self):
        # The generated conan_toolchain.cmake can embed a stale
        # CMAKE_C_COMPILER (/data/service/hnp/bin/clang) that does not
        # exist on the preflight image; override with a PATH-discovered
        # compiler so test_package configures (libbde/20240502 precedent).
        cc = self._usable_compiler("c", ["clang", "cc"])
        cxx = self._usable_compiler("cpp", ["clang++", "c++", "g++"])
        self.output.info("test_package CC=%s CXX=%s" % (cc, cxx))
        toolchain = os.path.join(self.generators_folder, "conan_toolchain.cmake")
        if os.path.isfile(toolchain):
            # Replace the longer clang++ path first so the clang
            # replacement cannot corrupt it into "<cc>++".
            for stale, new in (
                ("/data/service/hnp/bin/clang++", cxx),
                ("/data/service/hnp/bin/clang", cc),
            ):
                try:
                    replace_in_file(self, toolchain, stale, new)
                except Exception:
                    pass
        cmake = CMake(self)
        cmake.configure(variables={"CMAKE_C_COMPILER": cc,
                                   "CMAKE_CXX_COMPILER": cxx})
        cmake.build()

    def test(self):
        if can_run(self):
            cmd = os.path.join(self.cpp.build.bindirs[0], "test_libewf")
            # 6 assertions defined in test_libewf.c / MANIFEST.yml
            test_pkg = {
                "executed": True,
                "passed": True,
                "command": cmd,
                "discovered": 6,
                "passedCount": 6,
            }
            try:
                self.run(cmd, env="conanrun")
            except Exception:
                test_pkg["passed"] = False
                test_pkg["passedCount"] = 0
                tp_msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg)
                print(tp_msg, flush=True)
                self.output.info(tp_msg)
                raise
            tp_msg = "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(test_pkg)
            print(tp_msg, flush=True)
            self.output.info(tp_msg)

            dep = self.dependencies["libewf"]
            result_path = os.path.join(
                dep.package_folder, "res", "upstream_test_result.json")
            if not os.path.isfile(result_path):
                raise ConanException(
                    "upstream_test_result.json not found in package (%s): "
                    "upstream tests did not run during build(); refusing to "
                    "pass silently" % result_path)
            with open(result_path, "r", encoding="utf-8") as f:
                upstream = json.load(f)
            for _k in ("status", "discovered", "executed", "passed",
                       "failed", "skipped", "reason"):
                if _k not in upstream:
                    raise ConanException(
                        "upstream_test_result.json missing key %s: refusing "
                        "to pass silently" % _k)
            up_msg = "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream)
            print(up_msg, flush=True)
            self.output.info(up_msg)
