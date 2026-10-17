#!/usr/bin/env python3
"""Conan test_package for mpop 1.4.22.

mpop is a POP3 **client program**, not a library, so a consumer test has to
execute the installed programs rather than include a header.  This device has no
reachable POP3 server, no external network and a reduced name-service surface,
therefore the behaviour assertions cover the public code paths that run
**before** ``src/mpop.c`` reaches ``net_lib_init()`` (measured: line 2659), and
the network-dependent features are declared skipped in ``MANIFEST.yml`` with the
measured reason instead of being quietly dropped:

  * ``sh test_mpop.sh`` really executes the packaged ``mpop`` / ``mpopd`` and
    accumulates 22 behaviour assertions over the option-parsing, config-file and
    address-validation surfaces, including
    a negative control that removes the dependency library search path and must
    be refused by the runtime loader (R34 proof that the package is really
    consumed);
  * this file adds 4 platform checks parsed straight out of the packaged ELF
    (ELF64/AArch64, the dynamic NEEDED closure, the ``.codesign`` section, and
    the absence of any build-host absolute path).

The distinction that matters here is *where* a run stops: a ``mpop`` that prints
an upstream diagnostic means the loader accepted the binary and resolved
libgnutls/libidn2, whereas ``Error loading shared library`` / exit 127 / 126
would mean the package is broken.  Both signatures are asserted - the second one
only as the negative control with the loader path removed.

E386 family: the script is handed to a shell that was capability-probed from the
real scratch directory (``CONFIG_SHELL`` points at the HMDFS-broken hnp bash),
and the scratch directory is seeded with ``PWD``.
"""
import json
import os
import shlex
import struct
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import can_run
from conan.tools.layout import basic_layout

DT_NEEDED = 1
DT_STRTAB = 5
PT_LOAD = 1
PT_DYNAMIC = 2
EM_AARCH64 = 183

SCRIPT_CHECKS = 22       # must match the runtime count emitted by test_mpop.sh
PLATFORM_CHECKS = 4      # ELF64/AArch64, NEEDED closure, .codesign, no host path


