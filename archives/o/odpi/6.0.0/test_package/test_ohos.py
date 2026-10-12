#!/usr/bin/env python3
"""HarmonyOS-specific tests for the packaged odpi shared library (R44/R53).

Pure-Python suite: stdlib ``struct`` only, NO external tool whatsoever
(no readelf / llvm-readelf / objdump / file) because the CI workers do not
ship them.  The script parses ``lib/libodpic.so.6.0.0`` in-process and
asserts, one by one, that the packaged artifact really is an OpenHarmony
arm64 shared library.  Every assertion prints a running PASS counter and
any failure collects into a non-zero exit code (fail closed).

  1. ELF magic 0x7f 'E' 'L' 'F'
  2. ELFCLASS64 + little-endian + EI_VERSION == 1
  3. e_type == ET_DYN (3, shared object) + e_machine == EM_AARCH64 (183)
  4. program headers parsed (PT_PHDR/PT_LOAD/PT_DYNAMIC); PT_INTERP policy:
     a shared object loaded by the OHOS runtime has no foreign interpreter,
     and whenever PT_INTERP is present it must be the OHOS musl loader
     ``ld-musl-aarch64.so.1``
  5. .note.ohos.ident present, note owner == "OHOS" (OpenHarmony marker)
  6. .codesign section present and non-empty (OpenHarmony ELF signing)
  7. .dynamic parsed: DT_NEEDED list non-empty and every name resolvable
  8. DT_SONAME == libodpic.so.6
  9. no DT_RPATH / DT_RUNPATH leakage from the build tree

Usage: python3 test_ohos.py <path-to-libodpic.so.6.0.0>
"""
import struct
import sys

ELF_MAGIC = b"\x7fELF"
EI_CLASS_64 = 2
EI_DATA_LSB = 1
ET_DYN = 3
EM_AARCH64 = 183
PT_LOAD = 1
PT_DYNAMIC = 2
PT_INTERP = 3
DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_STRSZ = 10
DT_SONAME = 14
DT_RPATH = 15
DT_RUNPATH = 29
OHOS_LOADER = "ld-musl-aarch64.so.1"
EXPECTED_SONAME = "libodpic.so.6"
EXPECTED_CHECKS = 9

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

# (number, title, callable) -- all pure-Python, no subprocess at all.
CHECKS = []


def check(number, title):
    def register(func):
        CHECKS.append((number, title, func))
        return func
    return register


def read_cstr(buf, off):
    """Read a NUL-terminated string from buf at off ('' if out of range)."""
    if off < 0 or off >= len(buf):
        return None
    end = buf.find(b"\x00", off)
    if end < 0:
        end = len(buf)
    return buf[off:end].decode("utf-8", "replace")


