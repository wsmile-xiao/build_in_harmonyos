#!/usr/bin/env python3
"""消费测试：验证 chinadns 1.3.2 安装布局 + 真实运行。

chinadns 是 DNS 分流工具（ChinaDNS-C）。上游 tests/ 6 个 dig 集成
用例（N=6）在配方 build() 末尾真实运行（Python 3 移植版 test.py，
见 conanfile.py _run_upstream_tests，本机实测 6/6 通过）。本消费测试
做 API 冒烟（R34：实质依赖被测包——真实执行 chinadns）：
1. bin/chinadns 可执行文件存在
2. chinadns -h 真实运行——usage 输出 + rc=0
3. chinadns -V 真实运行——版本输出 "ChinaDNS 1.3.2" + rc=0
4. share/iplist.txt + share/chnroute.txt 数据文件存在（dist_data_DATA）
所有子进程 stdin 重定向 /dev/null（airview P3——防管道/tty 阻塞）。
终态：任一 FAIL 即 exit 1，全部 PASS 才 "ALL PASS"。
"""
import os
import subprocess
import sys

PASS = "PASS:"
NOTE = "NOTE:"
FAIL = "FAIL:"


def run_tool(bindir, prog, args=None):
    """运行工具并返回 (stdout+stderr, returncode)。stdin 重定向到
    /dev/null 避免管道/tty 环境下阻塞（airview P3）。"""
    cmd = [os.path.join(bindir, prog)] + (args or [])
    try:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                           stdin=subprocess.DEVNULL)
    except (FileNotFoundError, PermissionError, OSError) as e:
        return str(e), -1
    out = (r.stdout or "") + (r.stderr or "")
    return out, r.returncode


def main():
    pkg_folder = sys.argv[1]
    bindir = os.path.join(pkg_folder, "bin")
    failures = 0

    # 1. chinadns 可执行文件存在
    exe = os.path.join(bindir, "chinadns")
    if not os.path.isfile(exe) or not os.access(exe, os.X_OK):
        print(f"{FAIL} bin/chinadns 不存在或不可执行")
        failures += 1
    else:
        print(f"{PASS} bin/chinadns 可执行文件存在")

    # 2. chinadns -h —— usage 输出 + rc=0
    out, rc = run_tool(bindir, "chinadns", ["-h"])
    if rc != 0 or "usage" not in out.lower():
        print(f"{FAIL} chinadns -h 运行异常（rc={rc}）")
        print(out[:300])
        failures += 1
    else:
        print(f"{PASS} chinadns -h 真实运行（usage 输出，rc={rc}）")

    # 3. chinadns -V —— 版本输出 "ChinaDNS 1.3.2"
    out, rc = run_tool(bindir, "chinadns", ["-V"])
    if rc != 0 or "1.3.2" not in out:
        print(f"{FAIL} chinadns -V 运行异常（rc={rc}, out={out[:100]!r}）")
        failures += 1
    else:
        print(f'{PASS} chinadns -V 真实运行（版本输出: {out.strip()}）')

    # 4. share 数据文件存在（dist_data_DATA = iplist.txt chnroute.txt）
    for data in ("iplist.txt", "chnroute.txt"):
        p = os.path.join(pkg_folder, "share", data)
        if not os.path.isfile(p):
            print(f"{FAIL} share/{data} 数据文件缺失")
            failures += 1
        else:
            print(f"{PASS} share/{data} 数据文件存在")

    # 上游测试口径说明（N=6，build() 内真实运行）
    print(f"{NOTE} 上游 N=6（tests/ 6 个 dig 集成用例）已在配方 build() "
          f"真实运行（见 conanfile.py _run_upstream_tests），本消费测试"
          f"为安装布局 + CLI API 冒烟")

    if failures > 0:
        print(f"{FAIL} {failures} 项检查失败")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
