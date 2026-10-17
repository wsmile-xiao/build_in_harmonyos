import os

from conan import ConanFile
from conan.errors import ConanException


class KlibcRunInitTestConan(ConanFile):
    """test_package：校验包内 run-init 产物并执行负向 smoke（usage + 退出码 1）。"""

    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def _run_init_path(self):
        dep = self.dependencies["klibc-run-init"].cpp_info
        if not dep.bindirs:
            raise ConanException("klibc-run-init package declares no bindirs")
        bindir = dep.bindirs[0]
        if not os.path.isdir(bindir):
            raise ConanException(f"klibc-run-init package bin dir missing: {bindir}")
        prog = os.path.join(bindir, "run-init")
        if not os.path.isfile(prog):
            raise ConanException(f"klibc-run-init package run-init missing: {prog}")
        return prog

    def build(self):
        # R34/L1e：显式校验包内产物，避免假阳性。
        prog = self._run_init_path()
        with open(prog, "rb") as handle:
            data = handle.read()
        # ELF 魔数（0x7F 'E' 'L' 'F'）
        if data[:4] != bytes([127, 69, 76, 70]):
            raise ConanException("packaged run-init is not an ELF binary")
        # OHOS 代码签名段（E077）：无 .codesign 段内核拒绝 exec，负向 smoke 会失败
        if b".codesign" not in data:
            raise ConanException("packaged run-init has no .codesign signature section")

    def test(self):
        # OHOS: /system/bin/sh (mksh) 不能直接 exec ELF，经 hnp bash 包装执行。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        prog = self._run_init_path()
        # 负向 smoke：无参调用期望 usage 并退出码 1（真实删根/MS_MOVE/chroot 路径
        # 需 root/PID-1 上下文，-n dry-run 仍会 chroot，均不在 CI 执行）。
        self.run(f'{bash} test.sh "{prog}"', env="conanrun")
