#!/usr/bin/env python3
"""HarmonyOS-specific tests for libnfs-tools binaries (R44: readelf-free).

Standalone suite executed by test_package/conanfile.py.  For each packaged
binary it asserts (fail closed) with NO external-tool dependency (no
readelf/objdump/llvm-readelf/file): the ELF is parsed in pure Python with
the stdlib ``struct`` module only.

  * ELF64 little-endian + e_machine == EM_AARCH64 (183)
  * PT_INTERP is the OHOS musl loader ld-musl-aarch64.so.1
  * the OHOS .codesign section is present (OpenHarmony ELF signing)
  * no DT_RPATH / DT_RUNPATH leakage from the build tree
  * libnfs is statically linked: no dynamic libnfs.so NEEDED
  * the binary actually executes and prints its usage line

Each binary -> 7 assertions (28 total), reported per-tool.
Usage: python3 ohos_specific_test.py <bin-dir>
"""
import os
import struct
import subprocess
import sys

# ---- ELF64 (little-endian) constants -----------------------------------
ELF_MAGIC = b"\x7fELF"
EI_CLASS_64 = 2                 # e_ident[4]: 2 == ELFCLASS64
EM_AARCH64 = 183                # e_machine value for AArch64 (0xB7)
PT_INTERP = 3                   # program header type: interpreter path
PT_DYNAMIC = 2                  # program header type: .dynamic segment
DT_NULL = 0                     # end-of-array marker in .dynamic
DT_NEEDED = 1                     # .dynamic tag: needed library name
DT_STRTAB = 5                     # .dynamic tag: string table offset
DT_STRSZ = 10                     # .dynamic tag: string table size
DT_RPATH = 15
DT_RUNPATH = 29
SHT_STRTAB = 3                  # section type: string table

# ELF64 header (little-endian):
#   e_ident[16] e_type[2] e_machine[2] e_version[4] e_entry[8]
#   e_phoff[8] e_shoff[8] e_flags[4] e_ehsize[2] e_phentsize[2]
#   e_phnum[2] e_shentsize[2] e_shnum[2] e_shstrndx[2]
ELF_HDR = struct.Struct("<16sHHIQQQIHHHHHH")
# ELF64 program header:
#   p_type[4] p_flags[4] p_offset[8] p_vaddr[8] p_paddr[8]
#   p_filesz[8] p_memsz[8] p_align[8]
ELF_PHDR = struct.Struct("<IIQQQQQQ")
# ELF64 section header:
#   sh_name[4] sh_type[4] sh_flags[8] sh_addr[8] sh_offset[8]
#   sh_size[8] sh_link[4] sh_info[4] sh_addralign[8] sh_entsize[8]
ELF_SHDR = struct.Struct("<IIQQQQIIQQ")
# ELF64 dynamic entry: d_tag[8] d_val[8]
ELF_DYN = struct.Struct("<QQ")


def read_cstr(buf, off):
    """Read a NUL-terminated string from buf starting at off ('' if none)."""
    end = buf.find(b"\x00", off)
    if end < 0:
        end = len(buf)
    return buf[off:end].decode("utf-8", "replace")


class Elf64:
    """Minimal pure-Python ELF64 (little-endian) parser.

    Every accessor is bounds-checked and returns None / [] on any parse
    problem so callers can fail closed instead of crashing.
    """

    def __init__(self, path):
        with open(path, "rb") as fh:
            self.data = fh.read()
        hdr = ELF_HDR.unpack_from(self.data, 0)
        self.ident = hdr[0]
        self.e_machine = hdr[2]
        self.phoff = hdr[5]
        self.shoff = hdr[6]
        self.phentsize = hdr[9]
        self.phnum = hdr[10]
        self.shentsize = hdr[11]
        self.shnum = hdr[12]
        self.shstrndx = hdr[13]
        if self.ident[:4] != ELF_MAGIC:
            raise ValueError("not an ELF file (bad magic)")

    def _unpack(self, fmt, off):
        if off < 0 or off + fmt.size > len(self.data):
            return None
        return fmt.unpack_from(self.data, off)

    def program_headers(self):
        """Yield (p_type, p_offset, p_filesz) tuples, stopping at EOF."""
        for i in range(self.phnum):
            ph = self._unpack(ELF_PHDR,
                              self.phoff + i * self.phentsize)
            if ph is None:
                break
            yield ph[0], ph[2], ph[5]  # type, offset, filesz

    def find_program(self, ptype):
        for t, off, size in self.program_headers():
            if t == ptype:
                return off, size
        return None

    def interpreter(self):
        """Return the PT_INTERP path string, or None when absent/broken."""
        ph = self.find_program(PT_INTERP)
        if ph is None:
            return None
        off, _size = ph
        try:
            return read_cstr(self.data, off)
        except Exception:
            return None

    def rpath_entries(self):
        """Return [(kind, value)] for DT_RPATH / DT_RUNPATH, [] if none."""
        ph = self.find_program(PT_DYNAMIC)
        if ph is None:
            return []
        off, size = ph
        end = off + size
        found = []
        pos = off
        while pos + ELF_DYN.size <= end:
            dyn = self._unpack(ELF_DYN, pos)
            if dyn is None:
                break
            tag, val = dyn
            pos += ELF_DYN.size
            if tag == DT_NULL:
                break
            if tag in (DT_RPATH, DT_RUNPATH):
                kind = "RUNPATH" if tag == DT_RUNPATH else "RPATH"
                found.append((kind, read_cstr(self.data, val)))
        return found

    def needed_libraries(self):
        """Return sorted list of DT_NEEDED library names, [] if none."""
        ph = self.find_program(PT_DYNAMIC)
        if ph is None:
            return []
        off, size = ph
        end = off + size
        strtab = None
        strsz = 0
        needed_offs = []
        pos = off
        while pos + ELF_DYN.size <= end:
            dyn = self._unpack(ELF_DYN, pos)
            if dyn is None:
                break
            tag, val = dyn
            pos += ELF_DYN.size
            if tag == DT_NULL:
                break
            if tag == DT_NEEDED:
                needed_offs.append(val)
            elif tag == DT_STRTAB:
                strtab = val
            elif tag == DT_STRSZ:
                strsz = val
        if strtab is None or not needed_offs:
            return []
        names = []
        for n in needed_offs:
            if n < 0 or n >= strsz:
                continue
            names.append(read_cstr(self.data, strtab + n))
        return sorted(names)

    def section_headers(self):
        """Yield (sh_name, sh_type, sh_offset, sh_size), stopping at EOF."""
        for i in range(self.shnum):
            sh = self._unpack(ELF_SHDR,
                              self.shoff + i * self.shentsize)
            if sh is None:
                break
            yield sh[0], sh[1], sh[4], sh[5]  # name, type, offset, size

    def section_names(self):
        """Resolve section names via the e_shstrndx string table."""
        strtab = None
        for idx, (_name, _typ, off, size) in enumerate(self.section_headers()):
            if idx == self.shstrndx:
                strtab = self.data[off:off + size]
                break
        if strtab is None:
            return []
        return [read_cstr(strtab, sh_name)
                for sh_name, _t, _o, _s in self.section_headers()]

    def has_section(self, name):
        return name in self.section_names()


