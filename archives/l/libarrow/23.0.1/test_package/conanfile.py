from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.cmake import cmake_layout, CMake
import os


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeDeps", "CMakeToolchain", "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if can_run(self):
            bin_path = os.path.join(self.cpp.build.bindirs[0], "test_package")
            # OHOS: libc++_shared.so is in the SDK llvm/lib directory
            # Shared deps (openssl, re2, utf8proc, snappy, zstd) need it at runtime
            sdk_lib = "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib/aarch64-linux-ohos"
            old_ld = os.environ.get("LD_LIBRARY_PATH", "")
            if os.path.isdir(sdk_lib):
                os.environ["LD_LIBRARY_PATH"] = sdk_lib + (":" + old_ld if old_ld else "")
            self.run(bin_path, env="conanrun")
            os.environ["LD_LIBRARY_PATH"] = old_ld
