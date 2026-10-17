#!/usr/bin/env python3
"""nmail 5.14.12 test_package — 消费者验证 + 无头冒烟（纯 IO 退出路径）。

冒烟断言（R34 真实执行被测二进制，共 5 项）：
  1. nmail --version → 版本 banner + 退出码 0
  2. nmail -v       → 版本 banner + 退出码 0
  3. nmail --help   → 使用说明文本 + 退出码 0
  4. nmail -h       → 使用说明文本 + 退出码 0
  5. nmail 未知参数  → 退出码 1（ShowHelp + return 1）
全程不启动 TUI（-v/-h 在参数解析阶段直接 return）。
"""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class NmailTestPackageConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式声明动态库依赖，保证 self.dependencies[*].package_folder 有效
        # （只 require 被测包时传递依赖的 package_folder 可能为 None）
        self.requires("xapian-core/1.4.26")
        self.requires("curl/8.15.0.1")
        self.requires("expat/2.8.4")

    def test(self):
        if not can_run(self):
            return

        package = self.dependencies["nmail"].package_folder
        nmail_bin = os.path.join(package, "bin", "nmail")
        if not os.path.exists(nmail_bin):
            raise ConanException(f"nmail binary not found: {nmail_bin}")

        # 运行时依赖（xapian/curl/expat 动态库）路径
        ld_library_path = ""
        for dep_name in ("xapian-core", "curl", "expat", "openssl", "zlib",
                         "sqlite3", "ncurses", "cyrus-sasl", "libmagic", "uuid"):
            dep = self.dependencies.get(dep_name)
            if dep is None or dep.package_folder is None:
                continue
            libdir = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(libdir):
                if ld_library_path:
                    ld_library_path = libdir + ":" + ld_library_path
                else:
                    ld_library_path = libdir

        runner = os.path.join(self.build_folder, "test_nmail.sh")
        shutil.copy2(
            os.path.join(self.recipe_folder, "src", "test_nmail.sh"), runner
        )
        log = os.path.join(self.build_folder, "nmail-tests.log")

        self.run(
            f'bash "{runner}" "{nmail_bin}" "{ld_library_path}" > "{log}" 2>&1',
            env="conanrun",
            ignore_errors=True,
        )
        lines = open(log, encoding="utf-8", errors="replace").read()
        self.output.info(lines)

        summary = {}
        for line in lines.splitlines():
            if line.startswith("NMAIL_TEST_SUMMARY "):
                for token in line.split()[1:]:
                    key, _, value = token.partition("=")
                    summary[key] = int(value)

        total = summary.get("total")
        passed = summary.get("pass")
        failed = summary.get("fail")
        if (total, passed, failed) != (5, 5, 0):
            tail = [ln for ln in lines.splitlines() if ln.startswith("FAIL ")][-10:]
            raise ConanException(
                f"nmail smoke expectations not met: expected total=5 pass=5 "
                f"fail=0, got total={total} pass={passed} fail={failed}; "
                f"failing: {' | '.join(tail)}"
            )
        self.output.info(f"NMAIL_TEST_PACKAGE_PASS={passed}/{total}")