class MpopTestConan(ConanFile):
    settings = "os", "arch", "compiler", "build_type"
    generators = "VirtualRunEnv"
    test_type = "explicit"

    def requirements(self):
        self.requires(self.tested_reference_str)

    def layout(self):
        # Keep every generated file (env scripts, scratch/) inside
        # test_package/build-release instead of the archive directory itself.
        basic_layout(self)

    # ── behaviour ────────────────────────────────────────────────────────
    def test(self):
        if not can_run(self):
            raise ConanException("mpop test_package must run on the host")

        package = self.dependencies["mpop"]
        bindir = os.path.join(package.package_folder, "bin")
        script = os.path.join(self.recipe_folder, "test_mpop.sh")
        if not os.path.isfile(script):
            raise ConanException("test script is missing: " + script)

        scratch = os.path.join(self.build_folder, "scratch")
        os.makedirs(scratch, exist_ok=True)

        shell = self._probed_shell(scratch)
        ldpath = ":".join(self._dependency_libdirs())
        counter = os.path.join(scratch, "checks.count")
        if os.path.isfile(counter):
            os.unlink(counter)

        self.run("PWD={} {} {} {} {} {} {}".format(
            shlex.quote(scratch),
            shlex.quote(shell),
            shlex.quote(script),
            shlex.quote(package.package_folder),
            shlex.quote(bindir),
            shlex.quote(scratch),
            shlex.quote(ldpath)), cwd=scratch, env="conanrun")

        executed = self._read_count(counter)
        if executed != SCRIPT_CHECKS:
            raise ConanException(
                "behaviour check count drifted: script reported {}, "
                "test_package declares {}".format(executed, SCRIPT_CHECKS))

        needed = self._platform_checks(os.path.join(bindir, "mpop"),
                                       package.package_folder)

        total = SCRIPT_CHECKS + PLATFORM_CHECKS
        print("HMBS_MPOP_NEEDED=" + json.dumps(sorted(needed)))
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_mpop.sh (behaviour) + packaged-ELF parsing",
            "consumer_passed": total,
            "consumer_total": total,
        }, sort_keys=True))

    @staticmethod
    def _read_count(path):
        if not os.path.isfile(path):
            raise ConanException("test script did not report its check count: "
                                 + path)
        with open(path, "r", encoding="utf-8", errors="replace") as handle:
            return int(handle.read().strip() or "-1")

    def _dependency_libdirs(self):
        """Absolute libdirs of the tested package and of its whole host closure."""
        found, seen = [], set()
        for _, dep in self.dependencies.host.items():
            base = dep.package_folder or ""
            for entry in dep.cpp_info.libdirs:
                path = entry if os.path.isabs(entry) else os.path.join(base, entry)
                if os.path.isdir(path) and path not in seen:
                    seen.add(path)
                    found.append(path)
        return found

    def _probed_shell(self, workdir):
        """E386: never trust an exported shell, probe it from the real directory.

        ``CONFIG_SHELL``/``SHELL`` come from the profile ``[buildenv]`` and point
        at ``/data/service/hnp/bin/bash``, which cannot ``getcwd()`` on HMDFS
        while ``/bin/sh`` works.  A shell is accepted only when ``pwd`` exits 0,
        echoes the requested directory and stays silent on stderr.
        """
        candidates = [os.environ.get("CONFIG_SHELL"), os.environ.get("SHELL"),
                      "/bin/sh", "/system/bin/sh"]
        tried = []
        for shell in filter(None, candidates):
            if not os.path.isfile(shell):
                continue
            try:
                probe = subprocess.run([shell, "-c", "pwd"], cwd=workdir,
                                       capture_output=True, text=True,
                                       timeout=30)
            except OSError as error:
                tried.append("{}({})".format(shell, error))
                continue
            if (probe.returncode == 0
                    and (probe.stdout or "").strip() == workdir
                    and not (probe.stderr or "").strip()):
                self.output.info("test shell selected: " + shell)
                return shell
            tried.append("{}(rc={})".format(shell, probe.returncode))
        raise ConanException(
            "no usable POSIX shell for the test script (tried: "
            + ", ".join(tried) + ")")

    # ── platform assertions (pure Python ELF parsing, no host tool needed) ──
    def _platform_checks(self, binary, package_folder):
        blob = self._read_binary(binary)

        if blob[:4] != b"\x7fELF" or blob[4] != 2 or blob[5] != 1:
            raise ConanException("packaged mpop is not an ELF64 little-endian "
                                 "object (magic={!r} class={} data={})".format(
                                     blob[:4], blob[4], blob[5]))
        machine = struct.unpack_from("<H", blob, 18)[0]
        if machine != EM_AARCH64:
            raise ConanException("packaged mpop is not AArch64: e_machine={}"
                                 .format(machine))
        print("OK: ELF is ELF64/AArch64 (e_machine={})".format(machine))

        needed = self._elf_needed(blob)
        # Measured DT_NEEDED set of the packaged mpop is exactly:
        #   libc.so, libgcrypt.so.20, libgnutls.so.30, libgpg-error.so.0,
        #   libidn2.so.0, libtasn1.so.6
        # Both declared host requirements must show up, otherwise the recipe
        # would be declaring something the binary does not consume.
        for expected in ("libgnutls.so", "libidn2.so"):
            if not [entry for entry in needed
                    if entry.startswith(expected)]:
                raise ConanException(
                    "dynamic NEEDED lacks {}*, i.e. the declared dependency is "
                    "not actually consumed (got: {})".format(
                        expected, ", ".join(needed)))
        print("OK: NEEDED carries libgnutls.so* and libidn2.so* out of "
              "{} entries: {}".format(len(needed), ", ".join(needed)))

        sections = self._elf_sections(blob)
        if ".codesign" not in sections:
            raise ConanException("packaged mpop carries no .codesign section "
                                 "(sections: {})".format(", ".join(sections[:8])))
        print("OK: .codesign section present ({} sections parsed)".format(
            len(sections)))

        build_dir = os.path.dirname(package_folder.rstrip("/"))
        cache_root = package_folder.split(os.sep + "p" + os.sep)[0]
        for leaked in (cache_root, build_dir, package_folder):
            if leaked and leaked.encode() in blob:
                raise ConanException("packaged mpop leaks a build-host path: "
                                     + leaked)
        print("OK: no build-host absolute path inside the binary "
              "({} bytes scanned)".format(len(blob)))
        return needed

    @staticmethod
    def _read_binary(path):
        if not os.path.isfile(path):
            raise ConanException("packaged binary is missing: " + path)
        with open(path, "rb") as handle:
            return handle.read()

    @staticmethod
    def _elf_needed(blob):
        e_phoff = struct.unpack_from("<Q", blob, 32)[0]
        e_phentsize = struct.unpack_from("<H", blob, 54)[0]
        e_phnum = struct.unpack_from("<H", blob, 56)[0]
        loads, dynamic = [], None
        for index in range(e_phnum):
            base = e_phoff + index * e_phentsize
            p_type = struct.unpack_from("<I", blob, base)[0]
            p_offset = struct.unpack_from("<Q", blob, base + 8)[0]
            p_vaddr = struct.unpack_from("<Q", blob, base + 16)[0]
            p_filesz = struct.unpack_from("<Q", blob, base + 32)[0]
            if p_type == PT_LOAD:
                loads.append((p_vaddr, p_offset, p_filesz))
            elif p_type == PT_DYNAMIC:
                dynamic = p_offset
        if dynamic is None:
            raise ConanException("ELF has no PT_DYNAMIC segment")

        entries, strtab = [], None
        offset = dynamic
        while offset + 16 <= len(blob):
            d_tag, d_val = struct.unpack_from("<qQ", blob, offset)
            if d_tag == 0:
                break
            if d_tag == DT_STRTAB:
                strtab = d_val
            elif d_tag == DT_NEEDED:
                entries.append(d_val)
            offset += 16
        if strtab is None:
            raise ConanException("DT_STRTAB missing")
        for vaddr, file_offset, filesz in loads:
            if vaddr <= strtab < vaddr + filesz:
                base = file_offset + (strtab - vaddr)
                break
        else:
            raise ConanException("DT_STRTAB is not covered by any PT_LOAD")

        names = []
        for string_offset in entries:
            start = base + string_offset
            end = blob.find(b"\x00", start)
            names.append(blob[start:end].decode("ascii", "replace"))
        return names

    @staticmethod
    def _elf_sections(blob):
        e_shoff = struct.unpack_from("<Q", blob, 40)[0]
        e_shentsize = struct.unpack_from("<H", blob, 58)[0]
        e_shnum = struct.unpack_from("<H", blob, 60)[0]
        e_shstrndx = struct.unpack_from("<H", blob, 62)[0]
        if not e_shoff or not e_shnum:
            raise ConanException("ELF section header table is missing")
        strtab_base = e_shoff + e_shstrndx * e_shentsize
        strtab_off = struct.unpack_from("<Q", blob, strtab_base + 24)[0]
        names = []
        for index in range(e_shnum):
            base = e_shoff + index * e_shentsize
            name_idx = struct.unpack_from("<I", blob, base)[0]
            start = strtab_off + name_idx
            end = blob.find(b"\x00", start)
            names.append(blob[start:end].decode("ascii", "replace"))
        return names
