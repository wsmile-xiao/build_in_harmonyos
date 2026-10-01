"""Conan recipe — libebur128 1.2.6 (CMake build).

libebur128 is a library implementing the EBU R128 loudness
standard (ITU-R BS.1770 gated loudness, LRA, sample peak).
Pure C, no external runtime dependencies on POSIX targets
(only libm); upstream tests need libsndfile which has no
OHOS package, so the upstream test suite is not run in
build() — see notes.md for the documented skip and the
consumer-side coverage in test_package/.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get


class Libebur128Conan(ConanFile):
    name = "libebur128"
    version = "1.2.6"
    description = "Library implementing the EBU R128 loudness standard (gated loudness, loudness range, sample peak)"
    license = "MIT"
    homepage = "https://github.com/jiixyj/libebur128"
    url = "https://github.com/jiixyj/libebur128"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False], "fPIC": [True, False]}
    default_options = {"shared": False, "fPIC": True}

    def export_sources(self):
        export_conandata_patches(self)

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def validate(self):
        # Upstream is pure C99 + POSIX; OHOS shares the Linux code path
        # (sys/queue.h exists in musl, so the internal queue.h fallback
        # is not needed either).
        if self.settings.os not in ("Linux", "OHOS", "Windows", "Macos", "FreeBSD", "Android"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        cmake_layout(self, src_folder=".")

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        toolchain = CMakeToolchain(self)
        # Upstream toggles shared/static via the global BUILD_SHARED_LIBS.
        toolchain.variables["BUILD_SHARED_LIBS"] = bool(self.options.shared)
        if not self.options.shared and self.settings.os != "Windows":
            # Build the static archive with -fPIC so consumers can link it
            # into shared libraries (E005).
            toolchain.variables["WITH_STATIC_PIC"] = True
        toolchain.variables["ENABLE_TESTS"] = False
        toolchain.variables["ENABLE_FUZZER"] = False
        toolchain.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # Upstream test suite (test/tests.c) requires libsndfile plus the
        # R128 test vectors fetched at configure time; libsndfile has no
        # OHOS Conan package, so ENABLE_TESTS stays OFF and the upstream
        # suite is skipped here. The published 2026-06-03 prebuilt-package
        # adaptation ran an equivalent 43-check functional suite on the
        # device (see notes.md); test_package/ covers the consumer side.

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "COPYING", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        # CMake target: ebur128 (libebur128.a / libebur128.so, header ebur128.h)
        self.cpp_info.libs = ["ebur128"]
        self.cpp_info.set_property("pkg_config_name", "libebur128")
        if self.settings.os in ("Linux", "OHOS", "FreeBSD", "Android"):
            # ebur128/CMakeLists.txt links libm where find_library(m) succeeds.
            self.cpp_info.system_libs = ["m"]
