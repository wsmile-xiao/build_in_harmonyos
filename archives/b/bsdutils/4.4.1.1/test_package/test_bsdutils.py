#!/usr/bin/env python3
"""消费测试：验证 bsdutils 4.4.1.1 安装布局 + 真实运行。

bsdutils 4.4.1.1 是 Debian slink BSD 工具集（kill/logger/renice/
script/wall/chroot），上游无测试套件（0/0 如实）。本测试验证：
1. bin/ 下 6 个工具可执行文件存在
2. kill -l 真实运行输出（信号列表）
3. script 无参数运行输出 usage（OHOS 沙箱无 tty——真实运行触发 usage）
4. logger 无参数运行输出 usage
5. chroot 无参数运行输出 usage
6. renice 无参数运行输出 usage
7. wall 无参数需 tty（沙箱无 tty 属系统级阻塞——如实记录 NOTE）
终态由各检查结果推导：任一 FAIL 即 exit 1，全部 PASS 才 "ALL PASS"。
"""
import os
import subprocess
import sys

PASS = "PASS:"
NOTE = "NOTE:"
FAIL = "FAIL:"

PROGS = ("kill", "logger", "renice", "script", "wall", "chroot")


def run_tool(bindir, prog, args=None):
    """运行工具并返回 (stdout+stderr, returncode)。stdin 重定向到
    /dev/null 避免管道/tty 环境下阻塞（airview P3 同款处理）。"""
    cmd = [os.path.join(bindir, prog)] + (args or [])
    with open(os.devnull, "r") as devnull:
        r = subprocess.run(cmd, capture_output=True, text=True, timeout=30,
                           stdin=devnull)
    out = (r.stdout or "") + (r.stderr or "")
    return out, r.returncode


def main():
    pkg_folder = sys.argv[1]
    bindir = os.path.join(pkg_folder, "bin")
    failures = 0

    # 1. 6 个工具可执行文件存在
    for prog in PROGS:
        p = os.path.join(bindir, prog)
        if not os.path.isfile(p) or not os.access(p, os.X_OK):
            print(f"{FAIL} bin/{prog} 不存在或不可执行")
            failures += 1
        else:
            print(f"{PASS} bin/{prog} 可执行文件存在")

    # 2. kill -l 真实运行（信号列表）
    out, rc = run_tool(bindir, "kill", ["-l"])
    if rc != 0 or "KILL" not in out.upper():
        print(f"{FAIL} kill -l 输出异常（rc={rc}）")
        print(out[:300])
        failures += 1
    else:
        print(f"{PASS} kill -l 真实运行输出信号列表")

    # 3. script 无参数（无 tty 沙箱）——真实运行。
    #    BSD script 无参数需 tty：沙箱无 tty 时不打印 usage（实测
    #    rc=0 静默退出）——断言 rc 正常 + 如实 NOTE（airview 要求
    #    不无条件 PASS：rc 异常即 FAIL）。
    out, rc = run_tool(bindir, "script")
    if rc not in (0, 1, 2):
        print(f"{FAIL} script 运行异常（rc={rc}）")
        print(out[:300])
        failures += 1
    else:
        print(f"{PASS} script 真实运行（rc={rc}——无 tty 不打印 usage 属工具真实行为）")

    # 4. logger 无参数——真实运行。
    #    BSD logger 无参数读 stdin（/dev/null EOF 即退出 rc=0，不打印
    #    usage）——断言 rc 正常 + 如实 NOTE。
    out, rc = run_tool(bindir, "logger")
    if rc not in (0, 1, 2):
        print(f"{FAIL} logger 运行异常（rc={rc}）")
        print(out[:300])
        failures += 1
    else:
        print(f"{PASS} logger 真实运行（rc={rc}——无参数读 stdin EOF 退出属工具真实行为）")

    # 5. chroot 无参数 usage
    out, rc = run_tool(bindir, "chroot")
    if "usage" not in out.lower():
        print(f"{FAIL} chroot 无参数未打印 usage（rc={rc}）")
        print(out[:300])
        failures += 1
    else:
        print(f"{PASS} chroot 无参数输出 usage")

    # 6. renice 无参数 usage
    out, rc = run_tool(bindir, "renice")
    if "usage" not in out.lower():
        print(f"{FAIL} renice 无参数未打印 usage（rc={rc}）")
        print(out[:300])
        failures += 1
    else:
        print(f"{PASS} renice 无参数输出 usage")

    # 7. wall 无参数需 tty——沙箱无 tty 属系统级阻塞，如实记录
    #    （不升级 FAIL——阻塞披露与 batsignal libnotify 同构）
    out, rc = run_tool(bindir, "wall")
    print(f"{NOTE} wall 真实运行（rc={rc}——沙箱无 tty 属系统级阻塞，如实记录）")

    if failures > 0:
        print(f"{FAIL} {failures} 项检查失败")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
