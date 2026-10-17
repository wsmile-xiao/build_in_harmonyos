#!/usr/bin/env python3
"""Conan recipe for libudns 0.6 — async stub DNS resolver library + CLI tools.

udns uses a hand-written configure script that only recognises the
`ipv6` feature toggle (no --prefix / --host / --disable-shared), and
its Makefile has no `install` target.  The recipe therefore configures
and builds in place with the Conan profile compiler conf, then packages
the artifacts manually (R33/R38 compliant).
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class LibudnsConan(ConanFile):
    name = "libudns"
    version = "0.6"
    description = "libudns — async-capable DNS stub resolver (dnsget/rblcheck/ex-rdns)"
    license = "LGPL-2.1"
    homepage = "https://www.corpit.ru/mjt/udns.html"
    url = ""  # CI fills this

    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _c_compiler(self):
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        return compilers.get("c") or compilers.get("cpp")

    def _llvm_tool(self, name):
        compiler = self._c_compiler()
        if not compiler:
            return name
        candidate = os.path.join(os.path.dirname(compiler), name)
        return candidate if os.path.exists(candidate) else name

    def build(self):
        apply_conandata_patches(self)
        cc = self._c_compiler()
        if not cc:
            raise ConanInvalidConfiguration(
                "C compiler executable is not configured"
            )
        work = self.source_folder
        envline = (
            f'CC="{cc}" AR="{self._llvm_tool("llvm-ar")}" '
            f'RANLIB="{self._llvm_tool("llvm-ranlib")}"'
        )
        self.run(f'bash -c \'cd "{work}" && export {envline} && ./configure\'')
        self.run(f'bash -c \'cd "{work}" && export {envline} && make -j1\'')

    def package(self):
        copy(
            self,
            "udns.h",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "include"),
            keep_path=False,
        )
        copy(
            self,
            "libudns.a",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "lib"),
            keep_path=False,
        )
        for tool in ("dnsget", "rblcheck", "ex-rdns"):
            copy(
                self,
                tool,
                src=self.source_folder,
                dst=os.path.join(self.package_folder, "bin"),
                keep_path=False,
            )
        copy(
            self,
            "COPYING.LGPL",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )

    def package_info(self):
        self.cpp_info.libs = ["udns"]
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "libudns")
        self.cpp_info.set_property("cmake_target_name", "libudns::libudns")