#!/usr/bin/env python3
"""Conan recipe for dcled 2.2 — userland driver for the Dream Cheeky USB LED
message board.

Upstream ships a plain Makefile (no configure/CMake step); its `all` target
builds TWO device-facing executables from `CFILES= dcled.c cpuload.c`:

  * dcled   — the message board driver / CLI (libusb-1.0 backend)
  * cpuload — endless CPU-load producer, one 0-100 value per line, meant to be
              piped into dcled's tachometer mode: `cpuload 0.2 | dcled -T tach`

Build contract — every Makefile variable is set from Conan, never picked up
from the ambient shell (R33):

  CC            <- tools.build:compiler_executables["c"] (Makefile hardcodes gcc)
  FONTDIR       <- <pkg>/share/dcled  (compile-time font lookup directory)
  LIBUSB_CFLAGS <- -I<libusb>/include/libusb-1.0 (dcled.c does #include <libusb.h>)
  LIBUSB_LIBS   <- -L<libusb>/lib -lusb-1.0 -Wl,-rpath,<libusb>/lib

libusb-1.0 is not a system library on OHOS (nothing named libusb-1.0.so lives
in /lib or /lib64), so the default shared link is kept and the runtime search
path is pinned with -Wl,-rpath instead of relying on $ORIGIN.

patches/0001-init-ledscreen-maindisp.patch zero-initialises the stack-allocated
`struct ledscreen maindisp` before `disp = &maindisp`. Without it every
device-free run (`dcled -n ...`, the mode used by all checks below) hands a
garbage libusb handle to close_usbdev() and dies with SIGSEGV (exit 139).

Upstream ships NO automated test suite — the Makefile has no check/test target.
Its documented verification surface is the README "EXAMPLES" list plus the
`--test` test pattern, so every one of those commands is executed here from the
freshly built binaries with `-n` (nodev, no board attached) and the counts are
published through the HMBS_UPSTREAM_TEST_RESULT marker consumed by the PR gate.
Consumer-side assertions against the installed package live in test_package/.
"""

import json
import os
import subprocess

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get
from conan.tools.layout import basic_layout


