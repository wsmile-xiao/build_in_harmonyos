#!/usr/bin/env python3
"""Conan recipe — libtut 0.0.20070706 (header-only).

TUT (Template Unit Tests), a pure C++ template-based unit test
framework by Vladimir Dyuzhev. The library is three .hpp headers;
consumers just include <tut/tut.hpp> and compile. Zero dependencies,
C++98-era code that compiles cleanly with modern compilers
(MSVC 194 / clang 15 checked locally).

Install layout mirrors Debian libtut-dev exactly:
  include/tut/tut.hpp, tut_reporter.hpp, tut_restartable.hpp
  include/tut.h, tut_reporter.h, tut_restartable.h   (root shims)

Upstream site (tut.dozen.ru / tut-framework.sourceforge.net) is long
dead; the Debian pool archive is the canonical distribution point of
the 0.0.20070706 tarball (md5 883a9f66d8b073ef97490098d72eba72 matches
packages.debian.org).
"""
from conan import ConanFile
from conan.tools.files import get, copy
from conan.tools.layout import basic_layout
import os

required_conan_version = ">=2.0"


class LibtutConan(ConanFile):
    name = "libtut"
    version = "0.0.20070706"
    package_type = "header-library"

    description = (
        "TUT: template-based C++ unit test framework (header-only, "
        "zero dependencies)"
    )
    homepage = "https://sourceforge.net/projects/tut-framework/"
    license = "BSD-2-Clause"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("unit-testing", "test-framework", "template", "header-only")

    settings = "os", "arch", "compiler", "build_type"
    no_copy_source = True

    def layout(self):
        basic_layout(self, src_folder="src")

    def package_id(self):
        self.info.clear()

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def package(self):
        # canonical headers: #include <tut/tut.hpp> (Debian: tut/* → include/tut)
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "tut"),
             dst=os.path.join(self.package_folder, "include", "tut"))
        # backward-compat root shims: #include <tut.h> (Debian: *.h → include)
        for shim in ("tut.h", "tut_reporter.h", "tut_restartable.h"):
            copy(self, shim,
                 src=self.source_folder,
                 dst=os.path.join(self.package_folder, "include"))
        copy(self, "README",
             src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "doc"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "libtut")
        self.cpp_info.set_property("cmake_target_name", "libtut::libtut")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
