# test_package/conanfile.py — knxd 0.14.73 消费者测试（R34/PF3）
#
# 两臂：
#   1) test_eibclient —— 真链接被测包的 libeibclient，调用公开 API
#      （EIBSocketURL / EIBSocketLocal / EIB_Poll_FD），
#      产物被搬走时必须编不出/跑不了（CI L1e 破坏性反向验证的前提）；
#   2) test.sh —— 对安装的 knxd/knxtool 二进制做参数语义断言，
#      复用上游 tools/test.sh 的 "Bad argument A–F" 判据（不改语义、不缩分母）。
#
# ⛔ 不在 cwd 写任何参考输出（框架 L1e 会 mv 走产物后对同一 test_package 起第二轮）。
import os

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout
from conan.tools.files import collect_libs


class KnxdTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # 臂 1：链接并运行 libeibclient 的真实 API 调用
        test_bin = os.path.join(self.cpp.build.bindirs[0], "test_eibclient")
        self.run(f'"{test_bin}"', env="conanrun")

        # 臂 2：knxd / knxtool 二进制语义断言（脚本自带计数器与 SUMMARY 行）
        harness = os.path.join(self.recipe_folder, "test.sh")
        self.run(f'sh "{harness}"', env="conanrun")
