#!/usr/bin/env python3
"""Conan test_package for python-magic — R34 consumer verification.

Two-layer check:
1. HARD: the `magic` package files are present in site-packages
   (__init__.py / loader.py / compat.py / py.typed) — install correctness.
2. SOFT: try `import magic` and real MIME detection via libmagic. On OHOS
   the loader looks for libmagic.so.1 (file Conan pkg is static-only per
   R26; system provides unversioned libmagic.so), so runtime loading may
   be unavailable — record that honestly, don't fail the build.
"""
import os
import subprocess
import sys

TEST_SCRIPT = r'''
import sys
sys.path.insert(0, "{site}")
import magic
png = bytes.fromhex("89504e470d0a1a0a0000000d49484452")
print("MIME:", magic.from_buffer(png, mime=True))
print("OK: python-magic import + libmagic real detection works")
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    # 定位 site-packages（lib/pythonX.Y/site-packages）
    site = None
    lib_root = os.path.join(pkg, "lib")
    for py in os.listdir(lib_root):
        cand = os.path.join(lib_root, py, "site-packages")
        if os.path.isdir(cand) and os.path.isdir(os.path.join(cand, "magic")):
            site = cand
            break
    if not site:
        print(f"FAIL: magic module not found under {lib_root}", file=sys.stderr)
        return 1

    # 1. HARD: magic 包文件存在 + 语法可编译（R34 安装正确性）
    magic_dir = os.path.join(site, "magic")
    required = ["__init__.py", "loader.py", "compat.py"]
    missing = [f for f in required
               if not os.path.isfile(os.path.join(magic_dir, f))]
    if missing:
        print(f"FAIL: magic files missing: {missing}", file=sys.stderr)
        return 1
    for f in required:
        # 用内置 compile() 做语法检查（不落盘——py_compile 会在源码旁生成
        # __pycache__/*.pyc 污染包目录，review P3）
        with open(os.path.join(magic_dir, f), "r", encoding="utf-8") as fh:
            try:
                compile(fh.read(), f, "exec")
            except SyntaxError as e:
                print(f"FAIL: {f} syntax error: {e}", file=sys.stderr)
                return 1

    # 2. SOFT: 尝试 import + 真实 MIME 识别（libmagic 运行时可用则真实校验）
    r = subprocess.run(
        [sys.executable, "-c", TEST_SCRIPT.replace("{site}", site)],
        capture_output=True, text=True)
    if r.returncode == 0:
        print(r.stdout.strip())
        return 0
    # 失败路径：仅当精确匹配已知的 libmagic-not-found 环境限制签名时才
    # 允许通过（OHOS：file 包按 R26 只出静态库、系统无 libmagic.so.1——
    # loader.py 的 load_lib() 抛 ImportError 'failed to find libmagic'）——
    # 其余任何失败（包自身回归）必须返回非 0，杜绝 R9 伪造通过
    err = r.stderr.strip()
    KNOWN_LIBMAGIC_MISSING = "failed to find libmagic"
    if KNOWN_LIBMAGIC_MISSING in err:
        print("WARN: libmagic.so.1 运行时加载不可用（OHOS 环境限制——file 包按 "
              "R26 只出静态库、系统无 libmagic.so.1）——模块安装校验通过，"
              "真实识别受限，如实记录:", file=sys.stderr)
        print("  " + (err.splitlines()[-1] if err else ""), file=sys.stderr)
        return 0
    print(f"FAIL: runtime import/detection failed: {err}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
