# conanfile.py - KFR 3.0.8
# HarmonyOS PC adaptation (OHOS 6.0 / aarch64 / musl / clang 15, native build).
import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get

required_conan_version = ">=1.52.0"


class KfrConan(ConanFile):
    name = "kfr"
    version = "3.0.8"
    description = ("Fast, modern C++ DSP framework: FFT, sample rate conversion, "
                   "FIR/IIR/Biquad filters")
    homepage = "https://www.kfrlib.com"
    license = "GPL-2.0-only"
    url = "https://github.com/kfrlib/kfr"
    topics = ("dsp", "fft", "filters", "simd", "audio")

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
        get(self, **self.conan_data["sources"], destination=self.source_folder, strip_root=True)

    def layout(self):
        cmake_layout(self, src_folder="src")

    def generate(self):
        tc = CMakeToolchain(self)
        # CMake 4.x removed compatibility with cmake_minimum_required(< 3.5);
        # KFR 3.0.8 declares 3.1 in the top level, tests/, examples/ and
        # tools/ CMakeLists. The override must be visible before the first
        # cmake_minimum_required() runs, so it has to be a command line
        # definition (cache_variables). Putting it in tc.variables would be
        # too late: conan_toolchain.cmake is included from inside the project
        # CMakeLists. See knowledge draft DRAFT-E321.
        tc.cache_variables["CMAKE_POLICY_VERSION_MINIMUM"] = "3.5"
        # Upstream defaults: ENABLE_TESTS=OFF, ENABLE_DFT=ON when the compiler
        # is Clang, CPU_ARCH=detect (auto-detection only runs on x86).
        tc.variables["ENABLE_TESTS"] = bool(self.options.with_tests)
        tc.variables["ENABLE_DFT"] = bool(self.options.dft)
        # SKIP_TESTS=OFF keeps the CTest entry in tests/CMakeLists.txt enabled
        # even for build-only runs, so the upstream suite is always registered.
        tc.variables["SKIP_TESTS"] = False
        tc.variables["CPU_ARCH"] = "generic"
        # Upstream only ever produces static archives; keep shared off so the
        # installed layout matches the declared options.
        tc.variables["BUILD_SHARED_LIBS"] = False
        tc.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        if self.options.with_tests:
            # Upstream registers its CTest entries inside tests/CMakeLists.txt
            # (enable_testing() is called there, not at the top level), so the
            # root build tree has no `make test` / `cmake --build --target test`
            # rule. Run ctest from the tests/ build directory instead, where
            # CTestTestfile.cmake is emitted.
            # Registered tests on aarch64: exactly one, `all_tests`, i.e.
            # bin/all_tests built from all_tests.cpp + the 7 unit test
            # translation units (53 TEST() cases in total).
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
        # kfr itself is an INTERFACE (header only) library; the compiled parts
        # are kfr_io always and kfr_dft when the DFT support is enabled.
        libs = ["kfr_io"]
        if self.options.dft:
            libs.append("kfr_dft")
        self.cpp_info.libs = libs
        if self.settings.os in ("Linux", "OHOS"):
            self.cpp_info.system_libs = ["m", "pthread"]
