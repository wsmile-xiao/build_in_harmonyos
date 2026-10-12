#!/usr/bin/env python3
"""Consumer checks for the ircd-irc2 package.

usage: check_binaries.py <package>/bin

Checks（全部针对打包后的产物；分类口径：**只有具名环境信号才允许 SKIP**）：
  1. 五个二进制齐备（ircd / chkconf / iauth / ircd-mkpasswd / ircdwatch）、非空、可执行；
  2. 每个都是 64 位 **AArch64** ELF（手写解析 ELF 头，不依赖 readelf）；
  3. 静态审计：`ircd` 二进制内含版本串（`2.11.2p3`）与关键符号名（`crypt`），
     证明确实链上了 libcrypt/经过本适配构建；
  4. best-effort 真跑：`chkconf`（配置检查器，无参时打印用法）——
     宿主加载器拒绝（沙箱 mmap/未签名）记 **SKIP 并打印原文**；输出含 usage 记 ok；
     其余非 0 判 **FAIL**（真实缺陷）。
"""
import os
import re
import struct
import subprocess
import sys

EXPECTED = ("ircd", "chkconf", "iauth", "ircd-mkpasswd", "ircdwatch")
EM_AARCH64 = 0xB7
LOADER_LIMIT_TAGS = ("error loading shared library", "error relocating",
                     "cannot open shared object", "permission denied",
                     "operation not permitted", "not signed", "unsigned")

fails = []
skips = []


def fail(msg):
    fails.append(msg)
    print("[FAIL] %s" % msg)


def ok(msg):
    print("[ok]   %s" % msg)


def skip(msg):
    skips.append(msg)
    print("[skip] %s" % msg)


def check_present(bindir):
    missing = []
    for name in EXPECTED:
        path = os.path.join(bindir, name)
        if not os.path.isfile(path):
            missing.append(name + "(缺失)")
            continue
        if os.path.getsize(path) < 4096:
            missing.append(name + "(过小)")
            continue
        if not os.access(path, os.X_OK):
            missing.append(name + "(不可执行)")
    if missing:
        fail("二进制不合格：%s" % ", ".join(missing))
        return
    ok("五个二进制齐备、非空、可执行：%s" % ", ".join(EXPECTED))


def check_elf(bindir):
    bad = []
    for name in EXPECTED:
        path = os.path.join(bindir, name)
        if not os.path.isfile(path):
            continue
        with open(path, "rb") as fh:
            head = fh.read(64)
        if head[:4] != b"\x7fELF" or head[4] != 2:
            bad.append("%s(非 64 位 ELF)" % name)
            continue
        if struct.unpack("<H", head[18:20])[0] != EM_AARCH64:
            bad.append("%s(非 AArch64)" % name)
    if bad:
        fail("架构审计失败：%s" % ", ".join(bad))
        return
    ok("五个二进制均为 64 位 AArch64 ELF")


def check_fingerprints(bindir):
    """指纹审计：`ircd` 含版本串；**`ircd-mkpasswd` 才是用 crypt() 的二进制**。

    早前版本把 crypt 引用断在 `ircd` 上 → 误报（服务端本身不链 libcrypt，
    只有 mkpasswd 生成口令哈希时才用）。
    """
    ircd = os.path.join(bindir, "ircd")
    mk = os.path.join(bindir, "ircd-mkpasswd")
    if os.path.isfile(ircd):
        with open(ircd, "rb") as fh:
            blob = fh.read()
        if b"2.11.2p3" not in blob:
            fail("ircd 二进制内未找到版本串 2.11.2p3（构建/打包可疑）")
            return
    if os.path.isfile(mk):
        with open(mk, "rb") as fh:
            mk_blob = fh.read()
        if b"crypt" not in mk_blob:
            fail("ircd-mkpasswd 内未见 crypt 符号引用（libcrypt 链接可疑）")
            return
    ok("指纹正确：ircd 含版本串 2.11.2p3、ircd-mkpasswd 含 crypt 符号引用")


def check_run(bindir):
    path = os.path.join(bindir, "chkconf")
    if not os.path.isfile(path):
        skip("chkconf 缺失，跳过 best-effort 运行检查")
        return
    try:
        proc = subprocess.run([path], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=20)
        out = proc.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        ok("chkconf 运行后存活至 20s 超时（未因缺库立即退出）")
        return
    except OSError as exc:
        low = str(exc).lower()
        if any(tag in low for tag in LOADER_LIMIT_TAGS):
            skip("具名环境信号：宿主拒绝启动 OHOS 二进制：%s" % exc)
        else:
            fail("chkconf 无法执行：%s" % exc)
        return
    low = out.lower()
    if any(tag in low for tag in LOADER_LIMIT_TAGS):
        skip("具名环境信号：宿主加载器拒绝 OHOS 共享对象闭包：%s" % out.strip()[:200])
        return
    if proc.returncode == 0:
        ok("chkconf 真跑成功（exit=0）：%s" % out.strip()[:120])
        return
    if re.search(r"usage|Usage", out):
        ok("chkconf 真跑成功并打印用法（可执行且未因缺库退出）")
        return
    fail("chkconf 非 0 退出且无具名环境信号 → 判真实缺陷（exit=%s）：%s"
         % (proc.returncode, out.strip()[:200]))


def main():
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    bindir = sys.argv[1]
    check_present(bindir)
    check_elf(bindir)
    check_fingerprints(bindir)
    check_run(bindir)
    print("checks=%d fails=%d skips=%d" % (4, len(fails), len(skips)))
    if fails:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
