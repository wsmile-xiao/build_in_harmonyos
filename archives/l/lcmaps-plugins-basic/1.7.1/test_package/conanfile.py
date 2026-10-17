#!/usr/bin/env python3
"""Conan test_package for lcmaps-plugins-basic 1.7.1 — OHOS consumer smoke verification.

Builds test_lcmaps_plugins_basic (C, dlopen-based) against the packaged plugin
modules and runs it with the package root as argument. See test.c for the
covered adaptation points.
"""
import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class LcmapsPluginsBasicTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = self.dependencies["lcmaps-plugins-basic"]
        fw = self.dependencies["lcmaps"]
        tc = CMakeToolchain(self)
        tc.variables["LCMAPS_TEST_ROOT"] = deps.package_folder
        tc.variables["LCMAPS_TEST_FW_ROOT"] = fw.package_folder
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            return
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_lcmaps_plugins_basic")
        pkg_path = self.dependencies["lcmaps-plugins-basic"].package_folder
        fw_pkg = self.dependencies["lcmaps"].package_folder
        # The test binary and the plugins carry DT_NEEDED entries for the
        # framework (liblcmaps_without_gsi.so.0) and, for ldap_enf, libldap
        # (and its own closure). conanrun does not export LD_LIBRARY_PATH for
        # this graph, so build it from every host dependency libdir.
        libdirs = []
        for _, dep in self.dependencies.host.items():
            if not getattr(dep, "package_folder", None):
                continue
            dirs = list(dep.cpp_info.libdirs)
            for comp in (getattr(dep.cpp_info, "components", None) or {}).values():
                dirs.extend(comp.libdirs)
            for d in dirs:
                libdirs.append(d if os.path.isabs(d) else os.path.join(dep.package_folder, d))
        ldlp = ":".join(dict.fromkeys(libdirs))
        self.run(
            "LD_LIBRARY_PATH='%s' '%s' '%s' '%s'" % (ldlp, bin_path, pkg_path, fw_pkg),
            env="conanrun",
        )
