#!/usr/bin/env python3
"""HarmonyOS-specific tests for the protobuf 21.12 package (R53, R44).

Standalone suite executed by ``test_package/conanfile.py`` on the HarmonyOS
PC.  It inspects AND really executes the two shipped artifacts:

  * ``bin/protoc``        - the packaged compiler (ELF64 aarch64 OHOS)
  * ``lib/libprotobuf.a`` - the packaged static library archive

No external tool is used (no readelf/objdump/llvm-readelf/file: the CI
worker has none of them): the ELF headers, program headers, dynamic
entries and section names are parsed in pure Python with ``struct`` only.

8 independent assertions, each printed with a running PASS counter, fail
closed (any parse error / execution error marks the assertion failed and
the process exits non-zero):

  1. libprotobuf.a is a valid ``ar`` archive carrying the core
     ``arena.cc.obj`` object member (>= 50 object members in total)
  2. every ELF member object of libprotobuf.a is ELF64 little-endian
     with e_machine == EM_AARCH64 (183)
  3. bin/protoc is ELF64 little-endian with e_machine == EM_AARCH64 (183)
  4. bin/protoc PT_INTERP is the OHOS musl loader
     ``/lib/ld-musl-aarch64.so.1``
  5. bin/protoc carries the OpenHarmony ``.codesign`` section
  6. bin/protoc has no DT_RPATH/DT_RUNPATH (no build-tree leakage)
  7. real execution: ``protoc --version`` prints ``libprotoc 3.21.12``
  8. real execution: ``protoc --cpp_out`` over a fixture ``.proto``
     really generates non-empty ``.pb.cc`` and ``.pb.h`` sources

Usage:
    python3 test_ohos.py [--tmp-dir DIR] <protoc> <libprotobuf.a>
    python3 test_ohos.py [--tmp-dir DIR] <package_folder>

Exit code 0 iff all 8 assertions pass.
"""

import os
import struct
import subprocess
import sys
import tempfile

EXPECTED_PROTOC_VERSION = "3.21.12"
ASSERTION_TOTAL = 8

# ─── pure-Python ELF64 (little-endian) constants ───────────────────────────
ELF_MAGIC = b"\x7fELF"
EI_CLASS_64 = 2                    # e_ident[4]: 2 == ELFCLASS64
EI_DATA_LSB = 1                    # e_ident[5]: 1 == ELFDATA2LSB
EM_AARCH64 = 183                   # e_machine value for AArch64 (0xB7)
PT_INTERP = 3                      # program header type: interpreter path
PT_DYNAMIC = 2                     # program header type: .dynamic segment
DT_NULL = 0                        # end-of-array marker in .dynamic
DT_RPATH = 15
DT_RUNPATH = 29

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


class Report:
    """Running pass/fail counter with per-assertion PASS lines."""

    def __init__(self, total):
        self.total = total
        self.done = 0
        self.failed = []

    def check(self, desc, ok, detail=""):
        self.done += 1
        tag = "PASS" if ok else "FAIL"
        line = f"{tag} {self.done}/{self.total} {desc}"
        if not ok:
            self.failed.append(desc)
            if detail:
                line += f" -- {detail}"
        print(line, flush=True)


def read_cstr(buf, off):
    """Read a NUL-terminated string from buf starting at off ('' if none)."""
    if off < 0 or off >= len(buf):
        return ""
    end = buf.find(b"\x00", off)
    if end < 0:
        end = len(buf)
    return buf[off:end].decode("utf-8", "replace")


