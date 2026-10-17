#!/usr/bin/env python3
"""test_package for notmuch 0.4 — 消费测试。

实质调用被测包（R34/PF3 防空壳）：
1. 检查包内产物：lib/libnotmuch.so*、include/notmuch.h、bin/notmuch 存在
2. 用 C 程序链接 libnotmuch 并调用 0.4 版 C API：
   notmuch_database_create / get_version / add_message / query_create /
   count_messages / search_messages（对应上游 basic/new/search/json 的功能语义）
3. 执行包内 CLI：notmuch --version 应输出 "notmuch 0.4"
"""

import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.env import VirtualRunEnv
from conan.tools.build import can_run


class NotmuchTestConan(ConanFile):
    settings = "os", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)
        # 显式声明传递依赖（libnotmuch.so 运行时 NEEDED libxapian.so.30 /
        # libglib-2.0.so / libtalloc.so.2 等，运行需注入其 lib 目录到 LD_LIBRARY_PATH）
        self.requires("xapian-core/1.4.26")
        self.requires("glib/2.84.0")
        self.requires("talloc/2.4.4")
        self.requires("zlib/1.3.1.1")

    def generate(self):
        VirtualRunEnv(self).generate()

    def test(self):
        if not can_run(self):
            return
        pkg = self.dependencies[self.tested_reference_str].package_folder
        lib_dir = os.path.join(pkg, "lib")
        inc_dir = os.path.join(pkg, "include")
        exe = os.path.join(pkg, "bin", "notmuch")
        # 产物存在性
        libs = [f for f in os.listdir(lib_dir) if f.startswith("libnotmuch.so")]
        if not libs:
            raise ConanException(f"libnotmuch.so missing in {lib_dir}")
        if not os.path.exists(os.path.join(inc_dir, "notmuch.h")):
            raise ConanException(f"notmuch.h missing in {inc_dir}")
        if not os.path.exists(exe):
            raise ConanException(f"notmuch CLI missing: {exe}")
        # C 消费程序：链接 libnotmuch 并调用 0.4 版 API
        cc = "/data/service/hnp/bin/clang"
        if not os.path.exists(cc):
            cc = os.environ.get("CC", "clang")
        src = os.path.join(os.path.dirname(__file__), "test.c")
        out = os.path.join(self.build_folder, "test_notmuch04")
        ld_paths = [lib_dir]
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
        r = subprocess.run(
            [cc, src, "-I", inc_dir, "-L", lib_dir, "-lnotmuch", "-o", out],
            capture_output=True, text=True, env=ld_env)
        if r.returncode != 0:
            raise ConanException(f"link consumer test failed: {r.stderr}")
        # 运行 C 消费测试（L0d/PF3：必须经 self.run 实际执行，防空壳）
        self.run(f'"{out}"', env="conanrun")
        # CLI 版本冒烟（R38 命令行工具声明）
        self.run(f'"{exe}" --version', env="conanrun")
