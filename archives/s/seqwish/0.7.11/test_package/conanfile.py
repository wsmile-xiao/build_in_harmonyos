#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""seqwish 消费者测试：驱动包内 bin/seqwish 完成 CLI 与真实数据往返断言。"""

import os

from conan import ConanFile


class SeqwishTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["seqwish"]
        pkg = str(dep.package_folder)
        bindir = str(dep.cpp_info.bindirs[0])
        if not os.path.isabs(bindir):
            bindir = os.path.join(pkg, bindir)
        script = os.path.join(os.path.dirname(__file__), "test_seqwish.sh")
        self.run('sh "{}" "{}" "{}"'.format(script, bindir, pkg))
