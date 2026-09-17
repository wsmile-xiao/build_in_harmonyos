#!/usr/bin/env python3
"""Conan test_package for template-glib 3.36.2 — Conan L1 official test.

Builds test_tmpl.c (real consumer: parses a template via TmplTemplate,
sets a scope variable via TmplScope, expands and asserts the rendered
output) and runs it.
"""
import os
import shutil

from conan import ConanFile
from conan.tools.cmake import CMake, cmake_layout


class TemplateGlibTestConan(ConanFile):
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
        # 真实消费者调用：TmplTemplate 解析 + TmplScope 变量注入 + 展开断言
        self.run(f"{bash} -c './test_tmpl'", env="conanrun")
