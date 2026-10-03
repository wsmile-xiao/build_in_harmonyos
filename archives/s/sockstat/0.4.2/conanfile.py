#!/usr/bin/env python3
"""Conan recipe for sockstat 0.4.2 -- detailed open-connection viewer for HarmonyOS PC.

sockstat reads /proc/net/{tcp,udp,raw,tcp6,udp6,raw6,unix} and correlates the
inodes with /proc/<pid>/fd to print one row per open socket (USER / PROCESS /
PID / PROTO / SOURCE ADDRESS / FOREIGN ADDRESS / STATE).  Upstream ships one
``sockstat.c`` plus a 16-line hand-written Makefile with no configure step and
no test suite.

OHOS notes
----------
* Upstream compiles and links in a single ``$(CC) $(CFLAGS) -o $@ $(LDFLAGS)``
  step, so the link mode travels in CFLAGS; command-line variables override the
  Makefile.  The compiler comes from the profile's
  ``tools.build:compiler_executables`` (R33), never a bare ``${CC}``.
* ``-Werror=implicit-function-declaration`` is deliberate: the source is C89
  flavoured and would otherwise build fine while silently truncating 64-bit
  return values if musl ever hid a POSIX declaration behind a feature macro
  (the tal/1.9 class of regression, which compiles clean and dies with SIGSEGV).
* Zero patches.  Upstream builds clean against the OHOS sysroot: ``<err.h>``,
  ``err``/``errx``, ``inet_lnaof`` and ``inet_ntop`` are all provided by the
  OHOS musl headers.  Keeping the recipe patch-free keeps the pinned sha256 an
  exact copy of upstream v0.4.2.
* The two upstream defects found while porting (``-G`` NULL dereference and the
  ``fclose(NULL)`` in ``get_program_name``) reproduce on plain Linux too, so
  they are *not* platform issues: they are recorded in notes.md and asserted as
  known-defect evidence in test_package/test.sh instead of being patched here.
"""
import os
import shlex

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import copy, get
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class SockstatConan(ConanFile):
    name = "sockstat"
    version = "0.4.2"
    description = (
        "Detailed viewer of open network connections: correlates /proc/net/* "
        "socket tables with /proc/<pid>/fd (FreeBSD sockstat for Linux)"
    )
    license = "BSD-3-Clause"
    homepage = "https://codeberg.org/alteholz/sockstat"
    url = "https://codeberg.org/alteholz/sockstat"
    topics = ("network", "sockets", "diagnostics", "procfs")

    package_type = "application"
    settings = "os", "arch", "compiler", "build_type"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"sockstat is validated on Linux/OHOS only, not {self.settings.os}")

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def _cflags(self):
        """Optimisation level follows build_type; the -Werror is unconditional.

        Upstream Makefile has no configure step, so the flags can only travel
        through the make command line.
        """
        opt = {
            "Release": "-O2",
            "RelWithDebInfo": "-O2 -g",
            "MinSizeRel": "-Os",
            "Debug": "-O0 -g",
        }.get(str(self.settings.build_type), "-O2")
        return f"{opt} -Werror=implicit-function-declaration"

    def build(self):
        compilers = self.conf.get("tools.build:compiler_executables",
                                  default={}, check_type=dict)
        cc = compilers.get("c", "clang")
        self.run(shlex.join(["make", "-j1", f"CC={cc}",
                             f"CFLAGS={self._cflags()}"]),
                 cwd=self.source_folder, env="conanbuild")

    def package(self):
        copy(self, "sockstat", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"), keep_path=False)
        copy(self, "sockstat.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"),
             keep_path=False)
        copy(self, "LICENSE", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"), keep_path=False)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
