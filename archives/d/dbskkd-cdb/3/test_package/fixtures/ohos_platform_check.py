#!/usr/bin/env python3
"""HarmonyOS-specific platform checks for the packaged dbskkd-cdb.

usage: ohos_platform_check.py <packaged dbskkd-cdb> <dictionary .cdb> <user-writable dir>

These are the *platform* requirements of OpenHarmony/HarmonyOS PC that a plain
Linux build of the same source does not have to satisfy, checked against the
binary that is actually shipped:

  OH1 ohos_elf_aarch64_pie      ELF64 / AArch64 / ET_DYN — the OHOS PC target
                                triple and the PIE form the platform loader and
                                the security baseline expect.
  OH2 ohos_elf_codesign         A non-empty `.codesign` section: the OHOS
                                loader only executes ELF images carrying a valid
                                signature (E077). Its length field also means the
                                image must not be rewritten after linking, which
                                is why the recipe does not strip the binary.
  OH3 ohos_elf_hardening        Non-executable stack (PT_GNU_STACK without
                                PF_X), PT_GNU_RELRO and DF_BIND_NOW — the
                                hardening set the platform L4 gate requires.
  OH4 ohos_elf_relocatable      DT_NEEDED is exactly {libc.so} with no path
                                separator, and neither DT_RPATH nor DT_RUNPATH
                                points at a build/cache directory: the artifact
                                is relocatable and needs nothing on the device
                                besides libc (the cdb library is linked in
                                statically, like the upstream Makefile does).
  OH5 ohos_runs_minimal_env     Runs with a minimal environment (PATH only) and
                                a dictionary in a user-writable directory: on
                                OHOS the system data directories are read-only,
                                so the dictionary must come from a path the
                                caller controls at run time (patch 0001), and no
                                build-time environment may be required.

Everything is parsed in pure Python (no readelf/eu-readelf dependency) so the
checks behave identically on the device and on CI workers.
Results are printed as "CHECK|<name>|<OK|FAIL>|<detail>" lines, one per check,
and the exit status is 0 only when every check passed. test.sh parses those
lines so the whole suite keeps a single case counter.
"""
import os
import struct
import subprocess
import sys

PT_LOAD = 1
PT_DYNAMIC = 2
PT_GNU_STACK = 0x6474E551
PT_GNU_RELRO = 0x6474E552
PF_X = 0x1

DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_RPATH = 15
DT_RUNPATH = 29
DT_FLAGS = 30
DT_FLAGS_1 = 0x6FFFFFFB
DF_BIND_NOW = 0x8
DF_1_NOW = 0x1
DF_1_PIE = 0x08000000

ET_DYN = 3
EM_AARCH64 = 183

VERSION_ANSWER = "dbskkd-cdb-3.00 ".encode("utf-8")


class Elf:
    """Minimal ELF64/LE reader: program headers, sections and the dynamic table."""

    def __init__(self, path):
        with open(path, "rb") as handle:
            self.data = handle.read()
        if self.data[:4] != b"\x7fELF":
            raise ValueError("not an ELF file")
        if self.data[4] != 2 or self.data[5] != 1:
            raise ValueError("expected ELF64 little-endian")
        (self.e_type, self.e_machine) = struct.unpack_from("<HH", self.data, 16)
        self.e_phoff = struct.unpack_from("<Q", self.data, 32)[0]
        self.e_shoff = struct.unpack_from("<Q", self.data, 40)[0]
        self.e_phentsize, self.e_phnum = struct.unpack_from("<HH", self.data, 54)
        self.e_shentsize, self.e_shnum, self.e_shstrndx = struct.unpack_from("<HHH", self.data, 58)
        self.phdrs = []
        for i in range(self.e_phnum):
            off = self.e_phoff + i * self.e_phentsize
            p_type, p_flags, p_offset, p_vaddr, _p_paddr, p_filesz, _p_memsz, _p_align = \
                struct.unpack_from("<IIQQQQQQ", self.data, off)
            self.phdrs.append((p_type, p_flags, p_offset, p_vaddr, p_filesz))

    def sections(self):
        """Return {name: (addr, size)} for every section with a name."""
        out = {}
        strtab_hdr = self.e_shoff + self.e_shstrndx * self.e_shentsize
        str_off, str_size = struct.unpack_from("<QQ", self.data, strtab_hdr + 24)
        strtab = self.data[str_off:str_off + str_size]
        for i in range(self.e_shnum):
            off = self.e_shoff + i * self.e_shentsize
            name_off = struct.unpack_from("<I", self.data, off)[0]
            sh_addr, sh_size = struct.unpack_from("<QQ", self.data, off + 16)
            end = strtab.find(b"\0", name_off)
            name = strtab[name_off:end].decode("utf-8", "replace")
            if name:
                out[name] = (sh_addr, sh_size)
        return out

    def dynamic_entries(self):
        (seg,) = [p for p in self.phdrs if p[0] == PT_DYNAMIC]
        _p_type, _p_flags, p_offset, _p_vaddr, p_filesz = seg
        entries = []
        for off in range(p_offset, p_offset + p_filesz, 16):
            d_tag, d_val = struct.unpack_from("<qQ", self.data, off)
            if d_tag == DT_NULL:
                break
            entries.append((d_tag, d_val))
        return entries

    def vaddr_to_offset(self, vaddr):
        for p_type, _p_flags, p_offset, p_vaddr, p_filesz in self.phdrs:
            if p_type == PT_LOAD and p_vaddr <= vaddr < p_vaddr + p_filesz:
                return p_offset + (vaddr - p_vaddr)
        raise ValueError("virtual address not covered by a PT_LOAD segment: 0x%x" % vaddr)

    def cstring(self, offset):
        end = self.data.find(b"\0", offset)
        return self.data[offset:end].decode("utf-8", "replace")


