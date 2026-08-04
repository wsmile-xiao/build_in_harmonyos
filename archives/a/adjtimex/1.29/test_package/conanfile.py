#!/usr/bin/env python3
"""Conan test_package for adjtimex 1.29.

Smoke test for the adjtimex CLI tool.
Upstream has no official test suite; R34 requires exercising the
tested package's binary. `adjtimex --version` is the only path that
does not trigger the adjtimex() syscall, which is blocked by the
OHOS seccomp sandbox (SIGSYS).
"""
from conan import ConanFile
from conan.tools.layout import basic_layout


class AdjtimexTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def build(self):
        pass

    def test(self):
        # adjtimex() syscall is blocked by OHOS seccomp (SIGSYS), so only
        # --version (which does not call the syscall) is usable as smoke test.
        self.run("adjtimex --version", env="conanrun")
