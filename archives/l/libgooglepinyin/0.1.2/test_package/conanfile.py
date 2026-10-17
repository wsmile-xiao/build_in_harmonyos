#!/usr/bin/env python3
"""Consumer test for libgooglepinyin 0.1.2: decode pinyin through the packaged library."""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout


class LibgooglepinyinTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            self.output.info(
                "Cross-built consumer compile/link passed; runtime decoding is "
                "verified by the matching native OHOS integration run"
            )
            return
        dependency = self.dependencies[self.tested_reference_str]
        dict_dat = os.path.join(
            dependency.package_folder, "lib", "googlepinyin", "data", "dict_pinyin.dat"
        )
        if not os.path.isfile(dict_dat):
            raise FileNotFoundError(f"packaged dictionary missing: {dict_dat}")
        user_dict = os.path.join(self.build_folder, "userdict.tmp")
        with open(user_dict, "wb"):
            pass
        executable = os.path.join(
            self.cpp.build.bindir.replace("\\", "/"), "test_libgooglepinyin"
        )
        with VirtualRunEnv(self).vars().apply():
            self.run(f'"{executable}" "{dict_dat}" "{user_dict}"')
