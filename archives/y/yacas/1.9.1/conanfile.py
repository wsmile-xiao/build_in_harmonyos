#!/usr/bin/env python3
"""Conan recipe for yacas 1.9.1 — Yet Another Computer Algebra System.

yacas (grzegorzmazur/yacas) is a C++ computer algebra system: libyacas
engine + yacas console.  CMake build (upstream min 3.10, fine with
CMake 4.x).  The console needs its script library at runtime, so the
package ships share/yacas/scripts and tests always pass --rootdir.

Platform notes:
- GUI (Qt) / Jupyter kernel / Java engine are all OFF — console + libs
  only (Qt is not on this platform).
- LD_LIBRARY_PATH is explicitly emptied during build (lld/libxml2
  shield — CI-021 build #48068, mechanism in libodfgen/libabw).
- Upstream tests: 53 .yts scripts registered with ctest (driven by the
  upstream test-yacas runner against the build-tree scripts dir), plus
  the optional C++ unit tests (ENABLE_CYACAS_UNIT_TESTS=ON).  ctest
  output is redirected to a file (orphaned test processes holding a
  pipe would block conan forever — yash lesson) and the per-test tally
  is parsed into the log.
"""

import os
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class YacasConan(ConanFile):
    name = "yacas"
    version = "1.9.1"
    description = ("yacas - Yet Another Computer Algebra System: "
                   "libyacas engine + yacas console")
    license = "LGPL-2.1-or-later"
    homepage = "https://github.com/grzegorzmazur/yacas"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # GTest is only used by the engine unit tests built during
        # build() (never packaged) — invisible to consumers.
        self.requires("gtest/1.17.0.2", visible=False)

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"yacas is adapted for Linux and OHOS, not {self.settings.os}"
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        # url may arrive as a candidate list (the CI pre-download step
        # rewrites conandata's url into [mirror, official]) — conan's
        # get() handles both shapes natively.
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["ENABLE_CYACAS_CONSOLE"] = True
        tc.cache_variables["ENABLE_CYACAS_GUI"] = False
        tc.cache_variables["ENABLE_CYACAS_KERNEL"] = False
        tc.cache_variables["ENABLE_JYACAS"] = False
        tc.cache_variables["ENABLE_DOCS"] = False
        tc.cache_variables["ENABLE_CYACAS_UNIT_TESTS"] = True
        tc.cache_variables["ENABLE_CYACAS_BENCHMARKS"] = False
        # CMake has no Platform/HarmonyOS module (E092), so the builtin
        # UNIX variable stays unset and upstream's `if (UNIX)` picks the
        # Win32 console sources (windows.h).  Pin it on explicitly.
        tc.cache_variables["UNIX"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        # lld/libxml2 shield — see class docstring.
        shield = Environment()
        shield.define("LD_LIBRARY_PATH", "")
        with shield.vars(self).apply():
            cmake = CMake(self)
            cmake.configure()
            cmake.build(build_tool_args=["-j2"])
            self._run_upstream_tests()

    def _run_upstream_tests(self):
        """Run upstream's ctest suite (53 .yts scripts + unit tests).

        Output goes to a file, not the inherited stdout (orphaned test
        processes holding a pipe block conan forever — yash lesson).
        """
        log = os.path.join(self.build_folder, "ctest-run.log")
        with open(log, "w") as sink:
            subprocess.run(
                "ctest --output-on-failure --timeout 300; echo CTEST_RC=$?",
                shell=True, cwd=self.build_folder,
                stdout=sink, stderr=subprocess.STDOUT)
        subprocess.run("pkill -9 -f 'test-yacas' 2>/dev/null; true",
                       shell=True)
        with open(log, errors="replace") as handle:
            content = handle.read()
        for line in content.splitlines():
            if "tests passed" in line or "tests failed" in line:
                self.output.info("[upstream-tests] " + line.strip())
        self.output.info("[upstream-tests] ctest log tail:")
        for line in content.splitlines()[-15:]:
            self.output.info("[ctest] " + line)

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "yacas")
        self.cpp_info.set_property("cmake_target_name", "yacas::yacas")
        self.cpp_info.set_property("pkg_config_name", "yacas")
        self.cpp_info.libs = ["yacas", "yacas_mp"]