class Elf64:
    """Minimal pure-Python ELF64 (little-endian) parser, bounds-checked."""

    def __init__(self, path):
        with open(path, "rb") as fh:
            self.data = fh.read()
        if self.data[:4] != ELF_MAGIC:
            raise ValueError("not an ELF file (bad magic)")
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

    def _unpack(self, fmt, off):
        if off < 0 or off + fmt.size > len(self.data):
            return None
        return fmt.unpack_from(self.data, off)

    def program_headers(self):
        for i in range(self.phnum):
            ph = self._unpack(ELF_PHDR, self.phoff + i * self.phentsize)
            if ph is None:
                break
            yield ph[0], ph[2], ph[5]  # p_type, p_offset, p_filesz

    def find_program(self, ptype):
        for t, off, size in self.program_headers():
            if t == ptype:
                return off, size
        return None

    def interpreter(self):
        ph = self.find_program(PT_INTERP)
        if ph is None:
            return None
        return read_cstr(self.data, ph[0]) or None

    def dynamic_entries(self):
        """Yield (d_tag, d_val) from PT_DYNAMIC, stopping at DT_NULL/EOF."""
        ph = self.find_program(PT_DYNAMIC)
        if ph is None:
            return
        off, size = ph
        end = min(off + size, len(self.data))
        pos = off
        while pos + ELF_DYN.size <= end:
            dyn = self._unpack(ELF_DYN, pos)
            if dyn is None:
                break
            tag, val = dyn
            pos += ELF_DYN.size
            if tag == DT_NULL:
                break
            yield tag, val

    def rpath_entries(self):
        """Return [(kind, value)] for DT_RPATH / DT_RUNPATH, [] if none."""
        found = []
        for tag, val in self.dynamic_entries():
            if tag in (DT_RPATH, DT_RUNPATH):
                kind = "RUNPATH" if tag == DT_RUNPATH else "RPATH"
                found.append((kind, read_cstr(self.data, val)))
        return found

    def section_headers(self):
        for i in range(self.shnum):
            sh = self._unpack(ELF_SHDR, self.shoff + i * self.shentsize)
            if sh is None:
                break
            yield sh[0], sh[1], sh[4], sh[5]  # name, type, offset, size

    def section_names(self):
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


def parse_archive(path):
    """Parse a GNU ar archive, return [(member_name, payload_bytes)]."""
    with open(path, "rb") as fh:
        data = fh.read()
    if data[:8] != b"!<arch>\n":
        raise ValueError("bad ar magic (not an archive)")
    members = []
    pos = 8
    while pos + 60 <= len(data):
        hdr = data[pos:pos + 60]
        if hdr[58:60] != b"`\n":
            break
        name = hdr[:16].decode("ascii", "replace").strip()
        size_field = hdr[48:58].decode("ascii", "replace").strip()
        if not size_field.isdigit():
            break
        size = int(size_field)
        payload = data[pos + 60:pos + 60 + size]
        members.append((name, payload))
        pos += 60 + size + (size % 2)
    if not members:
        raise ValueError("archive contains no members")
    return members


def elf_member_info(payload):
    """Return (class, data_encoding, e_machine) of an archive member ELF."""
    hdr = ELF_HDR.unpack_from(payload, 0)
    return hdr[0][4], hdr[0][5], hdr[2]


def pick_tmp_base(explicit):
    """First writable directory among explicit/TMPDIR/cwd/home (None if none)."""
    candidates = [
        explicit,
        os.environ.get("OHOS_TEST_TMPDIR"),
        os.environ.get("TMPDIR"),
        os.getcwd(),
        os.path.expanduser("~"),
    ]
    for candidate in candidates:
        if not candidate:
            continue
        try:
            os.makedirs(candidate, exist_ok=True)
            probe = os.path.join(candidate, ".ohos_test_write_probe")
            with open(probe, "w") as fh:
                fh.write("ok")
            os.remove(probe)
            return candidate
        except OSError:
            continue
    return None


def classify_paths(paths):
    """Resolve protoc and libprotobuf.a from files or a package folder."""
    protoc = archive = None
    for path in paths:
        if os.path.isdir(path):
            cand = os.path.join(path, "bin", "protoc")
            if protoc is None and os.path.isfile(cand):
                protoc = cand
            cand = os.path.join(path, "lib", "libprotobuf.a")
            if archive is None and os.path.isfile(cand):
                archive = cand
        elif path.endswith(".a"):
            archive = path
        else:
            protoc = path
    return protoc, archive


