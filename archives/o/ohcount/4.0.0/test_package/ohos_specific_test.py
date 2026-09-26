#!/usr/bin/env python3
"""HarmonyOS-specific and functional tests for the packaged ohcount CLI.

Executed by ``test_package/conanfile.py`` with the installed package bin
directory.  Only the Python stdlib is used: the CI worker has no readelf /
objdump / file, so the ELF headers are parsed with ``struct`` directly.

Assertions (10, fail-closed, each printed; any failure exits non-zero):

  packaging / HarmonyOS ELF identity
    1. bin/ohcount is installed in the package
    2. bin/ohcount parses as an ELF file
    3. ELF64, little-endian
    4. e_machine == EM_AARCH64 (183)
    5. PT_INTERP is the OHOS musl loader (/lib/ld-musl-aarch64.so.1)
    6. OpenHarmony .codesign section present
    7. no DT_RPATH / DT_RUNPATH build-tree leakage
    8. pcre/libmagic statically linked (no libpcre/libmagic DT_NEEDED)

  real execution of the packaged binary on fixtures with known contents
    9. C fixture:      c      1 file / 4 code / 5 comment / 1 blank / 10 total
   10. Python fixture: python 1 file / 4 code / 2 comment / 1 blank /  7 total

Usage: ohos_specific_test.py <bindir>
"""

import os
import struct
import subprocess
import sys
import tempfile

# ---- ELF64 (little-endian) constants -----------------------------------
ELF_MAGIC = b"\x7fELF"
ELFCLASS64 = 2                   # e_ident[4] == 2 -> 64-bit
ELFDATA2LSB = 1                  # e_ident[5] == 1 -> little-endian
EM_AARCH64 = 183                 # 0xB7
PT_INTERP = 3
PT_DYNAMIC = 2
DT_NULL = 0
DT_NEEDED = 1
DT_STRTAB = 5
DT_STRSZ = 10
DT_RPATH = 15
DT_RUNPATH = 29

# ELF64 header: e_ident[16] e_type[2] e_machine[2] e_version[4] e_entry[8]
#               e_phoff[8] e_shoff[8] e_flags[4] e_ehsize[2] e_phentsize[2]
#               e_phnum[2] e_shentsize[2] e_shnum[2] e_shstrndx[2]
ELF_HDR = struct.Struct("<16sHHIQQQIHHHHHH")
# program header: p_type[4] p_flags[4] p_offset[8] p_vaddr[8] p_paddr[8]
#                 p_filesz[8] p_memsz[8] p_align[8]
ELF_PHDR = struct.Struct("<IIQQQQQQ")
# section header: sh_name[4] sh_type[4] sh_flags[8] sh_addr[8] sh_offset[8]
#                 sh_size[8] sh_link[4] sh_info[4] sh_addralign[8] sh_entsize[8]
ELF_SHDR = struct.Struct("<IIQQQQIIQQ")
# dynamic entry: d_tag[8] d_val[8]
ELF_DYN = struct.Struct("<QQ")

# fixtures with hand-checked line counts (verified against the reference
# ohcount 4.0.0 binary built from the same sources)
FIXTURES = {
    "fixture.c": (
        "/* comment line 1 */\n"
        "#include <stdio.h>\n"
        "\n"
        "int main(void) {\n"
        "    // inline comment\n"
        "    return 0;\n"
        "}\n"
        "/* multi\n"
        "   line\n"
        "   comment */\n"
    ),
    "fixture.py": (
        "# module comment\n"
        "import sys\n"
        "\n"
        "def main():\n"
        "    # inline comment\n"
        '    print("hi")\n'
        "    return 0\n"
    ),
}
# language -> (files, code, comment, blank, total)
EXPECTED = {
    "fixture.c": ("c", 1, 4, 5, 1, 10),
    "fixture.py": ("python", 1, 4, 2, 1, 7),
}


