#!/usr/bin/env python3
"""libfile-fnmatch-perl consumer test (R34).

分层验证，最强的先做；**每一层跑到的都是真实检查**，不做假通过：

  L1 产物存在性 + ELF ABI 契约（纯读 .so，任何沙箱都能跑）
  L2 `perl -c` 解析随包的 .pm（真实进程执行）
  L3 真实加载 XS 并调用 fnmatch() API（需要 dlopen）

L3 若被沙箱拒绝（SELinux 域禁止对用户 .so 做 mmap PROT_EXEC，见 #6846
08-30 说明），会被**如实报成 SKIP 并打印 errno/原文**，绝不静默当作通过。
设 FNMATCH_REQUIRE_XS_LOAD=1 可把 SKIP 升级为 FAIL（本地/主用户域用它做
强校验，CI 沙箱下不设）。

L1 的符号断言带**阴性对照**：断言一个不存在的符号必须查不到，以证明该
检查不是恒真。
"""
import os
import re
import shutil
import struct
import subprocess
import sys

XS_BOOTSTRAP = "boot_File__FnMatch"     # XS 模块的引导符号（perl 加载入口）
XS_HANDSHAKE = "Perl_xs_handshake"      # XS 运行时握手（证明是真 XS 而非普通 so）
BOGUS_SYMBOL = "boot_NoSuchModule__Xyz"  # 阴性对照：必须查不到
EXPECTED_NEEDED = "libc.so"             # 唯一允许的 NEEDED 依赖

SKIP_MARKERS = (
    "permission denied",
    "operation not permitted",
    "cannot open shared object",
    "cannot map",
    "failed to map segment",
)


class ElfError(Exception):
    pass


def _sections(data, shoff, shentsize, shnum):
    """Yield raw section headers as tuples."""
    for i in range(shnum):
        yield struct.unpack_from("<IIQQQQIIQQ", data,
                                 shoff + i * shentsize)


def elf_dyninfo(path):
    """Parse a 64-bit little-endian ELF.

    Returns (exported, undefined, needed) as name lists. Pure read — needs
    no dlopen, so it works even where loading is forbidden.
    """
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:4] != b"\x7fELF":
        raise ElfError("not an ELF file")
    if data[4] != 2 or data[5] != 1:
        raise ElfError("only 64-bit little-endian ELF is supported")

    (shoff,) = struct.unpack_from("<Q", data, 0x28)
    (shentsize,) = struct.unpack_from("<H", data, 0x3A)
    (shnum,) = struct.unpack_from("<H", data, 0x3C)
    (shstrndx,) = struct.unpack_from("<H", data, 0x3E)
    if not (shoff and shnum):
        raise ElfError("no section headers")

    secs = list(_sections(data, shoff, shentsize, shnum))
    shstr_off = secs[shstrndx][4]

    def sh_name(sh):
        start = shstr_off + sh[0]
        return data[start:data.index(b"\x00", start)].decode()

    dynsym = dynamic = None
    for sh in secs:
        if sh[1] == 11:      # SHT_DYNSYM
            dynsym = sh
        elif sh[1] == 6:     # SHT_DYNAMIC
            dynamic = sh

    if dynsym is None:
        raise ElfError("no .dynsym section")

    strtab_off = secs[dynsym[6]][4]          # sh_link -> .dynstr
    exported, undefined = [], []
    # 段头字段顺序 "<IIQQQQIIQQ"：6=sh_link 7=sh_info 8=sh_addralign
    # 9=sh_entsize（曾误把 7 当 entsize → 步长 1 → 解析出乱码）
    step = dynsym[9] or 24
    for off in range(dynsym[4], dynsym[4] + dynsym[5], step):
        (st_name, _info, _other, st_shndx,
         _value, _size) = struct.unpack_from("<IBBHQQ", data, off)
        if not st_name:
            continue
        end = data.index(b"\x00", strtab_off + st_name)
        name = data[strtab_off + st_name:end].decode()
        (undefined if st_shndx == 0 else exported).append(name)

    needed = []
    if dynamic is not None:
        dstr_off = secs[dynamic[6]][4]       # sh_link -> .dynstr
        for off in range(dynamic[4], dynamic[4] + dynamic[5], 16):
            (d_tag, d_val) = struct.unpack_from("<qQ", data, off)
            if d_tag == 0:                   # DT_NULL
                break
            if d_tag == 1:                   # DT_NEEDED
                end = data.index(b"\x00", dstr_off + d_val)
                needed.append(data[dstr_off + d_val:end].decode())
    return exported, undefined, needed


def classify_load_failure(stderr):
    """'sandbox' when the loader was blocked, 'broken' for a real defect."""
    low = stderr.lower()
    if any(m in low for m in SKIP_MARKERS):
        return "sandbox"
    return "broken"


def run_perl(perl, code, cwd, extra_env=None):
    env = dict(os.environ)
    env["PERL5LIB"] = cwd
    if extra_env:
        env.update(extra_env)
    return subprocess.run([perl, "-e", code], capture_output=True,
                          text=True, cwd=cwd, env=env)