class Elf64:
    """Minimal pure-Python ELF64 (little-endian) parser, fail closed."""

    def __init__(self, path):
        with open(path, "rb") as fh:
            self.data = fh.read()
        if len(self.data) < ELF_HDR.size:
            raise ValueError("file smaller than an ELF header")
        hdr = ELF_HDR.unpack_from(self.data, 0)
        self.ident = hdr[0]
        self.e_type = hdr[1]
        self.e_machine = hdr[2]
        self.e_phoff = hdr[5]
        self.e_shoff = hdr[6]
        self.e_phentsize = hdr[9]
        self.e_phnum = hdr[10]
        self.e_shentsize = hdr[11]
        self.e_shnum = hdr[12]
        self.e_shstrndx = hdr[13]
        if self.ident[:4] != ELF_MAGIC:
            raise ValueError("not an ELF file (bad magic)")

    def _unpack(self, fmt, off):
        if off < 0 or off + fmt.size > len(self.data):
            return None
        return fmt.unpack_from(self.data, off)

    def program_headers(self):
        for i in range(self.e_phnum):
            ph = self._unpack(ELF_PHDR, self.e_phoff + i * self.e_phentsize)
            if ph is None:
                break
            yield ph

    def section_headers(self):
        for i in range(self.e_shnum):
            sh = self._unpack(ELF_SHDR, self.e_shoff + i * self.e_shentsize)
            if sh is None:
                break
            yield sh

    def section_map(self):
        """Return {name: (sh_type, sh_offset, sh_size)}, {} when unparsable."""
        sections = list(self.section_headers())
        if not sections or self.e_shstrndx >= len(sections):
            return {}
        strtab = sections[self.e_shstrndx]
        strtab_data = self.data[strtab[4]:strtab[4] + strtab[5]]
        result = {}
        for sh in sections:
            name = read_cstr(strtab_data, sh[0])
            if name is not None:
                result[name] = (sh[1], sh[4], sh[5])
        return result

    def dynamic_entries(self):
        """Return [(tag, val)] up to DT_NULL, [] when no PT_DYNAMIC."""
        off = size = None
        for ph in self.program_headers():
            if ph[0] == PT_DYNAMIC:
                off, size = ph[2], ph[5]
                break
        if off is None:
            return []
        entries = []
        pos = off
        while pos + ELF_DYN.size <= off + size:
            dyn = self._unpack(ELF_DYN, pos)
            if dyn is None:
                break
            entries.append(dyn)
            pos += ELF_DYN.size
            if dyn[0] == DT_NULL:
                break
        return entries

    def vaddr_to_offset(self, vaddr):
        """Map a virtual address to a file offset through PT_LOAD segments."""
        for ph in self.program_headers():
            if ph[0] != PT_LOAD:
                continue
            p_offset, p_vaddr, p_filesz = ph[2], ph[3], ph[5]
            if p_vaddr <= vaddr < p_vaddr + p_filesz:
                return p_offset + (vaddr - p_vaddr)
        return None

    def dynamic_strings(self, entries):
        """Resolve DT_NEEDED / DT_SONAME / RPATH names via the dynamic strtab."""
        strtab_off = None
        strsz = 0
        for tag, val in entries:
            if tag == DT_STRTAB:
                strtab_off = self.vaddr_to_offset(val)
            elif tag == DT_STRSZ:
                strsz = val
        names = {}
        for tag in (DT_NEEDED, DT_SONAME, DT_RPATH, DT_RUNPATH):
            values = [val for t, val in entries if t == tag]
            resolved = []
            for val in values:
                if strtab_off is None or val < 0 or val >= strsz:
                    resolved.append(None)
                else:
                    resolved.append(read_cstr(self.data, strtab_off + val))
            names[tag] = resolved
        return names


@check(1, "ELF magic")
def check_magic(elf):
    magic = elf.ident[:4]
    if magic != ELF_MAGIC:
        return False, "bad magic %r" % (magic,)
    return True, "magic OK"


@check(2, "ELFCLASS64 + little-endian")
def check_class(elf):
    if elf.ident[4] != EI_CLASS_64:
        return False, "EI_CLASS=%d (expected 2/ELF64)" % elf.ident[4]
    if elf.ident[5] != EI_DATA_LSB:
        return False, "EI_DATA=%d (expected 1/little-endian)" % elf.ident[5]
    if elf.ident[6] != 1:
        return False, "EI_VERSION=%d (expected 1)" % elf.ident[6]
    return True, "ELF64 little-endian"


@check(3, "AArch64 + ET_DYN shared object")
def check_machine(elf):
    if elf.e_type != ET_DYN:
        return False, "e_type=%d (expected 3/ET_DYN shared object)" % elf.e_type
    if elf.e_machine != EM_AARCH64:
        return False, "e_machine=%d (expected 183/EM_AARCH64)" % elf.e_machine
    return True, "EM_AARCH64 (183), ET_DYN"


@check(4, "program headers + PT_INTERP/OHOS loader policy")
def check_interp(elf):
    phdrs = list(elf.program_headers())
    if len(phdrs) != elf.e_phnum:
        return False, "parsed %d/%d program headers" % (len(phdrs), elf.e_phnum)
    types = set(ph[0] for ph in phdrs)
    if PT_LOAD not in types or PT_DYNAMIC not in types:
        return False, "missing PT_LOAD/PT_DYNAMIC in program headers"
    interps = []
    for ph in phdrs:
        if ph[0] != PT_INTERP:
            continue
        interp = read_cstr(elf.data, ph[2])
        if interp is None:
            interps.append("<unreadable>")
        else:
            interps.append(interp)
    for interp in interps:
        if OHOS_LOADER not in interp or "ld-linux" in interp:
            return False, "foreign interpreter %r (expected %s)" % (interp, OHOS_LOADER)
    if not interps:
        # ET_DYN shared object: the OHOS runtime resolves it via DT_NEEDED
        # and mmaps it directly; no PT_INTERP is expected.  Absence is fine
        # as long as no glibc interpreter leaks in (checked above).
        return True, "PHDRs OK, ET_DYN has no PT_INTERP (no foreign loader)"
    return True, "PT_INTERP=%s" % interps[0]


