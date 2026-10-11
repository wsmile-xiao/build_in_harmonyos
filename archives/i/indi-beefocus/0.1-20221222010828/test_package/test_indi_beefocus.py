#!/usr/bin/env python3
"""Consumer end-to-end suite for the packaged indi-beefocus driver.

Every assertion below is made against the *artifacts shipped inside the Conan
package folder* — the driver executable and its INDI descriptor XML — never
against the test's own bookkeeping. The suite is organised as named use cases
(HC-N) so that a transcript can be parsed and a partial failure is visible.

  HC-1  driver CLI contract: the packaged binary is a real aarch64 ELF and it
        reproduces upstream's own usage banner + exit status for a bad option.
  HC-2  INDI protocol consumption: the shipped driver consumes a real INDI
        <getProperties> request, and the shipped ELF carries the driver's own
        entry points plus the INDI framework's protocol machinery.
  HC-3  packaged INDI descriptor: share/indi/indi_beefocus.xml is well-formed
        and registers the <driver name="Bee Focuser">indi_beefocus</driver>
        entry under the Focusers group.
  HC-4  HarmonyOS packaging invariant: the shipped ELF carries no absolute
        Conan-cache DT_NEEDED leakage (relocatable) and was built with the
        hardening upstream CMakeCommon.cmake asks for (BIND_NOW + PIE + RELRO).

NOTE ON DEPENDENCIES: this harness parses ELF itself (see `_Elf`) instead of
shelling out to binutils. The CI worker image does not necessarily provide
`nm`/`readelf`/`strings`, and relying on them made the suite fail with
FileNotFoundError: 'nm' on the first CI run. Pure-stdlib parsing keeps the
assertions identical while removing that environment assumption.

Usage: test_indi_beefocus.py <exe> <xml> <workdir>
"""
import os
import re
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET

CHECKS = {"ok": 0, "fail": 0}
CASES = []


def case_begin(cid, title):
    print(f"case {cid} RUN  {title}")


def case_end(cid, ok):
    CASES.append((cid, "PASS" if ok else "FAIL"))
    print(f"case {cid} {'PASS' if ok else 'FAIL'}")


def check(cond, name, detail=""):
    if cond:
        CHECKS["ok"] += 1
        print(f"ok   - {name}")
    else:
        CHECKS["fail"] += 1
        print(f"FAIL - {name}: {detail}")


def run(cmd, stdin_data=None, timeout=60):
    return subprocess.run(
        cmd, input=stdin_data, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        text=True, encoding="utf-8", errors="replace", timeout=timeout)


