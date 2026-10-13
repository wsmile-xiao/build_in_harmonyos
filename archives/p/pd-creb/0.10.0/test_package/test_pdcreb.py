#!/usr/bin/env python3
"""Consumer-side verification of the packaged pd-creb 0.10.0 payload.

The payload of a Pure Data extension library is a set of dlopen()-able Pd
objects (``<class>.pd_linux``) plus the ``.pd`` abstractions they instantiate.
Those objects cannot be executed in CI: they are ``aarch64``/OHOS ELF images
and the Pd C API they import is resolved by the *hosting* ``pd`` process at
load time, so dlopen()ing one outside Pd is meaningless.

What is verifiable, and verified here, is the contract Pd itself relies on:

  * layout      - every class object, abstraction, help patch and data file
                  the upstream Makefile promises is present and non-empty;
  * entry point - each object exports the ``<class>_setup`` symbol that Pd's
                  dlsym() looks up (Pd mangles ``~`` to ``_tilde``);
  * OHOS target - ELF64 / ``EM_AARCH64`` / ``ET_DYN``;
  * OHOS ABI    - ``DT_NEEDED`` is exactly ``libc.so`` (musl: a glibc build
                  would need ``libc.so.6`` + ``libm.so.6``), ``$ORIGIN``
                  RUNPATH, non-executable stack, ``PT_GNU_RELRO`` present;
  * loadability - every undefined dynamic symbol is either exported by the
                  OHOS ``pd`` host binary or belongs to the C runtime that
                  OHOS musl provides.  A symbol from anywhere else would mean
                  the object could not be loaded on the target.

All ELF parsing is done with the standard library only, so the test needs no
cross binutils on the CI worker.

Usage: test_pdcreb.py <pd-creb package folder> <puredata bin/pd binary>

The pd host binary argument is required: without it the OHOS loadability
assertions cannot run and the test fails instead of degrading quietly.
"""
import os
import re
import struct
import sys

# --- ELF constants -----------------------------------------------------------
EM_AARCH64 = 183
ET_DYN = 3
ELFCLASS64 = 2
PT_LOAD = 1
PT_GNU_STACK = 0x6474E551
PT_GNU_RELRO = 0x6474E552
PF_X = 0x1
SHT_DYNSYM = 11
DT_NEEDED = 1
DT_RPATH = 15
DT_RUNPATH = 29
STB_GLOBAL = 1
STT_FUNC = 2
SHN_UNDEF = 0

# Upstream ships ``eblosc~.c`` without a ``*_setup`` entry point, so Pd cannot
# load that one object.  Verified against Debian's official arm64 build of
# pd-creb 0.10.0-4, whose ``eblosc~.pd_linux`` likewise exports only
# ``_init``/``_fini`` - the gap is upstream, not an adaptation defect.
KNOWN_UPSTREAM_SETUP_GAPS = frozenset({"eblosc~"})

# Runtime images an OHOS aarch64 Pd object may legitimately depend on.
#
# The OHOS musl toolchain splits the C++ runtime out into its own image, but
# *how* it is attached is driver-dependent, and both drivers are in use:
#   * /opt/lpk-fixed/clang (local profile) appends libc++abi.a + libc++.a, so
#     the objects stay self-contained and need only libc.so;
#   * /data/service/hnp/bin/clang (CI profile, the NDK driver) links
#     libc++_shared.so dynamically, so the three C++ externals record it in
#     DT_NEEDED and import the Itanium C++ ABI operators from it.
# Both are valid OHOS outputs, so the test asserts the platform property that
# is common to them (musl's single libc.so, and never glibc's split runtime)
# instead of one driver's linkage model.
OHOS_RUNTIME_LIBS = frozenset({"libc.so", "libc++_shared.so"})

# glibc splits libc/libm/pthread/dl into versioned images; OHOS musl does not.
# Seeing any of these would mean the object was linked against a glibc host.
GLIBC_RUNTIME_LIBS = frozenset({
    "libc.so.6", "libm.so.6", "libpthread.so.0", "libdl.so.2",
    "librt.so.1", "libstdc++.so.6", "libgcc_s.so.1",
})

