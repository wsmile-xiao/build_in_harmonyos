#!/usr/bin/env python3
"""Conan recipe for libnop - Native Object Protocols (header-only C++).

libnop (Google) is a header-only serialization / RPC library: annotate a type
with ``NOP_STRUCTURE`` (or use the built-in types) and
``nop::Serializer<StreamWriter<...>>`` writes a platform independent byte
stream while ``nop::Deserializer<...>`` reads it back, with optional values,
variants, handles and RPC interfaces on top.

OHOS notes
----------
* Header-only: nothing is compiled into the package.  ``package()`` installs
  the ``include/nop/**`` tree plus the license, and ``package_id()`` clears the
  binary settings.
* The upstream tree ships a GoogleTest/GoogleMock test suite (``test/*.cpp``,
  run by its Makefile when gtest is found) and runnable examples.  The recipe
  pulls ``gtest``/``gmock`` as ``test_requires``, points the Makefile at those
  package folders (``GTEST_INCLUDE``/``GTEST_LIB``) and executes the resulting
  suite on the device; the outcome is reported by ``test_package``.
* The Makefile's ``-Werror`` is relaxed to ``-Wextra`` for this build: the
  vendored GoogleTest 1.17 headers raise warnings under OHOS clang that are
  unrelated to libnop.
"""
import os
import platform

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

_TEST_MODULES = ("test",)


class LibnopConan(ConanFile):
    name = "libnop"
    version = "0.0-git20211103.35e800d"
    description = "Native Object Protocols: header-only serialization and RPC framework for C++"
    license = "Apache-2.0"
    homepage = "https://github.com/google/libnop"
    url = ""

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    no_copy_source = True

    def build_requirements(self):
        # Used by build() to compile and run the upstream GoogleTest suite.
        self.test_requires("gtest/1.17.0")
        self.test_requires("gmock/1.17.0")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def package_id(self):
        self.info.clear()

    def _compiler(self, name, fallback):
        executables = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict) or {}
        return executables.get(name) or fallback

    def _gtest_flags(self):
        include_dirs, lib_dirs = [], []
        for dependency_name in ("gtest", "gmock"):
            dependency = self.dependencies.get(dependency_name)
            if dependency is None or not dependency.package_folder:
                continue
            for folder in dependency.cpp_info.includedirs:
                candidate = os.path.join(dependency.package_folder, folder)
                if os.path.isdir(candidate):
                    include_dirs.append(candidate)
            for folder in dependency.cpp_info.libdirs:
                candidate = os.path.join(dependency.package_folder, folder)
                if os.path.isdir(candidate):
                    lib_dirs.append(candidate)
        return include_dirs, lib_dirs

    def build(self):
        if str(self.settings.os) != "OHOS" or platform.machine() not in ("aarch64", "arm64"):
            return
        include_dirs, lib_dirs = self._gtest_flags()
        if not include_dirs or not lib_dirs:
            self.output.warning("gtest/gmock not available, skipping upstream test suite")
            return
        arguments = [
            "-j1",
            "CC={}".format(self._compiler("c", "clang")),
            "CXX={}".format(self._compiler("cpp", "clang++")),
            # Keep -Wextra, drop -Werror (vendored gtest headers warn under clang).
            "HOST_CFLAGS=-g -O2 -Wall -Wextra -Iinclude",
            # The Makefile pins -std=c++14; the gtest/gmock packages require C++17.
            "HOST_CXXFLAGS=-std=c++17",
            "GTEST_INCLUDE={}".format(
                " ".join("-I" + folder for folder in include_dirs)),
            "GTEST_LIB={}".format(" ".join("-L" + folder for folder in lib_dirs)),
        ]
        self.run("make " + " ".join("'{}'".format(item) for item in arguments),
                 cwd=self.source_folder)
        binary = os.path.join(self.source_folder, "out", "test")
        if not os.path.isfile(binary):
            self.output.warning("upstream test binary was not produced")
            return
        library_path = os.pathsep.join(lib_dirs)
        log = os.path.join(self.build_folder, "upstream-gtest.log")
        self.run('LD_LIBRARY_PATH="{}" "{}" > "{}" 2>&1'.format(library_path, binary, log))
        with open(log, "r", errors="replace") as handle:
            content = handle.read()
        passed = failed = 0
        for line in content.splitlines():
            if line.startswith("[  PASSED  ]"):
                passed = int(line.split()[3])
            if line.startswith("[  FAILED  ]") and "tests listed below" not in line:
                failed += line.count(",") + 1
        self.output.info("upstream GoogleTest suite: {} passed, {} failed".format(passed, failed))
        if "[  FAILED  ]" in content and failed:
            raise ConanException(
                "upstream GoogleTest suite reported {} failing test(s)".format(failed))

    def package(self):
        include_dir = os.path.join(self.package_folder, "include")
        copy(self, "*.h", src=os.path.join(self.source_folder, "include"), dst=include_dir)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.set_property("cmake_file_name", "libnop")
        self.cpp_info.set_property("cmake_target_name", "libnop::libnop")
