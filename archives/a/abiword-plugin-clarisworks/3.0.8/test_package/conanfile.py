#!/usr/bin/env python3
"""test_package for abiword-plugin-clarisworks 3.0.8.

Consumer-level test (R34): compiles a small program that dlopens the
installed plugin module and drives its exported ABI
(abi_plugin_supports_version / abi_plugin_register / abi_plugin_unregister).
"""
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Use the compiler the profile points at (OHOS SDK clang)
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cpp = ccs.get("cpp") or "clang++"
        src = os.path.join(self.source_folder, "run_test.cpp")
        out = os.path.join(self.build_folder, "run_test")
        self.run(f"{cpp} {src} -o {out} -ldl")

    def test(self):
        dep = self.dependencies["abiword-plugin-clarisworks"]
        so = os.path.join(dep.package_folder, "lib", "abiword-3.0",
                          "plugins", "libabiword-plugin-clarisworks.so")
        if not os.path.exists(so):
            self.output.error("plugin module not found in package: " + so)
            raise SystemExit(1)
        exe = os.path.join(self.build_folder, "run_test")
        self.run(f"{exe} {so}")