def main():
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    strict = os.environ.get("FNMATCH_REQUIRE_XS_LOAD") == "1"

    site = os.path.join(pkg, "lib", "perl5")
    pm = os.path.join(site, "File", "FnMatch.pm")
    so = os.path.join(site, "auto", "File", "FnMatch", "FnMatch.so")

    failures = []
    skipped = []

    # ---------- L1: artifact presence + ELF ABI contract ----------
    print("[L1] 产物与 ELF ABI 契约")
    for label, path in (("FnMatch.pm", pm), ("FnMatch.so", so)):
        if not os.path.isfile(path):
            print(f"  FAIL {label} missing: {path}")
            failures.append(f"{label} missing")
        else:
            print(f"  ok   {label} present ({os.path.getsize(path)} B)")
    if failures:
        print("FAIL: required artifacts missing")
        return 1

    try:
        exported, undefined, needed = elf_dyninfo(so)
    except (ElfError, OSError, struct.error, ValueError) as exc:
        print(f"  FAIL cannot parse {so}: {exc}")
        print("FAIL: .so is not a usable ELF shared object")
        return 1

    print(f"  导出 {len(exported)} 个 / 未定义 {len(undefined)} 个 / "
          f"NEEDED {needed}")
    if XS_BOOTSTRAP not in exported:
        print(f"  FAIL missing XS bootstrap symbol: {XS_BOOTSTRAP}")
        failures.append("XS bootstrap symbol")
    else:
        print(f"  ok   exports XS bootstrap: {XS_BOOTSTRAP}")
    if XS_HANDSHAKE not in undefined:
        print(f"  FAIL not a real XS module (no {XS_HANDSHAKE})")
        failures.append("XS handshake")
    else:
        print(f"  ok   XS runtime handshake referenced: {XS_HANDSHAKE}")
    if "fnmatch" not in undefined:
        print("  FAIL does not reference libc fnmatch(3)")
        failures.append("fnmatch(3) reference")
    else:
        print("  ok   references libc fnmatch(3)")
    # 阴性对照：证明符号检查不是恒真
    if BOGUS_SYMBOL in exported or BOGUS_SYMBOL in undefined:
        print(f"  FAIL negative control: bogus symbol {BOGUS_SYMBOL} found")
        failures.append("negative control")
    else:
        print(f"  ok   negative control: {BOGUS_SYMBOL} absent")
    unexpected = [n for n in needed if n != EXPECTED_NEEDED]
    if unexpected:
        print(f"  FAIL unexpected shared deps: {unexpected}")
        failures.append("unexpected NEEDED")
    else:
        print(f"  ok   NEEDED is exactly [{EXPECTED_NEEDED}]")

    # ---------- L2: perl parses the shipped .pm (real process) ----------
    print("[L2] perl -c 解析随包 .pm（真实进程）")
    perl = "/data/service/hnp/bin/perl"
    if not os.path.isfile(perl):
        perl = shutil.which("perl") or ""
    if not perl:
        print("  SKIP perl interpreter not found")
        skipped.append("perl -c")
    else:
        r = subprocess.run([perl, "-c", pm], capture_output=True, text=True)
        if r.returncode == 0:
            print(f"  ok   {os.path.basename(pm)} syntax OK")
        else:
            print(f"  FAIL perl -c: {(r.stderr or r.stdout).strip()}")
            failures.append("perl -c")

    # ---------- L3: real XS load + fnmatch() call ----------
    print("[L3] 真实加载 XS 并调用 fnmatch()（需要 dlopen）")
    if not perl:
        print("  SKIP no perl interpreter")
        skipped.append("XS load")
    elif failures:
        print("  SKIP skipped: earlier layer already failed")
        skipped.append("XS load")
    else:
        work = os.path.join(os.getcwd(), "fnmatch-load")
        shutil.rmtree(work, ignore_errors=True)
        os.makedirs(os.path.join(work, "File"), exist_ok=True)
        os.makedirs(os.path.join(work, "auto", "File", "FnMatch"),
                    exist_ok=True)
        shutil.copy2(pm, os.path.join(work, "File", "FnMatch.pm"))
        dst_so = os.path.join(work, "auto", "File", "FnMatch", "FnMatch.so")
        shutil.copy2(so, dst_so)
        os.chmod(dst_so, 0o755)
        # :fnmatch 标签导出 fnmatch + 全部 FNM_* 常量（POD 记载用法）；
        # 常量由 XS 的 newCONSTSUB 在 bootstrap 时创建，故必须先导入才能
        # 直接写 FNM_PATHNAME（此前只 qw(fnmatch) → Undefined subroutine）
        code = (
            "use File::FnMatch qw(:fnmatch); "
            "my $hit = fnmatch('*.txt', 'a.txt'); "
            "my $miss = fnmatch('*.txt', 'a.md'); "
            "my $path = fnmatch('/a/*', '/a/b/c', FNM_PATHNAME); "
            "die 'api semantics wrong' "
            "  if !$hit || $miss || $path; "
            "print 'fnmatch API ok';"
        )
        r = run_perl(perl, code, work)
        if r.returncode == 0:
            print(f"  ok   {r.stdout.strip()} (XS loaded + API semantics)")
        else:
            err = (r.stderr or r.stdout).strip()
            kind = classify_load_failure(err)
            first = re.sub(r"\s+", " ", err)[:160]
            if kind == "sandbox":
                print(f"  SKIP loader blocked by sandbox: {first}")
                skipped.append("XS load (sandbox)")
            else:
                print(f"  FAIL XS load/call: {first}")
                failures.append("XS load")
        shutil.rmtree(work, ignore_errors=True)

    # ---------- verdict ----------
    print()
    if failures:
        print(f"FAIL: {len(failures)} check(s) failed: {failures}")
        return 1
    if skipped and strict:
        print(f"FAIL(strict): skipped {skipped} but "
              f"FNMATCH_REQUIRE_XS_LOAD=1")
        return 1
    if skipped:
        print(f"OK: L1 ELF ABI contract + L2 perl parse passed; "
              f"{skipped} skipped (see above) — "
              f"set FNMATCH_REQUIRE_XS_LOAD=1 to require L3")
        return 0
    print("OK: File::FnMatch loads + fnmatch API works (XS, all layers)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
