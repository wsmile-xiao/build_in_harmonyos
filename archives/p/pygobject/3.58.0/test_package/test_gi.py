#!/usr/bin/env python3
"""pygobject test_package 真实测试脚本。

验证 gi 包可导入 + GLib 版本号可读（GObject typelib 可访问）。
被 test_package/conanfile.py 的 test() 以 self.run() 调用执行。
"""
import os
import sys

# site-packages 路径经命令行参数传入（conanfile.py test() 的 self.run 调用）
SITE_PACKAGES = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PYGOBJECT_SITE_PACKAGES", "")


def main():
    if not SITE_PACKAGES:
        print("FAIL: PYGOBJECT_SITE_PACKAGES not set", file=sys.stderr)
        return 1
    # 前置被测包的 site-packages，确保加载的是被测产物
    sys.path.insert(0, SITE_PACKAGES)
    try:
        import gi
        from gi.repository import GLib
    except ImportError as e:
        # R34/R9：不得用"产物存在"冒充"功能可用"——import 失败即如实 FAIL
        print(f"FAIL: import gi failed ({e})", file=sys.stderr)
        return 1
    gi_file = os.path.abspath(getattr(gi, "__file__", ""))
    if SITE_PACKAGES and not gi_file.startswith(os.path.abspath(SITE_PACKAGES)):
        print(f"FAIL: gi loaded from system ({gi_file})", file=sys.stderr)
        return 1
    major = getattr(GLib, "MAJOR_VERSION", -1)
    if major <= 0:
        print("FAIL: GLib.MAJOR_VERSION invalid", file=sys.stderr)
        return 1
    print(f"gi OK: {gi_file} GLib {major}.x")
    return 0


if __name__ == "__main__":
    sys.exit(main())
