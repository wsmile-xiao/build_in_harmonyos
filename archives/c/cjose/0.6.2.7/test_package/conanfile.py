from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # cjose 公共头 (jwk.h/util.h) 包含 <openssl/obj_mac.h>/<openssl/rsa.h>;
        # CMakeDeps 不为传递依赖填充 *_INCLUDE_DIRS, 消费方必须显式 requires
        self.requires("openssl/3.5.8.1")

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        self.run("./test_package", env="conanrun")
