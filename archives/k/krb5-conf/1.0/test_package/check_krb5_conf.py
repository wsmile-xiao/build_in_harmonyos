#!/usr/bin/env python3
"""消费者测试脚本：验证 krb5.conf 在 OHOS 环境下正确安装且内容有效。"""
import sys
import os


def main():
    if len(sys.argv) != 2:
        print("Usage: check_krb5_conf.py <path-to-krb5.conf>")
        return 1

    conf_path = sys.argv[1]

    # 1. 文件存在性
    if not os.path.exists(conf_path):
        print(f"FAIL: {conf_path} not found")
        return 1

    # 2. 内容有效性
    with open(conf_path, "r") as f:
        content = f.read()

    if "[libdefaults]" not in content:
        print("FAIL: missing [libdefaults] section")
        return 1

    print(f"OK: krb5.conf verified at {conf_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
