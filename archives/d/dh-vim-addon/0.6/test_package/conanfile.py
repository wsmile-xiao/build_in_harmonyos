#!/usr/bin/env python3
"""Conan test_package for dh-vim-addon — verifies the packaged Perl CLI +
dh sequence module and really executes the script (R34).

test_type="explicit"：test() 由 conan create / conan test 触发；实际执行逻辑
在 test_dh_vim_addon.py（真实调用被测包 bin/dh_vim-addon）。
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

    def test(self):
        if can_run(self):
            pkg = self.dependencies["dh-vim-addon"].package_folder
            # 收集依赖包（debhelper/dpkg）路径——PERL5LIB 需含依赖包的
            # perl 库目录（Dh_Lib 来自 debhelper、Dpkg::* 来自 dpkg）
            dep_dirs = [d.package_folder
                        for _, d in self.dependencies.items()
                        if d.ref.name != "dh-vim-addon"]
            test_script = os.path.join(os.path.dirname(__file__),
                                       "test_dh_vim_addon.py")
            args = [sys.executable, test_script, pkg] + dep_dirs
            self.run(" ".join('"%s"' % a for a in args), env="conanrun")