class DcledConan(ConanFile):
    name = "dcled"
    version = "2.2"
    description = ("Userland driver for the Dream Cheeky USB LED message board "
                   "(dcled message driver + cpuload load producer)")
    # Upstream ships no LICENSE file. The README states the program is free
    # software ("you can redistribute it and/or modify it") and adds that
    # "because of the use of libusb, ... this might now be considered GPL
    # licensed".
    license = "GPL-2.0-or-later"
    homepage = "https://www.jeffrika.com/~malakai/dcled"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    # -t / --test / --clock --repeat / cpuload are endless by design: they are
    # bounded by this many seconds instead of being allowed to run forever.
    _CHECK_TIMEOUT = 20

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        self.requires("libusb/1.0.27")

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    # ── build ────────────────────────────────────────────────────────────────
    def build(self):
        apply_conandata_patches(self)
        self.run(self._make_command(), cwd=self.source_folder)
        self._run_upstream_checks()

    def _make_command(self):
        """`make all`, with every variable coming from Conan (R33)."""
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = compilers.get("c") or "clang"

        libusb = self.dependencies["libusb"]
        # The libusb package exports include/libusb-1.0 as its include dir and
        # dcled.c says #include <libusb.h>, so that is what -I must point at.
        usb_include = os.path.join(
            libusb.package_folder, libusb.cpp_info.includedirs[0]
        )
        usb_libdir = os.path.join(libusb.package_folder, libusb.cpp_info.libdirs[0])

        # FONTDIR ends up inside the binary via -DFONTDIR='$(FONTDIR)', i.e. the
        # Makefile expects the make variable itself to carry the double quotes.
        fontdir = os.path.join(self.package_folder, "share", "dcled")

        return (
            f'make CC="{cc}"'
            f' FONTDIR=\'"{fontdir}"\''
            f' LIBUSB_CFLAGS="-I{usb_include}"'
            f' LIBUSB_LIBS="-L{usb_libdir} -lusb-1.0 -Wl,-rpath,{usb_libdir}"'
            f" all"
        )

    # ── upstream verification (README EXAMPLES + --test) ─────────────────────
    def _run_env(self):
        """Run environment for the freshly built binaries.

        The binaries carry an rpath to the libusb package folder; exporting the
        same directory through LD_LIBRARY_PATH as well keeps the checks working
        even where -Wl,-rpath is ignored.
        """
        env = dict(os.environ)
        libusb = self.dependencies["libusb"]
        libdir = os.path.join(libusb.package_folder, libusb.cpp_info.libdirs[0])
        old = env.get("LD_LIBRARY_PATH")
        env["LD_LIBRARY_PATH"] = libdir + (os.pathsep + old if old else "")
        return env

    def _run_check(self, argv, expect=None, stdin=None):
        """Run one documented upstream command; return (ok, detail).

        ok is True when the process exited cleanly with `expect` present in its
        output, or — for the endless demonstration modes — when it survived the
        whole timeout window instead of dying early.
        """
        kwargs = {
            "cwd": self.source_folder,
            "env": self._run_env(),
            "stdout": subprocess.PIPE,
            "stderr": subprocess.STDOUT,
        }
        if stdin is not None:
            kwargs["input"] = stdin.encode()
        try:
            proc = subprocess.run(argv, timeout=self._CHECK_TIMEOUT, **kwargs)
        except subprocess.TimeoutExpired as exc:
            out = (exc.stdout or b"").decode("utf-8", "replace")
            if expect is not None and expect not in out:
                return False, f"timeout, missing {expect!r} in {out[:120]!r}"
            return True, f"endless mode survived {self._CHECK_TIMEOUT}s ({len(out)}B)"

        out = proc.stdout.decode("utf-8", "replace")
        if proc.returncode != 0:
            hint = " (SIGSEGV)" if proc.returncode in (139, -11) else ""
            return False, f"exit {proc.returncode}{hint}, out={out[:120]!r}"
        if expect is not None and expect not in out:
            return False, f"missing {expect!r} in {out[:120]!r}"
        return True, f"exit 0 ({len(out)}B)"

    def _upstream_examples(self):
        """The upstream README "EXAMPLES" list, plus the -h banner and the
        cpuload helper that the same Makefile target produces.

        Every command runs device-free with -n: the message board is not
        attached on the build host and upstream keeps all code paths working in
        that mode on purpose (the frames are printed instead of being sent).
        """
        dcled = os.path.join(self.source_folder, "dcled")
        cpuload = os.path.join(self.source_folder, "cpuload")
        f1 = os.path.join(self.source_folder, "check-files", "f1")
        f2 = os.path.join(self.source_folder, "check-files", "f2")
        return [
            # README EXAMPLES #1 — built-in test pattern (endless)
            ("dcled -t",
             [dcled, "-n", "-e", "-t"], "Version is 2.2", None),
            # #2 — message on the command line
            ("dcled -m 'Hello World!'",
             [dcled, "-n", "-e", "-m", "Hello World!"], "Hello World!", None),
            # #3 — message on stdin
            ("echo 'Hello World!' | dcled",
             [dcled, "-n", "-e"], "Hello World!", "Hello World!\n"),
            # #4 — messages read from files
            ("dcled f1 f2",
             [dcled, "-n", "-e", f1, f2], "Hello", None),
            # #5 — clock mode (endless)
            ("dcled --clock --repeat",
             [dcled, "-n", "-e", "--clock", "--repeat"], None, None),
            # #6 / #7 — preamble called by name and by number
            ("dcled -p static -m 'Hello World'",
             [dcled, "-n", "-e", "-p", "static", "-m", "Hello World"], "Hello World", None),
            ("dcled -p 2 -m 'Hello World'",
             [dcled, "-n", "-e", "-p", "2", "-m", "Hello World"], "Hello World", None),
            # #8 — demo of all preamble types (endless)
            ("dcled --test",
             [dcled, "-n", "-e", "--test"], "Version is 2.2", None),
            # #9 — `tail -f syslog | dcled -e -p static`, the piped-monitor shape
            ("syslog pipe | dcled -e -p static",
             [dcled, "-n", "-e", "-p", "static"], "syslog line", "syslog line\n"),
            # usage banner
            ("dcled -h",
             [dcled, "-h"], "Usage", None),
            # helper binary produced by the same `all` target (endless)
            ("cpuload 0.2",
             [cpuload, "0.2"], None, None),
        ]

    def _run_upstream_checks(self):
        files_dir = os.path.join(self.source_folder, "check-files")
        os.makedirs(files_dir, exist_ok=True)
        with open(os.path.join(files_dir, "f1"), "w", encoding="utf-8") as handle:
            handle.write("Hello\n")
        with open(os.path.join(files_dir, "f2"), "w", encoding="utf-8") as handle:
            handle.write("Hello\n")

        failed = []
        for name, argv, expect, stdin in self._upstream_examples():
            ok, detail = self._run_check(argv, expect=expect, stdin=stdin)
            self.output.info(f"  upstream check [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
            if not ok:
                failed.append(f"{name} -> {detail}")

        upstream = {
            "status": "failed" if failed else "passed",
            "framework": "upstream-readme-examples",
            "command": "dcled -n <README EXAMPLES> (+ --test, -h, cpuload)",
            "discovered": len(self._upstream_examples()),
            "executed": len(self._upstream_examples()),
            "passed": len(self._upstream_examples()) - len(failed),
            "failed": len(failed),
            "skipped": 0,
        }
        self.output.info(
            "HMBS_UPSTREAM_TEST_RESULT=" + json.dumps(upstream, ensure_ascii=False)
        )
        if failed:
            raise ConanException(
                "Upstream README EXAMPLES failed: " + "; ".join(failed)
            )

    # ── package ──────────────────────────────────────────────────────────────
    def package(self):
        # `make install` is deliberately NOT used: it writes the absolute
        # upstream defaults (INSTALLDIR=/usr/local/bin, FONTDIR=/usr/local/...)
        # straight into the build machine. Both binaries built by the `all`
        # target are packaged instead — upstream installs only dcled, but
        # cpuload is the documented companion for the tachometer mode.
        src = self.source_folder
        copy(self, "dcled", src, os.path.join(self.package_folder, "bin"))
        copy(self, "cpuload", src, os.path.join(self.package_folder, "bin"))
        copy(self, "*.dlf", os.path.join(src, "fonts"),
             os.path.join(self.package_folder, "share", "dcled"))
        copy(self, "40-dcled.rules", src, os.path.join(self.package_folder, "share", "dcled"))
        copy(self, "README", src, os.path.join(self.package_folder, "share", "doc", "dcled"))

    def package_info(self):
        # dcled/cpuload are CLI tools — expose bindirs and the font data dir
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["share/dcled"]
