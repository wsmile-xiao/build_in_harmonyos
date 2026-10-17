#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""xringd 1.20 消费者测试：真执行安装后的 CLI/守护命令面。

口径（R51/R34）：
  * 每条用例都真起子进程，断言退出码 + 实际输出文本；不是"编过即通过"。
  * 守护/可能阻塞的调用一律套 subprocess timeout；**超时按 FAIL 计**，不跳过。
  * xringd 的运行面要串口 Ring-Indicator 线（编译期内置 /dev/modem）。本设备
    /dev/modem 与 /dev/ttyS* 实测不存在，相关用例断言的是**真实失败形态**
    （open 失败 → 固定错误文 + ENOENT + 退出码 1），不把"跑不起来"记成功能通过。
"""

import os
import struct
import subprocess
import sys
import tempfile

TIMEOUT = 20
_counter = {"pass": 0, "fail": 0, "total": 0}
_lines = []


def check(name, cond, detail=""):
    """一条断言 = 一次 check。失败不抛异常，全部跑完再汇总（要真实分母）。"""
    _counter["total"] += 1
    if cond:
        _counter["pass"] += 1
        _lines.append("PASS  {}".format(name))
    else:
        _counter["fail"] += 1
        _lines.append("FAIL  {}  ::  {}".format(name, str(detail)[:300]))
    return bool(cond)


def run(args, **kw):
    """带 timeout 的真执行；超时抛给调用方按 FAIL 记账。"""
    kw.setdefault("input", None)
    return subprocess.run(args, capture_output=True, text=True, timeout=TIMEOUT, **kw)


def out(res):
    return (res.stdout or "") + (res.stderr or "")


def elf_machine(path):
    with open(path, "rb") as fh:
        head = fh.read(20)
    if len(head) < 20 or head[:4] != b"\x7fELF":
        return None, None
    return head[5], struct.unpack("<H", head[18:20])[0]


def main():
    if len(sys.argv) != 2:
        print("usage: test_xringd.py <package_folder>")
        return 2
    pkg = sys.argv[1]
    xringd = os.path.join(pkg, "bin", "xringd")
    uartcount = os.path.join(pkg, "bin", "uartcount")
    man8 = os.path.join(pkg, "share", "man", "man8", "xringd.8")
    sample = os.path.join(pkg, "res", "xringd.conf.sample")

    # --- 1) 交付物落位 -------------------------------------------------
    for label, path, exe in (
        ("bin/xringd 存在", xringd, True),
        ("bin/uartcount 存在", uartcount, True),
        ("man8/xringd.8 存在", man8, False),
        ("res/xringd.conf.sample 存在", sample, False),
    ):
        check(label, os.path.isfile(path), "missing " + path)
    check("bin/xringd 有可执行位", os.access(xringd, os.X_OK), oct(os.stat(xringd).st_mode) if os.path.exists(xringd) else "n/a")
    check("bin/uartcount 有可执行位", os.access(uartcount, os.X_OK), oct(os.stat(uartcount).st_mode) if os.path.exists(uartcount) else "n/a")

    # --- 2) 产物是本平台 ELF/AArch64（不是上游打包带的 i386 老二进制）---
    for label, path in (("xringd", xringd), ("uartcount", uartcount)):
        try:
            ei_class, e_machine = elf_machine(path)
        except OSError as exc:
            ei_class, e_machine = None, None
            check(label + " 可读 ELF 头", False, exc)
            continue
        check(label + " 是 ELF", ei_class is not None, repr(ei_class))
        check(label + " 是 AArch64(e_machine=183)", e_machine == 183, "got " + repr(e_machine))

    # --- 3) 配置夹具 ---------------------------------------------------
    tmp = tempfile.mkdtemp(prefix="xringd-t")
    good = os.path.join(tmp, "good.conf")
    with open(good, "w") as fh:
        fh.write("# fixture\nR 10-25 R 30 : /bin/true\n")
    bad = os.path.join(tmp, "bad.conf")
    with open(bad, "w") as fh:
        fh.write("# fixture\nBOGUS LINE HERE\n")

    # --- 4) 命令面：-h / 未知选项（usage_and_die 的退出码是 1）-----------
    try:
        r = run([xringd, "-h"])
        check("-h 退出码=1", r.returncode == 1, r.returncode)
        check("-h 打 usage 行", "usage:" in out(r), out(r)[:200])
        check("-h 报版本串 1.20（与任务版本一致）", "xringd version 1.20" in out(r), out(r)[:200])
    except subprocess.TimeoutExpired as exc:
        check("-h 在 20s 内返回", False, exc)

    try:
        r = run([xringd, "-Zzz"])
        check("未知选项退出码=1（走 usage_and_die）", r.returncode == 1, r.returncode)
        check("未知选项打 usage 行", "usage:" in out(r), out(r)[:200])
    except subprocess.TimeoutExpired as exc:
        check("未知选项在 20s 内返回", False, exc)

    # --- 5) 真实功能：配置文件语法校验（-n 在碰设备前就 exit(0)）---------
    try:
        r = run([xringd, "-c", good, "-n"])
        check("自建合法配置 -n 退出码=0", r.returncode == 0, out(r)[:200])
        check("自建合法配置 -n 报 syntax ok", "syntax ok" in out(r), out(r)[:200])

        r = run([xringd, "-c", sample, "-n"])
        check("上游样例配置 -n 退出码=0", r.returncode == 0, out(r)[:200])
        check("上游样例配置 -n 报 syntax ok", "syntax ok" in out(r), out(r)[:200])

        r = run([xringd, "-c", good, "-n", "-t", "3", "-i", "200", "-l", "100"])
        check("多选项组合仍 syntax ok", r.returncode == 0 and "syntax ok" in out(r), out(r)[:200])

        r = run([xringd, "-c", bad, "-n"])
        check("非法配置退出码=1", r.returncode == 1, out(r)[:200])
        check("非法配置报出错行号 line 2", "error in config file, line 2" in out(r), out(r)[:200])

        missing = os.path.join(tmp, "nope.conf")
        r = run([xringd, "-c", missing, "-n"])
        check("缺配置文件退出码=1", r.returncode == 1, out(r)[:200])
        check("缺配置文件报 cannot open config file", "cannot open config file" in out(r), out(r)[:200])
    except subprocess.TimeoutExpired as exc:
        check("配置校验类调用在 20s 内返回", False, exc)

    # --- 6) 运行面（平台能力缺失，断言真实失败形态，不记成功能可用）------
    try:
        r = run([xringd, "-c", good])
        o = out(r)
        check("默认设备运行退出码=1（非 0，未静默成功）", r.returncode == 1, o[:200])
        check("默认设备运行报 error opening modem device", "error opening modem device" in o, o[:200])
        check("失败形态是 ENOENT（/dev/modem 不存在，平台能力缺失）", "No such file or directory" in o, o[:200])

        r = run([xringd, "-c", good, "-m", "/dev/ttyS0"])
        o = out(r)
        check("-m 覆盖设备后仍退出码=1", r.returncode == 1, o[:200])
        check("-m /dev/ttyS0 同样 open 失败（串口面缺失）", "error opening modem device" in o, o[:200])
    except subprocess.TimeoutExpired as exc:
        check("守护路径在 20s 内返回（未阻塞）", False, exc)

    try:
        r = run([uartcount, "/dev/null"])
        check("uartcount 对非串口节点退出码=1（TIOCGICOUNT 被拒）", r.returncode == 1, out(r)[:200])
        check("uartcount 对非串口节点不吐计数", "Count:" not in (r.stdout or ""), (r.stdout or "")[:200])

        r = run([uartcount])
        o = out(r)
        check("uartcount 默认 /dev/modem 退出码=1", r.returncode == 1, o[:200])
        check("uartcount 默认设备报 cannot open modem device", "cannot open modem device" in o, o[:200])
    except subprocess.TimeoutExpired as exc:
        check("uartcount 在 20s 内返回（未阻塞）", False, exc)

    # --- 汇总（真实分母，不美化）----------------------------------------
    print("\n".join(_lines))
    print(
        "SUMMARY xringd consumer: total={} passed={} failed={}".format(
            _counter["total"], _counter["pass"], _counter["fail"]
        )
    )
    print("ASSERTION_COUNT={}".format(_counter["total"]))
    return 0 if _counter["fail"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
