# conanfile.py - KFR 7.0.1
# HarmonyOS PC adaptation (OHOS aarch64 / musl / clang, native build).
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)

required_conan_version = ">=1.52.0"


class KfrConan(ConanFile):
    name = "kfr"
    version = "7.0.1"
    description = ("Fast, modern C++ DSP framework: FFT, sample rate conversion, "
                   "FIR/IIR/Biquad filters")
    homepage = "https://www.kfrlib.com"
    license = "GPL-2.0-only"
    url = "https://github.com/kfrlib/kfr"
    topics = ("dsp", "fft", "filters", "simd", "audio")

    package_type = "static-library"
    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "dft": [True, False],
        "with_tests": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "dft": True,
        "with_tests": True,
    }

    exports_sources = "conandata.yml", "patches/*"

    def config_options(self):
        if self.settings.os == "Windows":
            del self.options.fPIC

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        # Fetch the pinned upstream release directly. Keeping the archive out
        # of the PR avoids the worker's checkout-pr failure on binary patches.
        get(self, **self.conan_data["sources"],
            filename="kfr-7.0.1.tar.gz", strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def generate(self):
        tc = CMakeToolchain(self)
        # 7.0.1 declares cmake_minimum_required(VERSION 3.16) everywhere, so the
        # 3.0.8 CMAKE_POLICY_VERSION_MINIMUM=3.5 workaround is no longer needed.
        # Tests (Catch2 suite) and DFT are the parts we build; examples pull in
        # extra surface and are disabled.
        tc.variables["ENABLE_TESTS"] = bool(self.options.with_tests)
        tc.variables["ENABLE_EXAMPLES"] = False
        tc.variables["KFR_ENABLE_DFT"] = bool(self.options.dft)
        # KFR_USE_BOOST_MATH makes src/dsp pull boostorg/math via CMake
        # FetchContent (a git clone of github.com/boostorg/math). github.com is
        # intermittently unreachable from the build device/CI (SSL eof mid-clone),
        # which makes the whole create non-deterministic. The only thing boost
        # buys here is the optional elliptic-filter design helper (kfr::dsp
        # `elliptic()`), which is guarded by KFR_HAVE_ELLIPTIC and referenced by
        # no upstream test. Disable it to build fully offline and deterministically.
        tc.variables["KFR_USE_BOOST_MATH"] = False
        # KFR_SKIP_TESTS=OFF keeps enable_testing()/add_test() in
        # tests/CMakeLists.txt, so the upstream suite is always registered.
        tc.variables["KFR_SKIP_TESTS"] = False
        # CPU_ARCH was renamed KFR_ARCH in 7.x; "generic" is a valid non-x86
        # architecture and matches the CPU_ARCH=generic used for 3.0.8. Runtime
        # multi-arch dispatch (KFR_ENABLE_MULTIARCH) is force-disabled by
        # upstream on non-x86, so there is no IFUNC to worry about here.
        tc.variables["KFR_ARCH"] = "generic"
        # HarmonyOS ships libc++ only. CMake does not model Platform/HarmonyOS,
        # so upstream's own `if (NOT IOS AND NOT ANDROID)` would append
        # `-lstdc++`. Patch 0001 adds a KFR_LINK_LIBSTDCXX switch; drive it off
        # here so STD_LIB is deterministically empty on OHOS (the profile already
        # selects -stdlib=libc++), independent of how the toolchain resolves a
        # stray -lstdc++.
        tc.variables["KFR_LINK_LIBSTDCXX"] = False
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.with_tests:
            # enable_testing() is called inside tests/CMakeLists.txt (not at the
            # root), so CTestTestfile.cmake lives in the tests build directory.
            # It registers two entries on aarch64: `all_tests` (Catch2 unit
            # suite: tests/unit/** + dft_test.cpp) and `audio_test`.
            self.run("ctest --output-on-failure",
                     cwd=os.path.join(self.build_folder, "tests"))

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE.txt", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.set_property("cmake_file_name", "kfr")
        self.cpp_info.set_property("cmake_target_name", "kfr::kfr")
        self.cpp_info.includedirs = ["include"]
        # kfr core is header-only (INTERFACE); the compiled archives we expose
        # are kfr_io always and kfr_dft when DFT support is enabled, matching
        # the symbols the public DSP API the consumer test links against.
        libs = ["kfr_io"]
        if self.options.dft:
            libs.append("kfr_dft")
        self.cpp_info.libs = libs
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
