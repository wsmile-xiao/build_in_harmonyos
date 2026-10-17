#!/usr/bin/env python3
import os
from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class OpenspTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualBuildEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _check_binary_exists(self, name):
        binary = os.path.join(self.dependencies["opensp"].package_folder, "bin", name)
        if os.path.exists(binary):
            self.output.info(f"opensp binary found: {binary}")
            return True
        self.output.error(f"opensp binary not found at {binary}")
        return False

    def test(self):
        # 检查多个关键二进制产物
        # opensp 二进制带 o 前缀（onsgmls/osgmlnorm/osx/ospam 等，非 nsgmls）
        binaries = ["onsgmls", "osgmlnorm", "osx", "ospam"]
        all_ok = all(self._check_binary_exists(b) for b in binaries)
        if not all_ok:
            raise Exception("Some opensp binaries not found in package")

        # 编译测试源文件（Conan 编译器标识符 ≠ 二进制名：apple-clang 的
        # C 编译器是 clang，非 apple-clang；gcc/clang 标识符即二进制名）
        cc_map = {"apple-clang": "clang"}
        cc = cc_map.get(str(self.settings.compiler), str(self.settings.compiler))
        src = os.path.join(self.source_folder, "src", "test_opensp.c")
        test_bin = os.path.join(self.build_folder, "test_opensp")
        ret = self.run(f"{cc} -o {test_bin} {src}")
        if ret != 0:
            raise ConanException(f"test_opensp.c compilation failed with exit code {ret}")

        if can_run(self):
            # 运行测试程序验证 onsgmls --help 输出（失败即测试失败）。
            # env="conanrun"：onsgmls 的 rpath 为 //lib（configure --prefix=/
            # 导致无效路径），运行时找不到 libosp.so（在包 lib/）→ --help
            # 输出动态链接错误；conanrun 环境注入 LD_LIBRARY_PATH 含包 lib
            nsgmls_bin = os.path.join(self.dependencies["opensp"].package_folder, "bin", "onsgmls")
            ret = self.run(f"{test_bin} {nsgmls_bin}", env="conanrun")
            if ret != 0:
                raise ConanException(f"opensp test run failed with exit code {ret}")
            self.output.info("opensp binaries verified successfully")
        else:
            # 交叉编译场景：无法运行二进制，但已编译测试程序并检查产物存在
            self.output.info("Cross-building: test compiled, binary existence verified")