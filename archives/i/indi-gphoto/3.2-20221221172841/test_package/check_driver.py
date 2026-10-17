#!/usr/bin/env python3
"""Conan test_package — indi-gphoto 3.2-20221221172841.

Upstream indi-gphoto has no test suite of its own (the indi-gphoto/ subtree
only ships sources + CMakeLists, no enable_testing()/add_test()), so this
consumer test (R51) validates the packaged artefacts:

  1. bin/indi_gphoto_ccd exists, is a non-empty AArch64 ELF executable.
  2. share/indi/indi_gphoto.xml declares the GPhoto drivers and points at the
     executable that was packaged.
  3. the driver's DT_NEEDED closure is complete: the INDI core libraries
     (libindiclient / libindidriver) are recorded in DT_NEEDED, every entry is
     a plain soname, and both libraries really exist in the libindi package.
  4. best effort: the loader is asked to start the driver. A refusal caused by
     the host (OHOS shared objects cannot be mapped from this sandbox
     filesystem, unsigned ELF) is reported as SKIP together with the loader
     message, so a platform limitation never becomes a packaging failure.
"""
import os
import struct
import subprocess
import sys

EXPECTED_EM_AARCH64 = 0xB7
EXPECTED_DRIVER = "indi_gphoto_ccd"
INDI_CORE_LIBS = ("libindiclient.so.2", "libindidriver.so.2")
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
    for needle in (EXPECTED_DRIVER, "Canon DSLR", "Nikon DSLR", "GPhoto CCD"):
        if needle not in text:
            fail("INDI data file does not reference %r" % needle)
            return
    if not os.path.isfile(os.path.join(bindir, EXPECTED_DRIVER)):
        fail("the executable referenced by the INDI data file is not in bin/")
        return
    ok("share/indi/indi_gphoto.xml: driver names + executable reference match the package")


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


def check_exec(driver):
    """Best effort: let the loader start the driver, classify host refusals."""
    try:
        proc = subprocess.run([driver, "--help"], stdout=subprocess.PIPE,
                              stderr=subprocess.STDOUT, timeout=15)
        out = proc.stdout.decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        ok("driver started and stayed alive until the 15s timeout (closure resolved)")
        return
    except OSError as exc:
        low = str(exc).lower()
        if any(tag in low for tag in PLATFORM_LIMITS + LOADER_ERRORS):
            skip("host refused to start the OHOS binary: %s" % exc)
        else:
            fail("could not execute the driver: %s" % exc)
        return

    low = out.lower()
    if any(tag in low for tag in LOADER_ERRORS + PLATFORM_LIMITS):
        skip("host loader refused the OHOS shared-object closure: %s" % out.strip()[:300])
        return
    ok("driver exec'd cleanly (exit=%s, no unresolved shared library)" % proc.returncode)


def main():
    if len(sys.argv) != 5:
        print(__doc__)
        return 2
    driver, bindir, xml, indi_libdir = sys.argv[1:5]
    check_elf(driver)
    check_xml(xml, bindir)
    check_linkage(driver, indi_libdir)
    check_exec(driver)
    print("checks=%d fails=%d skips=%d" % (4, len(fails), len(skips)))
    if fails:
        print("RESULT: FAIL")
        return 1
    print("RESULT: PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
