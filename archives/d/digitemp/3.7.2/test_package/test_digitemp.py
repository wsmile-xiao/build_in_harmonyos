#!/usr/bin/env python3
"""digitemp 3.7.2 消费者测试 (adaptation-added consumer tests).

上游 digitemp v3.7.2 没有自动化测试套件:
  * Makefile 无 check / test 目标;
  * `-T` 自检选项在本版本只登记了 OPT_TEST 标志, 无实现 (实测 exit 3),
    其实现是上游 master 后续才加入的;
本脚本因此全部为适配新增的消费者测试: 直接执行打包产物并断言其可观测行为,
覆盖命令行契约 (用法/版本横幅/适配器变体)、rcfile 错误处理、串口设备错误处理,
并通过 pty 真实走一遍串口设备打开 + 1-Wire 搜索代码路径。

被测二进制: digitemp_DS9097 / digitemp_DS9097U (均由本包产出)
"""
import os
import pty
import shutil
import subprocess
import sys
import tempfile

EXIT_OK = 0
EXIT_NORC = 2      # rcfile 解析失败
EXIT_HELP = 3      # -h / 非法选项 -> 打印用法
EXIT_NOPORT = 7    # 串口设备不存在

BANNER = "DigiTemp v3.7.2"
BINARIES = ("digitemp_DS9097", "digitemp_DS9097U")

_results = []


def check(name, ok, detail=""):
    _results.append((name, bool(ok)))
    print("[%s] %s%s" % ("PASS" if ok else "FAIL", name, (" -- " + detail) if detail else ""))
    return bool(ok)


def run_binary(binary, args, cwd, timeout=60):
    proc = subprocess.run(
        [binary] + args, cwd=cwd, capture_output=True, text=True, timeout=timeout
    )
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


def scratch_dir():
    """遵守 TMPDIR 的临时目录 (/tmp 在鸿蒙上只读, E002)."""
    base = os.environ.get("TMPDIR") or os.path.expanduser("~/tmp")
    os.makedirs(base, exist_ok=True)
    return tempfile.mkdtemp(prefix="digitemp-test-", dir=base)


def write_conf(path, body):
    with open(path, "w") as fh:
        fh.write(body)
    return path


def pty_roundtrip(binary, work):
    """用 pty 冒充串口, 真实执行 digitemp 的设备打开 + 1-Wire 搜索路径."""
    try:
        master, slave = pty.openpty()
    except OSError as exc:  # 受限环境下无法建 pty: 跳过该项, 不计入断言
        return None, "no pty available: %s" % exc
    try:
        conf = write_conf(os.path.join(work, "pty.conf"), "TTY %s\n" % os.ttyname(slave))
        rc, out = run_binary(binary, ["-c", conf, "-a"], work)
        return (rc == EXIT_OK and BANNER in out), "rc=%d" % rc
    finally:
        os.close(master)
        os.close(slave)


def main(package_folder):
    bindir = os.path.join(package_folder, "bin")
    work = scratch_dir()
    try:
        # 1-6: 两个适配器变体的用法契约 (用法退出码 / 版本横幅 / 变体标识)
        for name, adapter in (("digitemp_DS9097", "DS9097"),
                              ("digitemp_DS9097U", "DS9097U")):
            binary = os.path.join(bindir, name)
            rc, out = run_binary(binary, ["-h"], work)
            check("%s -h 退出码为用法状态 %d" % (name, EXIT_HELP), rc == EXIT_HELP, "rc=%d" % rc)
            check("%s -h 打印版本横幅" % name, BANNER in out)
            check("%s -h 标识适配器变体" % name, ("Compiled for %s" % adapter) in out)

        # 7-8: 非法选项 -> getopt 报错 + 用法退出码
        for name in BINARIES:
            rc, out = run_binary(os.path.join(bindir, name), ["-Z"], work)
            tolerant = "unrecognized option" in out or "invalid option" in out
            check("%s 拒绝未知选项" % name, rc == EXIT_HELP and tolerant, "rc=%d" % rc)

        # 9: rcfile 语法错误 -> EXIT_NORC
        bad = write_conf(os.path.join(work, "syntax.conf"), "THIS IS NOT A VALID RCFILE LINE\n")
        rc, out = run_binary(os.path.join(bindir, "digitemp_DS9097"), ["-c", bad, "-a"], work)
        check("rcfile 语法错误被拒绝", rc == EXIT_NORC and "Error reading rcfile" in out, "rc=%d" % rc)

        # 10-11: 串口设备不存在 -> EXIT_NOPORT
        nodev = write_conf(os.path.join(work, "nodev.conf"), "TTY /nonexistent/ttyS9\n")
        for name in BINARIES:
            rc, out = run_binary(os.path.join(bindir, name), ["-c", nodev, "-a"], work)
            check("%s 报告串口设备不存在" % name,
                  rc == EXIT_NOPORT and "does not exist" in out, "rc=%d" % rc)

        # 12: 真实串口 I/O 路径 (pty)
        ok, detail = pty_roundtrip(os.path.join(bindir, "digitemp_DS9097"), work)
        if ok is None:
            print("[SKIP] pty 串口往返: %s" % detail)
        else:
            check("digitemp_DS9097 与 pty 串口完成一次通信", ok, detail)
    finally:
        shutil.rmtree(work, ignore_errors=True)

    failed = [name for name, ok in _results if not ok]
    print("\n%d/%d 消费者断言通过" % (len(_results) - len(failed), len(_results)))
    return 1 if failed else 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: test_digitemp.py <package_folder>")
        sys.exit(2)
    sys.exit(main(sys.argv[1]))
