#!/usr/bin/env python3
"""test_package for kylin-cloud-ai-engine-plugin 1.1.0.2.

Consumer end-to-end smoke (HarmonyOS-specific): build a tiny dlopen
harness and load the 4 shipped plugin .so files from
lib/kylin-ai/plugins/ai-engines/ with RTLD_NOW — the exact consumption
path of the Kylin AI engine loader. VirtualRunEnv provides
LD_LIBRARY_PATH for the bare-name DT_NEEDED (libcurl.so,
libc++_shared.so) of the plugins.
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class KylinAiPluginTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # The real consumer host links jsoncpp itself; link it into the
        # harness so Json:: symbols are in the global scope for the
        # dlopen()ed plugins.
        self.requires("jsoncpp/1.9.8")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        pkg = self.dependencies["kylin-cloud-ai-engine-plugin"]
        plugin_dir = os.path.join(
            pkg.package_folder, "lib", "kylin-ai", "plugins", "ai-engines"
        )
        if not os.path.isdir(plugin_dir):
            raise ConanException("plugin dir not found: " + plugin_dir)
        tc.variables["KYLIN_PLUGIN_DIR"] = plugin_dir
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        test_bin = os.path.join(self.cpp.build.bindir, "test_kylinai")
        self.run('"{}"'.format(test_bin), env="conanrun")
