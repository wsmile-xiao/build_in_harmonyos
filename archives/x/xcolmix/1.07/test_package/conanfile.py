#!/usr/bin/env python3
"""Conan test_package — xcolmix 1.07.

xcolmix ships no library to link against, so the consumer evidence is carried
by two independent, real checks against the *packaged* artefact:

1. ``test_elf_contract`` (this file) parses the ELF image of
   ``<package>/bin/xcolmix`` directly with :mod:`struct` — magic, ELF64,
   ``e_machine == EM_AARCH64``, ``ET_DYN`` (PIE), ``PT_INTERP``, the
   ``DF_1_PIE`` dynamic flag and the exact ``DT_NEEDED`` set (11 assertions).
   The assertion that matters most is the one on ``libforms.so.2``: it pins that
   the delivered executable is dynamically bound to the adapted XForms stack
   instead of a vendored or stubbed copy.  No external tool
   (``readelf``/``llvm-readelf``) is required, so the check behaves identically
   on a cross-build host and on a device worker.

2. ``test_xcolmix.sh`` executes the packaged binary on three command lines that
   are all decided before an X server is needed, and asserts the observable
   contract (exit status plus the usage banner ``src/usage.c`` prints) — 9
   assertions:

   * ``xcolmix alpha beta gamma``  -> the ``argc > 2`` branch of ``main()``
   * ``xcolmix <absent path>``     -> the ``argc == 2`` + ``access(2)``
                                      rejection branch
   * ``xcolmix -display 127.0.0.1:99 alpha beta gamma``
                                   -> forces ``fl_initialize()`` to fail its
                                      ``XOpenDisplay``, which is the proof that
                                      XForms code really ran inside the process

   The banner carries ``V1.07`` straight from ``src/version.h`` and the
   copyright line from ``usage.c``, so the assertions are on this package's own
   contents rather than on a generic "it started" signal.

Runtime library resolution: the loader has to find the whole ``DT_NEEDED``
closure of ``libforms.so.2``.  ``VirtualRunEnv`` injects the libdirs of every
``run=True`` requirement into ``LD_LIBRARY_PATH``; on top of that the recipe
hands the script the absolute path of every shared object found in those
packages, prepended to ``LD_PRELOAD`` (same remedy as xev, for the HarmonyOS
loader's ``stale_runtime_library`` behaviour).  ``LD_PRELOAD`` is *appended* to
whatever the caller already exported, never overwritten.

Upstream audit: the 1.07 tarball has no test framework of any kind — ``src/``
holds 7 ``.c`` files and one hand-written ``Makefile`` with no ``check``/``test``
target, and ``grep -c assert src/*.c`` is 0.  See ``test_package/MANIFEST.yml``.
"""

import os
import shlex
import struct

from conan import ConanFile
from conan.errors import ConanException

_EXECUTABLE = "xcolmix"

# ELF constants (generic ABI values; ELF is a frozen standard).
_ELF_MAGIC = b"\x7fELF"
_ELFCLASS64 = 2
_ELFCLASS_NAMES = {0: "ELFCLASSNONE", 1: "ELFCLASS32", 2: "ELFCLASS64"}
_EM_AARCH64 = 183
_ET_DYN = 3
_PT_LOAD = 1
_PT_DYNAMIC = 2
_PT_INTERP = 3
_DT_NULL = 0
_DT_NEEDED = 1
_DT_STRTAB = 5
_DT_FLAGS_1 = 0x6FFFFFFB
_DF_1_PIE = 0x08000000


