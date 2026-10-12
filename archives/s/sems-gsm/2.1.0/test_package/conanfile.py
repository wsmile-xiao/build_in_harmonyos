#!/usr/bin/env python3
"""Conan test_package for sems-gsm 2.1.0 (SEMS + GSM 06.10 codec plug-in).

R34: the consumer exercises the *tested package* itself — it dlopen()s the
package's own plug-in (lib/sems/plug-in/gsm.so) the way the SEMS loader
does, looks up the plug-in ABI entry (amci_exports) and the codec symbols
the plug-in carries, runs a GSM 06.10 round trip through them, and
smoke-runs the packaged sbin/sems.  A package without its plug-in (or with
a renamed/broken plug-in symbol) cannot pass this test.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment


class SemsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        # application package: nothing propagates through cpp_info, the
        # consumer uses the package layout (plug-in + sbin) at test time
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        pkg = self.dependencies["sems-gsm"].package_folder
        env = Environment()
        env.define("SEMS_PACKAGE_FOLDER", pkg)
        env.prepend_path("LD_LIBRARY_PATH", os.path.join(pkg, "lib"))
        # the packaged plug-in/sems link conan deps (libevent/libgsm)
        for dep in self.dependencies.values():
            if dep and dep.package_folder:
                env.prepend_path(
                    "LD_LIBRARY_PATH", os.path.join(dep.package_folder, "lib"))
        if self.settings.os == "OHOS":
            env.prepend_path("LD_LIBRARY_PATH", "/system/lib64")

        with env.vars(self).apply():
            self.run(os.path.join(self.cpp.build.bindirs[0],
                                  "test_sems_consumer"))
            # CLI smoke test: the packaged server prints its version banner.
            # `sems -v` keeps running (server semantics), so bound the run and
            # assert on the captured banner text instead of the exit status.
            log_path = os.path.join(self.build_folder, "sems-cli-smoke.log")
            sems = os.path.join(pkg, "sbin", "sems")
            self.run(
                'if command -v timeout >/dev/null 2>&1; then '
                'timeout 10 "{s}" -v > "{l}" 2>&1 || true; '
                'else "{s}" -v > "{l}" 2>&1 & p=$!; sleep 3; '
                'kill $p 2>/dev/null || true; wait $p 2>/dev/null || true; fi'
                .format(s=sems, l=log_path))
            self.run('grep -q "Sip Express Media Server (2.1.0" "{}"'.format(
                log_path))
