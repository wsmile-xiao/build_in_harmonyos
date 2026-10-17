#!/usr/bin/env python3
"""test_package for notmuch 0.38.3 — 消费测试。

notmuch 无自带测试套件。消费测试验证：
1. libnotmuch.so 存在且可被链接器解析
2. 用 C 程序链接 libnotmuch 并调用 API（notmuch_database_create / get_version）
"""

import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run


class NotmuchTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式声明传递依赖（libnotmuch.so 运行时 NEEDED libxapian.so.30/
        # libglib-2.0.so 等，test 运行需注入其 lib 目录到 LD_LIBRARY_PATH）
        self.requires("xapian-core/1.4.26")
        self.requires("glib/2.84.0")
        self.requires("talloc/2.4.4")
        self.requires("zlib/1.3.1.1")

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies[self.tested_reference_str].package_folder
        lib_dir = os.path.join(pkg, "lib")
        inc_dir = os.path.join(pkg, "include")
        exe = os.path.join(pkg, "bin", "notmuch")
        # 库存在
        libs = [f for f in os.listdir(lib_dir) if f.startswith("libnotmuch.so")]
        if not libs:
            raise ConanException(f"libnotmuch.so missing in {lib_dir}")
        # 头文件存在
        if not os.path.exists(os.path.join(inc_dir, "notmuch.h")):
            raise ConanException(f"notmuch.h missing in {inc_dir}")
        # CLI 存在
        if not os.path.exists(exe):
            raise ConanException(f"notmuch CLI missing: {exe}")
        # C 消费程序：链接 libnotmuch 并调用 API（用完整 clang 路径，conan 运行环境 PATH 无 clang）
        cc = "/data/service/hnp/bin/clang"
        if not os.path.exists(cc):
            cc = os.environ.get("CC", "clang")
        src = os.path.join(os.path.dirname(__file__), "test.c")
        out = os.path.join(self.build_folder, "test_notmuch")
        # libnotmuch.so 运行时 NEEDED libgmime-3.0.so.0（随包分发）+ libxapian.so.30/
        # libglib-2.0.so（conan 依赖制品）→ 全部注入 LD_LIBRARY_PATH
        ld_paths = [lib_dir, os.path.join(pkg, "lib")]
        for dep_name in ("xapian-core", "glib", "talloc", "zlib"):
            try:
                dep = self.dependencies[dep_name]
            except KeyError:
                continue
            dl = os.path.join(dep.package_folder, "lib")
            if os.path.isdir(dl):
                ld_paths.append(dl)
        ld_env = dict(os.environ)
        ld_env["LD_LIBRARY_PATH"] = ":".join(ld_paths) + ":" + ld_env.get("LD_LIBRARY_PATH", "")
        # L0d: test() 必须经 self.run 执行真实测试（避免 stub 判定）
        r = subprocess.run(
            [cc, src, "-I", inc_dir, "-L", lib_dir, "-lnotmuch", "-o", out],
            capture_output=True, text=True, env=ld_env)
        if r.returncode != 0:
            raise ConanException(f"link test failed: {r.stderr}")
        self.run(f'"{out}"', env="conanrun")