def run_protoc(binary, args, timeout=300):
    return subprocess.run(
        [binary] + list(args),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    tmp_dir = None
    paths = []
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--tmp-dir":
            i += 1
            if i >= len(argv):
                print("FAIL: --tmp-dir requires a value")
                return 1
            tmp_dir = argv[i]
        elif arg.startswith("--tmp-dir="):
            tmp_dir = arg.split("=", 1)[1]
        else:
            paths.append(arg)
        i += 1

    protoc, archive = classify_paths(paths)
    if not protoc or not os.path.isfile(protoc):
        print(f"FAIL: protoc binary not found (paths: {paths})")
        return 1
    if not archive or not os.path.isfile(archive):
        print(f"FAIL: libprotobuf.a not found (paths: {paths})")
        return 1

    print("OHOS-specific protobuf test (pure python, no readelf/objdump)")
    print(f"  protoc       : {protoc}")
    print(f"  libprotobuf.a: {archive}")

    rep = Report(ASSERTION_TOTAL)

    # ── 1 + 2: static archive and its member objects ───────────────────
    members = None
    try:
        members = parse_archive(archive)
    except (OSError, ValueError, struct.error) as exc:
        rep.check("libprotobuf.a is a valid ar archive with core objects",
                  False, f"cannot parse archive: {exc}")
        rep.check("all archive ELF members are ELF64/AArch64", False,
                  "archive could not be parsed")
    else:
        names = [name for name, _payload in members]
        elf_members = [(n, p) for n, p in members if p[:4] == ELF_MAGIC]
        core_ok = any("arena.cc.obj" in n for n in names)
        rep.check(
            "libprotobuf.a is a valid ar archive with core objects",
            core_ok and len(elf_members) >= 50,
            f"core member arena.cc.obj={core_ok}, "
            f"{len(elf_members)} ELF members of {len(members)} total",
        )
        bad = []
        for name, payload in elf_members:
            if len(payload) < ELF_HDR.size:
                bad.append(f"{name}: truncated member")
                continue
            try:
                cls, enc, machine = elf_member_info(payload)
            except struct.error as exc:
                bad.append(f"{name}: {exc}")
                continue
            if cls != EI_CLASS_64 or enc != EI_DATA_LSB or machine != EM_AARCH64:
                bad.append(
                    f"{name}: class={cls} data={enc} machine={machine}"
                )
        rep.check(
            "all archive ELF members are ELF64/AArch64",
            bool(elf_members) and not bad,
            "; ".join(bad[:4]) if bad else "no ELF members found",
        )

    # ── 3-6: protoc binary structure ───────────────────────────────────
    elf = None
    try:
        elf = Elf64(protoc)
    except (OSError, ValueError, struct.error) as exc:
        for desc in (
            "bin/protoc is ELF64 little-endian AArch64 (EM_AARCH64=183)",
            "bin/protoc PT_INTERP is /lib/ld-musl-aarch64.so.1",
            "bin/protoc carries the OpenHarmony .codesign section",
            "bin/protoc has no DT_RPATH/DT_RUNPATH",
        ):
            rep.check(desc, False, f"cannot parse ELF: {exc}")
    else:
        rep.check(
            "bin/protoc is ELF64 little-endian AArch64 (EM_AARCH64=183)",
            elf.ident[4] == EI_CLASS_64
            and elf.ident[5] == EI_DATA_LSB
            and elf.e_machine == EM_AARCH64,
            f"class={elf.ident[4]} data={elf.ident[5]} "
            f"machine={elf.e_machine}",
        )
        interp = elf.interpreter()
        rep.check(
            "bin/protoc PT_INTERP is /lib/ld-musl-aarch64.so.1",
            interp is not None and "ld-musl-aarch64.so.1" in interp,
            f"interpreter={interp!r}",
        )
        rep.check(
            "bin/protoc carries the OpenHarmony .codesign section",
            elf.has_section(".codesign"),
            "section .codesign not found",
        )
        rpaths = elf.rpath_entries()
        rep.check(
            "bin/protoc has no DT_RPATH/DT_RUNPATH",
            not rpaths,
            ", ".join(f"{k}={v}" for k, v in rpaths),
        )

    # ── 7: real execution, --version ───────────────────────────────────
    version_ok = False
    version_detail = ""
    try:
        proc = run_protoc(protoc, ["--version"], timeout=300)
        out = (proc.stdout or "") + (proc.stderr or "")
        version_ok = proc.returncode == 0 and EXPECTED_PROTOC_VERSION in out
        version_detail = (
            f"rc={proc.returncode} out={out.strip()[:120]!r}"
        )
    except (OSError, subprocess.SubprocessError) as exc:
        version_detail = f"execution failed: {exc}"
    rep.check(
        f"protoc --version really runs and reports {EXPECTED_PROTOC_VERSION}",
        version_ok,
        version_detail,
    )

    # ── 8: real execution, C++ code generation ─────────────────────────
    codegen_ok = False
    codegen_detail = ""
    base = pick_tmp_base(tmp_dir)
    if base is None:
        codegen_detail = "no writable temp directory found"
    else:
        workdir = tempfile.mkdtemp(prefix="protobuf-ohos-", dir=base)
        proto_path = os.path.join(workdir, "ohos_probe.proto")
        out_dir = os.path.join(workdir, "gen")
        os.makedirs(out_dir, exist_ok=True)
        with open(proto_path, "w", encoding="utf-8") as fh:
            fh.write(
                'syntax = "proto3";\n'
                "package ohos.probe;\n"
                "message OhosProbe {\n"
                "  string name = 1;\n"
                "  int32 id = 2;\n"
                "  repeated bytes payload = 3;\n"
                "}\n"
            )
        try:
            proc = run_protoc(
                protoc,
                ["-I" + workdir, "--cpp_out=" + out_dir, proto_path],
                timeout=600,
            )
            cc = os.path.join(out_dir, "ohos_probe.pb.cc")
            header = os.path.join(out_dir, "ohos_probe.pb.h")
            if proc.returncode != 0:
                codegen_detail = (
                    f"protoc rc={proc.returncode}: "
                    f"{(proc.stderr or proc.stdout or '').strip()[:160]!r}"
                )
            elif not (os.path.isfile(cc) and os.path.isfile(header)):
                codegen_detail = "generated .pb.cc/.pb.h missing"
            elif os.path.getsize(cc) == 0 or os.path.getsize(header) == 0:
                codegen_detail = "generated files are empty"
            else:
                with open(header, "r", encoding="utf-8", errors="replace") as fh:
                    content = fh.read()
                if "OhosProbe" not in content:
                    codegen_detail = "generated header lacks OhosProbe message"
                else:
                    codegen_ok = True
                    codegen_detail = (
                        f"{os.path.basename(cc)}={os.path.getsize(cc)}B, "
                        f"{os.path.basename(header)}={os.path.getsize(header)}B"
                    )
        except (OSError, subprocess.SubprocessError) as exc:
            codegen_detail = f"execution failed: {exc}"
    rep.check(
        "protoc --cpp_out really generates non-empty .pb.cc/.pb.h",
        codegen_ok,
        codegen_detail,
    )

    if rep.failed:
        print(
            f"OHOS SPECIFIC TESTS: {rep.total - len(rep.failed)}/{rep.total} "
            f"passed; FAILED: {', '.join(rep.failed)}"
        )
        return 1
    print(f"OHOS SPECIFIC TESTS: {rep.total}/{rep.total} PASSED")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as exc:  # noqa: BLE001 - fail closed on any error
        print(f"OHOS SPECIFIC TESTS: fatal error: {exc}")
        sys.exit(1)
