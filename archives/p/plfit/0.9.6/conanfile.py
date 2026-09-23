#!/usr/bin/env python3
"""Conan recipe for plfit 0.9.6 — power-law distribution fitting.

plfit fits power-law distributions to empirical (discrete or continuous)
data according to the method of Clauset, Shalizi and Newman [1], and ships
the `plfit` and `plgen` command-line tools together with the C library.

Upstream: https://github.com/ntamas/plfit

OHOS adaptations (see patches/ and notes.md):
  - The OHOS sysroot bundles the math functions in the C runtime and has no
    separately discoverable libm. CMake's FIND_LIBRARY(MATH_LIBRARY NAMES m)
    returns NOTFOUND, which upstream would then pass verbatim to every link
    line; patch 0001 neutralizes the NOTFOUND value (zxcvbn-c 2.6 precedent).
  - Upstream install(TARGETS plfit LIBRARY ...) only covers the shared-library
    artifact kind; the static archive of the default build must be listed
    explicitly (patch 0002).
  - The upstream CTest suite (9 data-driven tests) is built and executed
    during conan create (R51).

[1] Clauset A, Shalizi CR, Newman MEJ: Power-law distributions in empirical
    data. SIAM Review 51, 661-703 (2009).
"""

import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)


class PlfitConan(ConanFile):
    name = "plfit"
    version = "0.9.6"
    description = "Library to fit power-law distributions to empirical data"
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/ntamas/plfit"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"
    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    exports_sources = "conandata.yml", "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # The SWIG-based Python bindings are out of scope for this recipe.
        tc.variables["PLFIT_COMPILE_PYTHON_MODULE"] = "OFF"
        # Experimental OpenMP parallelization stays off (upstream default;
        # pinned explicitly so the toolchain cannot flip it).
        tc.variables["PLFIT_USE_OPENMP"] = "OFF"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # E074: parallel make on the HMDFS workstations trips over the
        # jobserver fifo — serialize.
        cmake.build(build_tool_args=["-j1"])
        if can_run(self):
            # Run the upstream CTest suite explicitly: detailed failure output
            # for CI diagnosis (cmake.test() only forwards the limited
            # `cmake --build --target test` interface, which rejects
            # ctest-specific flags such as --output-on-failure).
            self.run("ctest --output-on-failure", cwd=self.build_folder,
                     env="conanbuild")
        else:
            self.output.info("Cross-building: upstream CTest suite runs on target")

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["plfit"]
        # Headers install to include/plfit/ (upstream layout, mirrored by the
        # pkg-config file's Cflags=-I${includedir}/plfit convention).
        self.cpp_info.includedirs = ["include/plfit"]
        # This package ships the plfit/plgen executables: declare bin/ so the
        # CLI component is visible to consumers and the R38 gates
        # (commands.json, package_type=library + non-empty bindirs).
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.set_property("cmake_file_name", "plfit")
        self.cpp_info.set_property("cmake_target_name", "plfit::plfit")
        self.cpp_info.set_property("pkg_config_name", "libplfit")
