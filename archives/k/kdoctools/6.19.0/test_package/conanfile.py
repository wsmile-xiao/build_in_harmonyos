#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.tools.build import can_run


class KDocToolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _check_binary_exists(self):
        """检查 meinproc 二进制是否已安装到 package 中"""
        binary = os.path.join(self.dependencies["kdoctools"].package_folder, "bin", "meinproc6")
        if os.path.exists(binary):
            self.output.info(f"meinproc binary found: {binary}")
            return True
        self.output.error(f"meinproc binary not found at {binary}")
        return False

    def test(self):
        # 始终检查二进制产物是否存在
        binary_ok = self._check_binary_exists()
        if not binary_ok:
            raise Exception("meinproc binary not found in package")

        # 编译测试源文件：在 shell 命令中直接使用 VirtualBuildEnv 注入的
        # $CC/$CFLAGS（env="conanbuild" 激活后自然展开，指向 OHOS 交叉编译器
        # 及 sysroot flags），避免 Python 侧 os.environ.get 裸读（R33）导致
        # 回退到宿主 clang；${CC:-clang} 提供 shell 层回退
        src = os.path.join(self.source_folder, "src", "test_kdoctools.c")
        test_bin = os.path.join(self.build_folder, "test_kdoctools")
        self.run(f'${{CC:-clang}} ${{CFLAGS}} -o "{test_bin}" "{src}"', env="conanbuild")

        if can_run(self):
            # 运行测试程序验证 meinproc 二进制 --help 输出用法信息
            meinproc_bin = os.path.join(self.dependencies["kdoctools"].package_folder, "bin", "meinproc6")
            self.run(f"{test_bin} {meinproc_bin}", env="conanrun")
            self.output.info("meinproc verified successfully")
        else:
            # 交叉编译场景：无法运行二进制，但已编译测试程序并检查产物存在
            self.output.info("Cross-building: test compiled, binary existence verified")