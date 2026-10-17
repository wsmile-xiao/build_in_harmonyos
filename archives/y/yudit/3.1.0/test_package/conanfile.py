#!/usr/bin/env python3
"""Conan test_package — yudit 3.1.0（OhOS / HarmonyOS PC aarch64）。

L1 测试。yudit 是纯 X11 应用（不产出可链接的库、无公开头文件），因此
test_package 通过**真实执行被测包安装的命令行工具**来验证（R34：实质依赖
被测包，禁止空壳测试）：

  功能用例（test_yudit.sh）
    T1  uniconv  UTF-8 -> UTF-16 -> UTF-8 往返一致性 + BOM 校验
    T2  uniprint 渲染样例为 PostScript 并校验 %!PS-Adobe-3.0 / %%EOF
    T3  yudit    启动并加载完整 X11 运行期依赖链
                 （libX11.so.6 -> libxcb.so.1 / libXau.so.6 / libXdmcp.so.6）

  鸿蒙特有用例（本文件，settings.os == "OHOS" 时执行）
    HMOS-1  产物为鸿蒙 PC 目标 ELF：64 位 + e_machine=AArch64(0xB7)
            + 解释器 /lib/ld-musl-aarch64.so.1
    HMOS-2  产物未被 strip（仍含 .symtab）—— 对应 patches/0001-Makefile.conf.in.patch（安装阶段去掉 -s）
            （鸿蒙 PC 上 strip 后 ELF 签名失效，二进制无法执行）

上游测试审计：yudit 3.1.0 无自动化测试套件（顶层 Makefile.in 的 SUBDIRS 不含
tests/，全仓无 check:/test: 目标；tests/ 仅两个 GUI 手搓程序 rasterizerTest /
toolTest，均无断言，见 test_package/MANIFEST.yml）。上游样例测试在执行
conan create 前由上游 tests/testtext/*.txt 全量 22 例单独跑过并单独汇报。
"""

import os
import shutil

from conan import ConanFile


class YuditTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    # ------------------------------------------------------------------ utils
    def _find_so(self, dep, soname_prefix):
        """在依赖包里定位 SONAME 对应的共享库（优先实体文件，HMFS 软链接不可靠）。"""
        hits = []
        for root, _dirs, files in os.walk(dep.package_folder):
            for name in sorted(files):
                if name.startswith(soname_prefix):
                    hits.append(os.path.join(root, name))
        for path in hits:
            if not os.path.islink(path):
                return path
        return hits[0] if hits else None

    def _runtime_preload(self):
        """按依赖顺序拼 LD_PRELOAD：libXau -> libXdmcp -> libxcb -> libX11。

        OhOS 的 loader 在某些路径下不遵循 LD_LIBRARY_PATH（见 xeyes 先例），
        VirtualRunEnv 之外再加一道绝对路径兜底。
        """
        order = (
            ("libxau", "libXau.so.6"),
            ("libxdmcp", "libXdmcp.so.6"),
            ("libxcb", "libxcb.so.1"),
            ("libx11", "libX11.so.6"),
        )
        found = []
        for name, soname in order:
            try:
                dep = self.dependencies[name]
            except KeyError:
                continue
            so = self._find_so(dep, soname)
            if so:
                found.append(so)
        return ":".join(found)

    # ------------------------------------------------------------- HMOS cases
    @staticmethod
    def _elf_header(path):
        """返回 (ei_class, e_machine) 或 (None, None)。"""
        with open(path, "rb") as handle:
            head = handle.read(20)
        if head[:4] != b"\x7fELF":
            return None, None
        return head[4], int.from_bytes(head[18:20], "little")

    @staticmethod
    def _contains(path, needle):
        with open(path, "rb") as handle:
            return needle in handle.read()

    def _hmost_tests(self, binary):
        results = []
        ei_class, machine = self._elf_header(binary)
        musl = self._contains(binary, b"/lib/ld-musl-aarch64.so.1")
        # HMOS-1: 鸿蒙 PC 目标三元组（aarch64 + musl 解释器）
        if ei_class == 2 and machine == 0xB7 and musl:
            results.append(
                ("HMOS-1", True,
                 "ELF64 AArch64(e_machine=0xB7) + /lib/ld-musl-aarch64.so.1（鸿蒙 PC 目标）")
            )
        else:
            results.append(
                ("HMOS-1", False,
                 f"ELF 目标不符: class={ei_class} machine={machine:#x} musl_interp={musl}")
            )
        # HMOS-2: 未被 strip（patches/0001-Makefile.conf.in.patch 的效果）
        symtab = self._contains(binary, b".symtab")
        if symtab:
            results.append(
                ("HMOS-2", True, "含 .symtab，未被 strip（可正常执行，见 patches/0001-Makefile.conf.in.patch）")
            )
        else:
            results.append(
                ("HMOS-2", False, "缺少 .symtab —— 二进制被 strip，鸿蒙 PC 上将无法执行")
            )
        return results

    # -------------------------------------------------------------------- test
    def test(self):
        dep = self.dependencies["yudit"]
        package_folder = dep.package_folder
        binary = os.path.join(package_folder, "bin", "yudit")

        shell = (os.environ.get("SHELL") or os.environ.get("CONFIG_SHELL")
                 or shutil.which("bash") or "/bin/sh")
        script = os.path.join(self.source_folder, "test_yudit.sh")
        preload = self._runtime_preload()
        if preload:
            self.output.info("runtime LD_PRELOAD=%s" % preload)

        env_prefix = f'LD_PRELOAD="{preload}" ' if preload else ""
        self.run(f'{env_prefix}"{shell}" "{script}" "{package_folder}"', env="conanrun")

        hmos_results = []
        if str(self.settings.os) == "OHOS":
            hmos_results = self._hmost_tests(binary)
            for name, ok, detail in hmos_results:
                self.output.info(f"CASE {name:<7} {'PASS' if ok else 'FAIL'}  {detail}")

        failed = [name for name, ok, _ in hmos_results if not ok]
        assert not failed, f"鸿蒙特有用例失败: {failed}"
