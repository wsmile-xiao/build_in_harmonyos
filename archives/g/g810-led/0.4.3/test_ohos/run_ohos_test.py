#!/usr/bin/env python3
"""test_ohos/run_ohos_test.py — g810-led 鸿蒙专项测试（OHOS aarch64）。

在 OHOS 平台上实际运行适配产物 bin/g810-led，验证真实可观察行为：
  case1: -h 帮助输出，版本号必须是 0.4.3，退出码 0
  case2: --list-keyboards 无设备时退出码 1 且输出 device not found
  case3: -a 非法颜色：无设备时 open 先失败，退出码 2
  case4: -a ff00ff 合法颜色、无设备时退出码 2（open 失败路径）
记录每条命令、cwd、退出码与输出，断言全部通过后写日志并退出 0。

用法: python3 run_ohos_test.py <g810-led 二进制绝对路径> [输出日志路径]
"""
import subprocess
import sys
import os
import datetime

BIN = sys.argv[1] if len(sys.argv) > 1 else "bin/g810-led"
LOG = sys.argv[2] if len(sys.argv) > 2 else "ohos_test.log"
CWD = os.path.dirname(os.path.abspath(BIN)) or "."

# 真实语义（实测）：命令类参数先执行 kbd.open(vendorID, productID, serial)，
# 无设备时 open 失败 -> main.cpp return 2 + "Matching or compatible device not found"；
# --list-keyboards 在 open 之前返回空列表 -> return 1。
CASES = [
    ("case1-help", ["-h"], 0, ["Version : 0.4.3"]),
    ("case2-list-no-device", ["--list-keyboards"], 1, ["device not found"]),
    ("case3-invalid-color", ["-a", "invalidcolor"], 2, ["device not found"]),
    ("case4-valid-color-no-device", ["-a", "ff00ff"], 2, ["device not found"]),
]


def run_case(name, args, want_rc, want_substrs):
    proc = subprocess.run(
        [BIN] + args,
        cwd=CWD,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        timeout=60,
    )
    out = proc.stdout.decode("utf-8", errors="replace")
    rc = proc.returncode
    ok_rc = rc == want_rc
    ok_str = all(s.lower() in out.lower() for s in want_substrs)
    lines = [
        f"===== {name} =====",
        f"command: {BIN} {' '.join(args)}",
        f"cwd: {CWD}",
        f"exit_code: {rc} (expected {want_rc}: {'PASS' if ok_rc else 'FAIL'})",
        f"substring_check: {want_substrs} -> {'PASS' if ok_str else 'FAIL'}",
        "stdout/stderr:",
        out.rstrip(),
        "",
    ]
    text = "\n".join(lines)
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(text)
    return ok_rc and ok_str


def main():
    with open(LOG, "w", encoding="utf-8") as f:
        f.write(f"g810-led OHOS test log\nstart: {datetime.datetime.now().isoformat()}\n")
        f.write(f"binary: {BIN}\n")
        f.write(f"host arch: {os.uname().machine}\n\n")
    results = [run_case(*case) for case in CASES]
    summary = f"OHOS-TEST {'ALL-PASS' if all(results) else 'FAILED'}: {sum(results)}/{len(results)} cases passed"
    with open(LOG, "a", encoding="utf-8") as f:
        f.write("\n" + summary + "\n")
    print(summary)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
