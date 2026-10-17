#!/usr/bin/env python3
"""Installed-package API tests for libXpm 3.5.17."""

import os
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


TEST_EXECUTABLES = (
    "libxpm_api_surface",
    "libxpm_version_contract",
    "XpmCreate",
    "XpmMisc",
    "XpmRead",
    "XpmWrite",
)


class LibxpmTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    exports_sources = "CMakeLists.txt", "*.c", "upstream/**"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # glib 2.88.0（PR #6619 已合并发布）：上游 4 个测试
        # XpmCreate/XpmMisc/XpmRead/XpmWrite 的 g_test 框架依赖。
        self.requires("glib/2.88.0")

    def layout(self):
        cmake_layout(self)

    def generate(self):
        CMakeDeps(self).generate()
        CMakeToolchain(self).generate()

    def build(self):
        cmake = CMake(self)
        cmake.configure()
        cmake.build()

    def test(self):
        if not can_run(self):
            raise ConanException("libxpm target consumers are not runnable")
        # 上游测试经 G_TEST_SRCDIR 定位 pixmaps/ 与 rgb.txt（G_TEST_DIST），
        # G_TEST_BUILDDIR 指向 build 目录。API/契约测试无需数据目录，设置后无害。
        g_test_srcdir = os.path.join(self.source_folder, "upstream", "test")
        for name in TEST_EXECUTABLES:
            executable = os.path.join(self.cpp.build.bindir, name)
            if str(self.settings.os) == "OHOS":
                self._sign_ohos_elf(executable)
            self.run(
                f'G_TEST_SRCDIR="{g_test_srcdir}" '
                f'G_TEST_BUILDDIR="{self.build_folder}" "{executable}"',
                env="conanrun",
            )

    def _sign_ohos_elf(self, path):
        signer = shutil.which("binary-sign-tool") or (
            "/data/service/hnp/bin/binary-sign-tool"
        )
        readelf = shutil.which("llvm-readelf") or (
            "/data/service/hnp/bin/llvm-readelf"
        )
        if not os.path.isfile(signer) or not os.path.isfile(readelf):
            raise ConanException("required OHOS signing tools are missing")
        temporary = f"{path}.signed"
        subprocess.run(
            [
                signer,
                "sign",
                "-inFile",
                path,
                "-outFile",
                temporary,
                "-selfSign",
                "1",
            ],
            check=True,
            timeout=60,
        )
        sections = subprocess.run(
            [readelf, "-SW", temporary],
            check=True,
            capture_output=True,
            text=True,
            timeout=30,
        ).stdout
        if sections.count(".codesign") != 1:
            raise ConanException(f"signed consumer has invalid .codesign: {path}")
        os.chmod(temporary, (os.stat(path).st_mode & 0o777) | 0o055)
        os.replace(temporary, path)
