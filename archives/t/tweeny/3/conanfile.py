#!/usr/bin/env python3
"""Conan recipe — tweeny 3 (CMake, header-only).

Tweeny is a header-only C++ inbetweening library (30+ easing functions,
multi-point tweening, forward/backward stepping, timeline seeking). Upstream
ships an INTERFACE CMake target plus install/export rules (TweenyConfig.cmake),
so this recipe drives the real CMake install instead of copying headers by hand.

Platform notes:
  * E103: upstream declares cmake_minimum_required(VERSION 3.0), which CMake 4.x
    rejects — CMAKE_POLICY_VERSION_MINIMUM=3.5 is injected.
  * examples/extras/docs builds are disabled: they pull demo/doc dependencies
    that are not part of this package.

Upstream v3 ships no test suite (no test/ directory in the tag), so verification
is delivered by the test_package consumer test, which compiles the installed
headers against OHOS clang and asserts on interpolation behaviour.

Version slug: the upstream release exists only as the single-character tag `v3`
(no dotted semver; TWEENY_VERSION is literally 3). Conan rejects
single-character versions (ConanName pattern needs >=2 chars: `Invalid package
version '3'`), so set_version() maps the artifact version to `v3` (tag form,
lowercased — same normalization as the repo's rapidhash/3 adaptation). The
archive directory and branch keep the task-card form `3` for the platform
branch-name gate (L0n).
"""
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class TweenyConan(ConanFile):
    name = "tweeny"
    description = "A modern C++ animation/tweening library (header-only, 30+ easings)."
    license = "MIT"
    homepage = "https://github.com/mobius3/tweeny"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "header-library"
    settings = "os", "compiler", "build_type", "arch"

    def set_version(self):
        # Upstream tag `v3` -> artifact version `v3` (see docstring).
        # Deliberately NOT a literal `version = "..."` attribute: the archive
        # directory keeps the task-card `3` (CI L0m-3 compares a literal
        # attribute against the directory), which a literal could never equal
        # since Conan itself rejects the single-character version.
        self.version = "v3"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        tc.variables["TWEENY_BUILD_EXAMPLES"] = False
        tc.variables["TWEENY_BUILD_EXTRAS"] = False
        tc.variables["TWEENY_BUILD_DOCUMENTATION"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        # NOTE: dst must be absolute — a relative dst is not resolved against
        # the package folder by conan.tools.files.copy (it lands in the
        # process cwd), so the template's `dst="licenses"` silently drops it.
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"),
             keep_path=False)

    def package_id(self):
        self.info.clear()

    def package_info(self):
        # Upstream installs headers under include/tweeny and exports the
        # INTERFACE target via lib/cmake/Tweeny (TweenyConfig.cmake). The
        # exported include dir is include/tweeny (mirrors upstream's
        # $<INSTALL_INTERFACE:include/tweeny>), so consumers #include <tweeny.h>.
        self.cpp_info.includedirs = ["include/tweeny"]
        self.cpp_info.set_property("cmake_file_name", "Tweeny")
        self.cpp_info.set_property("cmake_target_name", "Tweeny::tweeny")
        self.cpp_info.bindirs = []
        self.cpp_info.libdirs = []
