#!/usr/bin/env python3
"""Conan recipe for esekeyd 1.2.7 — ESE Key Daemon.

esekeyd taps /dev/input/event<N> and runs shell commands configured for
multimedia/function keys. It ships three programs:

- esekeyd  (upstream sbin) — the daemon
- keytest  — prints key names for events read from an input device file
- learnkeys — writes a commented config skeleton from observed keys

Upstream: https://github.com/burghardt/esekeyd (canonical releases on
SourceForge; the archive used here is the byte-identical Debian orig
tarball from the Ubuntu pool, see conandata.yml).

OHOS portability notes
----------------------
1. src/Makefile.am carries a generated-source rule
   ``parser.c: mkparser /usr/include/linux/input.h`` which (a) requires
   the *build* machine to have /usr/include/linux/input.h and (b) is
   timestamp-sensitive: any modern kernel header is newer than the 2010
   release tarball, so make would always try to re-run the host tool
   mkparser. The tarball already ships a pre-generated parser.c, and the
   configure.ac has no AC_CANONICAL_HOST support for cross setups, so
   patch 0001 removes the regeneration rule entirely.
2. The custom ``mkparser`` rule uses ``$(mkparser_SOURCES)`` as the
   compile input, which breaks under VPATH builds (the compiler does not
   resolve VPATH; only GNU make automatic variables do). Patch 0001
   changes it to ``$<``. mkparser itself is only a noinst helper.
3. configure.ac has no AC_CANONICAL_HOST, so no config.guess/config.sub
   is involved and the classic "cannot guess system type" failure (E007)
   does not apply. The generated configure runs fine under bash.
4. Only libc + pthread mutexes are used; musl provides both, no extra
   link flags are needed (pthread symbols live in musl libc).
5. linux/input.h is required unconditionally by esekey.h; the OHOS
   sysroot ships it (verified against DevEco openharmony sysroot).
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
)
from conan.tools.gnu import AutotoolsToolchain
from conan.tools.layout import basic_layout


class EsekeydConan(ConanFile):
    name = "esekeyd"
    version = "1.2.7"
    description = (
        "ESE Key Daemon: multimedia keyboard daemon that taps "
        "/dev/input event devices and runs configured shell commands; "
        "ships keytest and learnkeys helpers"
    )
    license = "GPL-2.0-or-later"
    homepage = "https://github.com/burghardt/esekeyd"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"

    package_type = "application"

    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"esekeyd is a Linux input-event daemon, "
                f"unsupported os: {self.settings.os}"
            )

    def export_sources(self):
        export_conandata_patches(self)

    def requirements(self):
        # esekeyd depends only on libc (musl) and the kernel UAPI header
        # linux/input.h shipped in the sysroot; no third-party deps.
        pass

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True, verify=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        tc.generate()

    def build(self):
        # HMDFS workaround (see rsyslog recipe): default umask may create
        # 640 files later steps cannot read.
        if str(self.settings.os) in ("Linux", "OHOS"):
            os.umask(0o022)
        apply_conandata_patches(self)
        # basic_layout: self.build_folder is the generators folder
        # (…/b/build-release) while the configure script copied from the
        # source cache lives one level up — locate it explicitly.
        conf_dir = None
        for cand in (self.build_folder, self.source_folder):
            if os.path.isfile(os.path.join(cand, "configure")):
                conf_dir = cand
                break
        if conf_dir is None:
            raise ConanInvalidConfiguration("configure script not found")
        # HMDFS ships no executable bit for scripts (E087): a direct
        # exec of ./configure fails with Permission denied (error 126),
        # so run it through the profile's CONFIG_SHELL explicitly
        # (same approach as the rotix recipe, R5).
        config_shell = os.environ.get("CONFIG_SHELL", "bash")
        prefix = "/"  # DESTDIR-style install, Conan convention
        configure_args = " ".join(
            [
                f"--prefix={prefix}",
                f"--bindir={prefix}/bin",
                f"--sbindir={prefix}/bin",  # upstream sbin program -> bin/
                f"--libdir={prefix}/lib",
                f"--includedir={prefix}/include",
            ]
        )
        self.run(
            f"{config_shell} ./configure {configure_args}",
            cwd=conf_dir,
            env="conanbuild",
        )
        # -j1: tiny project; avoids FIFO/jobserver issues (E074).
        # mkparser (noinst helper) is linked but never executed: the
        # parser.c regeneration rule that would run it on the HMDFS
        # build tree is removed by patch 0001.
        self.run("make -j1", cwd=conf_dir, env="conanbuild")

    def package(self):
        conf_dir = None
        for cand in (self.build_folder, self.source_folder):
            if os.path.isfile(os.path.join(cand, "configure")):
                conf_dir = cand
                break
        if conf_dir is None:
            raise ConanInvalidConfiguration("configure script not found")
        self.run(
            f'make install DESTDIR="{self.package_folder}"',
            cwd=conf_dir,
            env="conanbuild",
        )
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )
        for prog in ("esekeyd", "keytest", "learnkeys"):
            path = os.path.join(self.package_folder, "bin", prog)
            if os.path.isfile(path):
                os.chmod(path, 0o755)

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
        self.cpp_info.libs = []