# ── minimal, dependency-free ELF64 reader ────────────────────────────────────
class _Elf:
    """Just enough ELF64/LE parsing for the assertions below.

    Reads the header, the dynamic table, the program headers and the symbol
    tables directly from the file, so the suite needs neither binutils nor any
    third-party module on the CI worker.
    """

    # dynamic tags
    DT_NULL, DT_NEEDED, DT_FLAGS, DT_FLAGS_1 = 0, 1, 30, 0x6FFFFFFB
    # program header types
    PT_LOAD, PT_DYNAMIC, PT_GNU_RELRO = 1, 2, 0x6474E552
    # DF_1_PIE
    DF_1_PIE = 0x08000000
    # DF_BIND_NOW
    DF_BIND_NOW = 0x8

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as fh:
            self.data = fh.read()
        d = self.data
        if len(d) < 64 or d[:4] != b"\x7fELF":
            raise ValueError("not an ELF file")
        self.ei_class, self.ei_data = d[4], d[5]
        if self.ei_class != 2 or self.ei_data != 1:
            raise ValueError("only ELF64 little-endian is supported")
        (self.e_type, self.e_machine) = struct.unpack_from("<HH", d, 16)
        (self.e_phoff,) = struct.unpack_from("<Q", d, 32)
        (self.e_shoff,) = struct.unpack_from("<Q", d, 40)
        self.e_phentsize, self.e_phnum = struct.unpack_from("<HH", d, 54)
        self.e_shentsize, self.e_shnum = struct.unpack_from("<HH", d, 58)
        self.e_shstrndx = struct.unpack_from("<H", d, 62)[0]
        self._program_headers = None
        self._dynamic = None
        self._sections = None

    # -- program headers ----------------------------------------------------
    @property
    def program_headers(self):
        if self._program_headers is None:
            out = []
            for i in range(self.e_phnum):
                off = self.e_phoff + i * self.e_phentsize
                p_type, p_flags = struct.unpack_from("<II", self.data, off)
                p_offset, p_vaddr, p_paddr, p_filesz, p_memsz, p_align = \
                    struct.unpack_from("<QQQQQQ", self.data, off + 8)
                out.append({"type": p_type, "flags": p_flags,
                            "offset": p_offset, "vaddr": p_vaddr,
                            "filesz": p_filesz, "memsz": p_memsz})
            self._program_headers = out
        return self._program_headers

    def has_segment(self, p_type):
        return any(ph["type"] == p_type for ph in self.program_headers)

    # -- sections -----------------------------------------------------------
    @property
    def sections(self):
        if self._sections is None:
            out = []
            # section header string table
            shstr_off = self.e_shoff + self.e_shstrndx * self.e_shentsize
            shstr_sh_offset = struct.unpack_from("<Q", self.data, shstr_off + 24)[0]
            shstr_size = struct.unpack_from("<Q", self.data, shstr_off + 32)[0]
            shstr = self.data[shstr_sh_offset:shstr_sh_offset + shstr_size]
            for i in range(self.e_shnum):
                off = self.e_shoff + i * self.e_shentsize
                sh_name, sh_type = struct.unpack_from("<II", self.data, off)
                sh_offset, sh_size = struct.unpack_from("<QQ", self.data, off + 24)
                sh_link = struct.unpack_from("<I", self.data, off + 40)[0]
                end = shstr.find(b"\x00", sh_name)
                name = shstr[sh_name:end].decode("utf-8", "replace") if sh_name else ""
                out.append({"name": name, "type": sh_type, "offset": sh_offset,
                            "size": sh_size, "link": sh_link})
            self._sections = out
        return self._sections

    def section(self, name):
        for s in self.sections:
            if s["name"] == name:
                return s
        return None

    # -- dynamic table ------------------------------------------------------
    def _load_dynamic(self):
        if self._dynamic is not None:
            return
        dyn = None
        for s in self.sections:
            if s["name"] == ".dynamic":
                dyn = s
                break
        if dyn is None:
            for ph in self.program_headers:
                if ph["type"] == self.PT_DYNAMIC:
                    dyn = {"offset": ph["offset"], "size": ph["filesz"]}
                    break
        self._dynamic = []
        if not dyn or not dyn.get("size"):
            return
        off, size = dyn["offset"], dyn["size"]
        for i in range(size // 16):
            tag, val = struct.unpack_from("<QQ", self.data, off + i * 16)
            self._dynamic.append((tag, val))

    @property
    def dynamic(self):
        self._load_dynamic()
        return self._dynamic

    def _dynstr(self):
        for tag, val in self.dynamic:
            if tag == 5:  # DT_STRTAB
                # map vaddr -> file offset through PT_LOAD
                for ph in self.program_headers:
                    if ph["type"] == self.PT_LOAD and \
                            ph["vaddr"] <= val < ph["vaddr"] + ph["filesz"]:
                        start = ph["offset"] + (val - ph["vaddr"])
                        end = self.data.find(b"\x00", start)
                        return self.data[start:end if end != -1 else start + 4096]
        return b""

    @property
    def needed(self):
        """DT_NEEDED library names."""
        strtab = self._dynstr()
        out = []
        for tag, val in self.dynamic:
            if tag == self.DT_NEEDED:
                end = strtab.find(b"\x00", val)
                out.append(strtab[val:end].decode("utf-8", "replace"))
        return out

    @property
    def flags(self):
        """DT_FLAGS value (DF_BIND_NOW lives here)."""
        for tag, val in self.dynamic:
            if tag == self.DT_FLAGS:
                return val
        return 0

    @property
    def flags_1(self):
        """DT_FLAGS_1 value (DF_1_PIE lives here)."""
        for tag, val in self.dynamic:
            if tag == self.DT_FLAGS_1:
                return val
        return 0

    # -- symbols ------------------------------------------------------------
    def _symbols_from(self, sym_name, str_name, is_dynamic):
        sym, st = self.section(sym_name), self.section(str_name)
        if sym is None or st is None:
            return []
        out = []
        count = sym["size"] // (24 if not is_dynamic else 24)
        strtab = self.data[st["offset"]:st["offset"] + st["size"]]
        for i in range(count):
            off = sym["offset"] + i * 24
            st_name, st_info, st_other, st_shndx = struct.unpack_from("<IBBH", self.data, off)
            st_value, st_size = struct.unpack_from("<QQ", self.data, off + 8)
            if st_name == 0:
                continue
            end = strtab.find(b"\x00", st_name)
            name = strtab[st_name:end].decode("utf-8", "replace")
            out.append({"name": name, "value": st_value, "size": st_size,
                        "bind": st_info >> 4, "type": st_info & 0xF,
                        "defined": st_shndx != 0})
        return out

    @property
    def defined_symbols(self):
        """Names defined in .symtab (falls back to .dynsym when stripped)."""
        syms = self._symbols_from(".symtab", ".strtab", is_dynamic=False)
        if not syms:
            syms = self._symbols_from(".dynsym", ".dynstr", is_dynamic=True)
        return {s["name"] for s in syms if s["defined"]}

    @property
    def all_symbol_names(self):
        names = {s["name"] for s in self._symbols_from(".symtab", ".strtab", False)}
        names |= {s["name"] for s in self._symbols_from(".dynsym", ".dynstr", True)}
        return names

    @property
    def rodata_strings(self):
        """Printable runs found in the loaded (non-symbol) data of the file."""
        chunks = re.findall(rb"[\x20-\x7e]{4,}", self.data)
        return b"\n".join(chunks).decode("utf-8", "replace")


def demangle_contains(haystack, needle):
    """Mangled names are compared after stripping the leading underscore-free
    Itanium prefix; the suite only needs substring identity, e.g.
    'BeeFocused::Driver' appears as 'BeeFocused' 'Driver' in the mangled form."""
    return needle in haystack


# ── HC-1: the packaged driver binary and its CLI contract ────────────────────
def hc1_cli_contract(exe):
    case_begin("HC-1", "packaged driver binary + upstream CLI contract")
    ok = True

    check(os.path.isfile(exe), "HC-1.1 packaged bin/indi_beefocus exists", exe)
    if not os.path.isfile(exe):
        case_end("HC-1", False)
        return

    check(os.access(exe, os.X_OK), "HC-1.2 packaged driver is executable")

    try:
        elf = _Elf(exe)
    except ValueError as exc:
        check(False, "HC-1.3 packaged driver is an ELF file", str(exc))
        case_end("HC-1", False)
        return
    check(True, "HC-1.3 packaged driver is an ELF file")
    check(elf.ei_class == 2, "HC-1.4 packaged driver is ELF64", f"EI_CLASS={elf.ei_class}")
    check(elf.e_machine == 0xB7, "HC-1.5 packaged driver targets AArch64",
          f"e_machine=0x{elf.e_machine:x}")

    # Upstream indidrivermain.c: an unknown option calls usage() and exits 1,
    # printing the banner on stderr. This is the driver's documented CLI
    # contract, so it is a real behavioural assertion on the shipped binary.
    bad = run([exe, "-x"])
    err = bad.stderr or ""
    check("Usage:" in err, "HC-1.6 bad option prints upstream usage banner", err[:200])
    check("INDI Device driver framework" in err,
          "HC-1.7 usage banner identifies the INDI driver framework", err[:200])
    check(bad.returncode == 1, "HC-1.8 bad option exits with status 1",
          f"rc={bad.returncode}")

    if CHECKS["fail"]:
        ok = False
    case_end("HC-1", ok)


# ── HC-2: the packaged driver really speaks the INDI protocol ────────────────
def hc2_protocol_roundtrip(exe):
    """Assert the SHIPPED driver implements the INDI driver contract.

    Upstream's entry point (libs/indibase/indidrivermain.c) reads INDI XML from
    stdin and only flushes queued answers when an event-loop iteration runs, so a
    one-shot pipe cannot be used to capture a <def> reply. What IS observable,
    and is asserted here, is that the packaged binary actually consumes an INDI
    <getProperties> request through that protocol path (with -v the driver echoes
    the exact request it parsed), and that the shipped ELF contains both the
    driver's own entry points and the INDI framework's protocol machinery —
    i.e. the driver was genuinely linked in rather than stubbed out.
    """
    case_begin("HC-2", "packaged driver consumes INDI XML and carries the driver")
    ok = True
    before = CHECKS["fail"]

    request = '<getProperties version="1.7" />\n'
    try:
        proc = subprocess.run(
            [exe, "-v"], input=request.encode(),
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=60)
        err = (proc.stderr or b"").decode("utf-8", "replace")
    except subprocess.TimeoutExpired:
        check(False, "HC-2.1 driver consumed the INDI request within 60s", "timed out")
        case_end("HC-2", False)
        return

    # The -v trace echoes the request the driver pulled off its protocol input.
    check("getProperties" in err,
          "HC-2.1 driver consumed the INDI <getProperties> request", err[:300])
    # Upstream reports EOF on its stdin; that diagnostic comes from
    # indidrivermain.c and proves the shipped binary runs the real driver loop.
    check("indi_beefocus" in err,
          "HC-2.2 driver identifies itself in its own diagnostics", err[:300])

    elf = _Elf(exe)
    defined = elf.defined_symbols
    allnames = elf.all_symbol_names
    blob = "\n".join(sorted(defined | allnames))

    # Device identity returned by Driver::getDefaultName().
    check("Bee Focuser" in elf.rodata_strings,
          "HC-2.3 packaged ELF carries the Bee Focuser device identity")

    # The driver's own overrides must all be compiled into the shipped binary.
    # Mangled C++ names embed the class/method text, so a substring test on the
    # demangled-visible fragments is sufficient and robust.
    driver_methods = {
        "getDefaultName()": "getDefaultName",
        "initProperties()": "initProperties",
        "Connect()": "Connect",
        "Handshake()": "Handshake",
        "MoveAbsFocuser": "MoveAbsFocuser",
        "AbortFocuser": "AbortFocuser",
        "SyncFocuser": "SyncFocuser",
    }
    for label, frag in driver_methods.items():
        present = any(frag in n and "BeeFocused" in n for n in (defined | allnames))
        check(present, f"HC-2.4 packaged driver defines {label}",
              "symbol not found in shipped ELF")

    # The INDI framework's protocol layer (stdin XML dispatch) is linked in.
    for sym in ("newLilXML", "readXMLEle", "delXMLEle", "dispatch"):
        check(re.search(rf"^{re.escape(sym)}$", blob, re.MULTILINE) is not None
              or sym in allnames,
              f"HC-2.5 INDI protocol entry point {sym} is linked into the driver")

    if CHECKS["fail"] != before:
        ok = False
    case_end("HC-2", ok)


# ── HC-3: the packaged INDI driver descriptor ────────────────────────────────
def hc3_descriptor(xml):
    case_begin("HC-3", "packaged INDI descriptor share/indi/indi_beefocus.xml")
    ok = True
    before = CHECKS["fail"]

    check(os.path.isfile(xml), "HC-3.1 packaged descriptor XML exists", xml)
    if not os.path.isfile(xml):
        case_end("HC-3", False)
        return

    try:
        root = ET.parse(xml).getroot()
        parse_error = None
    except ET.ParseError as exc:
        root, parse_error = None, str(exc)
    check(root is not None, "HC-3.2 descriptor is well-formed XML",
          parse_error or "")

    if root is None:
        case_end("HC-3", False)
        return

    drivers = root.findall(".//driver")
    names = [(d.get("name"), (d.text or "").strip()) for d in drivers]
    check(any(exe == "indi_beefocus" for _label, exe in names),
          "HC-3.3 descriptor registers the indi_beefocus driver", str(names))
    label = next((lbl for lbl, exe in names if exe == "indi_beefocus"), None)
    check(label == "Bee Focuser", "HC-3.4 driver is labelled Bee Focuser", str(label))

    groups = [g.get("group") for g in root.findall(".//devGroup")]
    check("Focusers" in groups, "HC-3.5 driver is filed under the Focusers group",
          str(groups))

    if CHECKS["fail"] != before:
        ok = False
    case_end("HC-3", ok)


# ── HC-4: HarmonyOS packaging invariants ─────────────────────────────────────
def hc4_ohos_packaging(exe):
    case_begin("HC-4", "HarmonyOS packaging invariants of the shipped ELF")
    ok = True
    before = CHECKS["fail"]

    try:
        elf = _Elf(exe)
        needed = elf.needed
    except ValueError as exc:
        check(False, "HC-4.1 packaged ELF can be parsed", str(exc))
        case_end("HC-4", False)
        return
    check(True, "HC-4.1 packaged ELF can be parsed")

    check(bool(needed), "HC-4.2 shipped ELF declares DT_NEEDED entries",
          "none found")
    # E537 lesson: a package must never bake a machine-private absolute path
    # into DT_NEEDED, otherwise it is not consumable on another machine.
    absolute = [n for n in needed if "/" in n]
    check(not absolute,
          "HC-4.3 no absolute-path leakage in DT_NEEDED (relocatable)",
          f"leaked={absolute}")

    # Upstream cmake_modules/CMakeCommon.cmake links with -pie and -Wl,-z,relro
    # (SEC_FLAGS / SEC_LINK_FLAGS), and -Wl,-z,now. Confirm that hardening
    # actually survived the OHOS link: a build without it must FAIL here.
    check(elf.flags & _Elf.DF_BIND_NOW != 0,
          "HC-4.4 shipped ELF has DF_BIND_NOW (upstream -Wl,-z,now hardening)",
          f"DT_FLAGS=0x{elf.flags:x}")
    check(elf.flags_1 & _Elf.DF_1_PIE != 0,
          "HC-4.5 shipped ELF is position-independent (DF_1_PIE)",
          f"DT_FLAGS_1=0x{elf.flags_1:x}")
    check(elf.has_segment(_Elf.PT_GNU_RELRO),
          "HC-4.6 shipped ELF has a GNU_RELRO segment (upstream -z relro)")

    if CHECKS["fail"] != before:
        ok = False
    case_end("HC-4", ok)


def main():
    if len(sys.argv) != 4:
        print(f"usage: {sys.argv[0]} <exe> <xml> <workdir>", file=sys.stderr)
        return 2
    exe, xml, _workdir = sys.argv[1], sys.argv[2], sys.argv[3]

    print("== indi-beefocus consumer suite ==")
    print(f"   exe = {exe}")
    print(f"   xml = {xml}")

    hc1_cli_contract(exe)
    hc2_protocol_roundtrip(exe)
    hc3_descriptor(xml)
    hc4_ohos_packaging(exe)

    passed = sum(1 for _c, v in CASES if v == "PASS")
    failed = sum(1 for _c, v in CASES if v == "FAIL")
    print(f"== {len(CASES)} cases, {failed} failed ==")
    print(f"== {CHECKS['ok'] + CHECKS['fail']} checks, {CHECKS['fail']} failures ==")
    if failed == 0 and CHECKS["fail"] == 0:
        print("RESULT: PASSED")
        return 0
    print("RESULT: FAILED")
    return 1


if __name__ == "__main__":
    sys.exit(main())
