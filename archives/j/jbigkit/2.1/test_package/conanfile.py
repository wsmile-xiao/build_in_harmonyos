import os
from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.build import cross_building


class JbigkitTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeToolchain", "CMakeDeps"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if cross_building(self):
            self.output.info("cross-building：只验编译+链接")
            return
        # OHOS 的 /system/bin/sh(mksh) 不能直接 exec ELF → 用 bash 包一层；显式 self.run 跑测试二进制
        # （静态库无共享依赖，不需 LD_LIBRARY_PATH）。用 self.run 而非 cmake.test() 以过 CI L0d 反空壳门禁。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_bin = os.path.join(self.cpp.build.bindir, "test_jbig")
        self.run("{} -c '{}'".format(bash, test_bin), env="conanrun")
