#!/usr/bin/env python3
"""Conan test_package for wmcore 0.0.4.

wmcore is a dockapp: it draws into a window that a reparenting window manager
embeds in its dock, so the drawing loop needs an X server.  Neither this device
nor a CI worker has one (no Xorg/Xvfb binary in the image, no OHOS xorg-server
in the artifact repo), therefore the test asserts on the code paths that are
reached **before** and **independently of** the display connection, plus the
platform properties of the packaged ELF:

  * ``sh test_wmcore.sh`` (behaviour, 9 runtime-counted checks) really executes
    the installed program: the ``-h`` path, the version banner produced from
    ``config.h``, the usage screen, the headless X-connection failure, the
    ``DISPLAY``-respecting variant of it, the loader-refusal control, the
    generated man page and the license file;
  * this file adds 4 platform checks parsed straight out of the packaged ELF
    (AArch64/ELF64, the dynamic NEEDED closure, the ``.codesign`` section and
    the absence of any build-host path).

The distinction that matters for a headless dockapp is *where* the run stops:
reaching libdockapp's ``can't open display`` diagnostic means the runtime loader
accepted the binary and resolved libdockapp/libX11/libXext/libXpm/libxcb, while
``Error loading shared library`` / exit 127 / exit 126 would mean the package is
broken.  Both signatures are asserted, the second one only as a negative
control with the loader path removed.

E386 family: the script is handed to a shell that has been capability-probed
from the real scratch directory (``CONFIG_SHELL`` points at the HMDFS-broken
hnp bash), and the scratch directory is seeded with ``PWD``.
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

SCRIPT_CHECKS = 9        # must match the runtime count emitted by the script
PLATFORM_CHECKS = 4      # ELF64/AArch64, NEEDED closure, .codesign, no host path


class WmcoreTestConan(ConanFile):
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
            raise ConanException("wmcore test_package must run on the host")

        package = self.dependencies["wmcore"]
        bindir = os.path.join(package.package_folder, "bin")
        binary = os.path.join(bindir, "wmcore")
        script = os.path.join(self.recipe_folder, "test_wmcore.sh")
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
            shlex.quote(binary),
            shlex.quote(scratch),
            shlex.quote(ldpath)), cwd=scratch, env="conanrun")

        executed = self._read_count(counter)
        if executed != SCRIPT_CHECKS:
            raise ConanException(
                "behaviour check count drifted: script reported {}, "
                "test_package declares {}".format(executed, SCRIPT_CHECKS))

        self._platform_checks(binary, package.package_folder)

        total = SCRIPT_CHECKS + PLATFORM_CHECKS
        print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
            "executed": True,
            "passed": True,
            "command": "sh test_wmcore.sh (behaviour) + packaged-ELF parsing",
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
        (measured: ``bash -c pwd`` prints "shell-init: error retrieving current
        directory" and exits 1) while ``/bin/sh`` works.  A shell is accepted
        only when ``pwd`` exits 0, echoes the requested directory and stays
        silent on stderr.
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
            raise ConanException("packaged wmcore is not an ELF64 little-endian "
                                 "object (magic={!r} class={} data={})".format(
                                     blob[:4], blob[4], blob[5]))
        machine = struct.unpack_from("<H", blob, 18)[0]
        if machine != EM_AARCH64:
            raise ConanException("packaged wmcore is not AArch64: e_machine={}"
                                 .format(machine))
        print("OK: ELF is ELF64/AArch64 (e_machine={})".format(machine))

        needed = self._elf_needed(blob)
        for expected in ("libdockapp.so", "libX11.so", "libXext.so", "libXpm.so"):
            if not [entry for entry in needed if entry.startswith(expected)]:
                raise ConanException("dynamic NEEDED lacks {} (got: {})".format(
                    expected, ", ".join(needed[:6])))
        print("OK: NEEDED carries libdockapp/libX11/libXext/libXpm "
              "({} entries)".format(len(needed)))

        sections = self._elf_sections(blob)
        if ".codesign" not in sections:
            raise ConanException("packaged wmcore carries no .codesign section "
                                 "(sections: {})".format(", ".join(sections[:8])))
        print("OK: .codesign section present ({} sections parsed)".format(
            len(sections)))

        build_dir = os.path.dirname(package_folder.rstrip("/"))
        cache_root = package_folder.split(os.sep + "p" + os.sep)[0]
        for leaked in (cache_root, build_dir, package_folder):
            if leaked and leaked.encode() in blob:
                raise ConanException("packaged wmcore leaks a build-host path: "
                                     + leaked)
        print("OK: no build-host absolute path inside the binary "
              "({} bytes scanned)".format(len(blob)))

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
