#!/usr/bin/env python3
"""Conan test_package — kea-hooks 3.0.3 (consumer view).

Builds and runs a real consumer of the packaged library: it links against
libkea-hooks.so and exercises the public hooks framework API (ServerHooks
registry, command/hook name mapping, HookLibInfo/extractNames).

A second, HarmonyOS-specific check (``test_ohos_platform``) verifies the parts
of the delivery that only exist for OHOS: the aarch64 / musl / libc++ ABI
signature of the packaged library, that the OHOS loader maps it with
RTLD_NOW, and that the OHOS-only consumer define the package exports
(``BOOST_SP_NO_PTHREAD_SETCANCELSTATE``) reaches the consumer compile line.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, cmake_layout


class KeaHooksTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info("cross-building: consumer test skipped")
            return
        bindir = self.cpp.build.bindirs[0]
        self.run('"{}/test_kea_hooks"'.format(bindir), env="conanrun")

        library = os.path.join(
            self.dependencies[self.tested_reference_str].package_folder,
            "lib", "libkea-hooks.so")
        self.run('"{}/test_ohos_platform" "{}"'.format(bindir, library),
                 env="conanrun")
