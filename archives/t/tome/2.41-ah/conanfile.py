#!/usr/bin/env python3
"""Conan recipe for tome 2.41-ah - "Tales of Middle Earth" game engine.

Tome is an Angband/Moria-derived roguelike.  The reusable part of the project
is the platform-independent game engine (CMake targets ``game`` and
``squelch``); the frontends (X11/GTK2/ncurses) are thin display drivers.  The
recipe builds the engine headless (all three FIND_PACKAGE checks disabled),
runs the upstream Bandit test harness (``src/harness``), and packages the two
static libraries plus the public C++ headers.

Dependencies: Boost (system, filesystem) is mandatory upstream; fmt/jsoncons/
pcg-cpp/bandit/CppQuickCheck are vendored (header-only, or compiled into the
test harness only) and are shipped inside the snapshot tarball.
"""
import os

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

required_conan_version = ">=2.0"


class TomeConan(ConanFile):
    name = "tome"
    version = "2.41-ah"
    description = "Tales of Middle Earth (ToME) roguelike game engine"
    license = "ToME/Angband license (see README.md)"
    homepage = "https://github.com/tome2/tome2"
    url = ""

    package_type = "static-library"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "tome OHOS adaptation is validated on Linux/OHOS, not "
                + str(self.settings.os))

    def layout(self):
        cmake_layout(self)

    def requirements(self):
        self.requires("boost/1.85.0")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        deps = CMakeDeps(self)
        deps.generate()
        tc = CMakeToolchain(self)
        # Build the headless engine + test harness only.
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_X11"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_GTK2"] = True
        tc.variables["CMAKE_DISABLE_FIND_PACKAGE_Curses"] = True
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = True
        tc.cache_variables["CMAKE_POLICY_DEFAULT_CMP0074"] = "NEW"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build(target="harness")

        exe = os.path.join(self.build_folder, "src", "harness")
        log = os.path.join(self.build_folder, "harness.out")
        self.run('"{}" --reporter=spec > "{}" 2>&1'.format(exe, log),
                 cwd=os.path.join(self.build_folder, "src"))
        with open(log) as fh:
            out = fh.read()
        if "Success!" not in out:
            raise ConanException("upstream harness did not succeed:\n" + out[-3000:])
        passed = out.count("Success!")
        self.output.info("upstream harness: " + out.strip().splitlines()[-1])
        if not passed:
            raise ConanException("no successful test run recorded")

    def package(self):
        copy(self, "README.md", self.source_folder,
             os.path.join(self.package_folder, "licenses"))
        copy(self, "libgame.a", os.path.join(self.build_folder, "src"),
             os.path.join(self.package_folder, "lib"))
        copy(self, "libsquelch.a", os.path.join(self.build_folder, "src", "squelch"),
             os.path.join(self.package_folder, "lib"))
        # Public headers: top-level src/*.hpp plus the src/include tree
        # (tome/...).  Subdirectories keep their layout.
        copy(self, "*.hpp", os.path.join(self.source_folder, "src"),
             os.path.join(self.package_folder, "include"),
             excludes=("include/*", "include", "squelch/*", "squelch"))
        copy(self, "*.hpp", os.path.join(self.source_folder, "src", "include"),
             os.path.join(self.package_folder, "include"))

    def package_info(self):
        self.cpp_info.libs = ["game", "squelch"]
