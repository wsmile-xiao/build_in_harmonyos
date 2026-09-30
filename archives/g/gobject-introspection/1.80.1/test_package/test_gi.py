#!/usr/bin/env python3
"""test_gi.py — gobject-introspection test_package 独立测试源（L0c 要求）。

校验本包（1.80.1）实际安装的 typelib + g-ir 工具链存在。

注意与 1.78.1.1 的**交付差异**（上游 1.80 的行为变更，非本适配裁剪）：
  GLib-2.0 / GObject-2.0 / Gio-2.0 / GModule-2.0 的 GIR 在 1.80 中被上游放入
  `uninstalled_gir_files`（仅用于自测，**不随包安装**）—— 这四个核心 typelib
  自 glib 2.80 起由 **glib 自身**提供。故本包不再断言它们存在；
  改为断言本包真正交付的 GIRepository-2.0（1.80 的 girepository 已改为共享库）
  与若干随包安装的第三方 typelib。
"""
import os
import sys


def main():
    pkg = sys.argv[1]
    tl_dir = os.path.join(pkg, "lib", "girepository-1.0")
    bin_dir = os.path.join(pkg, "bin")
    ok = True
    # 本包实际交付的 typelib（1.80 安装 gir_files：GIRepository + 预置第三方）
    for _t in ("GIRepository-2.0.typelib", "cairo-1.0.typelib",
               "DBus-1.0.typelib", "libxml2-2.0.typelib"):
        _p = os.path.join(tl_dir, _t)
        if os.path.isfile(_p):
            print("[PASS] typelib %s" % _t)
        else:
            print("[FAIL] missing typelib: %s" % _t)
            ok = False
    # 共享形态：g-ir-scanner 生成 typelib 时需能解析 -lgirepository-1.0
    for _l in ("libgirepository-1.0.so", "libgirepository-1.0.so.1"):
        if os.path.exists(os.path.join(pkg, "lib", _l)):
            print("[PASS] shared %s" % _l)
        else:
            print("[FAIL] missing shared lib: %s" % _l)
            ok = False
    for _t in ("g-ir-scanner", "g-ir-compiler", "g-ir-generate"):
        if os.path.isfile(os.path.join(bin_dir, _t)):
            print("[PASS] tool %s" % _t)
        else:
            print("[FAIL] missing tool: %s" % _t)
            ok = False
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
