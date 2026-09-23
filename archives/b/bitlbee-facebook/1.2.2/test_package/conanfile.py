#!/usr/bin/env python3
"""test_package for bitlbee-facebook 1.2.2.

Consumer-level test (R34): compiles a small host-stub program that exports
the bitlbee plugin API surface, dlopens the packaged facebook.so module
with RTLD_NOW (every relocation must resolve), and drives both exported
entry points (init_plugin_info / init_plugin).
"""
import os

from conan import ConanFile


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        # Use the compiler the profile points at (OHOS SDK clang) — R33
        ccs = self.conf.get("tools.build:compiler_executables", default={}) or {}
        cc = ccs.get("c") or "clang"
        src = os.path.join(self.source_folder, "run_test.c")
        out = os.path.join(self.build_folder, "run_test")
        # -rdynamic: the plugin resolves the bitlbee plugin API against the
        # host executable's dynamic symbol table (dlopen contract)
        self.run(f'{cc} -rdynamic "{src}" -o "{out}" -ldl')

    def test(self):
        dep = self.dependencies["bitlbee-facebook"]
        so = os.path.join(dep.package_folder, "lib", "bitlbee",
                          "facebook.so")
        if not os.path.exists(so):
            # L1e: absent artifact must fail the test
            self.output.error("plugin module not found in package: " + so)
            raise SystemExit(1)
        exe = os.path.join(self.build_folder, "run_test")
        self.run(f'"{exe}" "{so}"')
