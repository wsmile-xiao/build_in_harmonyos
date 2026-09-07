#!/usr/bin/env python3
"""Conan recipe for pokerstove 1.1 — HarmonyOS PC (aarch64) adaptation.

pokerstove is a C++ poker hand evaluation library:
  - peval/penum static libraries (card parsing, hand evaluation, equity enumeration)
  - ps-eval / ps-colex / ps-lut CLI tools

Adaptation notes (see notes.md):
  - OHOS musl lacks pthread_setcancelstate; boost headers need
    BOOST_SP_NO_PTHREAD_SETCANCELSTATE (patch to root CMakeLists.txt, E127)
  - cmake >= 4 removed <3.5 compat; upstream requires 3.0 →
    CMAKE_POLICY_VERSION_MINIMUM=3.5 via toolchain cache variable
  - upstream installs no headers → package() copies src/lib/pokerstove
    to include/pokerstove
"""
from pathlib import Path

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class PokerstoveConan(ConanFile):
    name = "pokerstove"
    version = "1.1"
    description = "C++ poker hand evaluator and equity calculator (peval/penum libs + ps-eval/ps-colex/ps-lut tools)"
    license = "MIT"
    homepage = "https://github.com/andrewprock/pokerstove"
    url = "https://github.com/andrewprock/pokerstove"

    package_type = "library"
    languages = "C++"
    topics = ("poker", "hand-evaluation", "equity", "card-game")

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # pokerstove uses only boost program_options (CLI tools) plus
        # header-only parts (smart_ptr, format); public headers include
        # boost headers, so the dependency is required by consumers too.
        # visible=True: peval/penum public headers #include <boost/...>, so
        # consumers must see boost's include dirs / link interface (Conan 2
        # defaults requires to private, which strips include propagation).
        self.requires("boost/1.84.0", visible=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # R1: minimal parameters — only BUILD_SHARED_LIBS ( Conan option )
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # upstream embeds googletest for its own test suites; its install
        # rules must stay out of the package (upstream option, default ON)
        tc.variables["INSTALL_GTEST"] = "OFF"
        # upstream cmake_minimum_required(3.0); cmake >= 4 refuses < 3.5
        # (CI/local both use cmake 4.x). Cache variable is ignored by cmake 3.x.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # upstream installs targets (lib peval/penum + bin ps-eval/ps-colex/ps-lut)
        # but no headers; package them so consumers can #include <pokerstove/...>
        src_headers = Path(self.source_folder) / "src" / "lib" / "pokerstove"
        dst_include = Path(self.package_folder) / "include" / "pokerstove"
        for pattern in ("*.h", "*.hpp"):
            copy(self, pattern, src=src_headers, dst=dst_include)
        copy(self, "LICENSE.txt", src=self.source_folder, dst=self.package_folder)

    def package_info(self):
        # real library names (build products): libpenum.a + libpeval.a
        # order matters for static linking: penum depends on peval
        self.cpp_info.libs = ["penum", "peval"]
        # CLI tools installed alongside the libs (R38: declared in commands.json)
        self.cpp_info.bindirs = ["bin"]
