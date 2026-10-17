#!/usr/bin/env python3
"""test_gi.py — gobject-introspection test_package 独立测试源（L0c 要求）。

独立于 conanfile.py 的测试源文件：校验 GLib/GObject/Gio/GModule typelib
存在 + g-ir 工具链存在。由 test_package/conanfile.py 调用。
"""
import os
import sys


def main():
    pkg = sys.argv[1]
    tl_dir = os.path.join(pkg, "lib", "girepository-1.0")
    bin_dir = os.path.join(pkg, "bin")
    ok = True
    for _t in ("GLib-2.0.typelib", "GObject-2.0.typelib", "Gio-2.0.typelib",
               "GModule-2.0.typelib"):
        _p = os.path.join(tl_dir, _t)
        if os.path.isfile(_p):
            print("[PASS] typelib %s" % _t)
        else:
            print("[FAIL] missing typelib: %s" % _t)
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
