#!/usr/bin/env python3
"""Consumer test recipe for sprai 0.9.9.23.

Runs test_sprai.py. Two legs:

* static leg — always runs (package content, ELF arch/loader/libc linkage,
  no foreign-arch residue);
* runtime leg — only when can_run() is true (the four-stage sprai pipeline,
  asserted field by field).

本机 WSL 显式设了 tools.build.cross_building:can_run=false（qemu 能拉起 aarch64
ELF 但那不是可信环境），所以本地 conan create 只跑静态段；运行段在 aarch64/OHOS
产物上单独整条跑过一遍并全绿，见 notes.md §6.2。
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run
from conan.tools.layout import basic_layout


class SpraiTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        basic_layout(self)

    def test(self):
        package = self.dependencies["sprai"].package_folder
        script = os.path.join(self.recipe_folder, "test_sprai.py")
        runnable = can_run(self)
        command = '"%s" "%s" "%s"' % (sys.executable, script, package)
        if runnable:
            command += " --runtime"
        self.run(command, env="conanrun")
