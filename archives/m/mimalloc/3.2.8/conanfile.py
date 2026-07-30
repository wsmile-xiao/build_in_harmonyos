from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.files import copy, get
import os

class MimallocConan(ConanFile):
    name = "mimalloc"
    version = "3.2.8"
    package_type = "library"
    license = "MIT"
    homepage = "https://github.com/microsoft/mimalloc"
    url = "https://github.com/microsoft/mimalloc"
    description = "mimalloc is a compact general purpose allocator"
    topics = ("allocator", "memory", "performance")
    settings = "os", "compiler", "build_type", "arch"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
    }
    generators = "CMakeDeps"

    def config_options(self):
        if self.settings.os == "Windows":
            self.options.rm_safe("fPIC")

    def configure(self):
        if self.options.shared:
            self.options.rm_safe("fPIC")

    def layout(self):
        cmake_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["MI_OVERRIDE"] = "OFF"
        tc.cache_variables["MI_SECURE"] = "ON"
        # 上游测试套件在 OHOS 平台可用（本地 ctest 验：test-api/test-api-fill/test-stress/test-stress-dynamic 全过 4/4）
        tc.cache_variables["MI_BUILD_TESTS"] = "ON"
        tc.cache_variables["MI_LIBC_MUSL"] = "ON" if self.settings.os == "OHOS" else "OFF"
        tc.cache_variables["MI_DEBUG"] = "ON" if self.settings.build_type == "Debug" else "OFF"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()
        # 跑上游 ctest 套件（MI_BUILD_TESTS=ON）：test-api/test-api-fill/test-stress/test-stress-dynamic
        cmake.test()

    def package(self):
        copy(self, "LICENSE", src=self.source_folder, dst=os.path.join(self.package_folder, "licenses"))
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # mimalloc with MI_SECURE=ON produces libmimalloc-secure
        self.cpp_info.libs = ["mimalloc-secure"]
        # Headers are installed to include/mimalloc-<version>/ by upstream CMake
        self.cpp_info.includedirs = ["include/mimalloc-3.2"]
        if self.settings.os in ["Linux", "OHOS"]:
            self.cpp_info.system_libs = ["pthread", "dl"]
