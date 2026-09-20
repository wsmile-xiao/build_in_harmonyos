#!/usr/bin/env python3
"""Conan recipe for resolv-wrapper 1.1.8 (cwrap, DNS resolving wrapper).

CMake C library producing libresolv_wrapper.so, a LD_PRELOAD interposer for
the resolver API (res_*).  Only depends on system libc/libdl + POSIX headers.

OHOS notes:
  * OHOS libc exposes only the classic resolver API (res_init/res_query/
    res_search); the thread-safe res_n* family is absent and libresolv.a is
    an empty placeholder.  The recipe builds the wrapper (which provides its
    own res_n* / res_* exports and binds libc's classic symbols via dlsym).
  * The library is packaged as a shared object (LD_PRELOAD use case), which
    is expected here: it is NOT a system same-name .so (R26 applies only to
    system-name libraries like ncurses/openssl).
"""

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class ResolvWrapperConan(ConanFile):
    name = "resolv-wrapper"
    version = "1.1.8"
    description = "resolv_wrapper - DNS resolving or faking via LD_PRELOAD"
    license = "BSD-3-Clause"
    homepage = "https://cwrap.org/resolv_wrapper.html"
    url = ""  # CI fills this
    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": True, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        if str(self.settings.os) == "OHOS":
            tc.cache_variables["CMAKE_SYSTEM_NAME"] = "Linux"
            tc.cache_variables["CMAKE_SYSTEM_PROCESSOR"] = "aarch64"
        # resolv_wrapper is built as a preload library (shared on all
        # POSIX platforms by design); no UNIT_TESTING in the packaged build.
        tc.variables["UNIT_TESTING"] = "OFF"
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
        # The library ships no headers of its own (resolv.h/arpa/nameser.h come
        # from the system/libc); do not advertise an (empty) include dir.
        self.cpp_info.includedirs = []
        self.cpp_info.set_property("cmake_file_name", "resolv-wrapper")
        self.cpp_info.set_property("cmake_target_name", "resolv-wrapper::resolv-wrapper")
        self.cpp_info.set_property("cmake_config_version_compat", "AnyNewerVersion")
        self.cpp_info.set_property("pkg_config_name", "resolv-wrapper")
        # The library is built as a preload shared object (libresolv_wrapper.so)
        # on all POSIX platforms; that is the deliverable consumers LD_PRELOAD.
        self.cpp_info.libs = ["resolv_wrapper"]
