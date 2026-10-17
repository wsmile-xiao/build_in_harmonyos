#!/usr/bin/env python3
"""消费测试：验证 cdw 0.8.1 失败记录归档完整性。

cdw（cdrecord 前端）依赖 burn 制品仓完全缺失（configure 硬性必需
不可绕过）——按 adplay 先例失败记录模式（status: failed +
failure_reason 如实记录）。本测试验证归档记录完整性：
1. 归档 conanfile.py + manifest.yaml + conandata.yml 存在
2. manifest status 记录为 failed（真实构建不可能，不伪造）
3. 终态计数正确
"""
import os
import sys

PASS = "PASS:"
NOTE = "NOTE:"
FAIL = "FAIL:"


def main():
    pkg_folder = sys.argv[1]
    test_dir = os.path.dirname(os.path.abspath(__file__))
    # 归档目录 = test_package 上级（archives/c/cdw/0.8.1/）
    arch_dir = os.path.dirname(test_dir)
    failures = 0

    # 1. 归档文件完整
    for f in ("conanfile.py", "manifest.yaml", "conandata.yml"):
        if os.path.isfile(os.path.join(arch_dir, f)):
            print(f"{PASS} 归档 {f} 存在")
        else:
            print(f"{FAIL} 归档 {f} 缺失")
            failures += 1

    # 2. manifest status 如实记录 failed（依赖 burn 缺失）——防伪造
    # 守卫：status 非 failed 或 failure_reason 不含 burn 必须 FAIL
    # （禁止伪造状态标记是项目最高优先级规则）
    manifest = os.path.join(arch_dir, "manifest.yaml")
    if os.path.isfile(manifest):
        with open(manifest, encoding="utf-8") as fh:
            m = fh.read()
        if "status: failed" in m:
            print(f"{PASS} manifest status=failed 如实记录（依赖 burn 制品缺失）")
        else:
            print(f"{FAIL} manifest 未记录 failed——防伪造守卫触发（状态被篡改）")
            failures += 1
        if "failure_reason" in m and "burn" in m:
            print(f"{PASS} failure_reason 含依赖 burn 缺失说明")
        else:
            print(f"{FAIL} failure_reason 未含 burn 说明——防伪造守卫触发")
            failures += 1
    else:
        print(f"{FAIL} manifest.yaml 缺失")
        failures += 1

    if failures > 0:
        print(f"{FAIL} {failures} 项检查失败")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
