#!/usr/bin/env python3
"""Conan test_package - installed cbindgen and the Rust/C/C++ consumer ABI."""

import os
import shlex
import sys

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.build import can_run
from conan.tools.env import Environment, VirtualBuildEnv, VirtualRunEnv
from conan.tools.layout import basic_layout


class CbindgenTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build_requirements(self):
        self.tool_requires("rust-toolchain/1.97.1")

    def layout(self):
        basic_layout(self)

    def generate(self):
        VirtualBuildEnv(self).generate()
        VirtualRunEnv(self).generate()
        compilers = self.conf.get("tools.build:compiler_executables", default={})
        rust = self.dependencies.build["rust-toolchain"].package_folder
        env = Environment()
        for name in ("CFLAGS", "CXXFLAGS", "CPATH", "C_INCLUDE_PATH",
                     "CPLUS_INCLUDE_PATH", "LIBRARY_PATH", "RUSTC_BOOTSTRAP"):
            env.unset(name)
        env.define("CC", compilers.get("c", "clang"))
        env.define("CXX", compilers.get("cpp", "clang++"))
        env.define("CBINDGEN_RUST_CACHE", os.path.join(self.build_folder, "rust-exec-cache"))
        env.define("CARGO_HOME", os.path.join(self.build_folder, "cargo-home"))
        env.define("TMPDIR", self.build_folder)
        env.vars(self, scope=None).save_script("consumer_env")

    def test(self):
        if not can_run(self):
            raise ConanInvalidConfiguration("The cbindgen consumer must run on the target")
        binary = os.path.join(self.dependencies["cbindgen"].package_folder, "bin", "cbindgen")
        command = [sys.executable, os.path.join(self.source_folder, "test.py"), binary,
                   "--work", os.path.join(self.build_folder, "consumer-results")]
        self.run(shlex.join(command), env=["conanbuild", "conanrun", "consumer_env"])
