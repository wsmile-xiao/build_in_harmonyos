#!/usr/bin/env python3
"""test_package for argyll-cms 3.5.0 — consumer tests (R34: really execute the
packaged binaries).

test() runs two scripts, both of which invoke the tools installed by the
package (`conanrun` env, so `bin/` is on PATH):

1. test.sh       — 功能测试（上游行为视角，8 条断言）：ICC profile 解析
                   （iccdump ×2）、色彩转换引擎正/反向（icclu ×3，含 RGB→Lab→RGB
                   往返一致性）、色域引擎（iccgamut 产出 .gam）、测试图表生成
                   （targen 产出 .ti1）、以及 X11 链接的 GUI 工具能否加载运行。
2. test_ohos.sh  — 鸿蒙特有测试（14 条断言）：平台身份、ELF64/AArch64/PIE、
                   musl 解释器（/lib/ld-musl-aarch64.so.1）、无 glibc 专有
                   NEEDED、.note.ohos.ident/.codesign 段、RUNPATH 不指向系统
                   库目录（R26）、GUI 工具的 X11 NEEDED 集、无显示服务时优雅
                   退出、ref/ 参考数据随包、任意 cwd 可运行、包载荷完整。
"""
import os
import shutil

from conan import ConanFile


class ArgyllCmsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["argyll-cms"].package_folder
        bindir = os.path.join(pkg, "bin")
        refdir = os.path.join(pkg, "ref")
        for path in (os.path.join(bindir, "iccdump"), os.path.join(bindir, "dispwin")):
            if not os.path.isfile(path):
                raise FileNotFoundError(f"packaged binary not found: {path}")
        if not os.path.isfile(os.path.join(refdir, "sRGB.icm")):
            raise FileNotFoundError(f"packaged reference data not found: {refdir}")

        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries — wrap with bash.
        # isfile() instead of os.access(X_OK): chmod is ignored on HMDFS and
        # X_OK is always False (R49/E046).
        bash = os.environ.get("CONFIG_SHELL", "")
        if not (bash and os.path.isfile(bash)):
            bash = shutil.which("bash") or ""
        if not (bash and os.path.isfile(bash)):
            fallback = "/data/service/hnp/bin/bash"
            bash = fallback if os.path.isfile(fallback) else ""
        if not bash:
            raise FileNotFoundError("bash not found (set CONFIG_SHELL or add bash to PATH)")

        self.run(f'"{bash}" test.sh "{bindir}" "{refdir}"',
                 env="conanrun", cwd=self.source_folder)
        self.run(f'"{bash}" test_ohos.sh "{pkg}"',
                 env="conanrun", cwd=self.source_folder)
