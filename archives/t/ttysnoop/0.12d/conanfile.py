#!/usr/bin/env python3
"""Conan recipe for ttysnoop 0.12d.

ttysnoop lets an administrator watch, and type into, a login session: the
server ``ttysnoops`` is started as the login program by getty/telnetd, runs
the real login program on a pseudo terminal and mirrors the session either to
a snoop tty named in snooptab or to a UNIX socket that the ``ttysnoop`` client
connects to after a password check.

Upstream ships three C files and a bare Makefile whose CC/CCOPTS/LIBS are
plain make variables, so the recipe drives that Makefile with command-line
assignments (R33: compiler and flags from the Conan conf, never from ${CC})
and installs the artifacts itself; the upstream ``install`` target writes to
/sbin and /usr/man.
"""
import os
import platform
import shlex
import shutil
import subprocess

from conan import ConanFile
from conan.errors import ConanException, ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.layout import basic_layout


class TtysnoopConan(ConanFile):
    name = "ttysnoop"
    version = "0.12d"
    description = (
        "Snoop on a login tty: mirror a terminal session to another tty or to "
        "a password-protected socket client."
    )
    license = "GPL-2.0-or-later"
    homepage = "https://tracker.debian.org/pkg/ttysnoop"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    topics = ("tty", "pty", "terminal", "snoop", "tool")

    # R38: command line tools, not a library
    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    _tools = ("ttysnoops", "ttysnoop")

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: never compare settings.os with "Linux" only.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"ttysnoop needs Linux pty/utmp semantics, got os={self.settings.os}"
            )

    def layout(self):
        basic_layout(self, src_folder="src")

    def source(self):
        get(self, **self.conan_data["sources"][self.version], strip_root=True)

    def build(self):
        apply_conandata_patches(self)
        compilers = self.conf.get(
            "tools.build:compiler_executables", default={}, check_type=dict
        )
        cc = (compilers or {}).get("c") or "cc"
        # Upstream CCOPTS is "-O2"; profile flags are appended.  crypt() lives
        # in libc on OHOS (libcrypt.a is an empty archive), so upstream's
        # -lcrypt links unchanged; no -lutil is needed.
        ccopts = ["-O2"] + self.conf.get("tools.build:cflags", default=[], check_type=list)
        libs = self.conf.get("tools.build:exelinkflags", default=[], check_type=list) + ["-lcrypt"]
        self.run(
            f"make -j1 CC={shlex.quote(cc)} CCOPTS={shlex.quote(' '.join(ccopts))} "
            f"LIBS={shlex.quote(' '.join(libs))} {' '.join(self._tools)}",
            cwd=self.source_folder,
        )
        # R51: upstream has no test suite (no test sources, no check target in
        # the Makefile); the behaviour is covered by test_package/.

    def package(self):
        bindir = os.path.join(self.package_folder, "bin")
        for tool in self._tools:
            copy(self, tool, self.source_folder, bindir)
            os.chmod(os.path.join(bindir, tool), 0o755)
        copy(self, "ttysnoop.8", self.source_folder,
             os.path.join(self.package_folder, "share", "man", "man8"))
        # Example configuration: /etc is read-only on OHOS, so an edited copy
        # is selected with TTYSNOOP_SNOOPTAB instead of /etc/snooptab.
        copy(self, "snooptab.dist", self.source_folder,
             os.path.join(self.package_folder, "res"))
        if self.settings.os == "OHOS":
            for tool in self._tools:
                self._sign_ohos_elf(os.path.join(bindir, tool))

    def _sign_ohos_elf(self, path):
        """OHOS only executes code-signed ELF files."""
        signer = shutil.which("binary-sign-tool") or "/data/service/hnp/bin/binary-sign-tool"
        if not os.path.isfile(signer):
            if platform.machine() in ("aarch64", "arm64"):
                raise ConanException("binary-sign-tool is required to package ttysnoop on OHOS")
            self.output.warning(
                f"binary-sign-tool not available on this {platform.machine()} build "
                f"machine: {os.path.basename(path)} is left unsigned"
            )
            return
        signed = path + ".signed"
        subprocess.run(
            [signer, "sign", "-inFile", path, "-outFile", signed, "-selfSign", "1"],
            check=True,
            timeout=120,
        )
        os.chmod(signed, 0o755)
        os.replace(signed, path)

    def package_info(self):
        self.cpp_info.libs = []
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.resdirs = ["res"]
        self.cpp_info.includedirs = []
        self.cpp_info.libdirs = []
