#!/usr/bin/env python3
"""adduser 3.158 test_package — 验证 adduser/deluser 脚本存在且可执行（R34 反空壳）。

adduser 是纯 Perl 脚本应用（无编译，脚本直接拷贝到 bin/）。本脚本用
os.access() 校验脚本存在（F_OK）+ 可执行（X_OK）。adduser 为文本脚本，
不依赖目标架构，交叉编译场景（CI worker 上检查 conan 缓存包）同样有效。

用法：python3 test_adduser.py "<adduser_bin>" "<deluser_bin>"
"""
import os
import sys


def check_script(path, name):
    if not os.path.exists(path):
        print(f"{name} script not found: {path}", file=sys.stderr)
        return 1
    if not os.access(path, os.X_OK):
        print(f"{name} script not executable: {path}", file=sys.stderr)
        return 1
    print(f"{name} script OK: {path}")
    return 0


def main():
    if len(sys.argv) < 3:
        print("usage: test_adduser.py <adduser_bin> <deluser_bin>", file=sys.stderr)
        return 1
    ret = 0
    ret |= check_script(sys.argv[1], "adduser")
    ret |= check_script(sys.argv[2], "deluser")
    if ret == 0:
        print("adduser runtime test PASSED (adduser/deluser scripts present and executable)")
    return ret


if __name__ == "__main__":
    sys.exit(main())
