#!/usr/bin/env python3
"""Conan test_package for at-spi2-core 2.60.5 — Conan L1 official test.

Builds test_atk.c (uses real ATK API) and runs it, then smoke-tests the two
daemons shipped in libexec/ (at-spi2-registryd / at-spi-bus-launcher).
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class Atspi2CoreTestConan(ConanFile):
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
        # OHOS: /system/bin/sh (mksh) cannot exec ELF binaries; wrap with bash.
        bash = os.environ.get("CONFIG_SHELL") or shutil.which("bash") or "/data/service/hnp/bin/bash"
        # 1) 真实调用 atk API（创建对象、设置/查询角色、取角色名）
        self.run(f"{bash} -c './test_atk'", env="conanrun")
        # 2) at-spi2-registryd 真实运行：--help 走 GOption 解析，无需 D-Bus/GSettings
        self.run(f"{bash} -c 'at-spi2-registryd --help'", env="conanrun")
        # 3) at-spi-bus-launcher 冒烟：OHOS 无 gsettings-desktop-schemas（get_schema()
        #    即 g_error/SIGABRT）且无 dbus-daemon 会话总线，二进制无法真实运行。
        #    因此降级为产物级验证：确认随包交付且为可执行 aarch64 ELF（平台限制见
        #    notes.md；registryd --help 已是真实 daemon 运行冒烟）。
        self.run(
            f"{bash} -c 'p=\"$(command -v at-spi-bus-launcher)\"; "
            '[ -n "$p" ] && /data/service/hnp/bin/readelf -h "$p" | grep -q "AArch64" && '
            'echo "at-spi-bus-launcher ELF OK: $p"\'',
            env="conanrun",
        )
