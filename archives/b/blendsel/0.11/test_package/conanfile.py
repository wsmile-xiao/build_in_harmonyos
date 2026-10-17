#!/usr/bin/env python3
"""test_package for blendsel 0.11 — consumer smoke tests (OHOS 实跑).

blendsel 是纯 Perl CLI（Debian blends 安装选择器，tasksel fork）。上游无
回归测试套件：tests/ 仅为运行期 task filter hooks，install/remove 与 UI
路径依赖 apt-get/dpkg/debconf（OHOS 无此生态，runnable=0 见 MANIFEST.yml）。
本 test() 在 conanrun 环境调用 test_blendsel.py，执行 8 项独立断言：
1. bin/blendsel 存在、可执行、shebang 为 #!/usr/bin/env perl
2. 包布局完整（bin/ + lib/blendsel + share/blendsel，6 个关键文件非空）
3. share/blendsel/descs/debian-tasks.desc 可读且含 med-blend 任务数据
4. perl -c 语法校验（补丁 Locale::gettext 可选加载后可编译）
5. perl 解释器来自 conan 依赖 perl/5.42.2 制品路径（非系统 perl）
6. perl --version 报告 v5.42.2（与声明依赖一致）
7. --task-packages=med-blend 输出 task-med-blend 且 exit 0（数据链+前缀推导）
8. 未知选项输出 usage（含 "blendsel [OPTIONS"）且 exit 非 0
"""
import os
import sys

from conan import ConanFile
from conan.errors import ConanException


class BlendselTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        dep = self.dependencies["blendsel"]
        pkg_folder = dep.package_folder
        blendsel = os.path.join(pkg_folder, "bin", "blendsel")
        perl_dep = self.dependencies["perl"]
        perl_pkg_folder = perl_dep.package_folder
        perl_bin = os.path.join(perl_pkg_folder, "bin", "perl")
        if not os.path.isfile(perl_bin):
            raise ConanException(f"perl interpreter not found: {perl_bin}")
        test_script = os.path.join(os.path.dirname(__file__),
                                   "test_blendsel.py")
        if not os.path.isfile(test_script):
            raise ConanException(f"test script not found: {test_script}")
        # L0d: test() 必须调用 self.run —— 在 conanrun 环境实跑 8 断言冒烟
        rc = self.run(f'"{sys.executable}" "{test_script}" "{pkg_folder}" '
                      f'"{blendsel}" "{perl_bin}" "{perl_pkg_folder}"',
                      env="conanrun", ignore_errors=True)
        if rc != 0:
            raise ConanException(f"test_blendsel.py failed (rc={rc})")
        self.output.info("blendsel smoke tests passed (8/8 assertions)")
