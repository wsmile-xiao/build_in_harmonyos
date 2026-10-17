#!/usr/bin/env python3
"""Conan recipe for libkml 1.3.0 (CMake build).

libkml is the reference implementation of OGC KML 2.2. Upstream is a
CMake project producing six libraries: libkmlbase, libkmldom, libkmlxsd,
libkmlengine, libkmlconvenience and libkmlregionator. Its CMakeLists uses
classic module-mode find_package for EXPAT/ZLIB/MiniZip/UriParser/Boost, so
we feed those Find modules explicit cache variables pointing at the Conan
package folders (config-mode CMakeDeps discovery does not apply).

Upstream tests use GoogleTest; they are built and run separately as part of
the local upstream-test gate (see notes.md / test_package/MANIFEST.yml), and
the recipe builds the six libraries with BUILD_TESTING=OFF for the shipped
artifact.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class LibkmlConan(ConanFile):
    name = "libkml"
    version = "1.3.0"
    description = "Reference implementation of OGC KML 2.2 (libkml base/dom/engine)"
    license = "BSD-3-Clause"
    homepage = "https://github.com/libkml/libkml"
    url = "https://github.com/libkml/libkml"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    exports_sources = "patches/*"

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"libkml supports Linux and OHOS targets, got {self.settings.os}"
            )
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def requirements(self):
        # All are published on ohpcd. Direct deps consumed by the build:
        self.requires("expat/2.8.2.1")
        self.requires("zlib/1.3.1.1")
        self.requires("minizip/1.3.1")
        self.requires("uriparser/1.0.2")
        # Boost is header-only for libkml (scoped_ptr / intrusive_ptr / boost
        # static headers); the upstream CMake finds Boost include dir only.
        # Public headers expose <boost/scoped_ptr.hpp> (kml/engine/kml_file.h),
        # so boost headers must propagate to consumers (transitive_headers).
        self.requires("boost/1.91.0", transitive_headers=True)

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        shared = bool(self.options.shared)
        tc.cache_variables["BUILD_SHARED_LIBS"] = shared
        tc.cache_variables["BUILD_TESTING"] = "OFF"
        tc.cache_variables["BUILD_EXAMPLES"] = "OFF"
        tc.cache_variables["WITH_SWIG"] = "OFF"
        # Upstream declares cmake_minimum_required(2.8); CMake >= 4 dropped
        # compatibility with < 3.5. Re-enable the legacy-policy shim so the
        # 2011-era CMakeLists still configures.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"

        expat = self.dependencies["expat"].cpp_info
        zlib = self.dependencies["zlib"].cpp_info
        minizip = self.dependencies["minizip"].cpp_info
        uriparser = self.dependencies["uriparser"].cpp_info
        boost = self.dependencies["boost"].cpp_info

        # Classic module-mode Find modules used by upstream CMakeLists.
        tc.cache_variables["EXPAT_INCLUDE_DIR"] = expat.includedirs[0]
        tc.cache_variables["EXPAT_LIBRARY"] = os.path.join(expat.libdirs[0], "libexpat.a")
        tc.cache_variables["ZLIB_INCLUDE_DIR"] = zlib.includedirs[0]
        tc.cache_variables["ZLIB_LIBRARY"] = os.path.join(zlib.libdirs[0], "libz.a")
        tc.cache_variables["MINIZIP_INCLUDE_DIR"] = minizip.includedirs[0]
        tc.cache_variables["MINIZIP_LIBRARY"] = os.path.join(minizip.libdirs[0], "libminizip.a")
        tc.cache_variables["URIPARSER_INCLUDE_DIR"] = uriparser.includedirs[0]
        tc.cache_variables["URIPARSER_LIBRARY"] = os.path.join(uriparser.libdirs[0], "liburiparser.a")
        tc.cache_variables["Boost_INCLUDE_DIRS"] = boost.includedirs[0]
        tc.cache_variables["Boost_INCLUDE_DIR"] = boost.includedirs[0]
        tc.cache_variables["Boost_FOUND"] = True
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # Six upstream libraries, in topological link order.
        self.cpp_info.set_property("cmake_file_name", "libkml")
        self.cpp_info.set_property("cmake_target_name", "libkml::libkml")
        self.cpp_info.libs = [
            "kmlbase",
            "kmldom",
            "kmlxsd",
            "kmlengine",
            "kmlconvenience",
            "kmlregionator",
        ]
        self.cpp_info.requires = [
            "expat::expat",
            "zlib::zlib",
            "minizip::minizip",
            "uriparser::uriparser",
            "boost::boost",
        ]