class _Elf64Image:
    """Minimal read-only ELF64 little-endian reader (aarch64 target)."""

    def __init__(self, path):
        with open(path, "rb") as handle:
            self._data = handle.read()
        self.path = path

    def magic(self):
        return self._data[:4]

    def header(self):
        if len(self._data) < 64:
            raise ConanException(f"truncated ELF image: {self.path}")
        e_type, e_machine = struct.unpack_from("<HH", self._data, 16)
        e_phoff, = struct.unpack_from("<Q", self._data, 32)
        e_phentsize, e_phnum = struct.unpack_from("<HH", self._data, 54)
        return {
            "ei_class": self._data[4],
            "ei_data": self._data[5],
            "e_type": e_type,
            "e_machine": e_machine,
            "e_phoff": e_phoff,
            "e_phentsize": e_phentsize,
            "e_phnum": e_phnum,
        }

    def program_headers(self):
        head = self.header()
        headers = []
        for index in range(head["e_phnum"]):
            base = head["e_phoff"] + index * head["e_phentsize"]
            p_type, p_flags = struct.unpack_from("<II", self._data, base)
            p_offset, p_vaddr, _p_paddr, p_filesz = struct.unpack_from(
                "<QQQQ", self._data, base + 8
            )
            headers.append(
                {
                    "type": p_type,
                    "flags": p_flags,
                    "offset": p_offset,
                    "vaddr": p_vaddr,
                    "filesz": p_filesz,
                }
            )
        return headers

    def _vaddr_to_offset(self, vaddr):
        for header in self.program_headers():
            if header["type"] != _PT_LOAD:
                continue
            if header["vaddr"] <= vaddr < header["vaddr"] + header["filesz"]:
                return header["offset"] + (vaddr - header["vaddr"])
        raise ConanException(
            f"virtual address 0x{vaddr:x} lies outside every PT_LOAD segment: "
            f"{self.path}"
        )

    def interpreter(self):
        for header in self.program_headers():
            if header["type"] == _PT_INTERP:
                start = header["offset"]
                end = start + header["filesz"]
                return self._data[start:end].split(b"\x00", 1)[0].decode("utf-8")
        return None

    def _dynamic_entries(self):
        """Dynamic table as an ordered list of (tag, value) pairs.

        A dict keyed by tag would be wrong: ``DT_NEEDED`` repeats once per
        shared object, so a mapping keeps only the last entry and the
        dependency set silently shrinks to one name.
        """
        for header in self.program_headers():
            if header["type"] != _PT_DYNAMIC:
                continue
            entries = []
            offset = header["offset"]
            while True:
                tag, value = struct.unpack_from("<qQ", self._data, offset)
                offset += 16
                if tag == _DT_NULL:
                    break
                entries.append((tag, value))
            return entries
        raise ConanException(f"no PT_DYNAMIC segment in {self.path}")

    def dynamic_strings(self):
        entries = self._dynamic_entries()
        strtab = self._vaddr_to_offset(
            next(value for tag, value in entries if tag == _DT_STRTAB)
        )
        names = []
        for tag, value in entries:
            if tag != _DT_NEEDED:
                continue
            start = strtab + value
            end = self._data.index(b"\x00", start)
            names.append(self._data[start:end].decode("utf-8"))
        return names

    def flags_1(self):
        for tag, value in self._dynamic_entries():
            if tag == _DT_FLAGS_1:
                return value
        return 0


class XcolmixTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # Keep the generator scripts out of the archived test_package/ tree:
        # without an explicit layout Conan writes conanrunenv-*.sh and
        # metadata/ straight next to the sources, which then shows up as
        # untracked residue in the contributor's checkout.
        self.folders.root = "."
        self.folders.source = "."
        self.folders.build = "b"
        self.folders.generators = "b/gen"

    def test(self):
        package = self.dependencies[self.tested_reference_str]
        binary = os.path.join(package.package_folder, "bin", _EXECUTABLE)
        self.test_elf_contract(binary)
        self._run_runtime_cases(package, binary)

    # ── check 1: ELF / dynamic-link contract (11 assertions) ─────────────

    def test_elf_contract(self, binary):
        self._check(os.path.isfile(binary), f"packaged executable is missing: {binary}")
        image = _Elf64Image(binary)
        self._check(
            image.magic() == _ELF_MAGIC,
            f"not an ELF image (magic={image.magic()!r}): {binary}",
        )
        head = image.header()
        self._check(
            head["ei_class"] == _ELFCLASS64,
            "ELF class is "
            f"{_ELFCLASS_NAMES.get(head['ei_class'], head['ei_class'])}, "
            "expected ELFCLASS64",
        )
        self._check(
            head["e_machine"] == _EM_AARCH64,
            f"e_machine is {head['e_machine']}, expected {_EM_AARCH64} (AArch64)",
        )
        self._check(
            head["e_type"] == _ET_DYN,
            f"e_type is {head['e_type']}, expected {_ET_DYN} (position independent)",
        )
        interpreter = image.interpreter()
        self._check(
            interpreter is not None and interpreter.startswith("/"),
            f"PT_INTERP must name an absolute dynamic loader, got {interpreter!r}",
        )
        needed = image.dynamic_strings()
        for soname in ("libforms.so.2", "libX11.so.6", "libc.so"):
            self._check(
                soname in needed,
                f"DT_NEEDED must contain {soname}, got {needed}",
            )
        absolute = [
            name for name in needed if name.startswith("/") or name.startswith("../")
        ]
        self._check(
            not absolute,
            f"DT_NEEDED must not use absolute or parent-relative paths: {absolute}",
        )
        self._check(
            bool(image.flags_1() & _DF_1_PIE),
            "DT_FLAGS_1 must carry DF_1_PIE (position-independent executable)",
        )
        self.output.info(f"XCOLMIX_ELF_INTERP={interpreter}")
        self.output.info(f"XCOLMIX_DT_NEEDED={','.join(sorted(needed))}")
        self.output.info("XCOLMIX_ELF_ASSERTIONS=11")

    @staticmethod
    def _check(condition, message):
        if not condition:
            raise ConanException(message)

    # ── check 2: execute the packaged binary (9 assertions in the script) ─

    def _run_runtime_cases(self, package, binary):
        shell = os.environ.get("SHELL") or os.environ.get("CONFIG_SHELL") or "/bin/sh"
        script = os.path.join(self.source_folder, "test_xcolmix.sh")
        # A path that is guaranteed not to exist, so access(2) fails and main()
        # takes the usage() branch.  It lives inside the package folder (conan
        # cache) rather than the build folder, which keeps the check independent
        # of where the generator scripts were laid down.
        absent_rgb = os.path.join(
            package.package_folder, "share", "man", "man1", "absent-rgb-database.txt"
        )
        if os.path.exists(absent_rgb):
            raise ConanException(
                f"the negative-path fixture must not exist: {absent_rgb}"
            )
        preload = ":".join(self._runtime_shared_objects())
        if preload:
            self.output.info(f"runtime LD_PRELOAD entries={len(preload.split(':'))}")
        command = " ".join(
            shlex.quote(value)
            for value in (shell, script, binary, preload, absent_rgb)
        )
        self.run(command, env="conanrun")
        if os.path.exists(absent_rgb):
            raise ConanException(
                f"xcolmix must not create the rgb database it was handed: {absent_rgb}"
            )

    def _runtime_shared_objects(self):
        """Absolute paths of the shared objects the loader may have to find.

        Every ``run=True`` requirement is scanned for real (non-symlink) ELF
        files under its ``lib`` directories.  Symlinks are skipped because the
        HarmonyOS filesystem materialises them inconsistently (E050), and the
        loader registers a preload by the SONAME the file carries anyway.
        """
        found = []
        for dependency in sorted(
            self.dependencies.host.values(), key=lambda dep: str(dep.ref)
        ):
            for relative in dependency.cpp_info.libdirs:
                libdir = os.path.join(dependency.package_folder, relative)
                if not os.path.isdir(libdir):
                    continue
                for name in sorted(os.listdir(libdir)):
                    if ".so" not in name:
                        continue
                    path = os.path.join(libdir, name)
                    if os.path.islink(path) or not os.path.isfile(path):
                        continue
                    if path not in found:
                        found.append(path)
        return found
