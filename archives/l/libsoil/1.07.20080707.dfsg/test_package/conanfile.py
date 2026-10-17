#!/usr/bin/env python3
"""Conan test_package — libsoil 1.07.20080707.dfsg L1 test.

真实调用被测库 API（R34 禁空壳）：
  1. test_libsoil 二进制：SOIL_load_image 解码 4 种格式测试图（bmp/png/tga/dds），
     校验尺寸/通道数/关键像素；SOIL_save_image 往返保存；SOIL_last_result。
     测试图为二进制文件、不随仓库提交（否则 CI checkout-pr 的 git apply
     因 missing binary patch data 失败，CI #60156），由 CMakeLists.txt 在
     构建期调用 make_images.py 确定性生成（需 python3，CI 环境自带）。
  2. 鸿蒙平台特有断言（构建产物属性）：
     - 产物是 aarch64-linux-ohos ELF（Machine: AArch64）
     - 无 GLIBC 符号依赖（无 NEEDED 的 glibc 动态库）
     - ELF 已签名（存在 .codesign 段）
"""
import os
import re
import shutil

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.cmake import CMake, cmake_layout


class LibsoilTestConan(ConanFile):
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

    def _readelf_tool(self):
        cc = self.conf.get("tools.build:compiler_executables", check_type=dict, default={}).get("c", "clang")
        cc_dir = os.path.dirname(cc)
        for cand in (os.path.join(cc_dir, "llvm-readelf"),
                     shutil.which("llvm-readelf"),
                     shutil.which("readelf")):
            if cand and os.path.exists(cand):
                return cand
        raise ConanInvalidConfiguration(
            "llvm-readelf or readelf is required for ELF assertions"
        )

    def test(self):
        # ── 1. 运行真实功能测试（调用被测库 API）──
        # CMake 把测试图拷贝到构建目录（CMAKE_CURRENT_BINARY_DIR = self.build_folder），
        # 与可执行文件同目录；test.c 按 argv[1] 加载图片目录
        bin_path = os.path.join(self.cpp.build.bindirs[0], "test_libsoil")
        self.run(f'"{bin_path}" "{self.build_folder}"')

        # ── 2. 鸿蒙平台特有断言 ──
        if str(self.settings.os) != "OHOS":
            self.output.info("非 OHOS 平台，跳过 ELF 平台断言")
            return

        readelf = self._readelf_tool()
        header = self._capture(f"{readelf} -h {bin_path}")
        if not re.search(r"Machine:\s+AArch64", header):
            raise ConanException(
                f"产物不是 aarch64 ELF（Machine 非 AArch64）: {header}"
            )
        self.output.info("PASS: 产物为 aarch64-linux-ohos ELF (Machine: AArch64)")

        dynamic = self._capture(f"{readelf} -d {bin_path}")
        if re.search(r"libc\.so\.6|libm\.so\.6|GLIBC", dynamic):
            raise ConanException(f"产物存在 GLIBC 符号依赖: {dynamic}")
        self.output.info("PASS: 产物无 GLIBC 符号依赖")

        sections = self._capture(f"{readelf} -S {bin_path}")
        if not re.search(r"\.codesign", sections):
            raise ConanException(f"产物未签名（无 .codesign 段）: {sections}")
        self.output.info("PASS: 产物 ELF 已签名（存在 .codesign 段）")

    def _capture(self, cmd: str) -> str:
        import subprocess
        proc = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if proc.returncode != 0:
            raise ConanException(f"命令执行失败 ({cmd}): {proc.stderr or proc.stdout}")
        return proc.stdout
