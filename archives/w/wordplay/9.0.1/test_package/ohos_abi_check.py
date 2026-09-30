#!/usr/bin/env python3
"""HarmonyOS artifact/ABI checks for wordplay 9.0.1 (pure Python, no tools).

The checks inspect the packaged executable instead of running it, so they
work on any build host: the Windows host cross-compiles the package but
cannot execute an aarch64-linux-ohos ELF, and it must still validate the
artifact rather than pass silently.  They also make the CI L1e destructive
reverse check meaningful when cross-building -- move bin/ away and this
layer fails.

Why these are HarmonyOS specific

Upstream wordplay is portable C plus ICU and needed no source patch, so
every real adaptation point of this port lives in the toolchain / ABI /
packaging layer:

  A1 elf64_aarch64       ELF64 little-endian with e_machine == EM_AARCH64:
                         proves the recipe injected the Conan compiler
                         instead of the makefile's default toolchain.
  A2 ohos_musl_interp    PT_INTERP == /lib/ld-musl-aarch64.so.1, the OHOS
                         musl loader; a glibc sysroot yields
                         /lib/ld-linux-aarch64.so.1, which will not load.
  A3 ohos_ident_note     .note.ohos.ident with owner "OHOS", emitted by the
                         OHOS clang/lld and by no generic Linux toolchain.
  A4 dt_needed_musl      DT_NEEDED contains only unversioned musl/OHOS
                         sonames (libc.so and, because ICU is C++, the OHOS
                         system runtime libc++_shared.so from
                         /system/lib64); no glibc-style versioned soname
                         (libc.so.6, libm.so.6) and no host library.
  A5 icu_statically_linked  icu4c/78 is a static-only OHOS package, so no
                         libicuio/libicui18n/libicuuc/libicudata may appear
                         in DT_NEEDED and no ICU u_* symbol may remain UND
                         in .dynsym: the ICU code (and its embedded data)
                         must be folded into the executable.
  A6_words_file_intact   The packaged res/words721.txt is byte-identical to
                         the upstream tarball file (sha256), i.e. the
                         runtime word list the functional suite exercises is
                         the upstream data, not a rebuilt or truncated copy.
  A7 no_host_rpath       No DT_RPATH/DT_RUNPATH: build-host library paths do
                         not exist on the device.
  A8 nx_pie_relro        ET_DYN + DF_1_PIE, PT_GNU_RELRO present,
                         non-executable PT_GNU_STACK, DT_BIND_NOW: the OHOS
                         HNP hardening baseline (CI L4 scans the same
                         attributes).
  A9 no_glibc_versioning No .gnu.version_r GLIBC_* requirement and no GNU
                         .note.ABI-tag: musl/OHOS objects carry neither, a
                         glibc-linked artifact carries both.

Deliberately NOT asserted: the presence/absence of `.codesign`.  Per
knowledge/operations/harmonyos-specifics.md (E077) the recipe strips any old
`.codesign` and `binary-sign-tool` re-adds it, so the section exists on the
signing-capable HarmonyOS worker and not on a cross-compiling dev box.  An
assertion in either direction would be host dependent, i.e. not reproducible.

Exit code 0 = every check passed, 1 = at least one failure.
"""
import argparse
import hashlib
import json
import struct
import sys

ELFCLASS64 = 2
ELFDATA2LSB = 1
EM_AARCH64 = 183
ET_DYN = 3

PT_INTERP = 3
PT_GNU_STACK = 0x6474E551
PT_GNU_RELRO = 0x6474E552
PF_X = 0x1

DT_NEEDED = 1
DT_RPATH = 15
DT_BIND_NOW = 24
DT_RUNPATH = 29
DT_FLAGS_1 = 0x6FFFFFFB
DF_1_NOW = 0x1
DF_1_PIE = 0x08000000

SHT_DYNAMIC = 6
SHT_NOTE = 7
SHT_DYNSYM = 11
SHT_GNU_VERNEED = 0x6FFFFFFE

OHOS_INTERP = "/lib/ld-musl-aarch64.so.1"
# glibc loaders / versioned sonames that must never appear in an OHOS artifact.
GLIBC_INTERPS = ("/lib/ld-linux-aarch64.so.1", "/lib/ld-linux.so.3")
# Unversioned musl/OHOS sonames the executable may legitimately need.
# libc++_shared.so is the OHOS system C++ runtime (/system/lib64): wordplay
# links the C++ ICU statically, so the C++ runtime stays the one dynamic
# dependency - the same shape as the HNP-shipped cmake/ninja binaries
# (knowledge: opencsg-1.8.2, E630).
ALLOWED_NEEDED = ("libc.so", "libm.so", "libdl.so", "libpthread.so",
                  "libc++_shared.so", "libclang_rt.builtins-aarch64.so")
