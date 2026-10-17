#!/usr/bin/env python3
"""Conan recipe — taskflow 4.1.0 (header-only 通用并行任务编程库).

taskflow is a general-purpose task-parallel programming system built on
work-stealing task flow graphs. Upstream ships a CMake INTERFACE target
that exports headers only — there are no compiled artifacts.

OHOS adaptation notes (details in notes.md):

  * Header-only: the package ships include/taskflow/ headers + LICENSE and
    package_id is cleared to a single id (templates/conanfile-headeronly.py.tmpl
    pattern, variant A). build() only configures and builds the upstream CMake
    project's INTERFACE target as a consistency check — no translation unit of
    the library is compiled and no binary is produced.
  * Upstream requires C++20 (CMAKE_CXX_STANDARD 20 with
    CMAKE_CXX_STANDARD_REQUIRED ON) while the OHOS profile pins
    cppstd=17. The package itself compiles nothing, so validate() does
    not reject a lower cppstd; instead the requirement is propagated to
    consumers through cpp_info.cxxflags and documented in manifest.yaml
    and notes.md.
  * The OHOS SDK libc++ 15 ships neither the <memory_resource> header
    nor any std::pmr symbol, so patches/0003 replaces the cold-path
    backing allocator of tf::ObjectPool with an in-library equivalent
    pool, selected by __has_include(<memory_resource>) feature detection
    (no platform conditional compilation).
  * Upstream unit tests use class template argument deduction through an
    alias template, which clang does not implement (LLVM issue 106839);
    patches/0001 and patches/0002 spell the template argument out
    explicitly without changing case or assertion counts.
  * find_package(Taskflow) / Taskflow::taskflow compatibility is kept
    via cmake_file_name / cmake_target_name cpp_info properties
    (mirrors the upstream TaskflowConfig.cmake export names).
  * Consumers need threading support: upstream links Threads::Threads.
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain
from conan.tools.files import (
    copy, get, apply_conandata_patches, export_conandata_patches,
)
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class TaskflowConan(ConanFile):
    name = "taskflow"
    version = "4.1.0"
    package_type = "header-library"

    description = ("General-purpose parallel and heterogeneous task "
                   "programming system (header-only C++20 library)")
    homepage = "https://github.com/taskflow/taskflow"
    license = "MIT"
    url = "https://github.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    settings = "os", "arch", "compiler", "build_type"

    no_copy_source = True

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # Upstream builds examples and the doctest unit-test tree by default
        # (TF_BUILD_EXAMPLES/TF_BUILD_TESTS default ON). This package ships the
        # INTERFACE target only, so everything that would drag in tests,
        # benchmarks, the network profiler, CUDA or C++ modules is turned off
        # explicitly; the upstream test suite is exercised separately on the
        # device (see test_package/MANIFEST.yml).
        tc.cache_variables["TF_BUILD_TESTS"] = "OFF"
        tc.cache_variables["TF_BUILD_EXAMPLES"] = "OFF"
        tc.cache_variables["TF_BUILD_BENCHMARKS"] = "OFF"
        tc.cache_variables["TF_BUILD_PROFILER"] = "OFF"
        tc.cache_variables["TF_BUILD_CUDA"] = "OFF"
        tc.cache_variables["TF_BUILD_MODULES"] = "OFF"
        tc.generate()

    def build(self):
        # Header-only INTERFACE target: configure + build validate that the
        # patched upstream CMake project is consistent; no translation unit
        # of the library is compiled.
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package_id(self):
        # Header-only, no build artifacts: a single package_id serves
        # every configuration (template variant A).
        self.info.clear()

    def package(self):
        # Ship the whole taskflow/ header tree with paths preserved so
        # `#include <taskflow/taskflow.hpp>` keeps working.
        copy(self, "*.hpp",
             src=os.path.join(self.source_folder, "taskflow"),
             dst=os.path.join(self.package_folder, "include", "taskflow"))
        copy(self, "LICENSE", self.source_folder,
             os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.includedirs = ["include"]
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
        # Match the upstream export names: find_package(Taskflow) and
        # target Taskflow::taskflow (TaskflowConfig.cmake.in).
        self.cpp_info.set_property("cmake_file_name", "Taskflow")
        self.cpp_info.set_property("cmake_target_name", "Taskflow::taskflow")
        # The OHOS profile pins cppstd=17 while the headers require C++20
        # (upstream forces CMAKE_CXX_STANDARD 20 + REQUIRED, and the
        # headers use C++20 concepts and designated initializers). The
        # package itself compiles nothing, so propagate the requirement to
        # consumers through cxxflags; without it a cppstd=17 consumer fails
        # to compile the headers.
        self.cpp_info.cxxflags = ["-std=c++20"]
        # Upstream links Threads::Threads. musl-based OHOS exposes an empty
        # libpthread (libc carries the implementation), so -lpthread is a
        # harmless no-op there and the required one on Linux.
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["pthread"]
