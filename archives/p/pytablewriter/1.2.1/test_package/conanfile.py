#!/usr/bin/env python3
"""Conan test_package for pytablewriter — runs the R34 consumer check.

L1 official test: runs a Python script that imports the packaged
pytablewriter and writes a real Markdown table via MarkdownTableWriter,
asserting the output. R34 real API usage, not just file presence.

pytablewriter's runtime deps (dataproperty/mbstrdecoder/pathvalidate/
tabledata/tcolorpy/typepy) must be explicitly required here — otherwise
self.dependencies[dep].package_folder is None (conan skips their binaries
in the test graph, dataproperty 同款实测教训) and the module import fails.
All deps' site-packages are added to PYTHONPATH.
"""
import os
import sys

from conan import ConanFile
from conan.tools.build import can_run


class TestPackageConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # pytablewriter 运行时依赖——显式 requires（否则 package_folder 为 None）
        self.requires("dataproperty/1.1.1")
        self.requires("mbstrdecoder/1.1.5")
        self.requires("pathvalidate/3.3.1")
        self.requires("tabledata/1.3.5")
        self.requires("tcolorpy/0.1.7")
        self.requires("typepy/2.0.0")

    def test(self):
        if can_run(self):
            pkg = self.dependencies["pytablewriter"].package_folder
            # 遍历所有依赖的 site-packages 全加 PYTHONPATH（逐个加易漏）
            py_paths = []
            for dep_name, dep in self.dependencies.items():
                for sp in ("lib/python3.12/site-packages",
                           "lib/python3/site-packages", "lib/python3"):
                    p = os.path.join(dep.package_folder, sp)
                    if os.path.isdir(p):
                        py_paths.append(p)
                        break
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_pytablewriter.py")
            self.run(
                f'PYTHONPATH="{os.pathsep.join(py_paths)}" '
                f'{sys.executable} "{test_script}" "{pkg}"',
                env="conanrun")
