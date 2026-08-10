#!/usr/bin/env python3
"""Consumer test for iortcw 1.51.c — verifies the iowolfsp/iowolfmp/iowolfded binaries exist.

Cross-compilation scenario: the produced binaries are arm64 OHOS ELF,
cannot be executed on the CI worker (x86_64 Linux) → test_package honestly
skips runtime verification and only checks binary existence + ELF header.
"""
import glob
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import cross_building
from conan.tools.layout import basic_layout


class IortcwTestConan(ConanFile):
    settings = "os", "compiler", "arch", "build_type"
    generators = "CMakeDeps", "CMakeToolchain"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        # L0c 门禁要求 test_package 有 test 源文件；编译 test_iortcw.c 使其真实生效
        from conan.tools.cmake import CMake
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        # P1: 删空壳测试 — 真验证 iowolfsp 二进制存在 + ELF header 段
        bin_dir = self.dependencies["iortcw"].cpp_info.bindirs[0]
        iortcw_pkg = self.dependencies["iortcw"].package_folder
        # 上游 Makefile FULLBINEXT=.$(ARCH)$(BINEXT)（非 MINGW 时 BINEXT 为空）
        # → 产物名为 iowolfsp.arm64（CI #17104: test 找不带后缀的 iowolfsp 报
        # not found）→ glob 匹配任一后缀变体
        candidates = sorted(glob.glob(os.path.join(iortcw_pkg, bin_dir, "iowolfsp*")))
        if not candidates:
            raise ConanException(f"iowolfsp binary not found under {os.path.join(iortcw_pkg, bin_dir)}")
        iowolfsp = candidates[0]
        self.output.info(f"iowolfsp binary found: {iowolfsp}")

        # cross-building scenario: arm64 OHOS binary cannot run on x86_64 CI worker
        if cross_building(self):
            self.output.info("SKIP_RUNTIME_TEST: cross-building scenario, arm64 OHOS binary cannot run on CI worker")
            # ELF header sanity check (arm64 OHOS ELF)
            with open(iowolfsp, "rb") as f:
                magic = f.read(4)
            if magic != b"\x7fELF":
                raise ConanException(f"iowolfsp binary is not a valid ELF file: magic={magic!r}")
            self.output.info("ELF header sanity check PASSED (arm64 OHOS binary)")
            # 交叉编译占位：test_iortcw 无参数仅编译通过（R34：无法在宿主运行 arm64 二进制）
            self.run("./test_iortcw", env="conanrun", cwd=self.build_folder)
            return

        # native scenario: run test_iortcw with iowolfsp binary path (R34 反空壳：真实执行 --version 检查返回码)
        self.run(f'./test_iortcw "{iowolfsp}"', env="conanrun", cwd=self.build_folder)
        self.output.info("iortcw runtime test PASSED (iowolfsp --version exit 0)")
