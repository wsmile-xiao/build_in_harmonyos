#!/usr/bin/env python3
"""Conan test_package for buildessential — 验证 Chef cookbook 文件完整性 + Ruby DSL 语法。"""
import os
import shutil
import subprocess
import sys


def main():
    pkg_dir = sys.argv[1] if len(sys.argv) > 1 else os.getcwd()
    # P3（aireview）：不硬编码 ruby 绝对路径——PATH 查找，找不到即失败
    ruby = shutil.which("ruby") or "/data/service/hnp/bin/ruby"
    if not os.path.isfile(ruby):
        print(f"FAIL: ruby 解释器不存在（{ruby}）")
        return 1
    fails = 0

    # 1. 文件完整性：metadata.rb + recipes/default.rb 必须存在
    for f in ("metadata.rb", "metadata.json", "recipes", "README.md"):
        p = os.path.join(pkg_dir, f)
        if os.path.exists(p):
            print(f"PASS: {f} 存在")
        else:
            print(f"FAIL: {f} 缺失")
            fails += 1

    # 2. Ruby DSL 语法验证（ruby -c——真实解析）
    for f in ("metadata.rb", "recipes/default.rb"):
        p = os.path.join(pkg_dir, f)
        # P2（aireview）：缺失不得假阳性跳过——必须 FAIL（破损包拦截）
        if not os.path.isfile(p):
            print(f"FAIL: {f} 缺失——ruby 语法验证无法执行")
            fails += 1
            continue
        # P3（aireview）：捕获 FileNotFoundError/TimeoutExpired，不得让门禁崩掉
        try:
            r = subprocess.run([ruby, "-c", p], capture_output=True, text=True,
                               timeout=60)
        except FileNotFoundError as e:
            print(f"FAIL: {f} ruby 无法执行（{e}）")
            fails += 1
            continue
        except subprocess.TimeoutExpired:
            print(f"FAIL: {f} ruby -c 超时")
            fails += 1
            continue
        out = (r.stdout or "") + (r.stderr or "")
        if "Syntax OK" in out:
            print(f"PASS: {f} ruby 语法 OK")
        else:
            print(f"FAIL: {f} 语法错误: {out.strip()}")
            fails += 1

    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
