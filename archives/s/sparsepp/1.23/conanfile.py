#!/usr/bin/env python3
"""Conan recipe for sparsepp 1.23 (header-only Makefile project)."""

import os
import shlex

from conan import ConanFile
from conan.tools.build import can_run, check_min_cppstd
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class SparseppConan(ConanFile):
    name = "sparsepp"
    version = "1.23"
    description = "A fast, memory efficient hash map for C++"
    license = "BSD-3-Clause"
    homepage = "https://github.com/greg7mdp/sparsepp"
    url = "https://github.com/greg7mdp/sparsepp"
    topics = ("hash", "hash-map", "hash-table", "header-only", "cpp")

    package_type = "header-library"
    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        pass

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, "11")

    def build(self):
        apply_conandata_patches(self)

        compiler_executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        ) or {}
        cxx = compiler_executables.get("cpp") or "clang++"
        tests_dir = os.path.join(self.source_folder, "tests")

        # This is the upstream CI entry: the default target builds spp_test and
        # the relative-include compile check, then `test` runs spp_test.
        self.run(
            "make -C {} CXX={} -j1".format(
                shlex.quote(tests_dir), shlex.quote(cxx)
            ),
            env="conanbuild",
        )
        if can_run(self):
            self.run(
                "make -C {} test -j1".format(shlex.quote(tests_dir)),
                env="conanrun",
            )
        else:
            self.output.info(
                "Cross-building: upstream spp_test was built but cannot run on the build machine"
            )

    def package(self):
        copy(
            self,
            "*.h",
            src=os.path.join(self.source_folder, "sparsepp"),
            dst=os.path.join(self.package_folder, "include", "sparsepp"),
            keep_path=False,
        )
        copy(
            self,
            "LICENSE",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_id(self):
        self.info.clear()

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = []
        self.cpp_info.libs = []
        self.cpp_info.set_property("cmake_file_name", "sparsepp")
        self.cpp_info.set_property("cmake_target_name", "sparsepp::sparsepp")
