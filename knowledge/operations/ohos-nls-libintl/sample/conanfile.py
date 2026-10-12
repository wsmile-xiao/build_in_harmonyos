from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout
from conan.tools.files import copy
import os


class I18nDemoConan(ConanFile):
    """OHOS NLS/gettext 适配样例库（最小复现 + 三种处理策略）。

    同一份调用 gettext 家族函数的源码，三种 nls_mode：
      * none    —— 不提供任何 gettext 声明：复现缺陷态（GNU/glibc 可隐式声明，
                   OHOS/musl 直接编译失败）
      * gettext —— 策略①：依赖 gettext 包（真实 libintl.h + libintl）
      * shim    —— 策略③：使用随样例附带的 shim/include/libintl.h（声明 + 恒等实现，
                   不引入外部依赖），适用于"无本地化需求"的兜底
    """

    name = "i18n-demo"
    version = "1.0.0"
    description = "Minimal reproducer: gettext/libintl portability (GNU glibc vs OHOS musl)"
    license = "MIT"
    package_type = "library"

    settings = "os", "arch", "compiler", "build_type"
    options = {
        "shared": [True, False],
        "fPIC": [True, False],
        "nls_mode": ["none", "gettext", "shim"],
    }
    default_options = {
        "shared": False,
        "fPIC": True,
        "nls_mode": "shim",
    }
    exports_sources = "CMakeLists.txt", "src/*", "include/*", "states/*", "shim/*"

    def requirements(self):
        # 策略①：显式依赖 gettext（提供 libintl.h + libintl）
        if self.options.nls_mode == "gettext":
            self.requires("gettext/0.22.5.1")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        tc = CMakeToolchain(self)
        tc.cache_variables["I18N_DEMO_NLS_MODE"] = str(self.options.nls_mode)
        tc.generate()
        CMakeDeps(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def package(self):
        cmake = CMake(self)
        cmake.install()
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.libs = ["i18n-demo"]
        self.cpp_info.bindirs = ["bin"]
        if self.options.nls_mode == "gettext":
            # 消费者也要链接 libintl（CMakeDeps 生成 gettext::gettext）
            self.cpp_info.requires = ["gettext::gettext"]
        elif self.options.nls_mode == "shim":
            # 消费者需要能解析 <libintl.h>：把兜底头的安装目录加入包含路径
            self.cpp_info.includedirs = ["include", "include/shim"]
