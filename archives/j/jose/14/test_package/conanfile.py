import os

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout


class JoseTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # CMakeToolchain 由下面的 generate() 显式创建（要往里塞 JOSE_BIN），
    # 所以不再放进 generators，避免生成两份 toolchain。
    generators = "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 只额外声明 jansson：jose 的公共头会 include <jansson.h>。故意不再把
        # openssl/zlib 塞进来，让消费者测试跑在「只依赖 jose 一个包」的真实
        # 处境下 —— 若配方少传了运行期信息，这里就会立刻暴露。
        self.requires("jansson/2.15.1.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        # 把「安装后的 jose 可执行文件绝对路径」交给 C 测试：安装包专项测试要跑
        # 的就是消费者拿到的那个二进制，不能依赖 shell 的 PATH 语义。
        jose = self.dependencies["jose"]
        tc = CMakeToolchain(self)
        tc.variables["JOSE_BIN"] = os.path.join(jose.package_folder, "bin",
                                                "jose").replace("\\", "/")
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 编译在 conanbuild（CMake helper 默认），运行必须在 conanrun：
        # 静态包仍要能在运行期定位到 libjansson.so/libcrypto.so。
        for name in ("test_jose", "test_jose_ohos"):
            exe = os.path.join(self.cpp.build.bindirs[0], name)
            self.run(exe, env="conanrun")
