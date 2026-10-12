#!/usr/bin/env python3
"""Conan test_package — rsnapshot 1.5.1.

R34: test.sh actually exercises the installed tool — it runs
`rsnapshot configtest` against a generated configuration and performs a real
`hourly` snapshot backup (rsync copy into the snapshot root), then verifies
the snapshot directory was created and populated.
"""
from conan import ConanFile


class RsnapshotTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    # No build step — the tested package is a script application; the test
    # runs directly from test_package sources.

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        # test.sh (R34): rsnapshot --version / configtest + 真实 hourly 快照，
        # 验证快照目录内容落地。依赖工具经 conanrun.sh 的 PATH 解析。
        self.run("bash test.sh", env=["conanrun"])
