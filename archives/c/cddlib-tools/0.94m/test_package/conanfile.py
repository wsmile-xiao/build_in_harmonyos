#!/usr/bin/env python3
"""Conan test_package — cddlib-tools 0.94m (command-line tools)

真实计算断言：编译 test_cddlib_tools.c，实际执行被测包 cddexec 二进制，
对 6 维超立方体的 H-表示做 --rep 变换，断言输出 V-表示有 2^6 = 64 个顶点
（可手算的精确值）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class CddlibtoolsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def build(self):
        """编译测试源 test_cddlib_tools.c（.c 测试源由 L0c 结构门禁强制要求，
        此处实际编译它，test() 阶段运行编译产物）。"""
        bindir = self.dependencies["cddlib-tools"].cpp_info.bindirs[0]
        self.output.info(f"cddlib-tools bindirs[0] = {bindir}")
        src = os.path.join(self.source_folder, "test_cddlib_tools.c")
        if not os.path.isfile(src):
            raise ConanException(f"missing test source: {src}")
        cc = os.environ.get("CC", "clang")
        exe = os.path.join(self.build_folder, "test_cddlib_tools")
        self.run(f'"{cc}" "{src}" -o "{exe}"', env="conanbuild")

    def test(self):
        bindir = self.dependencies["cddlib-tools"].cpp_info.bindirs[0]
        executable = os.path.join(bindir, "cddexec")
        if not os.path.isfile(executable):
            raise ConanException(f"missing packaged executable: {executable}")
        if not can_run(self):
            self.output.info("cross build: executable exists; runtime is validated on the OHOS emulator")
            return
        exe = os.path.join(self.build_folder, "test_cddlib_tools")
        if not os.path.isfile(exe):
            raise ConanException(f"test binary not built: {exe}")
        # env="conanrun" 注入 VirtualRunEnv 的 LD_LIBRARY_PATH（含包内 lib/），
        # 否则 cddexec 运行时找不到 libcdd.so，退出码 127。
        self.run(f'"{exe}" "{executable}"', env="conanrun", ignore_errors=False)
        self.output.info("cddlib-tools: 6 维超立方体 H→V 得到 64 个顶点，断言通过")