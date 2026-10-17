#!/usr/bin/env python3
"""Conan recipe for PDAL 2.10.1 — CMake build system.

PDAL (Point Data Abstraction Library) is a C++ library for translating and
processing point cloud data.  This recipe builds the core pdalcpp library and
the `pdal` command line utility against the OHOS PC aarch64 Conan packages
published in the ohpcd registry.

Scope decisions (see notes.md for the full list):
  * Core library + default readers/writers that come with the source tree.
  * Optional plugins (postgres/oci/hdf5/arrow/draco/e57/...) are all OFF.
  * WITH_ZSTD is OFF: zstd is available in the registry, but this adaptation
    keeps the dependency set to the eight packages validated for the task.
  * WITH_TESTS is OFF in the packaged build: the upstream unit tests need the
    149 MB test/data tree plus a native test runner; the conan package is
    verified through the test_package consumer test instead.
"""
import os
import subprocess

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class PdalConan(ConanFile):
    name = "pdal"
    version = "2.10.1"
    description = "PDAL is Point Data Abstraction Library. GDAL for point cloud data."
    license = "BSD-3-Clause"
    homepage = "https://pdal.io"
    url = "https://github.com/PDAL/PDAL"
    topics = ("gdal", "point-cloud-data", "lidar")

    package_type = "shared-library"
    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def requirements(self):
        # Versions aligned with the binaries published in the ohpcd registry.
        self.requires("gdal/3.9.2.3")
        self.requires("libcurl/8.5.0")
        self.requires("libgeotiff/1.7.4")
        # libgeotiff's public headers include <tiffio.h> from libtiff, but the
        # registry's libgeotiff package does not aggregate libtiff's include
        # dir into its own package_info, so libtiff must be a direct
        # requirement for consumers compiling against xtiffio.h (see patch
        # 0003).  It is also a transitive dependency of libgeotiff itself.
        self.requires("libtiff/4.7.2")
        self.requires("proj/9.3.1.1")
        self.requires("zlib/1.3.1.1")
        self.requires("libxml2/2.15.3")
        self.requires("xz/5.6.2")

    def validate(self):
        # PDAL requires C++17 (upstream CMakeLists sets CMAKE_CXX_STANDARD 17).
        if self.settings.compiler.cppstd:
            from conan.tools.build import check_min_cppstd
            check_min_cppstd(self, 17)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def generate(self):
        tc = CMakeToolchain(self)
        # dimbuilder is a build-time code generator that must run on the build
        # host.  We are doing a native OHOS build (host == target), so the
        # executable built in this tree can be executed directly.  The cache
        # variable makes the location explicit for cross builds as well.
        dimbuilder_suffix = ".exe" if self.settings.os == "Windows" else ""
        tc.cache_variables["DIMBUILDER_EXECUTABLE"] = os.path.join(
            self.build_folder, "bin", f"dimbuilder{dimbuilder_suffix}"
        ).replace("\\", "/")
        # Trim the build to the core library + pdal app.
        tc.cache_variables["WITH_TESTS"] = False
        tc.cache_variables["WITH_ZSTD"] = False
        tc.cache_variables["WITH_ZLIB"] = True
        tc.cache_variables["WITH_LZMA"] = True
        tc.cache_variables["WITH_BACKTRACE"] = False
        tc.cache_variables["WITH_GCS"] = False
        tc.cache_variables["WITH_COMPLETION"] = False
        tc.cache_variables["BUILD_DOCS"] = False
        tc.cache_variables["BUILD_TOOLS_LASDUMP"] = False
        tc.cache_variables["BUILD_TOOLS_NITFWRAP"] = False
        # All optional plugins off (postgres/oci/hdf5/arrow/draco/...).
        tc.cache_variables["BUILD_PLUGIN_CPD"] = False
        tc.cache_variables["BUILD_PLUGIN_DRACO"] = False
        tc.cache_variables["BUILD_PLUGIN_ICEBRIDGE"] = False
        tc.cache_variables["BUILD_PLUGIN_HDF"] = False
        tc.cache_variables["BUILD_PLUGIN_MATLAB"] = False
        tc.cache_variables["BUILD_PLUGIN_NITF"] = False
        tc.cache_variables["BUILD_PLUGIN_OPENSCENEGRAPH"] = False
        tc.cache_variables["BUILD_PLUGIN_PGPOINTCLOUD"] = False
        tc.cache_variables["BUILD_PLUGIN_RIVLIB"] = False
        tc.cache_variables["BUILD_PLUGIN_RDBLIB"] = False
        tc.cache_variables["BUILD_PLUGIN_MBIO"] = False
        tc.cache_variables["BUILD_PLUGIN_FBX"] = False
        tc.cache_variables["BUILD_PLUGIN_TEASER"] = False
        tc.cache_variables["BUILD_PLUGIN_TILEDB"] = False
        tc.cache_variables["BUILD_PLUGIN_TRAJECTORY"] = False
        tc.cache_variables["BUILD_PLUGIN_E57"] = False
        tc.cache_variables["BUILD_PLUGIN_ARROW"] = False
        tc.cache_variables["BUILD_PLUGIN_SPZ"] = False
        # Stop CMake from finding system libxml2/backtrace helpers.
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Libexecinfo"] = True
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_Libunwind"] = True
        tc.cache_variables["CMAKE_DISABLE_FIND_PACKAGE_OpenSSL"] = True
        tc.generate()

        deps = CMakeDeps(self)
        deps.generate()

        # PDAL generates Dimension.hpp by RUNNING the just-built `dimbuilder`
        # binary during cmake --build.  The OHOS loader has no default search
        # path for libc++_shared.so (clang's C++ runtime), so the binary fails
        # with "Error loading shared library libc++_shared.so".  Locate the
        # runtime next to the compiler configured in the profile and prepend
        # its directory to LD_LIBRARY_PATH for the build.
        env = Environment()
        cpp_exe = None
        try:
            compilers = self.conf.get("tools.build:compiler_executables",
                                      check_type=None)
            if isinstance(compilers, dict):
                cpp_exe = compilers.get("cpp")
        except Exception:
            cpp_exe = None
        if not cpp_exe:
            cpp_exe = "c++"
        libcxx_shared = ""
        try:
            libcxx_shared = subprocess.run(
                [cpp_exe, "-print-file-name=libc++_shared.so"],
                capture_output=True, text=True, timeout=60,
            ).stdout.strip()
        except Exception:
            libcxx_shared = ""
        if libcxx_shared and os.path.isfile(libcxx_shared):
            env.prepend_path("LD_LIBRARY_PATH", os.path.dirname(libcxx_shared))
        # NOTE: dependency libdirs are deliberately NOT added here.  The SDK
        # linker (lld, an arm64-musl binary) resolves its own libxml2.so.16
        # through RUNPATH ($ORIGIN/../lib inside the SDK).  Any LD_LIBRARY_PATH
        # entry pointing at conan's OHOS-cross libxml2 hijacks that lookup and
        # breaks lld with "symbol not found" relocation errors — verified
        # locally 2026-09-03.  Workers whose SDK lib dir lacks libxml2.so.16
        # are environment-broken; retry on another worker (see notes.md).
        env.vars(self, scope="build").save_script("conanbuild_loader_path")

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        # License files of PDAL itself and the vendored third-party code.
        lic = os.path.join(self.package_folder, "licenses")
        copy(self, "LICENSE.txt", src=self.source_folder, dst=lic)
        for vendor, fname in (
            ("arbiter", ("LICENSE", "arbiter_LICENSE.txt")),
            ("utfcpp", ("LICENSE", "utfcpp_LICENSE.txt")),
        ):
            src = os.path.join(self.source_folder, "vendor", vendor, fname[0])
            if os.path.isfile(src):
                copy(self, fname[0], src=os.path.join(self.source_folder, "vendor", vendor),
                     dst=lic)
                dst_name = os.path.join(lic, fname[1])
                src_name = os.path.join(lic, fname[0])
                if src_name != dst_name and os.path.exists(src_name):
                    os.replace(src_name, dst_name)

        cmake = CMake(self)
        cmake.install()

        # Remove the upstream-installed CMake config: CMakeDeps generates its
        # own PDALConfig.cmake from cpp_info and a duplicate would conflict.
        from conan.tools.files import rmdir
        rmdir(self, os.path.join(self.package_folder, "lib", "cmake"))
        rmdir(self, os.path.join(self.package_folder, "lib", "pkgconfig"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "PDAL")
        self.cpp_info.set_property("cmake_target_name", "pdal::pdal")
        self.cpp_info.set_property("pkg_config_name", "pdal")
        self.cpp_info.libs = ["pdalcpp"]
        self.cpp_info.includedirs = ["include"]
        if self.settings.os in ("Linux", "OHOS", "FreeBSD", "Android"):
            self.cpp_info.system_libs = ["dl", "m", "pthread"]
        elif self.settings.os == "Windows":
            self.cpp_info.system_libs = ["shlwapi", "ws2_32"]
