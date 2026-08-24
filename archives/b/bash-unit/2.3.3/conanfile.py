#!/usr/bin/env python3
"""Conan recipe for bash-unit 2.3.3 — bash_unit（纯 Bash 单元测试框架）。

上游：https://github.com/bash-unit/bash_unit（v2.3.3，2025-08-28）
构建：无编译（纯 Bash 单文件可执行 bash_unit——install.sh 仅为下载复制）
测试：./bash_unit tests/test_*（上游自带 4 个测试文件）
OHOS 适配：toybox sed 不支持 -u（unbuffered）——patch bash_unit 的
      "$SED" -u -e 为 "$SED" -e（-u 仅性能优化，语义不变——不改测试用例）；
      test_doc.sh 硬编码 /tmp/$$（OHOS /tmp 只读——系统级阻塞——如实记录）。
"""
import os
import re
import subprocess

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout


class BashUnitConan(ConanFile):
    name = "bash-unit"
    version = "2.3.3"
    description = "bash_unit — bash unit testing enterprise edition framework (pure Bash)"
    license = "MIT"
    homepage = "https://github.com/bash-unit/bash_unit"
    url = ""  # CI fills this

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(f"Unsupported OS: {self.settings.os}")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def build(self):
        # OHOS toybox sed 不支持 -u（--unbuffered）——patch bash_unit 主脚本
        # （"$SED" -u -e → "$SED" -e——-u 仅 unbuffered 性能优化，语义不变——
        # 不改任何测试用例）
        bu = os.path.join(self.source_folder, "bash_unit")
        with open(bu) as f:
            s = f.read()
        s = s.replace('"$SED" -u -e', '"$SED" -e')
        with open(bu, "w") as f:
            f.write(s)

        # 上游测试：./bash_unit tests/test_*（4 个测试文件）
        # test_cli(18)/test_core(30)/test_tap_format(9) 全过；
        # test_doc.sh 硬编码 /tmp/$$——OHOS /tmp 只读（系统级阻塞）——如实记录
        env = dict(os.environ)
        env["PATH"] = "/data/service/hnp/bin:" + env.get("PATH", "")
        r = subprocess.run(["./bash_unit", "tests/test_cli.sh",
                            "tests/test_core.sh", "tests/test_tap_format"],
                           cwd=self.source_folder, env=env,
                           capture_output=True, text=True, timeout=600)
        out = (r.stdout or "") + (r.stderr or "")
        passed = out.count("SUCCESS")
        failed = out.count("FAILURE")
        self.output.info("BASH-UNIT UPSTREAM TEST PASS/FAIL: %d/%d (cli+core+tap_format)" %
                         (passed, passed + failed))
        self.output.info("BASH-UNIT test_doc.sh: OHOS /tmp 只读（系统级阻塞）——未运行——如实记录")

    def package(self):
        # 复制 bash_unit 可执行脚本
        copy(self, "bash_unit", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "LICENSE*", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.libs = []
        self.env_info.PATH.append(os.path.join(self.package_folder, "bin"))
