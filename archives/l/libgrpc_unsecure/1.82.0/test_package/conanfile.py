from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()

        # libgrpc_unsecure ships no CMake config (module split,
        # cmake_find_mode=none); the test links the libraries directly via
        # the variables below. Registry protobuf/33.6 ships
        # cmake_find_mode=none too, so its config is located explicitly
        # (mirrors the grpc 1.70.0 test_package wiring).
        protobuf = self.dependencies["protobuf"]
        abseil = self.dependencies["abseil-cpp"]
        tc = CMakeToolchain(self)
        pkg = self.dependencies["libgrpc_unsecure"]
        tc.variables["LIBGRPC_UNSECURE_LIB_DIR"] = os.path.join(
            pkg.package_folder, "lib"
        ).replace("\\", "/")
        tc.variables["LIBGRPC_UNSECURE_INC_DIR"] = os.path.join(
            pkg.package_folder, "include"
        ).replace("\\", "/")
        tc.variables["Protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf"
        ).replace("\\", "/")
        tc.variables["protobuf_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "protobuf"
        ).replace("\\", "/")
        tc.variables["utf8_range_DIR"] = os.path.join(
            protobuf.package_folder, "lib", "cmake", "utf8_range"
        ).replace("\\", "/")
        tc.variables["absl_DIR"] = os.path.join(
            abseil.package_folder, "lib", "cmake", "absl"
        ).replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            # OHOS: libc++_shared.so lives in the SDK llvm/lib directory;
            # the conanrun env does not include it, so prepend it before
            # ctest spawns the binary (also covers directly linked shared
            # registry deps like libc++_shared.so via re2/openssl).
            sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
            env = Environment()
            if os.path.isdir(sdk_lib):
                env.prepend_path("LD_LIBRARY_PATH", sdk_lib)
            with env.vars(self).apply():
                self.run(
                    "ctest --output-on-failure --no-tests=error",
                    cwd=self.build_folder,
                    env="conanrun",
                )
