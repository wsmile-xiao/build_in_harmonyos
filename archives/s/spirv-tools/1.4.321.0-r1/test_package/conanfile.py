#!/usr/bin/env python3
"""Conan test package for SPIRV-Tools 1.4.321.0-r1."""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.env import VirtualRunEnv
from conan.tools.layout import basic_layout


class SpirvToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualRunEnv(self).generate()

    def _find_library(self, pkg, name):
        dependency = self.dependencies[self.tested_reference_str]
        shared = bool(dependency.options.get_safe("shared", False))
        lib_dir = os.path.join(pkg, "lib")
        patterns = (
            [f"lib{name}.so", f"lib{name}.so.*", f"lib{name}.dylib"]
            if shared
            else [f"lib{name}.a"]
        )
        for pattern in patterns:
            matches = sorted(glob.glob(os.path.join(lib_dir, pattern)))
            if matches:
                return matches[0]
        kind = "shared" if shared else "static"
        raise ConanException(f"missing {kind} SPIRV-Tools library: {name}")

    def _check_package_layout(self, pkg):
        include_root = os.path.join(pkg, "include", "spirv-tools")
        checks = [
            ("libspirv header", os.path.join(include_root, "libspirv.h")),
            ("optimizer header", os.path.join(include_root, "optimizer.hpp")),
        ]
        missing = [name for name, path in checks if not os.path.exists(path)]
        if missing:
            raise ConanException("missing SPIRV-Tools package artifacts: " + ", ".join(missing))
        core_lib = self._find_library(pkg, "SPIRV-Tools")
        self._find_library(pkg, "SPIRV-Tools-opt")
        return core_lib

    def _build_api_smoke_test(self, pkg, core_lib):
        os.makedirs(self.build_folder, exist_ok=True)
        source = os.path.join(self.source_folder, "test_spirv_tools_api.cpp")
        binary = os.path.join(self.build_folder, "test_spirv_tools_api")
        include_dir = os.path.join(pkg, "include")

        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
        cxx = (
            compilers.get("cpp")
            or compilers.get("cxx")
            or os.environ.get("CXX")
            or shutil.which("clang++")
            or shutil.which("c++")
            or "c++"
        )
        self.run(
            f'"{cxx}" -I"{include_dir}" "{source}" "{core_lib}" -pthread -o "{binary}"',
        )
        return binary

    def test(self):
        pkg = self.dependencies[self.tested_reference_str].package_folder
        core_lib = self._check_package_layout(pkg)
        binary = self._build_api_smoke_test(pkg, core_lib)
        if can_run(self):
            self.run(f'"{binary}"', env="conanrun")
