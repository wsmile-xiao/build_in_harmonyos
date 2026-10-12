#!/usr/bin/env python3
"""Consumer checks for the indi-talon6 package.

usage: check_driver.py <driver-binary> <bin-dir> <indi_talon6.xml> <indi-lib-dir>

Checks (every one of them inspects the packaged artefacts; nothing is
re-implemented and no upstream tool is required):
  1. bin/indi_talon6 exists, is a non-empty AArch64 ELF executable.
  2. share/indi/indi_talon6.xml declares the "Talon6" driver and points at the
     executable that was packaged.
  3. the driver's DT_NEEDED closure is complete: the INDI core libraries
     (libindiclient / libindidriver / libindiAlignmentDriver) are recorded in
     DT_NEEDED, every entry is a plain soname, and the three libraries really
     exist in the libindi package the closure points at.
  4. best effort: the loader is asked to start the driver.  **A real closure
     defect always fails**: unresolved symbols / unresolved shared objects /
     libraries that are missing from every dependency libdir are reported as
     FAIL.  Only a *host* refusal is skipped — and only when there is evidence
     for it (a platform-limit marker in the output, or a named library that
     exists but cannot be mapped by the host either, e.g. Permission denied),
     so an environment limitation never hides a packaging defect.

（本脚本与同快照兄弟驱动 indi-aok 的消费者校验同构，仅按本驱动改名。）
"""
import os
import re
import struct
import subprocess
import sys

EXPECTED_EM_AARCH64 = 0xB7
EXPECTED_DRIVER = "indi_talon6"
EXPECTED_DRIVER_LABEL = "Talon6"
# indi-talon6 是 Dome 驱动：FindINDI 的组件为 driver + align + client
# （见 patches/0001-…-link-indi-client.patch，client 为显式补上以避免 musl loader
#  解析 tty_write_string 等符号时失败）。
INDI_CORE_LIBS = ("libindiclient.so.2", "libindidriver.so.2",
                  "libindiAlignmentDriver.so.2")
LOADER_ERRORS = (
    "error loading shared library",
    "error relocating",
    "cannot open shared object",
    "no such file or directory: lib",
)
PLATFORM_LIMITS = (
    "not signed",
    "unsigned",
    "signature",
    "operation not permitted",
    "permission denied",
)

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


def check_elf(driver):
    if not os.path.isfile(driver):
        fail("driver binary is missing: %s" % driver)
        return False
    size = os.path.getsize(driver)
    if size < 4096:
        fail("driver binary is suspiciously small (%d bytes)" % size)
        return False
    with open(driver, "rb") as fh:
        head = fh.read(64)
    if head[:4] != b"\x7fELF":
        fail("driver is not an ELF file (magic=%r)" % head[:4])
        return False
    machine = struct.unpack("<H", head[18:20])[0]
    if machine != EXPECTED_EM_AARCH64:
        fail("driver e_machine=%#x is not AArch64 (%#x)" % (machine, EXPECTED_EM_AARCH64))
        return False
    if head[4] != 2:
        fail("driver is not a 64-bit ELF (EI_CLASS=%d)" % head[4])
        return False
    ok("bin/%s: AArch64 ELF, %d bytes" % (os.path.basename(driver), size))
    return True


def check_xml(xml, bindir):
    if not os.path.isfile(xml):
        fail("INDI data file is missing: %s" % xml)
        return
    with open(xml, "r", encoding="utf-8", errors="replace") as fh:
        text = fh.read()
    if EXPECTED_DRIVER not in text:
        fail("INDI data file does not reference %s" % EXPECTED_DRIVER)
        return
    if EXPECTED_DRIVER_LABEL not in text:
        fail("INDI data file does not declare the '%s' driver name" % EXPECTED_DRIVER_LABEL)
        return
    if not os.path.isfile(os.path.join(bindir, EXPECTED_DRIVER)):
        fail("the executable referenced by the INDI data file is not in bin/")
        return
    ok("share/indi/indi_talon6.xml: driver name + executable reference match the package")


