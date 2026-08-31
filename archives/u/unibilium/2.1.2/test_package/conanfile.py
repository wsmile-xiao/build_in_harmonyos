#!/usr/bin/env python3
"""Conan test_package — unibilium 2.1.2 L1 test.

Builds test_unibilium (real API calls: lifecycle, capability round-trips,
serialization via unibi_dump/unibi_from_mem, unibi_run) and executes the
compiled binary (R34 compliance, no stub-only test method).  Additionally
verifies the shipped unibilium.pc can be consumed via pkg-config semantics
(W4 P1-1).
"""
import os

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.cmake import CMake, cmake_layout


class UnibiliumTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "CMakeDeps", "CMakeToolchain"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        cmake_layout(self)

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        binary = os.path.join(self.cpp.build.bindirs[0], "test_unibilium")
        self.run(binary, env="conanrun")
        # P1-1: 验证配方生成的 unibilium.pc 可被 pkg-config 正常消费。
        # CI 环境无 pkg-config 命令，直接在 recipe 内用 Python 解析 .pc：
        # 确认 .pc 存在于包内 lib/pkgconfig，且 Name/Libs/Cflags 字段指向
        # 包内相对路径（${pcfiledir}/../.. 可解析到 prefix）。
        # 注意：用 Python 直接解析而非 self.run 包裹 shell，避免
        # ${pcfiledir}/${includedir}/${libdir} 被外层 shell 展开失真。
        # 与 recipe package() 的 lib/lib64 遍历保持一致（R3-1）：上游未来
        # 若开始在 lib64/pkgconfig 安装同名 .pc，recipe 会复用 lib64 产物，
        # 此处也应能定位到对应 .pc，避免误报失败。
        package_folder = self.dependencies["unibilium"].package_folder
        pc_path = None
        for libsub in ("lib", "lib64"):
            cand = os.path.join(
                package_folder, libsub, "pkgconfig", "unibilium.pc",
            )
            if os.path.exists(cand):
                pc_path = cand
                break
        if pc_path is None:
            raise ConanException(
                "unibilium.pc not found in package lib/pkgconfig or "
                "lib64/pkgconfig"
            )
        with open(pc_path, "r", encoding="utf-8") as fh:
            pc = fh.read()
        for expected in (
            "Name: unibilium",
            "-lunibilium",
            "${pcfiledir}/../..",
            "-I${includedir}",
            "-L${libdir}",
        ):
            if expected not in pc:
                raise ConanException(
                    f"unibilium.pc missing expected token: {expected!r}"
                )
        self.output.info(f"pkg-config check OK: {pc_path}")