HOST_LIB_MARKERS = ("libSystem", "libc++.so.1", "libobjc", "CoreFoundation")
# Static ICU libs that must be folded into the executable, never DT_NEEDED.
ICU_SONAMES = ("libicuio", "libicui18n", "libicuuc", "libicudata",
               "libicu", "libicudt")
# ICU API the binary imports; after static linking none may stay UND.
ICU_SYMBOLS = ("u_strlen", "u_uastrcpy", "u_printf", "u_finit",
               "unorm2_getNFDInstance")
# sha256 of words721.txt as shipped in wordplay_9.0.1.orig.tar.gz
# (24867 entries despite the historical "721" name).
UPSTREAM_WORDS_SHA256 = (
    "eb5441226e0474901b3970037b6e209d5846276dae280560d008522eb59a19fb"
)


class ElfError(Exception):
    pass


class Elf(object):
    """Minimal ELF64 reader: header, program headers, sections, dynamic, notes."""

    def __init__(self, path):
        with open(path, "rb") as fh:
            self.data = fh.read()
        self.sha256 = hashlib.sha256(self.data).hexdigest()
        data = self.data
        if data[:4] != b"\x7fELF":
            raise ElfError("not an ELF file (magic %r)" % (data[:4],))
        if data[4] != ELFCLASS64:
            raise ElfError("not ELF64 (EI_CLASS=%d)" % data[4])
        if data[5] != ELFDATA2LSB:
            raise ElfError("not little-endian (EI_DATA=%d)" % data[5])
        (self.e_type, self.e_machine) = struct.unpack_from("<HH", data, 16)
        (self.e_phoff,) = struct.unpack_from("<Q", data, 32)
        (self.e_shoff,) = struct.unpack_from("<Q", data, 40)
        (self.e_phentsize, self.e_phnum) = struct.unpack_from("<HH", data, 54)
        (self.e_shentsize, self.e_shnum, self.e_shstrndx) = struct.unpack_from(
            "<HHH", data, 58)
        self.programs = self._programs()
        self.sections = self._sections()

    def _programs(self):
        out = []
        for i in range(self.e_phnum):
            off = self.e_phoff + i * self.e_phentsize
            p_type, p_flags, p_offset, _va, _pa, filesz, _memsz, _align = \
                struct.unpack_from("<IIQQQQQQ", self.data, off)
            value = None
            if p_type == PT_INTERP:
                raw = self.data[p_offset:p_offset + filesz]
                value = raw.split(b"\x00")[0].decode("utf-8", "replace")
            out.append({"type": p_type, "flags": p_flags, "value": value})
        return out

    def _sections(self):
        if self.e_shoff == 0 or self.e_shnum == 0:
            return []
        raw = []
        for i in range(self.e_shnum):
            off = self.e_shoff + i * self.e_shentsize
            name, sh_type, _flags, _addr, sh_offset, sh_size, sh_link, _info, \
                _align, sh_entsize = struct.unpack_from(
                    "<IIQQQQIIQQ", self.data, off)
            raw.append({"name_off": name, "type": sh_type, "offset": sh_offset,
                        "size": sh_size, "link": sh_link, "entsize": sh_entsize})
        shstr = raw[self.e_shstrndx]
        blob = self.data[shstr["offset"]:shstr["offset"] + shstr["size"]]
        for sec in raw:
            end = blob.find(b"\x00", sec["name_off"])
            sec["name"] = blob[sec["name_off"]:end].decode("utf-8", "replace")
        return raw

    def section(self, name):
        for sec in self.sections:
            if sec["name"] == name:
                return sec
        return None

    def _blob(self, sec):
        return self.data[sec["offset"]:sec["offset"] + sec["size"]]

    def dynamic(self):
        """Return [(tag, value)] from .dynamic; string tags are resolved."""
        sec = self.section(".dynamic")
        if sec is not None:
            offset, size = sec["offset"], sec["size"]
        else:
            offset = size = 0
        dynstr = self.section(".dynstr")
        strtab = self._blob(dynstr) if dynstr is not None else b""
        entries = []
        for pos in range(offset, offset + size, 16):
            tag, value = struct.unpack_from("<qQ", self.data, pos)
            if tag == 0:
                break
            if strtab and tag in (DT_NEEDED, DT_RPATH, DT_RUNPATH):
                end = strtab.find(b"\x00", value)
                value = strtab[value:end].decode("utf-8", "replace")
            entries.append((tag, value))
        return entries

    def undefined_symbols(self):
        sec = None
        for cand in self.sections:
            if cand["type"] == SHT_DYNSYM:
                sec = cand
                break
        if sec is None or sec["entsize"] == 0:
            return set()
        strtab = b""
        if sec["link"] < len(self.sections):
            strtab = self._blob(self.sections[sec["link"]])
        names = set()
        for pos in range(sec["offset"], sec["offset"] + sec["size"],
                         sec["entsize"]):
            st_name, _info, _other, st_shndx = struct.unpack_from(
                "<IBBH", self.data, pos)
            if st_shndx != 0 or not strtab:
                continue
            end = strtab.find(b"\x00", st_name)
            names.add(strtab[st_name:end].decode("utf-8", "replace"))
        return names

    def notes(self, section_name):
        """Yield (owner, note_type, desc) for every note in a SHT_NOTE section."""
        sec = self.section(section_name)
        if sec is None:
            return
        blob = self._blob(sec)
        pos = 0
        while pos + 12 <= len(blob):
            namesz, descsz, note_type = struct.unpack_from("<III", blob, pos)
            pos += 12
            owner = blob[pos:pos + namesz].split(b"\x00")[0]
            pos += (namesz + 3) & ~3
            desc = blob[pos:pos + descsz]
            pos += (descsz + 3) & ~3
            yield (owner.decode("utf-8", "replace"), note_type, desc)

    def version_requirements(self):
        """Return the set of version names in .gnu.version_r (SHT_GNU_verneed).

        glibc-linked artifacts carry entries such as GLIBC_2.17 here; musl/OHOS
        artifacts have no version requirements at all, so an empty set (or a
        missing section) is the expected HarmonyOS shape.
        """
        names = set()
        for sec in self.sections:
            if sec["type"] != SHT_GNU_VERNEED:
                continue
            strtab = b""
            if sec["link"] < len(self.sections):
                strtab = self._blob(self.sections[sec["link"]])
            blob = self._blob(sec)
            pos = 0
            while pos + 16 <= len(blob):
                _version, cnt, _file, aux, nxt = struct.unpack_from(
                    "<HHIII", blob, pos)
                aux_pos = pos + aux
                for _i in range(cnt):
                    if aux_pos + 16 > len(blob):
                        break
                    _hash, _flags, _other, name_off, aux_next = \
                        struct.unpack_from("<IHHII", blob, aux_pos)
                    if strtab:
                        end = strtab.find(b"\x00", name_off)
                        names.add(
                            strtab[name_off:end].decode("utf-8", "replace"))
                    if aux_next == 0:
                        break
                    aux_pos += aux_next
                if nxt == 0:
                    break
                pos += nxt
        return names


