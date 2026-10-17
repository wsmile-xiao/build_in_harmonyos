#!/usr/bin/env python3
"""Conan recipe for pdqsort (Pattern-Defeating Quicksort).

pdqsort is a single-file header-only C++ sorting library: ``pdqsort`` and
``pdqsort_branchless`` are drop-in replacements for ``std::sort`` that stay
O(n log n) on the patterns that degrade other quicksort variants (many equal
elements, already sorted, organ-pipe, ...).

OHOS notes
----------
* Header-only: there is nothing to compile in the recipe.  The package ships
  ``pdqsort.h`` and the license, and ``package_id()`` clears the binary
  settings so a single header package serves every OHOS configuration.
* The upstream tarball carries no build system (no CMake/Makefile), so the
  consumer verification lives entirely in ``test_package`` (CMake + a real
  sort-and-compare program, per R34).
* Version naming: the platform version ``0.0.0-git20180419`` is the Debian
  spelling of the 2018-04-19 git snapshot (``0.0.0+git20180419``); ``+`` is not
  usable in a Conan version, hence the ``-git<date>`` form in the archive path.
"""
from conan import ConanFile
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout
import os

_REQUIRED_HEADERS = ("pdqsort.h",)


class PdqsortConan(ConanFile):
    name = "pdqsort"
    version = "0.0.0-git20180419"
    description = "Pattern-defeating quicksort: a drop-in std::sort replacement (single header)"
    license = "Zlib"
    homepage = "https://github.com/orlp/pdqsort"
    url = ""

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package_id(self):
        self.info.clear()

    def package(self):
        include_dir = os.path.join(self.package_folder, "include")
        for header in _REQUIRED_HEADERS:
            copy(self, header, src=self.source_folder, dst=include_dir)
        copy(self, "license.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "pdqsort")
        self.cpp_info.set_property("cmake_target_name", "pdqsort::pdqsort")
