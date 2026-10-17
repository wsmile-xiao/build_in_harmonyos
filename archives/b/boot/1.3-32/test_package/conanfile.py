#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""test_package for boot 1.3-32 — consumer-side R-free structural validation (R34).

``test()`` 真跑 ``validate_boot.py`` 校验**已安装的包树**
（``lib/R/library/boot/``），而不是打印字符串的空壳测试：

* 逐项核对 DESCRIPTION 字段、NAMESPACE 导出集合（36 个）、R/*.q 中的函数定义、
  50 个 .rda 数据集的 gzip/RDX2 序列化与列名、88 个 man 页 / 25 个含 examples、
  上游 tests/ 资产；
* 脚本在 ``lib/`` 被移走时会失败——CI L1e 破坏性反向验证依赖这一性质。

依赖只声明被测包自身（``self.tested_reference_str``）；**不声明 r-base 等任何
未发布依赖**（ohpcd 无 r-base，L0i 门禁会 hard-fail）。
"""
import os

from conan import ConanFile
from conan.errors import ConanException


class BootTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"
    # 需要 conanrun 环境（包 package_info 定义 R_BOOT_PACKAGE_DIR）
    generators = "VirtualRunEnv"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["boot"].package_folder
        tree = os.path.join(pkg, "lib", "R", "library", "boot")
        if not os.path.isdir(tree):
            raise ConanException("boot R library tree missing: %s" % tree)
        script = os.path.join(os.path.dirname(__file__), "validate_boot.py")
        if not os.path.isfile(script):
            raise ConanException("validate_boot.py missing: %s" % script)
        self.run("python3 '%s' '%s'" % (script, pkg), env="conanrun")
