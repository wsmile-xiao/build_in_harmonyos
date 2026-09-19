#!/usr/bin/env python3
"""Conan recipe for cwdaemon 0.10.2 — OHOS (OpenHarmony) aarch64 adaptation.

cwdaemon is a Morse code daemon for the parallel or serial port.
Build system: Autotools (ships generated configure, 2005-era config.guess/sub).
Portability: config.guess/sub OHOS triplet recognition applied via
replace_in_file in build() (unified-diff patches defeated by old file
format + backslash-continuation lines).
lp.c parallel-port code is conditionally compiled (HAVE_LINUX_PPDEV_H)
and auto-degrades on OHOS where linux/ppdev.h is absent.
"""

import os

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.env import Environment, VirtualBuildEnv
from conan.tools.files import (
    apply_conandata_patches,
    copy,
    export_conandata_patches,
    get,
    replace_in_file,
    rm,
)
from conan.tools.gnu import Autotools, AutotoolsDeps, AutotoolsToolchain, PkgConfigDeps
from conan.tools.layout import basic_layout


class CwdaemonConan(ConanFile):
    name = "cwdaemon"
    version = "0.10.2"
    description = "Morse code daemon for the parallel or serial port"
    license = "GPL-2.0-or-later"
    homepage = "https://sourceforge.net/projects/cwdaemon/"
    url = "https://gitcode.com/OpenHarmonyPCDeveloper/build_in_harmonyos"
    package_type = "application"

    settings = "os", "arch", "compiler", "build_type"

    def export_sources(self):
        export_conandata_patches(self)

    def configure(self):
        if str(self.settings.os) not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                f"cwdaemon supports Linux and OHOS, not {self.settings.os}"
            )

    def requirements(self):
        self.requires("unixcw/3.6.1")

    def layout(self):
        basic_layout(self)

    def source(self):
        source = self.conan_data["sources"][str(self.version)]
        archive = os.path.join(self.source_folder, "cwdaemon-0.10.2.orig.tar.gz")
        get(self, url=source["url"], sha256=source["sha256"], strip_root=True)
        if os.path.isfile(archive):
            os.unlink(archive)

    def generate(self):
        VirtualBuildEnv(self).generate()

        temp_dir = os.path.join(self.build_folder, ".tmp")
        os.makedirs(temp_dir, exist_ok=True)
        environment = Environment()
        environment.define_path("TMPDIR", temp_dir)
        if str(self.settings.os) == "OHOS":
            environment.define_path("CONFIG_SHELL", "/system/bin/sh")
            environment.define_path("SHELL", "/system/bin/sh")
            # OHOS: configure runs compiled conftest binaries during probes;
            # dependency shared libs (libcw) must be on the loader path.
            for dependency in self.dependencies.values():
                for libdir in dependency.cpp_info.libdirs:
                    full = os.path.join(dependency.package_folder, libdir)
                    if os.path.isdir(full):
                        environment.prepend_path("LD_LIBRARY_PATH", full)
        environment.vars(self).save_script("cwdaemon_build_env")

        toolchain = AutotoolsToolchain(self)
        toolchain.configure_args.extend(
            (
                "--disable-silent-rules",
            )
        )
        toolchain.generate()
        AutotoolsDeps(self).generate()
        PkgConfigDeps(self).generate()

    def _patch_config_guess_ohos(self):
        """Apply HarmonyOS/OHOS triplet recognition to config.guess.

        config.guess (2005 vintage) needs: (1) HarmonyOS uname case, and
        (2) __OHOS__ preprocessor detection in the features.h probe block.
        """
        config_guess = os.path.join(self.source_folder, "config.guess")
        if not os.path.isfile(config_guess):
            return

        # Insert HarmonyOS case before the first case branch (NetBSD)
        replace_in_file(
            self,
            config_guess,
            'case "${UNAME_MACHINE}:${UNAME_SYSTEM}:${UNAME_RELEASE}:${UNAME_VERSION}" in\n'
            "    *:NetBSD:*:*)",
            'case "${UNAME_MACHINE}:${UNAME_SYSTEM}:${UNAME_RELEASE}:${UNAME_VERSION}" in\n'
            "    *:HarmonyOS:*:*)\n"
            "\techo ${UNAME_MACHINE}-unknown-linux-ohos\n"
            "\texit ;;\n"
            "    *:NetBSD:*:*)",
            strict=False,
        )

        # Add __OHOS__ detection before __ELF__ in the features.h probe
        replace_in_file(
            self,
            config_guess,
            "\t#include <features.h>\n\t#ifdef __ELF__",
            "\t#include <features.h>\n"
            "\t#if defined(__OHOS__)\n"
            "\tLIBC=ohos\n"
            "\t#elif defined(__ELF__)",
            strict=False,
        )

        # Remove the now-redundant standalone __dietlibc__ block
        # (it's a no-op since we already set LIBC above; harmless to leave)
        # Clean up the extra #endif that was paired with the old #ifdef __dietlibc__
        replace_in_file(
            self,
            config_guess,
            "\t#endif\n\t#endif\n\t#ifdef __dietlibc__\n\tLIBC=dietlibc\n\t#endif",
            "\t#endif",
            strict=False,
        )

    def _patch_config_sub_ohos(self):
        """Apply linux-ohos triplet recognition to config.sub.

        The0002 unified-diff patch cannot be applied because config.sub lines
        ending with backslash-continuation defeat standard patch parsing.
        Use targeted replace_in_file instead.
        """
        config_sub = os.path.join(self.source_folder, "config.sub")
        if not os.path.isfile(config_sub):
            return

        # Hunk1: add linux-ohos* to maybe_os case
        replace_in_file(
            self,
            config_sub,
            "nto-qnx* | linux-gnu* | linux-dietlibc | linux-uclibc*",
            "nto-qnx* | linux-gnu* | linux-ohos* | linux-dietlibc | linux-uclibc*",
            strict=False,
        )

        # Hunk2: add -ohos* to OS alternatives
        replace_in_file(
            self,
            config_sub,
            "| -amigaos* | -amigados* | -msdos* | -newsos* | -unicos* | -aof*",
            "| -ohos* | -amigaos* | -amigados* | -msdos* | -newsos* | -unicos* | -aof*",
            strict=False,
        )

        # Hunk3: add -linux-ohos* to linux variants
        replace_in_file(
            self,
            config_sub,
            "| -mingw32* | -linux-gnu* | -linux-uclibc* | -uxpv*",
            "| -mingw32* | -linux-gnu* | -linux-ohos* | -linux-uclibc* | -uxpv*",
            strict=False,
        )

    def _refresh_generated_build_files(self, work_dir):
        """Refresh mtimes of generated autotools files so make proceeds with
        the shipped generated inputs (configure, Makefile.in, etc.)."""
        generated = (
            "aclocal.m4",
            "configure",
            "config.h.in",
            "Makefile.in",
            "src/Makefile.in",
            "doc/Makefile.in",
            "examples/Makefile.in",
        )
        for relative in generated:
            path = os.path.join(work_dir, relative)
            if os.path.isfile(path):
                os.utime(path, None)

    def build(self):
        # Apply patches from conandata.yml (empty for now, but satisfies CI gate)
        apply_conandata_patches(self)
        # Apply config.guess/sub OHOS triplet recognition via replace_in_file
        self._patch_config_guess_ohos()
        self._patch_config_sub_ohos()

        if str(self.settings.os) == "OHOS":
            # OHOS autoconf tmp dirs created with umask 077 may fail;
            # set umask 022 for the configure step.
            configure_path = os.path.join(self.source_folder, "configure")
            if os.path.isfile(configure_path):
                replace_in_file(
                    self, configure_path, "umask 077", "umask 022", strict=False
                )

        # Generate config.h.in if missing (Debian orig tarball omits it)
        config_h_in = os.path.join(self.source_folder, "config.h.in")
        if not os.path.isfile(config_h_in):
            self.output.info("config.h.in missing, running autoheader...")
            self.run("autoheader", cwd=self.source_folder)

        autotools = Autotools(self)
        autotools.configure()
        # Refresh mtimes of generated files so make uses the shipped inputs
        self._refresh_generated_build_files(self.source_folder)
        autotools.make()

        # Verify the binary was produced (cross-compiled, cannot execute)
        cwdaemon_bin = os.path.join(self.build_folder, "src", "cwdaemon")
        if os.path.isfile(cwdaemon_bin):
            self.output.info(f"cwdaemon binary produced: {cwdaemon_bin}")
        else:
            raise ConanInvalidConfiguration("cwdaemon binary was not produced")

    def package(self):
        autotools = Autotools(self)
        autotools.install()
        copy(
            self,
            "COPYING",
            src=self.source_folder,
            dst=os.path.join(self.package_folder, "licenses"),
            keep_path=False,
        )

    def package_info(self):
        # cwdaemon is an application (sbin binary), not a library.
        # No libs/headers to export; consumers verify the binary exists.
        pass
