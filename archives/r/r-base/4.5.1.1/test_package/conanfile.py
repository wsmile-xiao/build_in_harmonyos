import os
import shlex
import shutil

from conan import ConanFile
from conan.tools.build import can_run


class RBaseTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if not can_run(self):
            return
        dependency = self.dependencies.host[self.tested_reference_str]
        package_folder = dependency.package_folder
        runner = os.path.join(self.source_folder, "run_test.sh")
        script = os.path.join(self.source_folder, "test_r.R")
        moved = os.path.join(self.build_folder, "moved-r-base")
        command = "/system/bin/sh " + " ".join(
            shlex.quote(value)
            for value in (runner, package_folder, moved, script)
        )
        # Conan 对仓库内 test_package 以该目录自身作为 build_folder，因此被测包副本默认
        # 落在源码树里；不清理就会把整棵 R 安装树留进归档（4.5.1 归档即因此混入
        # 87MB / 2025 个文件的构建产物）。这里始终清理，失败时也清理，避免归档污染
        # 随测试结果漂移。
        try:
            self.run(command, env=None)
        finally:
            shutil.rmtree(moved, ignore_errors=True)