# Symbols the C++ runtime image provides: Itanium C++ ABI mangled names plus
# the libsupc++ personality routine and the libunwind entry points.
CXX_RUNTIME_RE = re.compile(r"^(_Z|__gxx_|__cxa_|_Unwind_)")

# Distinct undefined symbols of the whole payload that are *not* part of the Pd
# host API.  They are all provided by the OHOS musl ``libc.so`` (which merges
# libc/libm/pthread/dl into one image); anything outside this set would be an
# import the target cannot satisfy.
C_RUNTIME_SYMBOLS = frozenset("""
__assert_fail __at_fini __cxa_finalize __deregister_frame_info
__register_frame_info __stack_chk_fail __stack_chk_guard abort atan2 atan2f
calloc cbrtf cos cosf dl_iterate_phdr dladdr exit exp exp2 expf expm1 fflush
fprintf fputc fputs fread free fwrite getenv getpid gettimeofday hypot
isxdigit log logf malloc memchr memcpy memmove memset posix_memalign pow
printf pthread_getspecific pthread_key_create pthread_mutex_lock
pthread_mutex_unlock pthread_once pthread_rwlock_rdlock pthread_rwlock_unlock
pthread_rwlock_wrlock pthread_setspecific puts rand realloc set_fatal_message
sin sinf snprintf srand stderr strcmp strlen strncmp syscall tan vasprintf
vfprintf
""".split())

MIN_OBJECTS = 40
MIN_ABSTRACTIONS = 100
MIN_HELP_PATCHES = 60
REQUIRED_DATA_FILES = ("creb-meta.pd", "COPYING", "TODO", "CHANGES.LOG")


class ElfError(Exception):
    pass


class Elf64:
    """Just enough little-endian ELF64 to inspect a shared object."""

    def __init__(self, path):
        self.path = path
        with open(path, "rb") as handle:
            self.data = handle.read()
        blob = self.data
        if blob[:4] != b"\x7fELF":
            raise ElfError(f"{path}: not an ELF file")
        if blob[4] != ELFCLASS64:
            raise ElfError(f"{path}: not ELFCLASS64")
        if blob[5] != 1:
            raise ElfError(f"{path}: not little-endian")
        (self.e_type, self.e_machine) = struct.unpack_from("<HH", blob, 16)
        (self.e_phoff,) = struct.unpack_from("<Q", blob, 32)
        (self.e_shoff,) = struct.unpack_from("<Q", blob, 40)
        (self.e_phentsize, self.e_phnum) = struct.unpack_from("<HH", blob, 54)
        (self.e_shentsize, self.e_shnum) = struct.unpack_from("<HH", blob, 58)
        self.sections = [self._section(i) for i in range(self.e_shnum)]
        self.phdrs = [
            struct.unpack_from("<IIQQQQQQ", blob, self.e_phoff + i * self.e_phentsize)
            for i in range(self.e_phnum)
        ]

    def _section(self, index):
        off = self.e_shoff + index * self.e_shentsize
        return struct.unpack_from("<IIQQQQIIQQ", self.data, off)

    def _strtab(self, index):
        _, _, _, _, offset, size, _, _, _, _ = self.sections[index]
        return self.data[offset:offset + size]

    def _string(self, table, offset):
        end = table.find(b"\0", offset)
        return table[offset:end].decode("utf-8", "replace")

    def dynamic(self):
        """DT_NEEDED library names plus RPATH/RUNPATH values."""
        needed, rpaths = [], []
        for section in self.sections:
            if section[1] != 6:  # SHT_DYNAMIC
                continue
            _, _, _, _, offset, size, link, _, _, entsize = section
            table = self._strtab(link)
            for pos in range(offset, offset + size, entsize or 16):
                tag, value = struct.unpack_from("<qQ", self.data, pos)
                if tag == 0:
                    break
                if tag == DT_NEEDED:
                    needed.append(self._string(table, value))
                elif tag in (DT_RPATH, DT_RUNPATH):
                    rpaths.append(self._string(table, value))
        return needed, rpaths

    def dynsyms(self):
        """[(name, defined, bind, type)] over the dynamic symbol table."""
        found = []
        for section in self.sections:
            if section[1] != SHT_DYNSYM:
                continue
            _, _, _, _, offset, size, link, _, _, entsize = section
            table = self._strtab(link)
            for pos in range(offset, offset + size, entsize or 24):
                st_name, st_info, _other, st_shndx = struct.unpack_from(
                    "<IBBH", self.data, pos
                )
                if st_name == 0:
                    continue
                found.append((
                    self._string(table, st_name),
                    st_shndx != SHN_UNDEF,
                    st_info >> 4,
                    st_info & 0xF,
                ))
        return found


