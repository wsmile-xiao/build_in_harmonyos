#!/usr/bin/env python3
"""消费测试：验证 adplay 1.9 安装布局 + 真实运行。

adplay（AdPlay/UNIX）是 console 端 OPL2 音频播放器（AdPlug 前端），
上游无独立测试框架（0/0 如实）。本测试验证：
1. bin/adplay 可执行文件存在
2. adplay --help 真实运行（纯命令行参数解析，不依赖音频设备）
3. adplay 无参数运行（无音频文件——应输出 usage/错误信息，真实执行）
终态由各检查结果推导：任一 FAIL 即 exit 1，全部 PASS 才 "ALL PASS"。
"""
import os
import subprocess
import sys

PASS = "PASS:"
NOTE = "NOTE:"
FAIL = "FAIL:"


def run_tool(binpath, args=None):
    """运行工具并返回 (stdout+stderr, returncode)。stdin 重定向到
    /dev/null 避免管道/tty 环境下阻塞（catdoc/bsdutils 同款处理）。"""
    cmd = [binpath] + (args or [])
    with open(os.devnull, "r") as devnull:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                           stdin=devnull)
    out = (r.stdout or "") + (r.stderr or "")
    return out, r.returncode


def main():
    pkg_folder = sys.argv[1]
    bindir = os.path.join(pkg_folder, "bin")
    failures = 0

    # 1. bin/adplay 可执行文件存在
    adplay = os.path.join(bindir, "adplay")
    if not os.path.isfile(adplay) or not os.access(adplay, os.X_OK):
        print(f"{FAIL} bin/adplay 不存在或不可执行")
        sys.exit(1)
    print(f"{PASS} bin/adplay 可执行文件存在")

    # 2. adplay --help 真实运行（纯参数解析，不依赖音频设备）
    out, rc = run_tool(adplay, ["--help"])
    if rc != 0:
        print(f"{FAIL} adplay --help 运行失败（rc={rc}）")
        print(out[:300])
        failures += 1
    else:
        print(f"{PASS} adplay --help 真实运行（rc=0）")

    # 3. adplay 无参数运行（无音频文件——应输出 usage 或报错，真实执行）
    out, rc = run_tool(adplay)
    if rc not in (0, 1, 2):
        print(f"{FAIL} adplay 无参数运行异常（rc={rc}）")
        print(out[:300])
        failures += 1
    else:
        print(f"{PASS} adplay 无参数真实运行（rc={rc}——无音频文件属预期）")

    if failures > 0:
        print(f"{FAIL} {failures} 项检查失败")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