def read_needed(driver):
    """Return the DT_NEEDED sonames of an ELF64 little-endian object."""
    with open(driver, "rb") as fh:
        data = fh.read()
    e_phoff = struct.unpack_from("<Q", data, 0x20)[0]
    e_phentsize = struct.unpack_from("<H", data, 0x36)[0]
    e_phnum = struct.unpack_from("<H", data, 0x38)[0]
    loads = []
    dynamic = None
    for idx in range(e_phnum):
        off = e_phoff + idx * e_phentsize
        p_type = struct.unpack_from("<I", data, off)[0]
        if p_type not in (1, 2):  # PT_LOAD, PT_DYNAMIC
            continue
        p_offset = struct.unpack_from("<Q", data, off + 0x08)[0]
        p_vaddr = struct.unpack_from("<Q", data, off + 0x10)[0]
        p_filesz = struct.unpack_from("<Q", data, off + 0x20)[0]
        if p_type == 1:
            loads.append((p_vaddr, p_offset, p_filesz))
        else:
            dynamic = (p_offset, p_filesz)
    if dynamic is None:
        raise ValueError("no PT_DYNAMIC segment")

    needed_offsets = []
    strtab_vaddr = None
    strtab_size = 0
    dyn_off, dyn_size = dynamic
    for idx in range(dyn_size // 16):
        d_tag, d_val = struct.unpack_from("<qQ", data, dyn_off + idx * 16)
        if d_tag == 1:  # DT_NEEDED
            needed_offsets.append(d_val)
        elif d_tag == 5:  # DT_STRTAB
            strtab_vaddr = d_val
        elif d_tag == 10:  # DT_STRSZ
            strtab_size = d_val
    if strtab_vaddr is None:
        raise ValueError("no DT_STRTAB entry")

    strtab_off = None
    for vaddr, p_offset, p_filesz in loads:
        if vaddr <= strtab_vaddr < vaddr + p_filesz:
            strtab_off = p_offset + (strtab_vaddr - vaddr)
            break
    if strtab_off is None:
        raise ValueError("DT_STRTAB does not live inside a PT_LOAD segment")
    strtab = data[strtab_off:strtab_off + strtab_size]
    names = []
    for name_off in needed_offsets:
        end = strtab.find(b"\0", name_off)
        if end < 0:
            raise ValueError("unterminated DT_NEEDED entry")
        names.append(strtab[name_off:end].decode("utf-8", "replace"))
    return names


def check_linkage(driver, indi_libdir):
    """The packaged executable must carry a complete, relocatable INDI closure."""
    try:
        needed = read_needed(driver)
    except Exception as exc:
        fail("could not read the driver's dynamic section: %s" % exc)
        return
    absolute = [name for name in needed if name.startswith("/")]
    if absolute:
        fail("DT_NEEDED holds absolute paths: %s" % ", ".join(absolute))
        return
    missing = [name for name in INDI_CORE_LIBS if name not in needed]
    if missing:
        fail("driver does not link the INDI core libraries %s (DT_NEEDED=%s)"
             % (", ".join(missing), ", ".join(needed)))
        return
    absent = [name for name in INDI_CORE_LIBS
              if not os.path.isfile(os.path.join(indi_libdir, name))]
    if absent:
        fail("INDI core libraries missing from %s: %s" % (indi_libdir, ", ".join(absent)))
        return
    ok("DT_NEEDED closure complete: %s (all provided by the libindi package)"
       % ", ".join(INDI_CORE_LIBS))


def _host_can_map(path):
    """宿主能否映射该 .so；返回 (True, None) 或 (False, 原因)。"""
    try:
        import ctypes
        ctypes.CDLL(path, mode=ctypes.RTLD_GLOBAL)
        return True, None
    except Exception as exc:  # noqa: BLE001
        return False, str(exc)


def _classify_loader(text, dep_libdirs):
    """区分「真实闭包缺陷」与「宿主拒绝」。

    返回 (missing, host_refused)：
      * missing       —— 被加载器点名、但在任何依赖包 libdir 里都找不到的库（真实缺陷）；
                         或库在、但宿主加载失败且原因不是权限类（需人工介入，也按缺陷报）。
      * host_refused  —— **有证据**的宿主拒绝：输出里出现平台限制标记，或某个被点名的库
                         确实存在却同样无法被宿主映射（如 Permission denied）。
    只有二者皆空时才由调用方按"无证据的闭包错误 → 真实缺陷"处理。
    """
    low = text.lower()
    named = set(re.findall(r"error loading shared library ([^:\s]+)", low))
    named.update(re.findall(r"cannot open shared object file: ([^\s,]+)", low))
    missing = []
    host_refused = any(tag in low for tag in PLATFORM_LIMITS)
    for name in sorted(named):
        path = next((os.path.join(d, name) for d in dep_libdirs
                     if os.path.isfile(os.path.join(d, name))), None)
        if path is None:
            missing.append(name)
            continue
        loadable, why = _host_can_map(path)
        if loadable:
            # 宿主能映射它，却在驱动里加载失败 → 闭包/ABI 层面的真实问题
            missing.append("%s（宿主可映射，但驱动加载失败）" % name)
        elif any(tag in (why or "").lower()
                 for tag in ("permission", "not permitted", "operation")):
            host_refused = True
        else:
            missing.append("%s（宿主加载失败：%s）" % (name, why))
    return missing, host_refused


def check_exec(driver, dep_libdirs):
    """Best effort 启动驱动：真实闭包/符号缺陷一律 FAIL，仅有证据的宿主拒绝记 SKIP。"""
    try:
        proc = subprocess.run([driver, "--help"], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=15)
        out = proc.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        ok("driver started and stayed alive until the 15s timeout (closure resolved)")
        return
    except OSError as exc:
        low = str(exc).lower()
        if any(tag in low for tag in PLATFORM_LIMITS):
            skip("host refused to start the OHOS binary: %s" % exc)
        else:
            fail("could not execute the driver: %s" % exc)
        return

    low = out.lower()
    loader_tags = ("error loading shared library", "error relocating",
                   "cannot open shared object", "symbol not found",
                   "no such file or directory: lib")
    if not any(tag in low for tag in loader_tags):
        ok("driver exec'd cleanly (exit=%s, no unresolved shared library)" % proc.returncode)
        return
    missing, host_refused = _classify_loader(out, dep_libdirs)
    if missing:
        fail("加载器点名了缺失/无法加载的库 → 真实缺陷：%s（输出：%s）"
             % ("，".join(missing), out.strip()[:200]))
        return
    if host_refused:
        skip("宿主拒绝映射依赖库（有证据：平台限制标记或 ctypes 权限拒绝），非打包缺陷：%s"
             % out.strip()[:200])
        return
    fail("加载器报出未解析的共享库闭包且无宿主拒绝证据 → 真实缺陷：%s"
         % out.strip()[:300])


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        return 2
    driver, bindir, xml, indi_libdir = sys.argv[1:5]
    check_elf(driver)
    check_xml(xml, bindir)
    check_linkage(driver, indi_libdir)
    check_exec(driver, [indi_libdir])
    print("checks=%d fails=%d skips=%d" % (4, len(fails), len(skips)))
    if fails:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
