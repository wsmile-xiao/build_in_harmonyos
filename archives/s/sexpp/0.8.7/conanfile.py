#!/usr/bin/env python3
"""Conan recipe — sexpp 0.8.7

sexpp: S-expressions parser and generator C++ library (MIT), compliant with
Rivest's Sexp.txt. Build system: CMake (upstream requires >= 3.14).

HarmonyOS adaptation notes:
- Library plus the upstream `sexpp` CLI are built; the CLI is installed into
  bin/ and declared through the software-level commands.json (R38).
- The upstream GoogleTest suite (tests/src/*.cpp) is really built and executed
  inside build() through ctest. Upstream fetches googletest with CMake
  FetchContent from github.com, which the OHOS device cannot reach, so
  DOWNLOAD_GTEST=OFF plus find_package(GTest REQUIRED) is used and googletest
  comes from the conan registry (gtest/1.17.0) as a test_requires — it stays
  out of the consumers' dependency closure.
- The two CaptureStdout()/CaptureStderr() warning tests abort unless their
  scratch file lands in a writable directory: /tmp and /data/local/tmp are
  both read-only on OHOS. The registry gtest/1.17.0 package carries
  patches/0001-tmpdir-ohos-sandbox.patch, which makes that scratch path come
  from getenv("TMPDIR") only (measured: TMP/TEMP/TEST_TMPDIR are ignored), so
  build() exports TMPDIR to a writable directory inside the build folder
  before ctest runs and all 68 cases execute.
"""
import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get


class SexppConan(ConanFile):
    name = "sexpp"
    version = "0.8.7"
    description = "S-expressions parser and generator C++ library, fully compliant to Rivest's Sexp.txt"
    license = "MIT"
    homepage = "https://github.com/rnpgp/sexpp"
    url = ""  # CI fills this

    package_type = "library"

    settings = "os", "compiler", "build_type", "arch"
    options = {"shared": [True, False]}
    default_options = {"shared": False}

    def export_sources(self):
        export_conandata_patches(self)

    def build_requirements(self):
        # Upstream unit tests need GoogleTest. Declared as test_requires so it
        # is available to build() without leaking into the consumer closure.
        self.test_requires("gtest/1.17.0")

    def layout(self):
        cmake_layout(self)

    def source(self):
        # codeload URL carries no ".tar.gz" suffix: pin the filename so Conan
        # does not mistake the stream for a ZIP archive (libmongocrypt lesson).
        get(self, **self.conan_data["sources"], strip_root=True,
            filename="sexpp-0.8.7.tar.gz")

    def generate(self):
        tc = CMakeToolchain(self)
        tc.variables["BUILD_SHARED_LIBS"] = "ON" if self.options.shared else "OFF"
        # Build the upstream GoogleTest suite so build() can run it
        tc.variables["WITH_SEXP_TESTS"] = "ON"
        tc.variables["WITH_SEXP_CLI"] = "ON"
        # Never let CMake FetchContent reach github.com from the OHOS device:
        # resolve GoogleTest from the conan-provided package instead.
        tc.variables["DOWNLOAD_GTEST"] = "OFF"
        gtest = self.dependencies.get("gtest")
        if gtest:
            tc.variables["GTest_DIR"] = os.path.join(
                gtest.package_folder, "lib", "cmake", "GTest").replace("\\", "/")
        tc.generate()
        deps = CMakeDeps(self)
        deps.generate()

    def build(self):
        apply_conandata_patches(self)
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # L1: run the upstream unit suite on the device. ctest is driven by
        # gtest_discover_tests(), which enumerates the cases by executing the
        # freshly built sexpp-tests binary (native OHOS aarch64 build).
        if can_run(self):
            tmpdir = os.path.join(self.build_folder, "gtest-tmp")
            os.makedirs(tmpdir, exist_ok=True)
            test_env = Environment()
            # The registry gtest/1.17.0 reads exactly one variable here:
            # TMPDIR. TMP/TEMP/TEST_TMPDIR were measured to be no-ops.
            test_env.define("TMPDIR", tmpdir)
            test_env.define("CTEST_OUTPUT_ON_FAILURE", "1")
            with test_env.vars(self).apply():
                cmake.test()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        self.cpp_info.libs = ["sexpp"]
        self.cpp_info.set_property("cmake_file_name", "sexpp")
        self.cpp_info.set_property("cmake_target_name", "sexpp::sexpp")
