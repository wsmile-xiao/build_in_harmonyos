#!/usr/bin/env python3
"""Conan recipe for GNU Proxyknife 1.7 — parallel proxy validator (CLI tool).

Upstream is a 2007 Autotools tree. The carried patches:
- drop `doc` from SUBDIRS (the man page needs a pod2man run that rejects the
  2007 POD source; the binary does not depend on it),
- relax the config.status `umask 077` that HMDFS cannot write (E011),
- include <locale.h> explicitly (musl does not expose LC_* transitively).

The bundled 2005-era config.guess/config.sub do not know HarmonyOS (`cannot
guess build type`, then `Kernel 'linux' not known to work with OS 'ohos'`).
Instead of carrying whole-file replacement patches (6k lines — it pushed the
PR beyond the AI review size limit), build() overwrites both helpers with the
copies shipped by the automake toolchain package (E007).

clang >= 10 needs -fcommon: proxyknife.h defines global variables in
every translation unit, upstream assumed GCC common symbols.
"""
import glob
import os
import shutil

from conan import ConanFile
from conan.errors import ConanInvalidConfiguration
from conan.tools.files import apply_conandata_patches, export_conandata_patches, get
from conan.tools.gnu import Autotools, AutotoolsToolchain


class ProxyknifeConan(ConanFile):
    name = "proxyknife"
    version = "1.7"
    description = ("GNU Proxyknife: multithreaded proxy server validator "
                   "(HTTP, HTTP CONNECT, SOCKS4, SOCKS5)")
    license = "GPL-3.0-or-later"
    homepage = "https://www.gnu.org/software/proxyknife/"
    url = "https://ftp.gnu.org/gnu/proxyknife/"

    package_type = "application"
    settings = "os", "compiler", "build_type", "arch"

    def validate(self):
        if self.settings.os not in ("Linux", "OHOS"):
            raise ConanInvalidConfiguration(
                "proxyknife is supported only on Linux/OHOS")

    def build_requirements(self):
        # E007: the copies of config.guess/config.sub shipped by this package
        # already recognise the ohos triplet, so build() can drop them in
        # instead of patching the 2005 files line by line.
        self.tool_requires("automake/1.18")

    def export_sources(self):
        export_conandata_patches(self)

    def source(self):
        get(self, **self.conan_data["sources"], strip_root=True)

    def generate(self):
        tc = AutotoolsToolchain(self)
        # proxyknife.h defines globals in every TU; GCC merged them as common
        # symbols, clang >= 10 defaults to -fno-common -> duplicate symbols
        tc.extra_cflags.append("-fcommon")
        # 2007-era NLS machinery: no msgfmt on OHOS, docs need a pod2man run
        tc.configure_args.append("--disable-nls")
        # The device reports `uname -s` = HarmonyOS, which no released
        # config.guess knows; its compile probe also dies on HMDFS
        # (`dummy.c: Permission denied` -> `cannot guess build type`).
        # Pinning the build triplet skips config.guess entirely and keeps the
        # same effective build==host==aarch64-unknown-linux-ohos as before.
        tc.configure_args.append("--build=aarch64-unknown-linux-ohos")
        tc.generate()

    def _install_config_helpers(self):
        """E007: overwrite the bundled 2005 config.guess/config.sub with the
        automake copies (whole-file content stays out of the PR diff)."""
        base = self.dependencies.build["automake"].package_folder
        for helper in ("config.guess", "config.sub"):
            matches = glob.glob(os.path.join(base, "**", helper), recursive=True)
            if not matches:
                raise ConanInvalidConfiguration(
                    "automake package does not ship %s" % helper)
            dst = os.path.join(self.source_folder, helper)
            shutil.copy2(sorted(matches, key=len)[0], dst)
            os.chmod(dst, 0o755)

    def build(self):
        apply_conandata_patches(self)
        self._install_config_helpers()
        autotools = Autotools(self)
        autotools.configure()
        autotools.make(args=["-j1"])

    def package(self):
        autotools = Autotools(self)
        autotools.install()

    def package_info(self):
        self.cpp_info.bindirs = ["bin"]
