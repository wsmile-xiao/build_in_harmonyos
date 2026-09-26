#!/usr/bin/env python3
"""Conan recipe — shmcat 1.10 (autotools)."""

import os
import shutil

from conan import ConanFile
from conan.errors import ConanException
from conan.tools.build import load_toolchain_args
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain
from conan.tools.layout import basic_layout


class ShmcatConan(ConanFile):
    name = "shmcat"
    version = "1.10"
    description = "shmcat — dump files, POSIX/System V shared memory segments and text to stdout, plus the ftok key helper"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/shmcat/"
    url = "https://sourceforge.net/projects/shmcat/"

    settings = "os", "compiler", "build_type", "arch"

    def export_sources(self):
        export_conandata_patches(self)

    def layout(self):
        basic_layout(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def _posix_shell(self):
        """R5: return a shell that is really executable in this domain.

        The CI profile exports CONFIG_SHELL=/data/service/hnp/bin/bash, but on some
        OHOS hosts that path is not executable for the build uid, and autoconf
        re-execs configure through $CONFIG_SHELL before it parses any argument -- so
        a "SHELL=..." configure argument cannot rescue it.
        """
        for cand in (os.environ.get("CONFIG_SHELL"), shutil.which("bash"),
                     "/data/service/hnp/bin/bash", "/bin/sh"):
            if cand and os.access(cand, os.X_OK):
                return cand
        raise ConanException("no executable shell for configure (checked CONFIG_SHELL, "
                             "PATH bash, /data/service/hnp/bin/bash, /bin/sh)")

    def generate(self):
        tc = AutotoolsToolchain(self)
        if self.settings.os in ("Linux", "OHOS"):
            tc.configure_args.append(f"SHELL={self._posix_shell()}")
            # The packaged config.guess knows nothing about HarmonyOS, so both
            # triplets are pinned by hand (config.sub does accept linux-ohos).
            tc.configure_args.extend(["--build=aarch64-unknown-linux-gnu",
                                      "--host=aarch64-unknown-linux-ohos"])
            # E544: the OHOS toolchain is LLVM-only, so a bare `ld` is not on PATH.
            # gettext's AC_LIB_PROG_LD aborts with "no acceptable ld found in $PATH"
            # even with --disable-nls; bind LD next to the profile's C compiler.
            cc = (self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}).get("c")
            ld = None
            for cand in (os.path.join(os.path.dirname(cc), "ld.lld") if cc else None,
                         shutil.which("ld.lld"), shutil.which("ld")):
                if cand and os.path.exists(cand):
                    ld = cand
                    break
            if ld:
                tc.configure_args.append(f"LD={ld}")
            else:
                self.output.warn("no ld/ld.lld found; configure will fail with 'no acceptable ld found'")
            self._shellfix = True
        # DRAFT-E580: the OHOS clang wrapper prepends -Wl,--code-sign (from
        # aarch64-unknown-linux-ohos.cfg) to every driver call, and AX_COMPILER_FLAGS'
        # -Werror turns "'linker' input unused" into a fatal error on compile-only
        # steps. -Qunused-arguments neutralises the injected flag only.
        if self.settings.os == "OHOS":
            tc.extra_cflags.append("-Qunused-arguments")
        # AM_GNU_GETTEXT([external]) would require libintl, which is not part of
        # the OHOS musl sysroot; the CLI needs no localization for validation.
        tc.configure_args.append("--disable-nls")
        # configure.ac gates the POSIX dumper on $enable_posix_shm (the check
        # blocks above use the misspelled $enable_posix-shm), so pin it explicitly.
        tc.configure_args.append("--enable-posix-shm")
        tc.generate()

    def _run(self, command):
        # E386 family: the profile's buildenv script is sourced *after* every
        # recipe-emitted one, so CONFIG_SHELL cannot be fixed from generate(); it has
        # to be dropped from the environment of the command that runs configure/make.
        sh = self._posix_shell()
        self.run(f'env -u CONFIG_SHELL SHELL="{sh}" {command}', env="conanbuild")

    def build(self):
        apply_conandata_patches(self)
        if getattr(self, "_shellfix", False):
            # Reuse the toolchain's assembled configure arguments instead of
            # Autotools.configure(), which execs the script through its shebang and
            # then lets autoconf re-exec it with the bogus $CONFIG_SHELL.
            args = load_toolchain_args(self.generators_folder)["configure_args"]
            self._run(f'"{self.source_folder}/configure" {args}')
            self._run("make -j1")
        else:
            autotools = Autotools(self)
            autotools.configure()
            autotools.make(args=["-j1"])

    def package(self):
        if getattr(self, "_shellfix", False):
            self._run(f'make install DESTDIR="{self.package_folder}"')
        else:
            Autotools(self).install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
