#!/usr/bin/env python3
"""Conan test_package for gnome-menus — 消费者视角实质测试（L1，R34）。

test_gmenu.c 在沙箱 XDG 目录里构造 applications.menu + 条目 + 子菜单目录，
真实走通 libgnome-menu-3 的加载/解析/遍历 API（与 alacarte 同一 API 面），
共 25 条断言；任一断言失败即非零退出 → conan create 失败。
另校验 GMenu-3.0.typelib 随包产出（GI 运行时供 pygobject 消费）。

用 self.run（L0d 要求），并回读断言计数形成证据链（L1b）。
"""
import glob
import os

from conan import ConanFile


class GnomeMenusTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def test(self):
        pkg = self.dependencies["gnome-menus"].package_folder
        inc = os.path.join(pkg, "include")
        libdir = os.path.join(pkg, "lib")
        here = os.path.dirname(__file__)
        src = os.path.join(here, "test_gmenu.c")
        out = os.path.join(here, "test_gmenu")
        summary_log = os.path.join(here, "test_gmenu_summary.txt")
        if os.path.exists(summary_log):
            os.remove(summary_log)
        cc = "/data/service/hnp/bin/clang"
        # glib 共享包 include/lib（依赖遍历 + glob 兜底）
        glib_inc = None
        for _dep in self.dependencies.values():
            if _dep.package_folder and str(_dep.ref).startswith("glib/"):
                glib_inc = _dep.package_folder
                break
        if not glib_inc:
            _cs = glob.glob("/storage/Users/currentUser/.conan2/p/glib*/p")
            if _cs:
                glib_inc = _cs[-1]
        glib_lib = os.path.join(glib_inc, "lib")
        # 1) 编译链接（符号缺失会在链接期暴露 ABI 问题）
        self.run(f"{cc} '{src}' -o '{out}' -I'{inc}' "
                 f"-I'{glib_inc}/include/glib-2.0' -I'{glib_inc}/lib/glib-2.0/include' "
                 f"-I'{glib_inc}/include/gio-unix-2.0' "
                 f"-L'{libdir}' -lgnome-menu-3 "
                 f"-L'{glib_lib}' -lglib-2.0 -lgobject-2.0 -lgio-2.0 "
                 f"-Wl,-rpath,'{libdir}' -Wl,-rpath,'{glib_lib}'")
        # 2) 运行（LD_LIBRARY_PATH 含被测包 + glib 共享库）；断言失败即非零退出
        self.run(f"GMENU_TEST_LOG='{summary_log}' "
                 f"LD_LIBRARY_PATH='{libdir}:{glib_lib}' '{out}'")
        # 3) 回读断言计数，作为测试真实执行的证据（L1b）
        if not os.path.isfile(summary_log):
            raise Exception("test_gmenu did not write assertion summary: %s"
                            % summary_log)
        with open(summary_log) as f:
            summary = f.read().strip()
        if "failures=0" not in summary:
            raise Exception("test_gmenu assertions failed: %s" % summary)
        self.output.info("[PASS] test_gmenu: %s" % summary)
        # 4) 校验 GMenu typelib（GI 运行时产物）
        tl = os.path.join(pkg, "lib", "girepository-1.0", "GMenu-3.0.typelib")
        if not os.path.isfile(tl):
            raise Exception("GMenu-3.0.typelib not found in package: %s" % tl)
        self.output.info("[PASS] GMenu-3.0.typelib present")
