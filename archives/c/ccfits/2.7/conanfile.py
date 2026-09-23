#!/usr/bin/env python3
"""Conan recipe for CCfits 2.7.

CCfits is the official NASA HEASARC object-oriented C++ interface to the
cfitsio library. This recipe builds the CMake path of the upstream tarball
into a self-contained library package.

Device verification notes (OpenHarmony aarch64, clang 15):
- Upstream configures its dependency exclusively through pkg-config
  (PKG_CHECK_MODULES(CFITSIO REQUIRED cfitsio)). The cfitsio Conan package
  ships its own cfitsio.pc with a stale absolute prefix baked in at packaging
  time, so we regenerate dependency .pc files with PkgConfigDeps and prepend
  the generators folder to PKG_CONFIG_PATH in the build environment (Conan
  2.29 does not do this automatically).
- The upstream CMakeLists.txt embeds version string 2.6 while configure.ac
  and CHANGES say 2.7 (upstream inconsistency). The produced library has no
  versioned file name / SONAME, so the mismatch does not affect artifacts;
  recorded in notes.md, not patched.
- Pure C++ codebase, no OHOS-specific patch required; C++11 required
  (TARGET_COMPILE_FEATURES cxx_std_11), built here with cppstd=17.
"""

import os

from conan import ConanFile
from conan.tools.build import check_min_cppstd
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.gnu import PkgConfigDeps


class CcfitsConan(ConanFile):
    name = "ccfits"
    version = "2.7"
    description = (
        "CCfits is an object oriented interface to the cfitsio library "
        "(NASA HEASARC FITS I/O)."
    )
    license = "CFITSIO"
    homepage = "https://heasarc.gsfc.nasa.gov/fitsio/ccfits"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # Public headers include fitsio.h (CCfits.h -> fitsio.h), so the
        # dependency must stay visible to consumers of this package.
        self.requires("cfitsio/4.6.4", transitive_headers=True)

    def validate(self):
        if self.settings.compiler.get_safe("cppstd"):
            check_min_cppstd(self, 11)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Regenerate .pc files for cfitsio (and its zlib dependency) with
        # paths that actually exist in the local cache. The pc file shipped
        # inside the cfitsio package carries a stale absolute prefix, which
        # makes upstream's PKG_CHECK_MODULES resolve unusable -I/-L flags.
        PkgConfigDeps(self).generate()
        # Conan 2.29 does not export PkgConfigDeps folders through the build
        # environment, so do it explicitly for the build scope.
        env = Environment()
        env.prepend_path("PKG_CONFIG_PATH", self.generators_folder)
        env.vars(self, scope="build").save_script("ccfits_pkg_config_path")

        tc = CMakeToolchain(self)
        # Package the library only; the upstream cookbook program is driven
        # separately as the upstream test (see test_package/MANIFEST.yml).
        tc.variables["TESTS"] = "OFF"
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Position-independent code so the static archive can be linked into
        # shared objects / extension modules by consumers.
        tc.variables["CMAKE_POSITION_INDEPENDENT_CODE"] = "ON"
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "License.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["CCfits"]
        self.cpp_info.set_property("cmake_file_name", "CCfits")
        self.cpp_info.set_property("cmake_target_name", "CCfits::CCfits")
        self.cpp_info.set_property("pkg_config_name", "CCfits")
