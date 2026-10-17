#!/usr/bin/env python3
"""Conan L1 test for epoxy 1.5.10 — real GL/EGL dispatch on OHOS/aarch64."""
import os
import shlex

from conan import ConanFile
from conan.tools.cmake import CMake, CMakeDeps, CMakeToolchain, cmake_layout


class EpoxyTestConan(ConanFile):
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
        # OHOS /bin/sh (mksh) 不能直接执行 ELF，用 bash 包一层（同 egl/1.0.5）。
        bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
        test_bin = os.path.join(self.build_folder, "test_epoxy")
        command = f"{shlex.quote(bash)} -c {shlex.quote(test_bin)}"
        try:
            self.run(command, env="conanrun")
        except Exception as e:
            # test 77 == SKIP（无 EGL 运行时），康调用环境缺口，非配方缺陷
            # conan 会把非 0 exit 抛异常；此处将 77 视为 skip，不阻断 conan create
            msg = str(e)
            if "77" in msg or "77" in repr(e):
                self.output.warning("[SKIP] test exited 77 — no EGL runtime on this host, lifecycle checks require real device/EGL stack (not a recipe failure)")
                return
            raise
