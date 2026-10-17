#!/usr/bin/env python3
"""Conan recipe — inoticoming 0.2.3 (Autotools: configure + make).

inoticoming is a daemon that watches an incoming directory through the
Linux inotify framework and triggers actions as soon as files with a
matching name (prefix / suffix / regular expression) are placed there.
Typical use: watch the upload directory of a Debian archive and call
reprepro for every new .changes file.

HarmonyOS notes
---------------
* E011 (HMDFS + autoconf), fixed by patches/0001-configure.patch: HMDFS
  maps freshly created directories to uid 20001006 and keeps the setgid
  bit, so autoconf's `(umask 077 && mktemp -d "./confXXXXXX")` temp
  directory ends up as drwx--S--- and is *not* writable by the build user.
  config.status then dies with
  "can't create ./confXXXXXX/subs1.awk: Permission denied".
  The patch relaxes `umask 077` to `umask 022` in the configure script
  shipped in the upstream tarball, which is what generates config.status.
* `sys/inotify.h` and the inotify syscalls are provided by HarmonyOS libc;
  the kernel side is exercised for real by test_package (see
  test_package/test_ohos_inoticoming.py).
* The daemon path uses syslog(3) when it detaches; OHOS has no syslogd by
  default, so the tests exercise the foreground mode (--foreground) for the
  event/pid/chdir contracts and cover the daemonized production mode with
  --logfile.
* Upstream ships no test suite.  `make check` (automake default target)
  exists but has no registered TESTS; test_package covers the real
  behaviour instead (see test_package/MANIFEST.yml for the audit).
"""
import os
import stat

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class InoticomingConan(ConanFile):
    name = "inoticoming"
    version = "0.2.3"
    description = ("Daemon that watches an incoming directory through inotify "
                   "and triggers actions when matching files arrive")
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/inoticoming"
    url = "https://sources.debian.org/src/inoticoming/"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: platform checks must accept both Linux and OHOS.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "inoticoming requires a Linux/OHOS inotify target, got %s"
                % self.settings.os
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        # Native build: only --prefix (from AutotoolsToolchain) is passed,
        # no --build/--host/--target cross-compilation arguments.
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        apply_conandata_patches(self)

        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])
        # Real upstream test entry point: automake's `check` target.
        # Upstream registers no TESTS, so this is a no-op that proves the
        # entry point exists (0 upstream test cases; see MANIFEST.yml).
        # -j1 as well: parallel make on OHOS trips the jobserver mkfifo
        # warning (E074).
        autotools.make(target="check", args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        # -j1 keeps the E074 jobserver warning away; Autotools.install()
        # still prepends its own DESTDIR because "-j1" contains no DESTDIR=.
        autotools.install(args=["-j1"])
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        binary = os.path.join(self.package_folder, "bin", "inoticoming")
        if os.path.isfile(binary):
            os.chmod(binary, os.stat(binary).st_mode | stat.S_IXUSR | stat.S_IXGRP)

    def package_info(self):
        # Pure CLI tool package: no headers, no libraries.
        self.cpp_info.libs = []
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
        self.cpp_info.bindirs = ["bin"]
        self.runenv_info.prepend_path(
            "PATH", os.path.join(self.package_folder, "bin")
        )
