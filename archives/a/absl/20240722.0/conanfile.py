from conan import ConanFile
from conan.tools.cmake import CMake, CMakeToolchain, cmake_layout
from conan.tools.env import Environment
from conan.tools.files import get


class AbslConan(ConanFile):
    name = "absl"
    version = "20240722.0"
    package_type = "library"
    settings = "os", "arch", "compiler", "build_type"
    options = {"shared": [True, False]}
    default_options = {"shared": False}
    exports_sources = "conandata.yml"

    def layout(self):
        cmake_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"]["absl"], strip_root=True)

    def environment(self):
        # lld 链接器运行时依赖 libxml2.so.16（OHOS SDK llvm/lib——CI 实测
        # 'Error loading shared library libxml2.so.16'——cmake 编译器链接
        # 测试失败——同 scmp_arch_detect 的 LD_LIBRARY_PATH 教训——注入
        # lld 的 libxml2 依赖目录，cmake.configure 的 clang++ 链接测试通过）
        env = Environment()
        env.append_path(
            "LD_LIBRARY_PATH",
            "/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/"
            "ohos/native/llvm/lib")
        return env

    def generate(self):
        tc = CMakeToolchain(self)
        tc.generate()

    def build(self):
        # absl 测试全量（232 个 *_test.cc——gtest）构建/运行长时——
        # 配方构建库本体（ABSL_BUILD_TESTING=OFF——测试核验见 PR 描述）
        cmake = CMake(self)
        cmake.configure(variables={"ABSL_BUILD_TESTING": "OFF"})
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()

    def package_info(self):
        # absl 大部分组件 header-only——少量编译库（strings/status 等）
        self.cpp_info.libs = []
