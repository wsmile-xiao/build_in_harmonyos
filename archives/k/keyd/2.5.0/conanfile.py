#!/usr/bin/env python3
"""Conan recipe for keyd 2.5.0 (upstream plain-Makefile C build, no third-party deps)."""

import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.files import (
    apply_conandata_patches,
    export_conandata_patches,
    get,
    copy,
    save,
    chmod,
)
from conan.tools.layout import basic_layout


class KeydConan(ConanFile):
    name = "keyd"
    version = "2.5.0"
    description = (
        "System-wide keyboard remapping daemon that works through kernel level "
        "input primitives (evdev read side, uinput write side) instead of XKB."
    )
    license = "MIT"
    homepage = "https://github.com/rvaiya/keyd"
    url = "https://github.com/rvaiya/keyd"
    topics = ("keyboard", "remap", "daemon", "evdev", "uinput", "tool")
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)
        # Upstream has no out-of-tree build support: the Makefile globs src/*.c.
        self.folders.build = "."

    def source(self):
        get(self, **self.conan_data["sources"][0], strip_root=True)

    def _cc(self):
        """R33: never rely on $CC being exported -- take the profile's compiler.

        The CI profile pins it to /data/service/hnp/bin/clang; reachability of
        that absolute path varies with the device
        state (in the pre-reboot session here stat() raised Permission denied and
        make died with "Error 2"; after a reboot the same path is visible and is
        in fact what the profile resolves to), so the configured value is verified
        before being trusted and a PATH lookup is used otherwise.
        """
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        home_clang = os.path.expanduser("~/usr/local/bin/clang")
        for cand in ((compilers or {}).get("c"), shutil.which("clang"),
                     shutil.which("cc"), home_clang):
            if cand and os.access(cand, os.X_OK):
                return cand
        raise ConanException("no executable C compiler (checked profile conf, "
                             "PATH clang/cc, ~/usr/local/bin/clang)")

    def _posix_shell(self):
        """R5: /system/bin/sh cannot exec ELF binaries here and the CI profile's
        CONFIG_SHELL (/data/service/hnp/bin/bash) is not reliably visible from a
        device session, so every candidate is probed with os.access() before being
        picked, and the winner is passed explicitly as argv[0] (the profile's
        [buildenv] is sourced last and would override any env var we exported)."""
        for cand in (os.environ.get("CONFIG_SHELL"), shutil.which("bash"),
                     "/data/service/hnp/bin/bash",
                     os.path.expanduser("~/usr/local/bin/bash"), "/bin/sh"):
            if cand and os.access(cand, os.X_OK):
                return cand
        raise ConanException("no executable shell for the upstream unit suite "
                             "(checked CONFIG_SHELL, PATH bash, hnp bash, "
                             "~/usr/local/bin/bash, /bin/sh)")

    def build(self):
        apply_conandata_patches(self)
        cc = self._cc()
        # The Makefile sets `platform=$(shell uname -s)`, which returns "HarmonyOS"
        # here, so the non-Linux branch appends `-linotify`. OHOS keeps the inotify
        # syscalls inside musl libc and ships no libinotify, so that link line
        # cannot resolve. A command-line assignment overrides the makefile `=`, and
        # the Linux branch differs only by leaving COMPAT_FILES empty as well.
        self.run(f'make -j1 platform=Linux CC="{cc}"')
        self._run_upstream_unit_suite()

    def _run_upstream_unit_suite(self):
        """`t/*.t` are 86 DSL cases driven in-process by t/test-io.c.

        They need neither root nor /dev access, so they run for real here.
        One process per case: run_test() calls exit(-1) on the first mismatch,
        which would silently truncate the suite after case #1.
        """
        src = self.source_folder
        test_bin = os.path.join(src, "bin", "test-io")
        test_conf = os.path.join(src, "t", "test.conf")
        units = " ".join(
            os.path.join(src, "src", name)
            for name in (
                "keyboard.c",
                "string.c",
                "macro.c",
                "config.c",
                "log.c",
                "ini.c",
                "keys.c",
                "unicode.c",
            )
        )
        # Mirrors the upstream `test-io` target, including its bare -DDATA_DIR=.
        self.run(
            f'"{self._cc()}" -DDATA_DIR= -o "{test_bin}" '
            f'{os.path.join(src, "t", "test-io.c")} {units}'
        )
        cases = sorted(glob.glob(os.path.join(src, "t", "*.t")))
        if not cases:
            raise ConanException("keyd: no upstream t/*.t cases found after get()")

        lines = ["#!/bin/sh", "set -u", 'p=0', 'f=0', 'ff=""']
        for case in cases:
            lines.append(
                '"{tb}" "{conf}" "{case}" >/dev/null 2>&1 && p=$((p+1)) '
                '|| {{ f=$((f+1)); ff="$ff {name}"; }}'.format(
                    tb=test_bin, conf=test_conf, case=case, name=os.path.basename(case)
                )
            )
        lines += [
            'echo "[upstream unit suite] registered=%s passed=$p failed=$f"' % len(cases),
            'if [ "$f" -ne 0 ]; then echo "[upstream unit suite] FAILED:$ff"; exit 1; fi',
        ]
        runner = os.path.join(self.build_folder, "run-keyd-unit-suite.sh")
        save(self, runner, "\n".join(lines) + "\n")
        chmod(self, runner, 0o755)
        self.run(f'"{self._posix_shell()}" "{runner}"')

    def package(self):
        pkg = self.package_folder
        copy(self, "keyd", src=os.path.join(self.build_folder, "bin"),
             dst=os.path.join(pkg, "bin"))
        # Upstream `make install` is not usable in an unprivileged build: `Makefile:72`
        # runs `groupadd keyd` and the default PREFIX /usr/local is not writable without
        # root. The device does ship `install` (/bin/install, toybox 0.8.12; probed with
        # -D/-m/-d -> rc=0), so this is a root/permission case, not a missing-tool one.
        # Each install rule is therefore reproduced by hand below.
        copy(self, "keyd-application-mapper",
             src=os.path.join(self.source_folder, "scripts"),
             dst=os.path.join(pkg, "bin"))
        chmod(self, os.path.join(pkg, "bin", "keyd"), 0o755)
        chmod(self, os.path.join(pkg, "bin", "keyd-application-mapper"), 0o755)

        copy(self, "*", src=os.path.join(self.source_folder, "layouts"),
             dst=os.path.join(pkg, "share", "keyd", "layouts"))
        copy(self, "keyd.compose", src=os.path.join(self.source_folder, "data"),
             dst=os.path.join(pkg, "share", "keyd"))
        copy(self, "*.md", src=os.path.join(self.source_folder, "docs"),
             dst=os.path.join(pkg, "share", "doc", "keyd"))
        copy(self, "*", src=os.path.join(self.source_folder, "examples"),
             dst=os.path.join(pkg, "share", "doc", "keyd", "examples"))
        copy(self, "*.1.gz", src=os.path.join(self.source_folder, "data"),
             dst=os.path.join(pkg, "share", "man", "man1"))
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(pkg, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
