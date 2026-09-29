#!/usr/bin/env python3
"""Conan recipe for mini-yaml 22d3dcf568 — YAML 1.0 C++11 serializer/deserializer.

Upstream: https://github.com/jimmiebergmann/mini-yaml (commit 22d3dcf568).
Library source is exactly two files under yaml/ (Yaml.hpp + Yaml.cpp).
Adapted for HarmonyOS OHOS (aarch64-linux-ohos): compile Yaml.cpp into a
static library and install the header at include/yaml/Yaml.hpp so consumers
keep the upstream include style `#include "yaml/Yaml.hpp"`.
"""
import os

from conan import ConanFile
from conan.tools.files import get, copy, apply_conandata_patches, export_conandata_patches
from conan.tools.layout import basic_layout


class MiniyamlConan(ConanFile):
    name = "mini-yaml"
    version = "22d3dcf568"
    description = "mini-yaml — YAML 1.0 C++11 serializer/deserializer"
    license = "MIT"
    homepage = "https://github.com/jimmiebergmann/mini-yaml"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)

        # R33: get compiler from Conan conf, never from bare shell env vars
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cxx = compilers.get("cpp", "clang++") if compilers else "clang++"
        ar = compilers.get("ar", "llvm-ar") if compilers else "llvm-ar"

        src_dir = self.source_folder
        build_dir = self.build_folder
        inc = os.path.join(src_dir, "yaml")
        obj = os.path.join(build_dir, "Yaml.o")
        lib = os.path.join(build_dir, "libmini-yaml.a")

        # Compile the single implementation file, then archive statically.
        self.run(f"{cxx} -std=c++11 -fPIC -I{inc} -c {os.path.join(src_dir, 'yaml', 'Yaml.cpp')} -o {obj}")
        self.run(f"{ar} rcs {lib} {obj}")

    def package(self):
        copy(self, "yaml/Yaml.hpp", self.source_folder, os.path.join(self.package_folder, "include"))
        copy(self, "libmini-yaml.a", self.build_folder, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["mini-yaml"]
        self.cpp_info.includedirs = ["include"]
