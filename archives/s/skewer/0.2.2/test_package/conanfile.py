#!/usr/bin/env python3
"""Conan test_package for skewer 0.2.2 — HarmonyOS consumer test via test_skewer.sh.

上游无任何测试套件（见 MANIFEST.yml 的三条清点证据），因此本 test_package 就是
唯一的行为验证层。test_skewer.sh 用**已安装包**里的 bin/skewer 跑 10 条断言：
版本/用法/参数诊断、版本串内嵌、ELF 架构、musl 解释器、NEEDED 集合、
OHOS .codesign + .note.ohos.ident 与 RPATH/RUNPATH、真实 FASTQ 的
适配子剪切功能断言（100bp → 42bp，偶数 8 条），以及奇数条（5 条）不丢
最后一条的缺陷回归断言（A10，钉死 EOF 哨兵补丁）。

R34: 必须真实执行被测包的可执行文件——不能只 print；L1e 会做破坏性反向验证。
"""

import os
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class SkewerTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        # run=True: application 包的 bin/ 只有作为 run 依赖才会进 VirtualRunEnv
        # 的 PATH（M19 教训）；断言本身用绝对路径，PATH 只是冗余保险。
        self.requires(self.tested_reference_str, run=True)

    def test(self):
        dep = self.dependencies["skewer"]
        bin_path = os.path.join(dep.package_folder, "bin", "skewer")
        assert os.path.isfile(bin_path), f"skewer binary not found: {bin_path}"
        self.output.info(f"skewer tested package bin: {bin_path}")
        try:
            for entry in sorted(os.listdir(os.path.dirname(bin_path))):
                fp = os.path.join(os.path.dirname(bin_path), entry)
                self.output.info(
                    "skewer bindir entry: %s size=%s exec=%s"
                    % (entry, os.path.getsize(fp), os.access(fp, os.X_OK)))
        except OSError as exc:  # 仅诊断，不影响断言
            self.output.warning(f"list skewer bindir failed: {exc}")

        if not can_run(self):
            # 交叉构建（host 无法执行目标产物）时退化到 ELF 魔数断言，
            # 仍然真实依赖被测产物；真机与 CI 均走下面的完整断言分支。
            with open(bin_path, "rb") as handle:
                magic = handle.read(4)
            assert magic == b"\x7fELF", f"skewer is not an ELF binary: {magic!r}"
            self.output.info(f"skewer binary present with ELF magic: {bin_path}")
            return

        script = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                              "test_skewer.sh")
        shell = self._usable_shell()
        scratch = self._usable_tmpdir()
        self.run(
            f'"{shell}" "{script}" "{bin_path}" "{scratch}"',
            env="conanrun",
        )

    def _usable_shell(self):
        # 真机实测：/bin/sh 可直接 exec 本产物（A1..A10 全绿），优先它；
        # HMBS 侧能力口径同样是 shell=/bin/sh。HNP bash 在部分宿主上
        # "inaccessible or not found"（bwm 教训），只作最后兜底。
        for cand in ("/bin/sh",
                     shutil.which("sh") or "",
                     os.environ.get("CONFIG_SHELL") or "",
                     "/data/service/hnp/bin/bash"):
            if cand and os.path.isfile(cand):
                return cand
        return "/bin/sh"

    def _usable_tmpdir(self):
        # OHOS /tmp 只读（E002）：只接受真实存在的目录，否则落到包构建目录。
        for var in ("TMPDIR", "TMP", "TEMP"):
            cand = os.environ.get(var, "")
            if cand and os.path.isdir(cand):
                return cand
        scratch = os.path.join(os.path.abspath(self.build_folder), "tmp")
        os.makedirs(scratch, exist_ok=True)
        return scratch
