#!/usr/bin/env python3
"""Conan recipe for pcalc.

pcalc is a command-line calculator that supports hexadecimal, decimal,
octal, and binary mixed arithmetic. It is a tool (not a library).

Build system: Makefile (no configure script)
Dependencies: flex, bison (Yacc/Lex)
"""
import os

from conan import ConanFile
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches, copy, mkdir, chdir
from conan.tools.layout import basic_layout
from conan.tools.env import VirtualBuildEnv


class PcalcConan(ConanFile):
    name = "pcalc"
    version = "3.0.0"
    license = "GPL-2.0"
    description = "Programmer's command-line calculator with hex/dec/oct/bin support"
    url = "https://github.com/vapier/pcalc"
    homepage = "https://github.com/vapier/pcalc"
    topics = ("calculator", "programmer", "hex", "binary")
    settings = "os", "compiler", "build_type", "arch"
    package_type = "application"

    def requirements(self):
        pass

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        self.tool_requires("flex/2.6.4")
        self.tool_requires("bison/3.8.2")

    def layout(self):
        basic_layout(self)

    def generate(self):
        env = VirtualBuildEnv(self)
        env.generate()

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        # R26: Terminal tools should be statically linked on OHOS
        # to avoid missing system library issues at runtime.
        # Only set LDFLAGS when needed; otherwise let Makefile defaults apply.
        ldflags = "-static" if self.settings.os == "OHOS" else None
        njobs = os.cpu_count() or 1
        with chdir(self, self.source_folder):
            cmd = f"make -j{njobs} CC=$CC CXX=$CXX"
            if ldflags:
                cmd += f" LDFLAGS='{ldflags}'"
            self.run(cmd, env="conanbuild")

    def package(self):
        mkdir(self, os.path.join(self.package_folder, "bin"))
        copy(self, "pcalc", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []