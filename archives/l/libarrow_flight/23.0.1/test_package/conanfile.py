import os

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import cmake_layout, CMake, CMakeDeps, CMakeToolchain
from conan.tools.env import Environment


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # Transitive deps with cmake_find_mode=none (grpc/protobuf): their
        # native CMake configs must be locatable for the tested package's
        # own config to resolve (find_dependency(grpc) inside
        # libarrow_flight-config.cmake).
        self.requires("grpc/1.70.0")
        self.requires("protobuf/33.6")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # CMakeDeps runs via the generators attribute; here we only add the
        # extra toolchain bits: native config paths for cmake_find_mode=none
        # packages (grpc/protobuf/abseil) that CMakeDeps cannot generate.
        tc = CMakeToolchain(self)
        try:
            grpc = self.dependencies["grpc"]
            tc.variables["gRPC_DIR"] = os.path.join(
                grpc.package_folder, "lib", "cmake", "grpc").replace("\\", "/")
        except KeyError:
            pass
        try:
            protobuf = self.dependencies["protobuf"]
            tc.variables["Protobuf_DIR"] = os.path.join(
                protobuf.package_folder, "lib", "cmake", "protobuf").replace("\\", "/")
            tc.variables["utf8_range_DIR"] = os.path.join(
                protobuf.package_folder, "lib", "cmake", "utf8_range").replace("\\", "/")
        except KeyError:
            pass
        try:
            abseil = self.dependencies["abseil-cpp"]
            tc.variables["absl_DIR"] = os.path.join(
                abseil.package_folder, "lib", "cmake", "absl").replace("\\", "/")
        except KeyError:
            pass
        # Runtime: libc++_shared.so for OHOS-native binaries
        sdk_llvm_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
        if os.path.isdir(sdk_llvm_lib):
            env = Environment()
            env.prepend_path("LD_LIBRARY_PATH", sdk_llvm_lib)
            env.vars(self).save_script("test_runtime_env")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_package")
            # OHOS: libc++_shared.so lives in the SDK llvm/lib directory and
            # is needed at runtime even for statically-linked consumers
            # (grpc/protobuf/abseil are static but libc++ is always dynamic).
            sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
            old_ld = os.environ.get("LD_LIBRARY_PATH", "")
            if os.path.isdir(sdk_lib):
                os.environ["LD_LIBRARY_PATH"] = sdk_lib + (":" + old_ld if old_ld else "")
            self.run(bin_path, env="conanrun")
            os.environ["LD_LIBRARY_PATH"] = old_ld
