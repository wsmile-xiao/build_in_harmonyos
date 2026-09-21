#!/usr/bin/env python3
"""Installed-package consumer test for libcomps 0.1.24.

Builds and runs one program that links against the packaged library and
exercises the public API contract on a real comps document:

* XML parsing through comps_parse_parsed_create/_init/comps_parse_str,
* the document filters comps_doc_get_groups/_categories/_envs,
* per-group package queries by type (mandatory/default/optional) and by name,
* the group property accessors comps_docgroup_get_id/_name/_uservisible/_def,
* serialization back to XML with comps2xml_str and a re-parse round trip,
* comps_doc_union merging two documents.

See test_package/MANIFEST.yml and ../notes.md for the counting rules: these
checks are the HarmonyOS-specific row and are NOT part of the upstream suite.
"""

import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


TEST_EXECUTABLES = ("test_libcomps",)


class LibcompsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException(
                "the libcomps consumer binary cannot run on this platform"
            )
        for name in TEST_EXECUTABLES:
            executable = os.path.join(self.cpp.build.bindir, name)
            self.run(f'"{executable}"', env="conanrun")
