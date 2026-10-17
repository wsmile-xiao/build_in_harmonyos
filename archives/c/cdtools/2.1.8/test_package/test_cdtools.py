#!/usr/bin/env python3
"""消费测试：验证 cdtools 2.1.8 安装布局 + 真实运行。

cdtools（上游 cdtool）是 CD-ROM 音频控制工具集（单程序多名字）：
主程序装在 lib/cdtool/cdtool，bin 下是符号链接（cdplay/cdstop/
cdeject/cdctrl/cdown 等指向 ../lib/cdtool/cdtool）。本测试验证：
1. bin/cdplay 符号链接存在（指向 lib/cdtool/cdtool 主程序）
2. cdplay --version 真实运行（输出 CDTOOL 版本）
3. 上游无独立测试目录（cdtool 运行需光驱——OHOS 无光驱，如实记录）
终态由各检查结果推导：任一 FAIL 即 exit 1，全部 PASS 才 "ALL PASS"。
"""
import os
import subprocess
import sys

PASS = "PASS:"
NOTE = "NOTE:"
FAIL = "FAIL:"


def main():
    pkg_folder = sys.argv[1]
    bindir = os.path.join(pkg_folder, "bin")
    failures = 0

    # 1. bin/cdplay 符号链接存在（指向 lib/cdtool/cdtool 主程序）
    cdplay = os.path.join(bindir, "cdplay")
    if not os.path.islink(cdplay):
        print(f"{FAIL} bin/cdplay 符号链接不存在")
        sys.exit(1)
    target = os.readlink(cdplay)
    if "cdtool" not in target:
        print(f"{FAIL} bin/cdplay 符号链接指向异常（{target}）")
        sys.exit(1)
    print(f"{PASS} bin/cdplay 符号链接存在（-> {target}）")

    # 2. cdplay --version 真实运行（回归信号：崩溃/无版本必须 FAIL；
    #    cdtool 是单程序多名字，cdplay 符号链接到 cdtool 主程序）
    with open(os.devnull, "r") as devnull:
        r = subprocess.run([cdplay, "--version"], capture_output=True,
                           text=True, timeout=30, stdin=devnull)
    out = (r.stdout or "") + (r.stderr or "")
    if "CDTOOL" in out and "2.1.8" in out:
        print(f"{PASS} cdplay --version 真实运行（CDTOOL 2.1.8）")
    else:
        print(f"{FAIL} cdplay --version 输出异常（rc={r.returncode}）")
        print(out[:200])
        failures += 1

    # 3. 上游无独立测试目录（cdtool 运行需光驱——OHOS 无光驱，
    #    如实记录不伪造通过率）
    print(f"{NOTE} 上游无独立测试目录——cdtool 运行需光驱"
          f"（OHOS 无光驱），如实记录不运行")
    # 4. R40：cdtool 属外设/硬件类库（CD-ROM 控制），消费测试仅覆盖
    #    符号链接 + --version 输出——CD 控制核心功能（播放/停止/弹出等
    #    ioctl 操作）无真机验证，需人工确认适配完整性
    print(f"{NOTE} R40：CD 控制核心功能无真机验证——需人工确认适配完整性")

    if failures > 0:
        print(f"{FAIL} {failures} 项检查失败")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