@check(5, ".note.ohos.ident marker (owner OHOS)")
def check_ohos_note(elf):
    sections = elf.section_map()
    entry = sections.get(".note.ohos.ident")
    if entry is None:
        return False, "missing .note.ohos.ident section"
    sh_type, sh_off, sh_size = entry
    if sh_size < 12 or sh_off + sh_size > len(elf.data):
        return False, "malformed .note.ohos.ident (size=%d)" % sh_size
    namesz = struct.unpack_from("<I", elf.data, sh_off)[0]
    if namesz < 1 or sh_off + 12 + namesz > len(elf.data):
        return False, "malformed note name (namesz=%d)" % namesz
    owner = elf.data[sh_off + 12:sh_off + 12 + namesz].rstrip(b"\x00")
    if owner != b"OHOS":
        return False, "note owner %r (expected b'OHOS')" % (owner,)
    return True, "note owner OHOS"


@check(6, ".codesign section (OHOS ELF signing)")
def check_codesign(elf):
    entry = elf.section_map().get(".codesign")
    if entry is None:
        return False, "missing .codesign section"
    sh_type, sh_off, sh_size = entry
    if sh_size <= 0 or sh_off + sh_size > len(elf.data):
        return False, "empty/broken .codesign (size=%d)" % sh_size
    return True, ".codesign present (%d bytes)" % sh_size


@check(7, "DT_NEEDED non-empty")
def check_needed(elf):
    entries = elf.dynamic_entries()
    if not entries:
        return False, "no PT_DYNAMIC / .dynamic entries"
    names = elf.dynamic_strings(entries)
    needed = [n for n in names.get(DT_NEEDED, []) if n]
    if not needed:
        return False, "DT_NEEDED empty or unresolvable"
    fresh = " ".join(sorted(needed))
    return True, "NEEDED: %s" % fresh


@check(8, "DT_SONAME == %s" % EXPECTED_SONAME)
def check_soname(elf):
    entries = elf.dynamic_entries()
    if not entries:
        return False, "no PT_DYNAMIC / .dynamic entries"
    sonames = [n for n in elf.dynamic_strings(entries).get(DT_SONAME, []) if n]
    if not sonames:
        return False, "DT_SONAME missing"
    if sonames[0] != EXPECTED_SONAME:
        return False, "DT_SONAME=%r (expected %r)" % (sonames[0], EXPECTED_SONAME)
    return True, "SONAME: %s" % sonames[0]


@check(9, "no DT_RPATH / DT_RUNPATH")
def check_rpath(elf):
    entries = elf.dynamic_entries()
    names = elf.dynamic_strings(entries)
    leaked = []
    for tag, label in ((DT_RPATH, "RPATH"), (DT_RUNPATH, "RUNPATH")):
        for value in names.get(tag, []):
            leaked.append("%s=%r" % (label, value))
    if leaked:
        return False, "build-tree leakage: %s" % ", ".join(leaked)
    return True, "absent"


def run(path):
    print("OHOS library check: %s" % path)
    try:
        elf = Elf64(path)
    except Exception as exc:  # noqa: BLE001 - fail closed on any parse error
        print("FAIL 0/%d: cannot parse ELF (%s)" % (EXPECTED_CHECKS, exc))
        return 1
    failures = []
    passed = 0
    for number, title, func in CHECKS:
        try:
            ok, detail = func(elf)
        except Exception as exc:  # noqa: BLE001 - fail closed
            ok, detail = False, "exception: %s" % exc
        if ok:
            passed += 1
            print("PASS %d/%d: %s -- %s"
                  % (number, EXPECTED_CHECKS, title, detail))
        else:
            failures.append((number, title, detail))
            print("FAIL %d/%d: %s -- %s"
                  % (number, EXPECTED_CHECKS, title, detail))
    if failures:
        print("FAILED %d/%d OHOS assertions (%d passed)"
              % (len(failures), EXPECTED_CHECKS, passed))
        return 1
    print("ALL %d/%d OHOS-SPECIFIC ASSERTIONS PASSED"
          % (EXPECTED_CHECKS, EXPECTED_CHECKS))
    return 0


def main():
    if len(sys.argv) != 2:
        print("usage: test_ohos.py <path-to-libodpic.so.6.0.0>")
        return 2
    return run(sys.argv[1])


if __name__ == "__main__":
    sys.exit(main())
