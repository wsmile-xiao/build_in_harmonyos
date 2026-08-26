#!/usr/bin/env python3
"""Conan test_package for jsonrpc-glib 3.44.0.

Uses meson + PkgConfigDeps to match the main recipe's build system.
PkgConfigDeps properly propagates transitive include directories
(unlike CMakeDeps with flat cpp_info packages like glib 2.84.0).
"""
import os
import configparser

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class JsonrpcGlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "PkgConfigDeps", "MesonToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self, src_folder=".")

    def generate(self):
        self._inject_meson_archive_tools()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def test(self):
        if can_run(self):
            test_exe = os.path.join(self.build_folder, "test_jsonrpc_glib")
            self.run(test_exe, env="conanrun")

    def _inject_meson_archive_tools(self):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c", "")
        bindir = os.path.dirname(compiler) if os.path.sep in compiler else ""
        ar = executables.get("ar") or os.path.join(bindir, "llvm-ar")
        ranlib = executables.get("ranlib") or os.path.join(bindir, "llvm-ranlib")
        native_file = os.path.join(self.generators_folder, "conan_meson_native.ini")
        if not bindir or not os.path.isfile(ar) or not os.path.isfile(native_file):
            return
        parser = configparser.ConfigParser(interpolation=None)
        parser.optionxform = str
        parser.read(native_file, encoding="utf-8")
        if not parser.has_section("binaries"):
            return
        if not parser.has_option("binaries", "ar"):
            parser.set("binaries", "ar", "'{}'".format(ar))
        if os.path.isfile(ranlib) and not parser.has_option("binaries", "ranlib"):
            parser.set("binaries", "ranlib", "'{}'".format(ranlib))
        with open(native_file, "w", encoding="utf-8") as native:
            parser.write(native, space_around_delimiters=True)
