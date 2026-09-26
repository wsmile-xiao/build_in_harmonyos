#!/usr/bin/env python3
"""Conan test_package for tdlib 1.8.0 — real consumer build + OHOS checks.

The consumer program links the packaged `libtdjson.so` through the upstream
`Td::TdJson` CMake target and drives the public JSON/C API
(`td/telegram/td_json_client.h`) for real: it resolves the exported symbols
with dlsym(), asks the library to classify MIME types through the
gperf-generated tables, extracts text entities and spins up a full TDLib
client to read the `version` option back.

That makes the test substantively depend on the produced artifacts (R34):
removing `lib/libtdjson.so` from the package breaks the link, so the CI L1e
destructive check re-runs it as a genuine negative control.
"""

import json
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import VirtualRunEnv
from conan.tools.files import save


class TdlibTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()

        tc = CMakeToolchain(self)
        # Point find_package(Td) at the CMake package installed by the recipe
        # instead of relying on CMAKE_PREFIX_PATH search order.
        tc.cache_variables["Td_DIR"] = os.path.join(
            self.dependencies["tdlib"].package_folder, "lib", "cmake", "Td"
        ).replace("\\", "/")
        if self.settings.os == "OHOS":
            # CMake has no HarmonyOS platform module, so it neither emits
            # -Wl,-soname, nor knows how to embed a runtime path; the packaged
            # libtdjson.so.<version> would not be found by the loader.
            # Restore the ELF link rules and pin the consumer's RUNPATH to the
            # package library directory (same wiring as the cpr recipe).
            self._write_ohos_elf_rules(tc)
            tc.cache_variables["CMAKE_BUILD_RPATH"] = ";".join(
                self.dependencies["tdlib"].cpp_info.libdirs)
        tc.generate()

        VirtualRunEnv(self).generate()

    def _write_ohos_elf_rules(self, tc):
        for lang in ("C", "CXX"):
            rules = os.path.join(
                self.generators_folder, "ohos-elf-rules-%s.cmake" % lang.lower())
            save(self, rules, "\n".join((
                'set(CMAKE_SHARED_LIBRARY_SONAME_%s_FLAG "-Wl,-soname,")' % lang,
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_%s_FLAG "-Wl,-rpath,")' % lang,
                'set(CMAKE_SHARED_LIBRARY_RUNTIME_%s_FLAG_SEP ":")' % lang,
                'set(CMAKE_SHARED_LIBRARY_RPATH_LINK_%s_FLAG "-Wl,-rpath-link,")' % lang,
            )) + "\n")
            tc.cache_variables["CMAKE_USER_MAKE_RULES_OVERRIDE_%s" % lang] = rules

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info(
                "cross-building: tdlib consumer linked but cannot run on this host")
            return

        exe = os.path.join(self.cpp.build.bindirs[0], "test_tdlib")
        result = {
            "executed": True,
            "passed": True,
            "command": os.path.basename(exe),
        }
        try:
            self.run(exe.replace("\\", "/"), env="conanrun")
        except Exception:
            result["passed"] = False
            self.output.info(
                "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False))
            raise
        self.output.info(
            "HMBS_TEST_PACKAGE_RESULT=" + json.dumps(result, ensure_ascii=False))
