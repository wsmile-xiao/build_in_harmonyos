#!/usr/bin/env python3
"""Conan test_package for objgraph 3.6.2 — consumer check (R34 真实 API).

由 test_objgraph.py 驱动，以消费者视角真实调用 objgraph 的公开 API。
env="conanrun" 注入是必需的——包侧 package_info() 用 runenv_info 声明了
PYTHONPATH，裸 subprocess 会丢失该注入（参见 perl-uri 先例的
FileNotFoundError 教训）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class ObjgraphTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["objgraph"].package_folder
        site = os.path.join(pkg, "lib", "python3.12", "site-packages")
        if not os.path.isfile(os.path.join(site, "objgraph.py")):
            raise ConanException(f"objgraph.py not found in package: {site}")

        test_script = os.path.join(os.path.dirname(__file__), "test_objgraph.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test_objgraph.py missing: {test_script}")

        self.run(f'python3 "{test_script}" "{site}"', env="conanrun")