def main(argv):
    if len(argv) != 4:
        raise SystemExit(__doc__)
    binary, dictionary, work_dir = argv[1], argv[2], argv[3]
    if not os.path.isfile(binary):
        raise SystemExit("[fail] ohos_platform_check: binary missing: %s" % binary)
    if not os.path.isfile(dictionary):
        raise SystemExit("[fail] ohos_platform_check: dictionary missing: %s" % dictionary)

    checks = []

    def check(name, condition, detail):
        checks.append(bool(condition))
        print("CHECK|%s|%s|%s" % (name, "OK" if condition else "FAIL", detail))

    try:
        elf = Elf(binary)
    except (ValueError, OSError) as exc:
        check("ohos_elf_aarch64_pie", False, "%s: %s" % (type(exc).__name__, exc))
        return 1

    # OH1: target triple and PIE form.
    check("ohos_elf_aarch64_pie",
          elf.e_type == ET_DYN and elf.e_machine == EM_AARCH64,
          "type=%d (ET_DYN=%d) machine=%d (AArch64=%d)"
          % (elf.e_type, ET_DYN, elf.e_machine, EM_AARCH64))

    # OH2: the OHOS loader requires a signed image.
    sections = elf.sections()
    codesign = sections.get(".codesign")
    check("ohos_elf_codesign",
          codesign is not None and codesign[1] > 0,
          ".codesign section %s" % ("size=%d" % codesign[1] if codesign else "MISSING"))

    # OH3: the hardening set the platform L4 gate checks.
    stack = [p for p in elf.phdrs if p[0] == PT_GNU_STACK]
    relro = [p for p in elf.phdrs if p[0] == PT_GNU_RELRO]
    dynamic = elf.dynamic_entries()
    dt_flags = [v for t, v in dynamic if t == DT_FLAGS]
    dt_flags1 = [v for t, v in dynamic if t == DT_FLAGS_1]
    nx = bool(stack) and not (stack[0][1] & PF_X)
    bind_now = any(v & DF_BIND_NOW for v in dt_flags) or any(v & DF_1_NOW for v in dt_flags1)
    pie_flag = any(v & DF_1_PIE for v in dt_flags1)
    check("ohos_elf_hardening",
          nx and bool(relro) and bind_now and pie_flag,
          "nx=%s relro=%s bind_now=%s df_1_pie=%s" % (nx, bool(relro), bind_now, pie_flag))

    # OH4: relocatable, libc-only runtime dependency set.
    needed = []
    strtab_addr = next((v for t, v in dynamic if t == DT_STRTAB), None)
    rpaths = [v for t, v in dynamic if t in (DT_RPATH, DT_RUNPATH)]
    if strtab_addr is not None:
        base = elf.vaddr_to_offset(strtab_addr)
        needed = [elf.cstring(base + v) for t, v in dynamic if t == DT_NEEDED]
    rpath_values = [elf.cstring(elf.vaddr_to_offset(a)) for a in rpaths] if rpaths else []
    tainted = [p for p in rpath_values
               if "/.conan2/" in p or "/build" in p or p.startswith("/storage/")]
    check("ohos_elf_relocatable",
          needed == ["libc.so"] and not rpath_values and not tainted,
          "DT_NEEDED=%s DT_RPATH/RUNPATH=%s" % (needed, rpath_values))

    # OH5: usable on a device without any build-time environment, with the
    # dictionary in a caller-controlled directory.
    target = os.path.join(work_dir, "ohos-minimal-env.cdb")
    with open(dictionary, "rb") as src, open(target, "wb") as dst:
        dst.write(src.read())
    try:
        proc = subprocess.run(
            [binary, target], input=b"2", stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, env={"PATH": "/bin:/usr/bin"},
        )
        ok = proc.returncode == 0 and proc.stdout == VERSION_ANSWER
        detail = "rc=%d stdout=%r" % (proc.returncode, proc.stdout)
    except OSError as exc:
        ok, detail = False, "%s: %s" % (type(exc).__name__, exc)
    check("ohos_runs_minimal_env", ok, detail)

    return 0 if all(checks) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
