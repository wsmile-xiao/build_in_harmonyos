#!/usr/bin/env python3
"""test_package — parted 3.8（CLI 工具包）。

- test.sh      功能 E2E（R34：真实执行包内 parted/partprobe；sparse 镜像上
               mklabel/mkpart/print/rm/JSON 等行为断言）
- test_ohos.sh 鸿蒙特有断言（R53：平台身份、ELF64/AArch64/PIE、musl 解释器、
               无 glibc NEEDED、.note.ohos.ident/.codesign、RUNPATH 无系统目录、
               libparted.so.2 依赖、任意 cwd 可运行、载荷完整）

脚本用 bash 包装执行：OHOS /system/bin/sh(mksh) 对部分构建产物不可靠，
且 test.sh 使用 bash 特性（argyll-cms 同款先例）。
"""
import os
import shutil

from conan import ConanFile


class PartedTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["parted"].package_folder
        bindir = os.path.join(pkg, "bin")
        for exe in ("parted", "partprobe"):
            if not os.path.isfile(os.path.join(bindir, exe)):
                raise FileNotFoundError(f"packaged binary not found: {bindir}/{exe}")

        bash = os.environ.get("CONFIG_SHELL", "")
        if not (bash and os.path.isfile(bash)):
            bash = shutil.which("bash") or ""
        if not (bash and os.path.isfile(bash)):
            fallback = "/data/service/hnp/bin/bash"
            bash = fallback if os.path.isfile(fallback) else ""
        if not bash:
            raise FileNotFoundError("bash not found (set CONFIG_SHELL or add bash to PATH)")

        self.run(f'"{bash}" test.sh "{bindir}"', env="conanrun",
                 cwd=self.source_folder)
        self.run(f'"{bash}" test_ohos.sh "{pkg}"', env="conanrun",
                 cwd=self.source_folder)