def check(bindir, tool):
    path = os.path.join(bindir, tool)
    fails = []
    if not os.path.isfile(path):
        return [f"{tool}: binary not packaged at {path}"]

    try:
        elf = Elf64(path)
    except Exception as exc:  # noqa: BLE001 - fail closed on any parse error
        return [f"{tool}: cannot parse ELF ({exc})"]

    # 1) ELF64 class + EM_AARCH64 (e_ident[4] == 2 -> 64-bit; 0xB7 = AArch64)
    if elf.ident[4] != EI_CLASS_64:
        fails.append(f"{tool}: not ELF64 class")
    if elf.e_machine != EM_AARCH64:
        fails.append(f"{tool}: e_machine != AArch64 (183), got {elf.e_machine}")

    # 2) OHOS musl loader as PT_INTERP
    interp = elf.interpreter()
    if interp is None or "ld-musl-aarch64.so.1" not in interp:
        fails.append(f"{tool}: interpreter != ld-musl-aarch64.so.1 "
                     f"(got {interp!r})")

    # 3) .codesign section (OpenHarmony-specific ELF signing)
    if not elf.has_section(".codesign"):
        fails.append(f"{tool}: missing .codesign section")

    # 4) no RPATH/RUNPATH leakage from the build tree
    rpaths = elf.rpath_entries()
    if rpaths:
        desc = ", ".join(f"{k}={v}" for k, v in rpaths)
        fails.append(f"{tool}: RPATH/RUNPATH present ({desc})")

    # 6) libnfs statically linked: no dynamic libnfs.so NEEDED (avoids
    #    runtime .so resolution / RPATH pitfalls on HarmonyOS)
    needed = elf.needed_libraries()
    if any("libnfs.so" in n for n in needed):
        fails.append(f"{tool}: unexpected dynamic libnfs.so NEEDED "
                     f"(expected static link, got {needed})")

    # 7) real execution: no-arg run prints a usage line
    bash = os.environ.get("CONFIG_SHELL", "/data/service/hnp/bin/bash")
    r = subprocess.run([bash, "-c", f'"{path}" >/dev/null 2>&1'])
    out = subprocess.run([bash, "-c", f'"{path}" 2>&1 | head -1'],
                         capture_output=True, text=True).stdout
    if "Usage" not in out and "usage" not in out and "URL" not in out:
        fails.append(f"{tool}: no usage output (rc={r.returncode})")
    return fails


def main():
    if len(sys.argv) < 2:
        print("usage: ohos_specific_test.py <bindir>")
        return 2
    bindir = sys.argv[1]
    tools = ["nfs-ls", "nfs-cat", "nfs-cp", "nfs-stat"]
    total = 0
    failures = []
    for tool in tools:
        tool_fails = check(bindir, tool)
        total += 7
        for f in tool_fails:
            failures.append(f)
        if not tool_fails:
            print(f"PASS {tool} (7/7)")
        else:
            print(f"FAIL {tool} ({len(tool_fails)}/7)")
    if failures:
        print("FAILURES:")
        for f in failures:
            print("  -", f)
        return 1
    print(f"ALL OHOS SPECIFIC TESTS PASSED ({total}/{total})")
    return 0


if __name__ == "__main__":
    sys.exit(main())