def read_cstr(buf, off):
    if off < 0 or off >= len(buf):
        return ""
    end = buf.find(b"\x00", off)
    if end < 0:
        end = len(buf)
    return buf[off:end].decode("utf-8", "replace")


class Elf64:
    """Minimal bounds-checked pure-python ELF64 (little-endian) parser."""

    def __init__(self, path):
        with open(path, "rb") as fh:
            self.data = fh.read()
        hdr = ELF_HDR.unpack_from(self.data, 0)
        self.ident = hdr[0]
        if self.ident[:4] != ELF_MAGIC:
            raise ValueError("not an ELF file (bad magic)")
        self.e_machine = hdr[2]
        self.phoff = hdr[5]
        self.shoff = hdr[6]
        self.phentsize = hdr[9]
        self.phnum = hdr[10]
        self.shentsize = hdr[11]
        self.shnum = hdr[12]
        self.shstrndx = hdr[13]

    def _unpack(self, fmt, off):
        if off < 0 or off + fmt.size > len(self.data):
            return None
        return fmt.unpack_from(self.data, off)

    def program_headers(self):
        for i in range(self.phnum):
            ph = self._unpack(ELF_PHDR, self.phoff + i * self.phentsize)
            if ph is None:
                break
            yield ph[0], ph[2], ph[5]          # p_type, p_offset, p_filesz

    def find_program(self, ptype):
        for p_type, off, size in self.program_headers():
            if p_type == ptype:
                return off, size
        return None

    def interpreter(self):
        ph = self.find_program(PT_INTERP)
        if ph is None:
            return None
        return read_cstr(self.data, ph[0])

    def dynamic_tags(self):
        """Return {tag: value} of the .dynamic segment (first occurrence)."""
        ph = self.find_program(PT_DYNAMIC)
        if ph is None:
            return {}
        off, size = ph
        tags = {}
        pos, end = off, off + size
        while pos + ELF_DYN.size <= end:
            dyn = self._unpack(ELF_DYN, pos)
            if dyn is None:
                break
            tag, val = dyn
            pos += ELF_DYN.size
            if tag == DT_NULL:
                break
            tags.setdefault(tag, val)
        return tags

    def needed_libraries(self):
        tags = self.dynamic_tags()
        strtab, strsz = tags.get(DT_STRTAB), tags.get(DT_STRSZ, 0)
        if strtab is None:
            return []
        # DT_NEEDED offsets are relative to DT_STRTAB's virtual address, but
        # for these binaries strtab is a file offset inside .dynstr, so read
        # from the file directly when the string looks sane.
        names = []
        off, size = self.find_program(PT_DYNAMIC)
        pos, end = off, off + size
        while pos + ELF_DYN.size <= end:
            dyn = self._unpack(ELF_DYN, pos)
            if dyn is None:
                break
            tag, val = dyn
            pos += ELF_DYN.size
            if tag == DT_NULL:
                break
            if tag == DT_NEEDED:
                name = read_cstr(self.data, strtab + val)
                if name:
                    names.append(name)
        return sorted(names)

    def rpath_entries(self):
        tags = self.dynamic_tags()
        found = []
        if DT_RPATH in tags:
            found.append(("RPATH", read_cstr(self.data, tags[DT_RPATH])))
        if DT_RUNPATH in tags:
            found.append(("RUNPATH", read_cstr(self.data, tags[DT_RUNPATH])))
        return found

    def section_names(self):
        strtab = None
        for i in range(self.shnum):
            sh = self._unpack(ELF_SHDR, self.shoff + i * self.shentsize)
            if sh is None:
                break
            if i == self.shstrndx:
                strtab = self.data[sh[4]:sh[4] + sh[5]]
                break
        if strtab is None:
            return []
        names = []
        for i in range(self.shnum):
            sh = self._unpack(ELF_SHDR, self.shoff + i * self.shentsize)
            if sh is None:
                break
            names.append(read_cstr(strtab, sh[0]))
        return names

    def has_section(self, name):
        return name in self.section_names()


