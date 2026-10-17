#!/usr/bin/env python3
"""Conan test_package for xdelta 1.1.3 — CLI round-trip test.

R34: executes the real xdelta binary end to end (delta/patch/info),
which drives the libxdelta/libedsio code paths; not a print-only stub.
The shell script emits the HMBS_TEST_PACKAGE_RESULT gate marker.
"""
import os

from conan import ConanFile


class XdeltaTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # Shell 存活探测：profile 把 CONFIG_SHELL 指向 hnp bash，但真机曾
        # 缺失该路径（依赖 configure 报 "inaccessible or not found"）。
        # test() 运行在真机上，此处探测真实可执行的 shell：现行
        # CONFIG_SHELL/SHELL 可执行则沿用，否则回退到 HMBS 保证的 /bin/sh。
        # 以 "$shell test_xdelta.sh" 显式解释执行，shebang 不会被内核使用。
        import shutil
        candidates = [
            os.environ.get("CONFIG_SHELL", ""),
            os.environ.get("SHELL", ""),
            "/bin/sh",
            "/data/service/hnp/bin/bash",
        ]
        bash = next(
            (s for s in candidates
             if s and os.path.isfile(s) and os.access(s, os.X_OK)),
            shutil.which("sh") or "/bin/sh",
        )
        self.run("%s test_xdelta.sh" % bash, env="conanrun")