class Check(object):
    def __init__(self, check_id, title):
        self.id = check_id
        self.title = title
        self.ok = False
        self.detail = ""


def run_checks(elf, words_path):
    checks = []

    c = Check("A1_elf64_aarch64", "ELF64 little-endian, e_machine == EM_AARCH64")
    c.ok = elf.e_machine == EM_AARCH64
    c.detail = "e_machine=%d (expected %d), e_type=%d" % (
        elf.e_machine, EM_AARCH64, elf.e_type)
    checks.append(c)

    c = Check("A2_ohos_musl_interp",
              "PT_INTERP is the OHOS musl loader, never a glibc one")
    interp = None
    for prog in elf.programs:
        if prog["type"] == PT_INTERP:
            interp = prog["value"]
    c.ok = interp == OHOS_INTERP and interp not in GLIBC_INTERPS
    c.detail = "PT_INTERP=%s (expected %s, glibc would be %s)" % (
        interp, OHOS_INTERP, GLIBC_INTERPS[0])
    checks.append(c)

    c = Check("A3_ohos_ident_note", ".note.ohos.ident carries owner OHOS")
    owners = [owner for owner, _t, _d in elf.notes(".note.ohos.ident")]
    c.ok = "OHOS" in owners
    c.detail = "note owners=%s" % (owners or "none")
    checks.append(c)

    dynamic = elf.dynamic()
    needed = [value for tag, value in dynamic if tag == DT_NEEDED]

    c = Check("A4_dt_needed_musl_libc",
              "unversioned musl libc.so, no glibc/host sonames")
    versioned = [lib for lib in needed if ".so." in lib]
    hostish = [lib for lib in needed
               if any(marker in lib for marker in HOST_LIB_MARKERS)]
    unexpected = [lib for lib in needed if lib not in ALLOWED_NEEDED]
    c.ok = ("libc.so" in needed) and not versioned and not hostish \
        and not unexpected
    c.detail = "DT_NEEDED=%s" % (needed,)
    if versioned:
        c.detail += "; glibc-style versioned sonames: %s" % versioned
    if hostish:
        c.detail += "; host libraries: %s" % hostish
    if unexpected:
        c.detail += "; unexpected: %s" % unexpected
    checks.append(c)

    c = Check("A5_icu_statically_linked",
              "no ICU soname in DT_NEEDED and no ICU symbol left UND")
    icu_needed = [lib for lib in needed
                  if any(lib.startswith(name) for name in ICU_SONAMES)]
    undef = elf.undefined_symbols()
    icu_und = sorted(sym for sym in ICU_SYMBOLS if sym in undef)
    c.ok = not icu_needed and not icu_und
    c.detail = "ICU libs in DT_NEEDED: %s; ICU symbols UND: %s" % (
        icu_needed or "none", icu_und or "none")
    checks.append(c)

    c = Check("A6_words_file_intact",
              "packaged res/words721.txt is the upstream file (sha256)")
    if words_path:
        try:
            with open(words_path, "rb") as fh:
                digest = hashlib.sha256(fh.read()).hexdigest()
            c.ok = digest == UPSTREAM_WORDS_SHA256
            c.detail = "sha256=%s... (expected %s...)" % (
                digest[:16], UPSTREAM_WORDS_SHA256[:16])
        except OSError as exc:
            c.detail = "cannot read %s: %s" % (words_path, exc)
    else:
        c.detail = "--words not provided"
    checks.append(c)

    c = Check("A7_no_host_rpath_runpath", "no DT_RPATH / DT_RUNPATH")
    rpaths = [value for tag, value in dynamic if tag in (DT_RPATH, DT_RUNPATH)]
    c.ok = not rpaths
    c.detail = "rpath/runpath=%s" % (rpaths or "none")
    checks.append(c)

    c = Check("A8_nx_pie_relro_bind_now",
              "PIE + PT_GNU_RELRO + non-exec stack + BIND_NOW")
    flags1 = 0
    bind_now = False
    for tag, value in dynamic:
        if tag == DT_FLAGS_1:
            flags1 = value
        if tag == DT_BIND_NOW:
            bind_now = True
    relro = any(prog["type"] == PT_GNU_RELRO for prog in elf.programs)
    stacks = [prog for prog in elf.programs if prog["type"] == PT_GNU_STACK]
    nx = bool(stacks) and not (stacks[0]["flags"] & PF_X)
    pie = elf.e_type == ET_DYN and bool(flags1 & DF_1_PIE)
    now = bind_now or bool(flags1 & DF_1_NOW)
    c.ok = pie and relro and nx and now
    c.detail = "PIE=%s GNU_RELRO=%s NX_stack=%s BIND_NOW=%s" % (pie, relro, nx, now)
    checks.append(c)

    c = Check("A9_no_glibc_symbol_versioning",
              "no GLIBC_* version requirement and no GNU .note.ABI-tag")
    version_needed = elf.version_requirements()
    glibc_versions = sorted(name for name in version_needed
                            if name.startswith("GLIBC"))
    abi_owners = [owner for owner, _t, _d in elf.notes(".note.ABI-tag")]
    c.ok = not glibc_versions and not abi_owners
    c.detail = "version requirements=%s; .note.ABI-tag owners=%s" % (
        sorted(version_needed) or "none", abi_owners or "none")
    if glibc_versions:
        c.detail += "; glibc symbol versions: %s" % glibc_versions
    checks.append(c)

    return checks


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="HarmonyOS artifact/ABI checks for the packaged wordplay binary")
    parser.add_argument("--binary", required=True,
                        help="path to the packaged bin/wordplay")
    parser.add_argument("--words", default=None,
                        help="path to the packaged res/words721.txt (A6)")
    args = parser.parse_args(argv)

    try:
        elf = Elf(args.binary)
    except (ElfError, OSError) as exc:
        print("[FAIL] A0_artifact_readable: %s" % exc)
        print("OHOS_ABI_CHECK=%s" % json.dumps(
            {"discovered": 1, "passed": 0, "failed": 1}))
        return 1

    checks = run_checks(elf, args.words)
    failed = 0
    for check in checks:
        print("[%s] %s: %s" % ("PASS" if check.ok else "FAIL", check.id,
                               check.detail))
        if not check.ok:
            print("        expected: %s" % check.title)
            failed += 1
    print("OHOS_ABI_CHECK=%s" % json.dumps(
        {"discovered": len(checks), "passed": len(checks) - failed,
         "failed": failed}))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
