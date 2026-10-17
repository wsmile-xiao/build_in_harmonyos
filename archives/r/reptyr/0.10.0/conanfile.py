#!/usr/bin/env python3
"""Conan recipe for reptyr 0.10.0 — reattach a running program to a new terminal.

reptyr is a single-binary C tool built by a plain Makefile.  It uses ptrace(2)
to take over a process connected to another terminal and re-attach it to a pty
created by reptyr itself.  The Makefile selects the platform backend by
`uname -s` (Linux or FreeBSD) and the sources include <linux/...> UAPI headers
through platform/platform.h.

OHOS adaptations (patches in conandata.yml):
  - Makefile: `uname -s` returns "HarmonyOS" on OHOS, so the Linux branch was
    skipped entirely; the Linux backend objects were never compiled and the
    final link failed with undefined platform symbols.  Treat HarmonyOS like
    Linux (same backend, same UAPI headers).  Same family as knowledge E007
    (config.guess does not know HarmonyOS) but for a hand-written Makefile.
  - platform/linux/linux.h: on musl-based systems (such as OHOS)
    <linux/net.h> pulls in <linux/socket.h>, which defines
    struct sockaddr_storage, and the later <sys/socket.h> defines the same
    struct again — clang -Werror reports "redefinition of 'sockaddr_storage'".
    The kernel-side struct is renamed while the linux headers are included;
    glibc builds are not affected.  This is knowledge entry E091 (same class,
    glibc-guarded form as used by accel-ppp).
Neither patch injects platform macros (R8/PF5).

The Makefile's `install` target calls install(1), which is absent on OHOS, so
package() copies the artifacts explicitly (bin/reptyr, en/fr man pages, bash
completion, license).

Upstream tests: test/basic.py and test/tty-steal.py (2 programs; pexpect,
python-prctl optional).  They need PTRACE_ATTACH, which the OHOS kernel
refuses with EPERM for unprivileged processes on this device (seccomp-filtered;
PTRACE_TRACEME and process_vm_readv fail the same way).  The suite was executed
on the device and both programs stop at that documented platform boundary; the
test_package assertions cover everything that is available (pty allocation,
argument and pid validation, attach error reporting).  Evidence per item in
reports/test-report.md.
"""
import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, copy, export_conandata_patches, get, rename
from conan.tools.layout import basic_layout

required_conan_version = ">=2.0"


class ReptyrConan(ConanFile):
    name = "reptyr"
    version = "0.10.0"
    description = (
        "Reattach a running process to a new terminal (steals a process from "
        "its current controlling tty using ptrace)"
    )
    license = "MIT"
    homepage = "https://github.com/nelhage/reptyr"
    url = "https://github.com/nelhage/reptyr"
    topics = ("reptyr", "pty", "ptrace", "terminal", "cli", "utility")
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def validate(self):
        # R32: check the OHOS family, not `== "Linux"`.
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "reptyr requires a Linux-like target (Linux or OHOS), not {0}".format(
                    self.settings.os
                )
            )

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)
        apply_conandata_patches(self)

    def build(self):
        # R33: the compiler comes from the Conan conf (never from shell env
        # vars); the upstream Makefile adds its own -MD -Wall -Werror
        # -D_GNU_SOURCE -g flags.  R9: single job (HMDFS jobserver FIFO).
        compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict)
        cc = compilers.get("c", "clang") if compilers else "clang"
        self.run("make CC={0} -j1".format(cc), cwd=self.source_folder)

    def package(self):
        copy(self, "reptyr", src=self.source_folder,
             dst=os.path.join(self.package_folder, "bin"))
        copy(self, "reptyr.1", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "man", "man1"))
        fr_man = os.path.join(self.package_folder, "share", "man", "fr", "man1")
        copy(self, "reptyr.fr.1", src=self.source_folder, dst=fr_man)
        rename(self,
               os.path.join(fr_man, "reptyr.fr.1"),
               os.path.join(fr_man, "reptyr.1"))
        copy(self, "reptyr.bash", src=self.source_folder,
             dst=os.path.join(self.package_folder, "share", "bash-completion", "completions"))
        copy(self, "COPYING", src=self.source_folder,
             dst=os.path.join(self.package_folder, "licenses"))

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libdirs = []
        self.cpp_info.includedirs = []
        self.runenv_info.prepend_path("PATH", os.path.join(self.package_folder, "bin"))
