#!/usr/bin/env python3
"""Consumer test for permlib 0.2.9 (header-only) —— 鸿蒙特有测试.

它证明的是「装进 Conan 包的那一份头文件」在第三方消费者手里可用：
  * `find_package(permlib CONFIG REQUIRED)` + 链接 `permlib::permlib`，
    boost 的 include 路径完全由 permlib 的 `cpp_info.requires = ["boost::headers"]`
    传递（消费者自己不写 boost 路径）；
  * 断言逐条在 `test.cpp` 里给出，对照物是闭式公式 / 自写 BFS 暴力枚举 /
    另一条构造路径，不靠被测库自证；
  * `test()` 里跑**两遍**：① Conan 注入的 conanrun 环境；② **裸环境**
    （`env -u LD_LIBRARY_PATH`）—— 裸环境也通过才说明消费者不依赖任何兜底的
    库路径（设备里已有的头/库"喂饱"这类假绿正是这样排除的）；
  * 断言前先核对**包目录里的实物**（`<pkg>_PACKAGE_FOLDER_<CONFIG>`/dependencies
    package_folder 取路径）：头文件不在包里就直接 FATAL，不让消费者从别处捡到头。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class PermlibTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        tc = CMakeToolchain(self)
        tc.variables["CMAKE_CXX_STANDARD"] = "17"
        tc.variables["CMAKE_CXX_STANDARD_REQUIRED"] = "ON"
        if self.settings.os in ("Linux", "OHOS"):
            tc.variables["CMAKE_SYSTEM_NAME"] = "Linux"
        tc.generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build(build_tool_args=["-j2"])

    def test(self):
        # ① 包实物核对：装进包的那一份头文件必须在
        package_folder = self.dependencies[self.tested_reference_str].package_folder
        required_headers = [
            os.path.join("include", "permlib", "version.h"),
            os.path.join("include", "permlib", "permlib_api.h"),
            os.path.join("include", "permlib", "bsgs.h"),
            os.path.join("include", "permlib", "permutation.h"),
        ]
        for rel in required_headers:
            path = os.path.join(package_folder, rel)
            if not os.path.isfile(path):
                raise ConanException("permlib 包头文件缺失（消费者会从别处捡到头 = 假绿）: %s" % path)

        executable = os.path.join(self.cpp.build.bindirs[0], "permlib_consumer_test")
        if not os.path.exists(executable):
            raise ConanException("消费者可执行文件不存在: %s" % executable)

        # ② conanrun 注入环境下的正常运行
        self.run('"%s"' % executable, env="conanrun")
        # ③ 裸环境 smoke：不靠 LD_LIBRARY_PATH 等注入也能跑
        self.run('env -u LD_LIBRARY_PATH "%s"' % executable)
