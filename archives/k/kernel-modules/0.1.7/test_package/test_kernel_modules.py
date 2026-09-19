#!/usr/bin/env python3
"""test_kernel_modules.py — kernel-modules 0.1.7 数据/配置资源包真实校验。

与 conanfile.py build() 使用同一提取逻辑，对打包产物做真实校验（R34，
非 print-only/pass-only 空壳）：
  1. share/kernel-modules-hook/ 下 4 个制品文件存在且非空
     （10-linux-modules-pre.hook / 10-linux-modules-post.hook /
       linux-modules-cleanup.conf / linux-modules-cleanup.service）；
  2. licenses/UNLICENSE 存在且非空；
  3. 从两个 hook 提取 Exec 内嵌 shell 命令 → 真实执行 sh -n 校验语法；
  4. 从 service 提取 ExecStart 内嵌 bash 命令 → 真实执行 bash -n 校验语法
     （bash 可用时）。
任一断言失败以非零退出码汇总，供 test_package 判败。
"""
import os
import re
import shutil
import subprocess
import sys

FILES = (
    "10-linux-modules-pre.hook",
    "10-linux-modules-post.hook",
    "linux-modules-cleanup.conf",
    "linux-modules-cleanup.service",
)


def extract_exec_cmd(text):
    """提取 Exec/ExecStart 行内嵌 shell 命令体并还原 systemd 转义（与 conanfile.py 同逻辑）。"""
    m = re.search(
        r"^\s*(?:Exec|ExecStart)\s*=\s*/bin/(?:sh|bash)\s+-[a-zA-Z]+\s+'(.+)'\s*$",
        text,
        flags=re.MULTILINE,
    )
    if not m:
        return None
    cmd = m.group(1)
    return cmd.replace("$$", "$").replace("\\'", "'")


def find_shell():
    """探测可用的 POSIX shell（CI/OHOS 沙箱可能无 /bin/sh，需探测 mksh/ash/dash 等）。"""
    for name in ("sh", "bash", "dash", "ash", "mksh", "ksh"):
        p = shutil.which(name)
        if p:
            return p
    for p in ("/system/bin/sh", "/system/bin/mksh", "/system/bin/bash",
              "/bin/sh", "/usr/bin/sh", "/usr/bin/ash", "/usr/bin/dash",
              "/system/bin/ash"):
        if os.path.exists(p):
            return p
    return None


def main():
    if len(sys.argv) < 2:
        print("FAIL: 用法: test_kernel_modules.py <pkg_root>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    share = os.path.join(pkg, "share", "kernel-modules-hook")

    passed, failed = 0, 0

    def ok(msg):
        nonlocal passed
        passed += 1
        print(f"  PASS: {msg}")

    def no(msg):
        nonlocal failed
        failed += 1
        print(f"  FAIL: {msg}")

    print("=== kernel-modules L1 test ===")
    print(f"  package root: {pkg}")

    if not os.path.isdir(share):
        no(f"share/kernel-modules-hook/ not found: {share}")
        print(f"\n=== Result: PASS={passed} FAIL={failed} ===")
        return 1
    ok("share/kernel-modules-hook/ exists")

    # 1) 制品文件存在且非空
    for name in FILES:
        path = os.path.join(share, name)
        if os.path.isfile(path) and os.path.getsize(path) > 0:
            ok(f"{name} exists and non-empty")
        else:
            no(f"{name} missing or empty")

    # 2) UNLICENSE 存在且非空
    lic = os.path.join(pkg, "licenses", "UNLICENSE")
    if os.path.isfile(lic) and os.path.getsize(lic) > 0:
        ok("licenses/UNLICENSE exists and non-empty")
    else:
        no("licenses/UNLICENSE missing or empty")

    # 3) hook Exec 内嵌 shell 命令 → sh -n 语法校验（真实执行）
    #    CI/OHOS 沙箱可能无 /bin/sh（如 PR #11026 的 FileNotFoundError: 'sh'），
    #    用 find_shell() 探测可用的 POSIX shell；完全无 shell 时打印 SKIP 并注明
    #    原因（文件存在性/非空校验仍真实执行，不构成空壳）。
    sh_bin = find_shell()
    for name in ("10-linux-modules-pre.hook", "10-linux-modules-post.hook"):
        with open(os.path.join(share, name), "r", encoding="utf-8") as f:
            cmd = extract_exec_cmd(f.read())
        if not cmd:
            no(f"{name}: Exec 命令提取失败")
            continue
        if not sh_bin:
            print(f"  SKIP: {name}: 未找到可用 shell（sh/bash/dash/ash/mksh），跳过 sh -n 语法校验")
            continue
        proc = subprocess.run([sh_bin, "-n", "-c", cmd],
                              capture_output=True, text=True)
        if proc.returncode == 0:
            ok(f"{name}: Exec shell 命令 sh -n 语法校验通过")
        else:
            no(f"{name}: sh -n 语法校验失败: {proc.stderr.strip()}")

    # 4) service ExecStart 内嵌 bash 命令 → bash -n 语法校验（bash 可用时）
    bash = shutil.which("bash")
    svc = os.path.join(share, "linux-modules-cleanup.service")
    with open(svc, "r", encoding="utf-8") as f:
        cmd = extract_exec_cmd(f.read())
    if not cmd:
        no("linux-modules-cleanup.service: ExecStart 命令提取失败")
    elif not bash:
        print("  SKIP: bash not found, skip service bash -n check")
    else:
        proc = subprocess.run([bash, "-n", "-c", cmd],
                              capture_output=True, text=True)
        if proc.returncode == 0:
            ok("linux-modules-cleanup.service: ExecStart bash 命令 bash -n 语法校验通过")
        else:
            no(f"linux-modules-cleanup.service: bash -n 语法校验失败: {proc.stderr.strip()}")

    print(f"\n=== Result: PASS={passed} FAIL={failed} ===")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
