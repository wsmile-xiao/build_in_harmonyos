#!/usr/bin/env python3
"""Conan recipe for GNU cgicc 3.2.19."""

import os

from conan import ConanFile
from conan.tools.build import cross_building
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rm
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class LibcgiccConan(ConanFile):
    name = "libcgicc"
    version = "3.2.19"
    description = "GNU C++ class library for writing CGI applications"
    license = "LGPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/cgicc/"
    url = "https://ftp.gnu.org/gnu/cgicc/"
    package_type = "static-library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"fPIC": [True, False]}
    default_options = {"fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.configure_args.extend(
            [
                "--disable-shared",
                "--enable-static",
                "--disable-demos",
                "--disable-fcgi-demos",
                "DOXYGEN=echo",
            ]
        )
        tc.generate()

    def _set_tmp_env(self):
        tmp_dir = os.path.join(self.build_folder, "tmp")
        os.makedirs(tmp_dir, exist_ok=True)
        os.environ["TMPDIR"] = tmp_dir
        os.environ["TMPPREFIX"] = os.path.join(tmp_dir, "sh")
        os.environ["TMP"] = tmp_dir
        os.environ["TEMP"] = tmp_dir
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cc = compilers.get("c") or os.environ.get("CC") or "clang"
        cxx = compilers.get("cpp") or os.environ.get("CXX") or "clang++"
        os.environ["CC"] = cc
        os.environ["CXX"] = cxx
        os.environ["LD"] = cc
        tool_dir = os.path.dirname(cc) if os.path.isabs(cc) else ""
        if tool_dir:
            os.environ["PATH"] = tool_dir + os.pathsep + os.environ.get("PATH", "")
            for env_name, tool_name in (
                ("AR", "llvm-ar"),
                ("NM", "llvm-nm"),
                ("RANLIB", "llvm-ranlib"),
                ("STRIP", "llvm-strip"),
            ):
                tool_path = os.path.join(tool_dir, tool_name)
                if os.path.exists(tool_path):
                    os.environ[env_name] = tool_path

    def _refresh_generated_timestamps(self):
        for relative_path in (
            "aclocal.m4",
            "configure",
            "Makefile.in",
            os.path.join("cgicc", "Makefile.in"),
            os.path.join("cgicc", "config.h.in"),
            os.path.join("doc", "Makefile.in"),
            os.path.join("support", "Makefile.in"),
        ):
            path = os.path.join(self.source_folder, relative_path)
            if os.path.exists(path):
                os.utime(path, None)

    def build(self):
        apply_conandata_patches(self)
        self._refresh_generated_timestamps()
        self._set_tmp_env()
        autotools = Autotools(self)
        autotools.configure()
        self._refresh_generated_timestamps()
        autotools.make(args=["-j1"])
        if not cross_building(self):
            autotools.make(target="check", args=["-j1"])

    def package(self):
        self._set_tmp_env()
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING.LIB",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
        )
        for pattern in ("*.la", "*.dylib"):
            rm(self, pattern, os.path.join(self.package_folder, "lib"))

    def package_info(self):
        self.cpp_info.libs = ["cgicc"]
        self.cpp_info.set_property("pkg_config_name", "cgicc")
        self.cpp_info.set_property("cmake_file_name", "libcgicc")
        self.cpp_info.set_property("cmake_target_name", "libcgicc::libcgicc")
