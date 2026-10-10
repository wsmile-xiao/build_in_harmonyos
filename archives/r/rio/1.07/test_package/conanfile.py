#!/usr/bin/env python3
"""test_package for rio 1.07 — consumer tests (R34: really execute the
packaged binary).

test() runs two scripts, both of which invoke the tool installed by the
package:

1. test.sh       — 功能测试（上游行为视角，6 条断言）：版本横幅、完整用法表、
                   默认端口/延时、未知选项回退、自定义端口基址、引号参数解析。
2. test_ohos.sh  — 鸿蒙特有测试（15 条断言）：平台身份、ELF64/AArch64/PIE、
                   musl 解释器、无 glibc 专有 NEEDED、.note.ohos.ident 段、
                   无 ISA I/O 端口空间的优雅降级、strerror() 诊断、
                   /dev/port 端口后端正向路径（测试替身）与端口偏移写语义、
                   自定义端口基址、任意 cwd、包载荷完整性。
"""
import os
import shutil

from conan import ConanFile


class RioTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["rio"].package_folder
        binary = os.path.join(pkg, "bin", "rio")
        # isfile() instead of os.access(X_OK): chmod is ignored on HMDFS and
        # X_OK is always False (R49/E046).
        if not os.path.isfile(binary):
            raise FileNotFoundError(f"packaged binary not found: {binary}")

        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries — wrap with bash.
        bash = os.environ.get("CONFIG_SHELL", "")
        if not (bash and os.path.isfile(bash)):
            bash = shutil.which("bash") or ""
        if not (bash and os.path.isfile(bash)):
            fallback = "/data/service/hnp/bin/bash"
            bash = fallback if os.path.isfile(fallback) else ""
        if not bash:
            raise FileNotFoundError("bash not found (set CONFIG_SHELL or add bash to PATH)")

        self.run(f'"{bash}" test.sh "{binary}"',
                 env="conanrun", cwd=self.source_folder)
        self.run(f'"{bash}" test_ohos.sh "{pkg}"',
                 env="conanrun", cwd=self.source_folder)
