#!/usr/bin/env python3
"""gnome-online-accounts test_package — 验证 libgoa 核心库可用性.

上游无自动化测试，本包验证：
  1. goa_check_version(3, 56, 5) 非 NULL（版本 >= 3.56.5）
  2. goa_major_version == 3（全局版本变量）
  3. libgoa.so 可加载（链接通过即验证）
共 3 断言。
"""
import os

from conan import ConanFile
from conan.tools.build import can_run


class GnomeOnlineAccountsTestConan(ConanFile):
    settings = "os", "compiler", "build_type", "arch"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        if can_run(self):
            import subprocess, sys
            cc_map = self.conf.get("tools.build:compiler_executables", default={}) or {}
            cc = cc_map.get("c") or os.environ.get("CC", "clang")
            goa = self.dependencies["gnome-online-accounts"]
            glib = self.dependencies["glib"]

            src = os.path.join(self.source_folder, "src", "test_goa.c")
            out = os.path.join(self.build_folder, "test_goa")

            glib_inc = os.path.join(glib.package_folder, "include")
            glib_glibdir = os.path.join(glib.package_folder, "lib")

            goa_inc = os.path.join(goa.package_folder, "include", "goa-1.0")
            goa_lib = os.path.join(goa.package_folder, "lib")
            goa_config_inc = os.path.join(goa.package_folder, "lib", "goa-1.0", "include")

            self.run(
                f"{cc} -o {out} {src} "
                f"-I{goa_inc} -I{goa_config_inc} "
                f"-I{glib_inc}/glib-2.0 -I{glib_glibdir}/glib-2.0/include "
                f"-DGOA_API_IS_SUBJECT_TO_CHANGE "
                f"-L{goa_lib} -L{glib_glibdir} "
                f"-lgoa-1.0 -lglib-2.0 -lpthread -lm",
                env="conanbuild")
            # 配方 shared=False，Conan 运行时不注入 goa/glib libdir 到
            # LD_LIBRARY_PATH，但 goa 实际产出 .so，运行需显式补路径
            self.run(
                f"LD_LIBRARY_PATH={goa_lib}:{glib_glibdir}:$LD_LIBRARY_PATH {out}",
                env="conanrun")
