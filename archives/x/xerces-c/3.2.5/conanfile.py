#!/usr/bin/env python3
"""Conan recipe for xerces-c 3.2.5 — CMake build system.

Apache Xerces-C++ is a validating XML parser written in C++. This recipe
builds it as a static library for HarmonyOS PC (aarch64, musl/clang).

The CMake platform detection in xerces-c keys off the universal UNIX/WIN32/
APPLE flags (no ``STREQUAL "Linux"`` branch), so it behaves identically under
CMAKE_SYSTEM_NAME=HarmonyOS. The three feature backends are pinned explicitly
to keep the build deterministic and free of external runtime dependencies:

* ``network-accessor=socket``  — native BSD sockets (musl libc), avoids libcurl
* ``transcoder=gnuiconv``      — libc iconv (musl), avoids ICU
* ``message-loader=inmemory``  — built-in message catalog, avoids ICU/NLS

musl provides pthread/iconv/socket directly in libc, so no system libraries
need to be declared. Only the library target is built; upstream's tests/ and
samples/ subdirectories still configure, but their executables are not shipped
— samples/ carries install(TARGETS) rules whose install-time relink
(CMakeRelink.dir) is unsupported on OHOS, so the generated samples install
script is neutralized and the package stays a clean library archive.
"""
from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import get, apply_conandata_patches, export_conandata_patches


class XercesCConan(ConanFile):
    name = "xerces-c"
    version = "3.2.5"
    description = "Apache Xerces-C++ validating XML parser library"
    license = "Apache-2.0"
    homepage = "https://xerces.apache.org/xerces-c/"
    url = ""  # CI fills this

    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # No external Conan deps: transcoder/message-loader/network backends
        # are pinned to libc-only implementations (iconv/inmemory/socket).
        pass

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        # Default static (shared=False): xerces-c is not a system same-name
        # library, but a static archive is the simplest dependency-free
        # deliverable and sidesteps shared-library SONAME/signing concerns.
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Pin the three feature backends to libc-only implementations so the
        # build never auto-picks ICU (transcoder/message-loader) or libcurl
        # (network-accessor), which would add unpublished dependencies (R36).
        tc.variables["network-accessor"] = "socket"
        tc.variables["transcoder"] = "gnuiconv"
        tc.variables["message-loader"] = "inmemory"
        tc.generate()

    def build(self):
        import glob
        import os
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        # Upstream add_subdirectory(samples) is unconditional, and samples/
        # has install(TARGETS <sample exes> …) rules. On OHOS the install-time
        # executable relink (CMakeRelink.dir) those rules trigger is
        # unsupported, and we don't ship samples anyway (xerces-c is a
        # library). Neutralize the generated samples install script so
        # ``cmake --install`` only ships the library + headers.
        samples_install = glob.glob(
            os.path.join(self.build_folder, "**", "samples", "cmake_install.cmake"),
            recursive=True)
        for path in samples_install:
            with open(path, "w") as f:
                f.write("# samples install disabled by recipe "
                        "(library-only package)\n")
        # Build only the library target. tests/samples still configure but are
        # neither built nor shipped; the library + headers are all we deliver.
        # R9: single-job build for the OHOS worker parallel constraint.
        cmake.build(cli_args=["--target", "xerces-c", "--parallel", "1"])

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["xerces-c"]
        self.cpp_info.set_property("cmake_file_name", "xerces-c")
        self.cpp_info.set_property("cmake_target_name", "xerces-c::xerces-c")
        self.cpp_info.set_property("pkg_config_name", "xerces-c")
