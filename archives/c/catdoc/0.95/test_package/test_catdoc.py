#!/usr/bin/env python3
"""消费测试：验证 catdoc 0.95 安装布局 + 真实运行。

catdoc 是 MS Word/Excel/PPT 文本提取工具（catdoc/catppt/xls2csv），
上游无测试套件（0/0 如实）。wordview 是 tcl 脚本（WISH 解释器）——
OHOS 无 tclsh，系统级阻塞如实记录。本测试验证：
1. bin/ 下 3 个工具可执行文件存在
2. catdoc 无参数真实运行（usage 或 rc 正常）
3. xls2csv 无参数真实运行（同强度校验——airview P2）
4. wordview 阻塞披露（系统级——无 tcl 解释器）
所有子进程 stdin 重定向 /dev/null（airview P3——防管道/tty 阻塞）。
终态由各检查结果推导：任一 FAIL 即 exit 1，全部 PASS 才 "ALL PASS"。
"""
import os
import subprocess
import sys

PASS = "PASS:"
NOTE = "NOTE:"
FAIL = "FAIL:"

PROGS = ("catdoc", "catppt", "xls2csv")


def run_tool(bindir, prog, args=None):
    """运行工具并返回 (stdout+stderr, returncode)。stdin 重定向到
    /dev/null 避免管道/tty 环境下阻塞（airview P3）。"""
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

    # 1. 3 个工具可执行文件存在
    for prog in PROGS:
        p = os.path.join(bindir, prog)
        if not os.path.isfile(p) or not os.access(p, os.X_OK):
            print(f"{FAIL} bin/{prog} 不存在或不可执行")
            failures += 1
        else:
            print(f"{PASS} bin/{prog} 可执行文件存在")

    # 2. catdoc 无参数（无输入文件）——真实运行（usage 或 rc 正常）
    out, rc = run_tool(bindir, "catdoc")
    if "usage" not in out.lower() and rc not in (0, 1, 2):
        print(f"{FAIL} catdoc 运行异常（rc={rc}）")
        print(out[:300])
        failures += 1
    else:
        print(f"{PASS} catdoc 真实运行（rc={rc}——无参数无输入文件属预期）")

    # 3. xls2csv 无参数——真实运行（同强度校验，airview P2）
    out, rc = run_tool(bindir, "xls2csv")
    if "usage" not in out.lower() and rc not in (0, 1, 2):
        print(f"{FAIL} xls2csv 运行异常（rc={rc}）")
        print(out[:300])
        failures += 1
    else:
        print(f"{PASS} xls2csv 真实运行（rc={rc}）")

    # 4. wordview 阻塞披露（系统级阻塞——tcl 脚本需 WISH 解释器，
    #    OHOS 沙箱无 tclsh——如实记录，不伪造通过）
    print(f"{NOTE} wordview 运行阻塞（系统级）：wordview 是 tcl 脚本需 "
          f"WISH 解释器，OHOS 沙箱无 tclsh——catdoc/catppt/xls2csv 验证不受影响")

    if failures > 0:
        print(f"{FAIL} {failures} 项检查失败")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
