#!/usr/bin/env python3
"""test_ohos — lsd2 1.9.9 HarmonyOS PC 专项验证.

在真实鸿蒙 PC（aarch64, musl）上对最终 Conan 包做独立专项检查。
lsd2 是 CLI 工具（package_type=application），因此本专项测试直接驱动
已安装的 lsd2 二进制（运行时产物），不链接库（上游无库产物）。

  T1  aarch64 ELF 验证（产物为 ELF64 AArch64）
  T2  musl libc（无 glibc / 无 ld-linux）
  T3  .codesign 段存在（OHOS 签名管线产出）
  T4  无宿主绝对路径泄漏（含 RPATH/RUNPATH 检查）
  T5  真实进化速率/定年计算：h1n1 示例（rooted tree + 日期约束）完整跑通，
      输出含 rate 与 tMRCA，退出码 0，时间为指数（可观察业务结果）

用法：python3 run_ohos_test.py <conan_package_folder>
退出码：0=全部通过；非 0=有失败（打印首个错误）。
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

READELF = os.environ.get("READELF") or shutil.which("readelf") \
    or "/data/service/hnp/bin/readelf"
STRINGS = os.environ.get("STRINGS") or shutil.which("strings") \
    or "/data/service/hnp/bin/strings"
BASH = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")

HOST_PATH_RES = [b"/storage/", b"/home/", b"/Users/", b"lsd2-1.9.9"]

# 上游 rooted_tree 示例 h1n1（由调用方复制到临时目录，来自 test_ohos data/）
TREE = "h1n1_phyml.tree"
DATE = "h1n1.date"


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: run_ohos_test.py <conan_package_folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    bin_dir = os.path.join(pkg, "bin")
    exe = os.path.join(bin_dir, "lsd2")
    if not os.path.isfile(exe):
        print("FAIL: lsd2 binary not found at %s" % exe, file=sys.stderr)
        return 1

    # T1: ELF64 AArch64
    r = subprocess.run([READELF, "-h", exe], capture_output=True)
    if b"ELF64" not in r.stdout or b"AArch64" not in r.stdout:
        print("FAIL: not ELF64 AArch64", file=sys.stderr)
        return 1

    # T2: musl libc（NEEDED 中无 glibc / ld-linux）
    r = subprocess.run([READELF, "-d", exe], capture_output=True)
    if b"GLIBC" in r.stdout or b"ld-linux" in r.stdout:
        print("FAIL: glibc/ld-linux detected", file=sys.stderr)
        return 1

    # T3: .codesign 段存在（OHOS 签名管线产出）
    r = subprocess.run([READELF, "-S", exe], capture_output=True)
    if b".codesign" not in r.stdout:
        print("FAIL: .codesign section missing", file=sys.stderr)
        return 1

    # T4: 无宿主机绝对路径
    st = subprocess.run([STRINGS, exe], capture_output=True)
    for pat in HOST_PATH_RES:
        if pat in st.stdout:
            print("FAIL: host path leak: %s" % pat.decode(), file=sys.stderr)
            return 1

    # T5: 真实定年计算（驱动最终产物 lsds2 二进制 + 上游 h1n1 示例）
    work = tempfile.mkdtemp(prefix="lsd2-test-ohos-")
    data = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    for fn in (TREE, DATE):
        with open(os.path.join(data, fn), "rb") as f:
            src = f.read()
        with open(os.path.join(work, fn), "wb") as f:
            f.write(src)
    out = os.path.join(work, "dating.out")
    run = subprocess.run(
        [BASH, "-c",
         '"$1" -i "$2" -d "$3" -o "$4" -s 1700 > run.log 2>&1; echo rc=$?',
         "run", exe, os.path.join(work, TREE), os.path.join(work, DATE), out],
        capture_output=True, text=True, cwd=work)
    log = ""
    try:
        with open(os.path.join(work, "run.log")) as f:
            log = f.read()
    except OSError:
        pass
    if "rc=0" not in run.stdout and run.returncode != 0:
        print("FAIL: lsd2 run rc != 0:\n" + log, file=sys.stderr)
        return 1
    m = re.search(r"rate\s+([0-9.eE+-]+)", log)
    t = re.search(r"tMRCA\s+([0-9.eE+-]+)", log)
    if not m or not t:
        print("FAIL: no rate/tMRCA in output:\n" + log, file=sys.stderr)
        return 1
    rate = float(m.group(1))
    tmca = float(t.group(1))
    # 与上游参考一致的量级：rate ~ 0.0027（H1N1 年进化速率），tMRCA ~ 2009
    if not (0.0001 < rate < 0.1 and 1900 < tmca < 2100):
        print("FAIL: rate/tMRCA out of expected range: %.6f / %.2f"
              % (rate, tmca), file=sys.stderr)
        return 1
    print("OHOS_LSD2_TESTS_PASS: rate=%.8f tMRCA=%.2f" % (rate, tmca))
    return 0


if __name__ == "__main__":
    sys.exit(main())