def parse_summary_row(out, language):
    """Return (files, code, comment, blank, total) for the language row."""
    for line in out.splitlines():
        parts = line.split()
        if len(parts) == 7 and parts[0] == language:
            try:
                return (int(parts[1]), int(parts[2]), int(parts[3]),
                        int(parts[5]), int(parts[6]))
            except ValueError:
                return None
    return None


def main():
    if len(sys.argv) < 2:
        print("usage: ohos_specific_test.py <bindir>")
        return 2
    bindir = sys.argv[1]
    binary = os.path.join(bindir, "ohcount")

    total = 0
    failed = []

    def check(ok, name, detail=""):
        nonlocal total
        total += 1
        if ok:
            print("PASS %02d: %s" % (total, name))
        else:
            print("FAIL %02d: %s%s" % (total, name,
                                       (" -- " + detail) if detail else ""))
            failed.append(name)

    check(os.path.isfile(binary), "bin/ohcount installed in the package",
          "missing: %s" % binary)

    elf = None
    parse_error = ""
    try:
        elf = Elf64(binary)
    except Exception as exc:                       # noqa: BLE001 fail closed
        parse_error = str(exc)
    check(elf is not None, "bin/ohcount parses as an ELF file", parse_error)

    check(elf is not None and elf.ident[4] == ELFCLASS64 and
          elf.ident[5] == ELFDATA2LSB,
          "ELF64 little-endian",
          "" if elf is None else "ident=%r" % (elf.ident,))

    check(elf is not None and elf.e_machine == EM_AARCH64,
          "e_machine == EM_AARCH64 (183)",
          "" if elf is None else "got %r" % (elf.e_machine,))

    interp = elf.interpreter() if elf is not None else None
    check(interp is not None and interp.endswith("ld-musl-aarch64.so.1"),
          "PT_INTERP == OHOS musl loader (ld-musl-aarch64.so.1)",
          "got %r" % (interp,))

    has_codesign = elf.has_section(".codesign") if elf is not None else False
    check(has_codesign, "OpenHarmony .codesign section present")

    rpaths = elf.rpath_entries() if elf is not None else []
    check(elf is not None and not rpaths,
          "no DT_RPATH / DT_RUNPATH leakage",
          ", ".join("%s=%s" % kv for kv in rpaths) if rpaths else "")

    needed = elf.needed_libraries() if elf is not None else ["no ELF"]
    leaked = [n for n in needed if "libpcre" in n or "libmagic" in n]
    check(elf is not None and not leaked,
          "pcre/libmagic statically linked (DT_NEEDED clean)",
          "DT_NEEDED=%r" % (needed,))

    bash = os.environ.get("CONFIG_SHELL") or "/data/service/hnp/bin/bash"
    tmpdir = tempfile.mkdtemp(prefix="ohcount-test-")
    for filename in sorted(EXPECTED):
        language, files, code, comment, blank, tlines = EXPECTED[filename]
        fixture = os.path.join(tmpdir, filename)
        with open(fixture, "w") as fh:
            fh.write(FIXTURES[filename])
        try:
            proc = subprocess.run(
                [bash, "-c", '"%s" "%s"' % (binary, fixture)],
                stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                text=True, timeout=120)
            out, rc = proc.stdout, proc.returncode
        except Exception as exc:                   # noqa: BLE001 fail closed
            out, rc = "", -1
            print("      runner error: %s" % exc)
        row = parse_summary_row(out, language) if rc == 0 else None
        check(row == (files, code, comment, blank, tlines),
              "functional: %s -> %s 1/%d/%d/%d/%d" %
              (filename, language, code, comment, blank, tlines),
              "rc=%r row=%r out=%r" % (rc, row, out[-400:]))

    import shutil
    shutil.rmtree(tmpdir, ignore_errors=True)

    print("OHOS SPECIFIC TESTS: %d/%d PASSED" % (total - len(failed), total))
    if failed:
        print("FAILED: %s" % "; ".join(failed))
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