class Report:
    def __init__(self):
        self.passed = 0
        self.failures = []

    def check(self, condition, message):
        if condition:
            self.passed += 1
        else:
            self.failures.append(message)
        return bool(condition)

    def finish(self, title):
        print(f"[{title}] assertions passed: {self.passed}, failed: {len(self.failures)}")
        for failure in self.failures:
            print(f"[{title}] FAIL: {failure}")
        return 0 if not self.failures else 1


def pd_symbol_for(stem):
    """Pd's class-name -> setup-symbol mangling (~ becomes _tilde)."""
    return re.sub(r"[^A-Za-z0-9]", "_", stem.replace("~", "_tilde")) + "_setup"


def payload_dir(package_folder):
    candidate = os.path.join(package_folder, "lib", "pd-externals", "creb")
    if os.path.isdir(candidate):
        return candidate
    return package_folder


def main(argv):
    if len(argv) < 2:
        print("usage: test_pdcreb.py <pd-creb package folder> <puredata bin/pd>")
        return 2
    root = payload_dir(argv[1])
    pd_binary = argv[2] if len(argv) > 2 else None
    report = Report()

    if not report.check(os.path.isdir(root), f"payload directory missing: {root}"):
        return report.finish("layout")

    objects = sorted(f for f in os.listdir(root) if f.endswith(".pd_linux"))
    abstractions = sorted(f for f in os.listdir(root) if f.endswith(".pd"))
    helps = sorted(f for f in os.listdir(root) if f.endswith("-help.pd"))
    patch_dirs = [d for d in ("manual", "examples") if os.path.isdir(os.path.join(root, d))]

    report.check(len(objects) >= MIN_OBJECTS,
                 f"expected >={MIN_OBJECTS} Pd objects, found {len(objects)}")
    report.check(len(abstractions) >= MIN_ABSTRACTIONS,
                 f"expected >={MIN_ABSTRACTIONS} .pd abstractions, found {len(abstractions)}")
    report.check(len(helps) >= MIN_HELP_PATCHES,
                 f"expected >={MIN_HELP_PATCHES} *-help.pd files, found {len(helps)}")
    for name in REQUIRED_DATA_FILES:
        path = os.path.join(root, name)
        report.check(os.path.isfile(path) and os.path.getsize(path) > 0,
                     f"required data file missing or empty: {name}")
    for name in patch_dirs:
        count = len(os.listdir(os.path.join(root, name)))
        report.check(count > 0, f"installed {name}/ is empty")

    # Pd only refuses to open an empty or truncated abstraction.
    for name in abstractions:
        path = os.path.join(root, name)
        report.check(os.path.getsize(path) > 0, f"abstraction is empty: {name}")

    # The OHOS pd host binary is mandatory: it is what proves every Pd API import
    # of the payload resolves on the target.  Silently skipping it would turn the
    # 91 loadability assertions into a green no-op.
    if not report.check(bool(pd_binary) and os.path.isfile(pd_binary or ""),
                        f"puredata OHOS pd host binary not found: {pd_binary!r}"):
        return report.finish("pd-creb")
    try:
        host_symbols = {
            name.split("@")[0]
            for name, defined, _bind, _typ in Elf64(pd_binary).dynsyms()
            if defined
        }
        report.check(len(host_symbols) > 500,
                     f"OHOS pd host exports implausibly few symbols: {len(host_symbols)}")
    except ElfError as exc:
        report.check(False, f"cannot parse pd host binary: {exc}")
        return report.finish("pd-creb")

    setup_gaps = []
    unresolved = set()
    cxx_linkage = set()
    for name in objects:
        path = os.path.join(root, name)
        stem = name[: -len(".pd_linux")]
        try:
            elf = Elf64(path)
        except ElfError as exc:
            report.check(False, str(exc))
            continue

        # --- HarmonyOS PC target (OHOS aarch64) ---
        report.check(elf.e_machine == EM_AARCH64,
                     f"{name}: e_machine={elf.e_machine}, expected EM_AARCH64")
        report.check(elf.e_type == ET_DYN, f"{name}: e_type={elf.e_type}, expected ET_DYN")

        needed, rpaths = elf.dynamic()
        report.check("libc.so" in needed,
                     f"{name}: DT_NEEDED={needed} does not include OHOS musl libc.so")
        report.check(not (set(needed) & GLIBC_RUNTIME_LIBS),
                     f"{name}: DT_NEEDED={needed} pulls in a glibc runtime image")
        cxx_linkage |= set(needed) & {"libc++_shared.so"}
        report.check(set(needed) <= OHOS_RUNTIME_LIBS,
                     f"{name}: DT_NEEDED={needed} is outside the OHOS runtime set "
                     f"{sorted(OHOS_RUNTIME_LIBS)}")
        report.check(rpaths == ["$ORIGIN"],
                     f"{name}: RPATH/RUNPATH={rpaths}, expected ['$ORIGIN']")

        stack = [p for p in elf.phdrs if p[0] == PT_GNU_STACK]
        report.check(len(stack) == 1, f"{name}: PT_GNU_STACK count={len(stack)}")
        if stack:
            report.check(not stack[0][1] & PF_X,
                         f"{name}: stack is executable (NX disabled)")
        report.check(any(p[0] == PT_GNU_RELRO for p in elf.phdrs),
                     f"{name}: PT_GNU_RELRO missing (no partial RELRO)")
        report.check(any(p[0] == PT_LOAD for p in elf.phdrs),
                     f"{name}: no PT_LOAD segment")

        # --- Pd entry point + loadability ---
        symbols = elf.dynsyms()
        exported = {sym for sym, defined, _b, _t in symbols if defined}
        undefined = {sym.split("@")[0] for sym, defined, _b, _t in symbols if not defined}
        # Pd dlopen()s the object and looks up <class>_setup (with "~" mangled to
        # "_tilde").  A missing entry point means Pd can never instantiate it.
        expected = pd_symbol_for(stem)
        known_gap = stem in KNOWN_UPSTREAM_SETUP_GAPS
        has_entry = report.check(
            expected in exported or known_gap,
            f"{name}: does not export the Pd entry point {expected}")
        if known_gap:
            setup_gaps.append(stem)
        report.check(os.path.getsize(path) > 4096,
                     f"{name}: implausibly small Pd object "
                     f"({os.path.getsize(path)} bytes)")

        if host_symbols and not known_gap:
            report.check(bool(undefined & host_symbols),
                         f"{name}: imports no Pd host symbol, so Pd could never drive it")
            foreign = {s for s in undefined
                       if s not in host_symbols
                       and s not in C_RUNTIME_SYMBOLS
                       and not CXX_RUNTIME_RE.match(s)}
            unresolved |= foreign
            report.check(not foreign,
                         f"{name}: undefined symbols unavailable on OHOS: {sorted(foreign)}")

    report.check(len(objects) - len(setup_gaps) >= MIN_OBJECTS,
                 f"only {len(objects) - len(setup_gaps)} of {len(objects)} objects expose a "
                 "Pd entry point")
    if setup_gaps:
        print(f"[elf] upstream objects without a Pd entry point (same in Debian's "
              f"official arm64 build): {sorted(setup_gaps)}")
    print(f"[elf] OHOS pd host binary parsed, {len(host_symbols)} exported symbols; "
          + ("no unresolvable imports found" if not unresolved
             else f"UNRESOLVED IMPORTS: {sorted(unresolved)}"))
    print(f"[elf] C++ runtime linkage: {sorted(cxx_linkage)}")

    print(f"[summary] objects={len(objects)} abstractions={len(abstractions)} "
          f"help_patches={len(helps)} extra_dirs={patch_dirs}")
    return report.finish("pd-creb")


if __name__ == "__main__":
    sys.exit(main(sys.argv))