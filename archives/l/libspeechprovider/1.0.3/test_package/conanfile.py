#!/usr/bin/env python3
"""Exercise the installed speech-provider C API on HarmonyOS PC."""

from conan import ConanFile
import os
import shutil
import subprocess

from conan.errors import ConanInvalidConfiguration
from conan.tools.layout import basic_layout
from conan.tools.meson import Meson, MesonToolchain


class LibspeechproviderTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "PkgConfigDeps"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def generate(self):
        tc = MesonToolchain(self)
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        compiler = executables.get("c") or shutil.which("clang")
        if not compiler:
            raise ConanInvalidConfiguration("clang is required")
        tc.binaries["c"] = compiler
        llvm_ar = os.path.join(os.path.dirname(os.path.realpath(compiler)), "llvm-ar")
        if not os.path.isfile(llvm_ar):
            llvm_ar = shutil.which("llvm-ar")
        if not llvm_ar:
            raise ConanInvalidConfiguration("llvm-ar is required")
        tc.binaries["ar"] = llvm_ar
        tc.generate()

    def build(self):
        meson = Meson(self)
        meson.configure()
        meson.build()

    def test(self):
        package_folder = self.dependencies["libspeechprovider"].package_folder
        library = os.path.join(package_folder, "lib", "libspeech-provider-1.0.so")
        readelf = shutil.which("llvm-readelf")
        if not readelf:
            raise ConanInvalidConfiguration("llvm-readelf is required")
        dynamic = subprocess.run(
            [readelf, "--dynamic", library], check=True, capture_output=True, text=True
        ).stdout
        if "(RPATH)" in dynamic or "(RUNPATH)" in dynamic:
            raise AssertionError("packaged library retains a build-machine RPATH")
        self.run(f"meson test --verbose -C {self.build_folder}",
                 env="conanrun")
